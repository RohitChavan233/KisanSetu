from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), index=True)
    language: Mapped[str] = mapped_column(String(8), default="mr")
    trust_score: Mapped[float] = mapped_column(Float, default=70.0)
    district: Mapped[str] = mapped_column(String(80), default="Nashik")
    geo_lat: Mapped[float] = mapped_column(Float, default=19.9975)
    geo_lng: Mapped[float] = mapped_column(Float, default=73.7898)
    fpo_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("fpos.id"), nullable=True)
    on_time_payment_pct: Mapped[float] = mapped_column(Float, default=0.0)
    quality_accept_pct: Mapped[float] = mapped_column(Float, default=0.0)
    dispute_count: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fpo = relationship("FPO", back_populates="members")
    lots = relationship("Lot", back_populates="farmer")
    offers = relationship("Offer", back_populates="buyer")


class FPO(Base):
    __tablename__ = "fpos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    registration_no: Mapped[str] = mapped_column(String(80), unique=True)
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    district: Mapped[str] = mapped_column(String(80), default="Nashik")

    members = relationship("User", back_populates="fpo")


class Lot(Base):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farmer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    commodity: Mapped[str] = mapped_column(String(40), index=True)
    quantity_kg: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(8), default="B")
    harvest_date: Mapped[datetime] = mapped_column(Date)
    geo_lat: Mapped[float] = mapped_column(Float)
    geo_lng: Mapped[float] = mapped_column(Float)
    location_name: Mapped[str] = mapped_column(String(80), default="Nashik")
    status: Mapped[str] = mapped_column(String(24), default="listed")
    qr_code: Mapped[str] = mapped_column(Text, default="")
    voice_original: Mapped[str] = mapped_column(Text, default="")
    created_via_voice: Mapped[bool] = mapped_column(Boolean, default=False)
    liquidity_urgency: Mapped[str] = mapped_column(String(16), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    farmer = relationship("User", back_populates="lots")
    offers = relationship("Offer", back_populates="lot")


class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commodity: Mapped[str] = mapped_column(String(40), index=True)
    mandi: Mapped[str] = mapped_column(String(80), index=True)
    date: Mapped[datetime] = mapped_column(Date, index=True)
    min_price: Mapped[float] = mapped_column(Float)
    max_price: Mapped[float] = mapped_column(Float)
    modal_price: Mapped[float] = mapped_column(Float)
    arrival_volume: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(40), default="AGMARKNET")


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commodity: Mapped[str] = mapped_column(String(40), index=True)
    mandi: Mapped[str] = mapped_column(String(80), index=True)
    horizon_days: Mapped[int] = mapped_column(Integer)
    predicted_price: Mapped[float] = mapped_column(Float)
    confidence_low: Mapped[float] = mapped_column(Float)
    confidence_high: Mapped[float] = mapped_column(Float)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(Integer, ForeignKey("lots.id"))
    buyer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    price_offered: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lot = relationship("Lot", back_populates="offers")
    buyer = relationship("User", back_populates="offers")
    transaction = relationship("Transaction", back_populates="offer", uselist=False)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(Integer, ForeignKey("offers.id"))
    escrow_status: Mapped[str] = mapped_column(String(24), default="held")
    amount: Mapped[float] = mapped_column(Float)
    payment_ref: Mapped[str] = mapped_column(String(80), default="")
    delivery_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer = relationship("Offer", back_populates="transaction")
    dispute = relationship("Dispute", back_populates="transaction", uselist=False)


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.id"))
    reason: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="dispute")


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    commodity: Mapped[str] = mapped_column(String(40))
    mandi: Mapped[str] = mapped_column(String(80))
    threshold: Mapped[float] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(8), default="above")
    triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ColdStorage(Base):
    __tablename__ = "cold_storage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    district: Mapped[str] = mapped_column(String(80))
    available_mt: Mapped[float] = mapped_column(Float)
    cost_per_kg_day: Mapped[float] = mapped_column(Float)
    geo_lat: Mapped[float] = mapped_column(Float)
    geo_lng: Mapped[float] = mapped_column(Float)


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(15), index=True)
    code: Mapped[str] = mapped_column(String(8))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
