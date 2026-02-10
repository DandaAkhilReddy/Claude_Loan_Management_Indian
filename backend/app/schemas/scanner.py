"""Scanner Pydantic v2 schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: UUID
    loan_id: str | None = None
    status: str = "uploaded"
    message: str = "Document uploaded. Processing will begin shortly."
    error: str | None = None


class ExtractedField(BaseModel):
    field_name: str
    value: str
    confidence: float


class ScanStatusResponse(BaseModel):
    job_id: UUID
    status: str
    extracted_fields: list[ExtractedField] | None = None
    error_message: str | None = None
    processing_time_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfirmScanRequest(BaseModel):
    bank_name: str
    loan_type: str
    principal_amount: float
    outstanding_principal: float
    interest_rate: float
    interest_rate_type: str = "floating"
    tenure_months: int
    remaining_tenure_months: int
    emi_amount: float
    emi_due_date: int | None = None
