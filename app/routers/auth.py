from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DEMO_OTP, OTP_TTL_SECONDS
from app.database import get_db
from app.deps import create_token, get_current_user
from app.models import OtpCode, User
from app.schemas import LanguageUpdate, OTPRequest, OTPVerify

router = APIRouter(prefix="/auth", tags=["auth"])


def user_public(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "phone": u.phone,
        "role": u.role,
        "language": u.language,
        "trust_score": u.trust_score,
        "district": u.district,
        "fpo_id": u.fpo_id,
        "geo_lat": u.geo_lat,
        "geo_lng": u.geo_lng,
    }


@router.post("/otp/request")
def request_otp(body: OTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == body.phone).first()
    if not user:
        raise HTTPException(404, "Phone not registered. Demo: 9876543210 farmer, 3211 FPO, 3212 buyer, 3213 admin.")
    otp = OtpCode(
        phone=body.phone,
        code=DEMO_OTP,
        expires_at=datetime.utcnow() + timedelta(seconds=OTP_TTL_SECONDS),
    )
    db.add(otp)
    db.commit()
    return {
        "ok": True,
        "message": "OTP sent (mocked). Use 123456 for MVP.",
        "demo_otp": DEMO_OTP,
        "expires_in": OTP_TTL_SECONDS,
        "user_hint": user.name,
    }


@router.post("/otp/verify")
def verify_otp(body: OTPVerify, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == body.phone).first()
    if not user:
        raise HTTPException(404, "Unknown phone")
    if body.code != DEMO_OTP:
        row = (
            db.query(OtpCode)
            .filter(OtpCode.phone == body.phone, OtpCode.code == body.code, OtpCode.used.is_(False))
            .order_by(OtpCode.id.desc())
            .first()
        )
        if not row or row.expires_at < datetime.utcnow():
            raise HTTPException(400, "Invalid or expired OTP")
        row.used = True
        db.commit()
    token = create_token(user)
    return {"access_token": token, "token_type": "bearer", "user": user_public(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_public(user)


@router.post("/language")
def set_language(body: LanguageUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.language not in ("mr", "hi", "en"):
        raise HTTPException(400, "Unsupported language")
    user.language = body.language
    db.commit()
    return user_public(user)


@router.post("/logout")
def logout():
    return {"ok": True, "message": "Client should discard JWT."}
