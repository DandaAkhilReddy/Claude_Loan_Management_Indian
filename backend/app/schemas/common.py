"""Common Pydantic v2 schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class ErrorResponse(BaseModel):
    detail: str
    status_code: int = 400


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int = 1
    page_size: int = 20


class MessageResponse(BaseModel):
    message: str
