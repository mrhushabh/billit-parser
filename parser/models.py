from pydantic import BaseModel
from enum import Enum
from typing import Optional


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class ValidationStatus(str, Enum):
    valid = "valid"
    mismatch = "mismatch"
    incomplete = "incomplete"


class ParsedItem(BaseModel):
    name: str
    unit_price: float
    quantity: int
    line_total: float
    confidence: Confidence
    raw_text: str


class ParsedReceipt(BaseModel):
    merchant: Optional[str] = None
    items: list[ParsedItem] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tip: Optional[float] = None
    total: Optional[float] = None
    validation_status: ValidationStatus
    # Only present when validation_status == mismatch
    mismatch_item_sum: Optional[float] = None
    mismatch_claimed_subtotal: Optional[float] = None


class ParseRequest(BaseModel):
    # Raw text lines from iOS Vision OCR, top-to-bottom order
    lines: list[str]
