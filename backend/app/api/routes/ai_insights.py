"""AI insights routes — explanations, RAG Q&A, TTS."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.models import User
from app.db.repositories.loan_repo import LoanRepository
from app.db.repositories.embedding_repo import EmbeddingRepository
from app.services.ai_service import AIService
from app.services.embedding_service import EmbeddingService
from app.services.translator_service import TranslatorService
from app.services.tts_service import TTSService

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ExplainLoanRequest(BaseModel):
    loan_id: str


class ExplainStrategyRequest(BaseModel):
    strategy_name: str
    num_loans: int
    extra: float
    interest_saved: float
    months_saved: int
    payoff_order: list[str]


class AskRequest(BaseModel):
    question: str


class TTSRequest(BaseModel):
    text: str
    language: str = "en"


class AIResponse(BaseModel):
    text: str
    language: str


class TTSResponse(BaseModel):
    audio_base64: str | None
    language: str


@router.post("/explain-loan", response_model=AIResponse)
async def explain_loan(
    req: ExplainLoanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI explanation of a loan."""
    from uuid import UUID
    repo = LoanRepository(db)
    loan = await repo.get_by_id(UUID(req.loan_id), user.id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    ai = AIService()
    explanation = await ai.explain_loan(
        bank_name=loan.bank_name,
        loan_type=loan.loan_type,
        principal=float(loan.principal_amount),
        outstanding=float(loan.outstanding_principal),
        rate=float(loan.interest_rate),
        rate_type=loan.interest_rate_type,
        emi=float(loan.emi_amount),
        remaining_months=loan.remaining_tenure_months,
    )

    # Translate if user prefers non-English
    lang = user.preferred_language
    if lang != "en":
        translator = TranslatorService()
        explanation = await translator.translate(explanation, lang)

    return AIResponse(text=explanation, language=lang)


@router.post("/explain-strategy", response_model=AIResponse)
async def explain_strategy(
    req: ExplainStrategyRequest,
    user: User = Depends(get_current_user),
):
    """Generate AI explanation of optimizer strategy."""
    ai = AIService()
    explanation = await ai.explain_strategy(
        strategy_name=req.strategy_name,
        num_loans=req.num_loans,
        extra=req.extra,
        interest_saved=req.interest_saved,
        months_saved=req.months_saved,
        payoff_order=req.payoff_order,
    )

    lang = user.preferred_language
    if lang != "en":
        translator = TranslatorService()
        explanation = await translator.translate(explanation, lang)

    return AIResponse(text=explanation, language=lang)


@router.post("/ask", response_model=AIResponse)
async def ask(
    req: AskRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG-powered Q&A about loans and RBI rules."""
    embedding_svc = EmbeddingService()
    query_embedding = await embedding_svc.generate_embedding(req.question)

    embed_repo = EmbeddingRepository(db)
    results = await embed_repo.similarity_search(query_embedding, limit=3)
    context_chunks = [r.chunk_text for r in results]

    ai = AIService()
    answer = await ai.ask_with_context(req.question, context_chunks)

    lang = user.preferred_language
    if lang != "en":
        translator = TranslatorService()
        answer = await translator.translate(answer, lang)

    return AIResponse(text=answer, language=lang)


@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    req: TTSRequest,
    user: User = Depends(get_current_user),
):
    """Generate TTS audio for AI explanation text."""
    tts = TTSService()
    audio = await tts.generate_audio(req.text, req.language)
    return TTSResponse(audio_base64=audio, language=req.language)
