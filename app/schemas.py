from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class OTPRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=15)
    role: Optional[str] = None


class OTPVerify(BaseModel):
    phone: str
    code: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class LotCreate(BaseModel):
    commodity: Optional[str] = None
    quantity_kg: Optional[float] = None
    grade: Optional[str] = "B"
    harvest_date: Optional[date] = None
    geo_lat: Optional[float] = None
    geo_lng: Optional[float] = None
    location_name: Optional[str] = "Nashik"
    voice_text: Optional[str] = None
    language: Optional[str] = "en"
    liquidity_urgency: Optional[str] = "medium"


class OfferCreate(BaseModel):
    lot_id: int
    price_offered: float


class OfferCounter(BaseModel):
    price_offered: float


class DisputeCreate(BaseModel):
    transaction_id: int
    reason: str
    evidence_url: str = ""


class AlertCreate(BaseModel):
    commodity: str
    mandi: str
    threshold: float
    direction: str = "above"


class LanguageUpdate(BaseModel):
    language: str
