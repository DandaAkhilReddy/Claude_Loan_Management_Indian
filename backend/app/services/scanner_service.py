"""Document scanner: GPT-4o Vision (primary) + Azure Doc Intel regex (fallback).

Primary: Sends images directly to GPT-4o-mini Vision for structured extraction.
Fallback: Azure Document Intelligence Layout model + regex patterns.
PDFs: Azure Doc Intel extracts text → GPT-4o-mini analyzes text.
"""

import re
import json
import time
import base64
import asyncio
import logging
from dataclasses import dataclass

from openai import AsyncAzureOpenAI
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential

from app.config import settings

logger = logging.getLogger(__name__)

# ---------- GPT-4o Vision prompts ----------

EXTRACTION_SYSTEM_PROMPT = """You are a document analysis AI that extracts loan/financial details from documents.
Extract whatever financial information you can find. Return a JSON object with these fields:
- bank_name: The bank or financial institution name (e.g., "SBI", "HDFC", "Chase")
- loan_type: One of: home, personal, car, education, gold, credit_card, business (best guess)
- principal_amount: The loan principal/sanctioned amount as a plain number string without commas or currency symbols (e.g., "2500000")
- interest_rate: Annual interest rate as a number string (e.g., "8.5")
- emi_amount: Monthly EMI/installment as a plain number string without commas (e.g., "21000")
- tenure_months: Loan tenure in months as a number string (e.g., "240"). Convert years to months if needed.
- account_number: Loan or account number if visible

Rules:
- Return "" (empty string) for any field you cannot find in the document.
- Only return values you are confident about from the document content.
- Remove currency symbols (₹, $, etc.) and commas from amounts.
- If the document is not a loan/financial document, still try to extract any financial amounts visible.
- Always return valid JSON."""

EXTRACTION_USER_PROMPT = "Extract all loan and financial details from this document."


@dataclass
class ExtractedField:
    field_name: str
    value: str
    confidence: float


# ---------- Indian patterns ----------

PATTERNS_IN = {
    "principal": [
        r"(?:loan|principal|sanctioned)\s*(?:amount|amt)?\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d{2})?)",
        r"₹\s*([\d,]+(?:\.\d{2})?)\s*(?:lakhs?|lacs?|crores?)?",
    ],
    "interest_rate": [
        r"(?:rate\s*of\s*interest|roi|interest\s*rate)\s*[:\-]?\s*([\d]+\.?\d*)\s*%",
        r"([\d]+\.?\d*)\s*%\s*(?:p\.?a\.?|per\s*annum)",
    ],
    "emi_amount": [
        r"(?:emi|equated\s*monthly\s*installment)\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d{2})?)",
        r"monthly\s*(?:installment|payment)\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d{2})?)",
    ],
    "tenure": [
        r"(?:tenure|term|period)\s*[:\-]?\s*(\d+)\s*(?:months?|yrs?|years?)",
        r"(\d+)\s*(?:months?|yrs?|years?)\s*(?:tenure|term)",
    ],
    "bank_name": [
        r"(state\s*bank\s*of\s*india|sbi)",
        r"(hdfc\s*(?:bank|ltd)?)",
        r"(icici\s*(?:bank|ltd)?)",
        r"(axis\s*(?:bank|ltd)?)",
        r"(punjab\s*national\s*bank|pnb)",
        r"(bank\s*of\s*baroda|bob)",
        r"(kotak\s*mahindra\s*(?:bank)?)",
        r"(canara\s*bank)",
        r"(union\s*bank)",
        r"(bajaj\s*(?:finance|finserv))",
    ],
    "loan_type": [
        r"(home\s*loan|housing\s*loan|mortgage)",
        r"(personal\s*loan|consumer\s*loan)",
        r"(car\s*loan|auto\s*loan|vehicle\s*loan)",
        r"(education\s*loan|student\s*loan)",
        r"(gold\s*loan)",
        r"(credit\s*card)",
    ],
    "account_number": [
        r"(?:a/c|account|loan)\s*(?:no|number|#)\s*[:\-]?\s*(\d{10,20})",
    ],
}

BANK_NORMALIZER_IN = {
    "state bank of india": "SBI", "sbi": "SBI",
    "hdfc bank": "HDFC", "hdfc ltd": "HDFC", "hdfc": "HDFC",
    "icici bank": "ICICI", "icici ltd": "ICICI", "icici": "ICICI",
    "axis bank": "AXIS", "axis ltd": "AXIS", "axis": "AXIS",
    "punjab national bank": "PNB", "pnb": "PNB",
    "bank of baroda": "BOB", "bob": "BOB",
    "kotak mahindra bank": "KOTAK", "kotak mahindra": "KOTAK", "kotak": "KOTAK",
    "canara bank": "CANARA",
    "union bank": "UNION",
    "bajaj finance": "BAJAJ", "bajaj finserv": "BAJAJ",
}

# ---------- US patterns ----------

PATTERNS_US = {
    "principal": [
        r"(?:loan|principal|original)\s*(?:amount|balance)?\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
        r"\$\s*([\d,]+(?:\.\d{2})?)",
    ],
    "interest_rate": [
        r"(?:interest\s*rate|apr|rate)\s*[:\-]?\s*([\d]+\.?\d*)\s*%",
        r"([\d]+\.?\d*)\s*%\s*(?:apr|annual|per\s*(?:year|annum))",
    ],
    "emi_amount": [
        r"(?:monthly\s*payment|payment\s*amount|installment)\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
    ],
    "tenure": [
        r"(?:term|tenure|period|duration)\s*[:\-]?\s*(\d+)\s*(?:months?|yrs?|years?)",
        r"(\d+)\s*(?:year|yr)\s*(?:term|mortgage|loan)",
    ],
    "bank_name": [
        r"(chase|jpmorgan\s*chase)",
        r"(bank\s*of\s*america|bofa|boa)",
        r"(wells\s*fargo)",
        r"(citi(?:bank)?)",
        r"(u\.?s\.?\s*bank)",
        r"(pnc\s*(?:bank|financial)?)",
        r"(capital\s*one)",
        r"(td\s*bank)",
        r"(ally\s*(?:bank|financial)?)",
        r"(sofi)",
    ],
    "loan_type": [
        r"(home\s*loan|mortgage|housing\s*loan)",
        r"(personal\s*loan|consumer\s*loan)",
        r"(car\s*loan|auto\s*loan|vehicle\s*loan)",
        r"(education\s*loan|student\s*loan)",
        r"(business\s*loan|sba\s*loan|commercial\s*loan)",
        r"(credit\s*card)",
    ],
    "account_number": [
        r"(?:account|loan)\s*(?:no|number|#)\s*[:\-]?\s*(\d{8,20})",
    ],
}

BANK_NORMALIZER_US = {
    "chase": "Chase", "jpmorgan chase": "Chase",
    "bank of america": "Bank of America", "bofa": "Bank of America", "boa": "Bank of America",
    "wells fargo": "Wells Fargo",
    "citi": "Citi", "citibank": "Citi",
    "u.s. bank": "US Bank", "us bank": "US Bank",
    "pnc": "PNC", "pnc bank": "PNC", "pnc financial": "PNC",
    "capital one": "Capital One",
    "td bank": "TD Bank",
    "ally": "Ally", "ally bank": "Ally", "ally financial": "Ally",
    "sofi": "SoFi",
}

LOAN_TYPE_NORMALIZER = {
    "home loan": "home", "housing loan": "home", "mortgage": "home",
    "personal loan": "personal", "consumer loan": "personal",
    "car loan": "car", "auto loan": "car", "vehicle loan": "car",
    "education loan": "education", "student loan": "education",
    "gold loan": "gold",
    "credit card": "credit_card",
    "business loan": "business", "sba loan": "business", "commercial loan": "business",
}


def _clean_amount(value: str) -> str:
    """Remove commas and normalize amount string."""
    return value.replace(",", "").strip()


def _extract_with_patterns(text: str, field: str, patterns: dict) -> tuple[str, float]:
    """Try all patterns for a field, return (value, confidence)."""
    field_patterns = patterns.get(field, [])
    for pattern in field_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            return value, 0.85
    return "", 0.0


class ScannerService:
    """Document scanner: GPT-4o Vision (primary) + Azure Doc Intel regex (fallback)."""

    def __init__(self):
        if settings.azure_doc_intel_endpoint and settings.azure_doc_intel_key:
            self.doc_intel_client = DocumentIntelligenceClient(
                endpoint=settings.azure_doc_intel_endpoint,
                credential=AzureKeyCredential(settings.azure_doc_intel_key),
            )
        else:
            self.doc_intel_client = None
            logger.warning("Azure Document Intelligence not configured")

        if settings.azure_openai_endpoint and settings.azure_openai_key:
            self.ai_client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_key,
                api_version="2024-10-21",
            )
        else:
            self.ai_client = None
            logger.warning("Azure OpenAI not configured — AI extraction unavailable")

    # ---------- Primary: GPT-4o Vision extraction ----------

    async def analyze_with_ai(self, content: bytes, content_type: str) -> list[ExtractedField]:
        """Use GPT-4o Vision to extract loan fields from any document."""
        if not self.ai_client:
            raise RuntimeError("Azure OpenAI not configured")

        start_time = time.time()

        if content_type in ("image/png", "image/jpeg", "image/jpg"):
            # Images: send directly to GPT-4o vision as base64
            b64 = base64.b64encode(content).decode("utf-8")
            messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": EXTRACTION_USER_PROMPT},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{content_type};base64,{b64}",
                    }},
                ]},
            ]
        else:
            # PDFs: extract text with Azure Doc Intel, then send text to GPT-4o
            text = await self._extract_text(content, content_type)
            if not text.strip():
                logger.warning("No text extracted from PDF")
                return []
            messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"{EXTRACTION_USER_PROMPT}\n\nDocument text:\n{text[:4000]}"},
            ]

        response = await self.ai_client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=messages,
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        fields = self._parse_ai_response(raw)

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"AI extraction completed in {elapsed_ms}ms, extracted {len(fields)} fields")
        return fields

    def _parse_ai_response(self, raw_json: str) -> list[ExtractedField]:
        """Parse GPT-4o JSON response into ExtractedField list."""
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response: {raw_json[:200]}")
            return []

        field_map = {
            "bank_name": "bank_name",
            "loan_type": "loan_type",
            "principal_amount": "principal_amount",
            "interest_rate": "interest_rate",
            "emi_amount": "emi_amount",
            "tenure_months": "tenure_months",
            "account_number": "account_number",
        }

        fields = []
        for json_key, field_name in field_map.items():
            value = str(data.get(json_key, "")).strip()
            if value:
                # Clean amounts: remove currency symbols, commas
                if field_name in ("principal_amount", "emi_amount"):
                    value = re.sub(r"[₹$,\s]", "", value)
                if field_name == "interest_rate":
                    value = value.replace("%", "").strip()
                fields.append(ExtractedField(field_name, value, 0.90))
        return fields

    async def _extract_text(self, content: bytes, content_type: str) -> str:
        """Extract raw text from a document using Azure Doc Intel."""
        if not self.doc_intel_client:
            return ""
        poller = await asyncio.to_thread(
            self.doc_intel_client.begin_analyze_document,
            "prebuilt-layout",
            body=content,
            content_type=content_type,
        )
        result = await asyncio.to_thread(poller.result)
        text = result.content or ""
        if result.tables:
            for table in result.tables:
                for cell in table.cells:
                    text += f" {cell.content}"
        return text

    async def analyze_document(self, document_url: str, country: str = "IN") -> list[ExtractedField]:
        """Analyze a document using Azure Layout model.

        Args:
            document_url: Azure Blob URL or SAS URL to the document
            country: 'IN' or 'US' for pattern selection

        Returns:
            List of extracted fields with confidence scores
        """
        if not self.doc_intel_client:
            raise RuntimeError("Azure Document Intelligence not configured")

        start_time = time.time()

        poller = await asyncio.to_thread(
            self.doc_intel_client.begin_analyze_document,
            "prebuilt-layout",
            AnalyzeDocumentRequest(url_source=document_url),
        )
        result = await asyncio.to_thread(poller.result)

        full_text = ""
        if result.content:
            full_text = result.content

        table_text = ""
        if result.tables:
            for table in result.tables:
                for cell in table.cells:
                    table_text += f" {cell.content}"

        combined_text = f"{full_text} {table_text}"

        fields = self._extract_fields(combined_text, country)

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Document analysis completed in {elapsed_ms}ms, extracted {len(fields)} fields")

        return fields

    def _extract_fields(self, text: str, country: str = "IN") -> list[ExtractedField]:
        """Extract loan-related fields from document text."""
        patterns = PATTERNS_IN if country == "IN" else PATTERNS_US
        bank_normalizer = BANK_NORMALIZER_IN if country == "IN" else BANK_NORMALIZER_US

        fields: list[ExtractedField] = []

        # Bank name
        bank_raw, bank_conf = _extract_with_patterns(text, "bank_name", patterns)
        if bank_raw:
            normalized = bank_normalizer.get(bank_raw.lower(), bank_raw.upper())
            fields.append(ExtractedField("bank_name", normalized, bank_conf))

        # Loan type
        type_raw, type_conf = _extract_with_patterns(text, "loan_type", patterns)
        if type_raw:
            normalized = LOAN_TYPE_NORMALIZER.get(type_raw.lower(), "personal")
            fields.append(ExtractedField("loan_type", normalized, type_conf))

        # Principal amount
        principal_raw, principal_conf = _extract_with_patterns(text, "principal", patterns)
        if principal_raw:
            fields.append(ExtractedField("principal_amount", _clean_amount(principal_raw), principal_conf))

        # Interest rate
        rate_raw, rate_conf = _extract_with_patterns(text, "interest_rate", patterns)
        if rate_raw:
            fields.append(ExtractedField("interest_rate", rate_raw, rate_conf))

        # EMI / Monthly payment
        emi_raw, emi_conf = _extract_with_patterns(text, "emi_amount", patterns)
        if emi_raw:
            fields.append(ExtractedField("emi_amount", _clean_amount(emi_raw), emi_conf))

        # Tenure
        tenure_raw, tenure_conf = _extract_with_patterns(text, "tenure", patterns)
        if tenure_raw:
            fields.append(ExtractedField("tenure_months", tenure_raw, tenure_conf))

        # Account number
        acc_raw, acc_conf = _extract_with_patterns(text, "account_number", patterns)
        if acc_raw:
            fields.append(ExtractedField("account_number", acc_raw, acc_conf))

        return fields

    async def analyze_from_bytes(self, content: bytes, content_type: str, country: str = "IN") -> list[ExtractedField]:
        """Analyze a document from raw bytes (regex fallback)."""
        if not self.doc_intel_client:
            raise RuntimeError("Azure Document Intelligence not configured")

        start_time = time.time()

        poller = await asyncio.to_thread(
            self.doc_intel_client.begin_analyze_document,
            "prebuilt-layout",
            body=content,
            content_type=content_type,
        )
        result = await asyncio.to_thread(poller.result)

        full_text = result.content or ""
        table_text = ""
        if result.tables:
            for table in result.tables:
                for cell in table.cells:
                    table_text += f" {cell.content}"

        combined_text = f"{full_text} {table_text}"
        fields = self._extract_fields(combined_text, country)

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Byte analysis completed in {elapsed_ms}ms")

        return fields
