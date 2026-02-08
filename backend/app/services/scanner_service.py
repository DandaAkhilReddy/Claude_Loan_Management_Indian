"""Azure Document Intelligence integration using Layout model.

Uses Layout model (NOT prebuilt-bankStatement.us which is US-only).
Extracts tables + text and post-processes with regex for Indian and US banks.
"""

import re
import time
import asyncio
import logging
from dataclasses import dataclass

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential

from app.config import settings

logger = logging.getLogger(__name__)


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
    """Azure Document Intelligence scanner for loan documents."""

    def __init__(self):
        if settings.azure_doc_intel_endpoint and settings.azure_doc_intel_key:
            self.client = DocumentIntelligenceClient(
                endpoint=settings.azure_doc_intel_endpoint,
                credential=AzureKeyCredential(settings.azure_doc_intel_key),
            )
        else:
            self.client = None
            logger.warning("Azure Document Intelligence not configured")

    async def analyze_document(self, document_url: str, country: str = "IN") -> list[ExtractedField]:
        """Analyze a document using Azure Layout model.

        Args:
            document_url: Azure Blob URL or SAS URL to the document
            country: 'IN' or 'US' for pattern selection

        Returns:
            List of extracted fields with confidence scores
        """
        if not self.client:
            raise RuntimeError("Azure Document Intelligence not configured")

        start_time = time.time()

        poller = await asyncio.to_thread(
            self.client.begin_analyze_document,
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
        """Analyze a document from raw bytes."""
        if not self.client:
            raise RuntimeError("Azure Document Intelligence not configured")

        start_time = time.time()

        poller = await asyncio.to_thread(
            self.client.begin_analyze_document,
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
