from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Lot, User
from app.schemas import LotCreate
from app.services import parse_voice
from app.services.qr import lot_certificate_qr

router = APIRouter(tags=["lots"])


def lot_out(lot: Lot) -> dict:
    return {
        "id": lot.id,
        "farmer_id": lot.farmer_id,
        "farmer_name": lot.farmer.name if lot.farmer else None,
        "commodity": lot.commodity,
        "quantity_kg": lot.quantity_kg,
        "grade": lot.grade,
        "harvest_date": lot.harvest_date.isoformat(),
        "geo_lat": lot.geo_lat,
        "geo_lng": lot.geo_lng,
        "location_name": lot.location_name,
        "status": lot.status,
        "qr_code": lot.qr_code,
        "created_via_voice": lot.created_via_voice,
        "voice_original": lot.voice_original,
        "liquidity_urgency": lot.liquidity_urgency,
        "created_at": lot.created_at.isoformat(),
    }


@router.post("/lots/transcribe")
def transcribe(body: LotCreate, user: User = Depends(get_current_user)):
    parsed = parse_voice(body.voice_text or "", body.language or user.language)
    return parsed


@router.post("/lots")
def create_lot(
    body: LotCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("farmer", "fpo")),
):
    parsed = {}
    via_voice = bool(body.voice_text)
    if via_voice:
        parsed = parse_voice(body.voice_text, body.language or user.language)
    commodity = body.commodity or parsed.get("commodity")
    qty = body.quantity_kg or parsed.get("quantity_kg")
    if not commodity or not qty:
        raise HTTPException(400, "Commodity and quantity are required")
    harvest = body.harvest_date
    if harvest is None and parsed.get("harvest_date"):
        harvest = date.fromisoformat(parsed["harvest_date"])
    harvest = harvest or date.today()
    lot = Lot(
        farmer_id=user.id if user.role == "farmer" else user.id,
        commodity=commodity,
        quantity_kg=float(qty),
        grade=body.grade or parsed.get("grade") or "B",
        harvest_date=harvest,
        geo_lat=body.geo_lat or user.geo_lat,
        geo_lng=body.geo_lng or user.geo_lng,
        location_name=body.location_name or parsed.get("location_name") or user.district,
        voice_original=body.voice_text or "",
        created_via_voice=via_voice,
        liquidity_urgency=body.liquidity_urgency or parsed.get("liquidity_urgency") or "medium",
        status="listed",
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    lot.qr_code = lot_certificate_qr(lot.id, lot.commodity, lot.quantity_kg, lot.grade)
    db.commit()
    return lot_out(lot)


@router.get("/lots/mine")
def my_lots(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Lot)
    if user.role == "farmer":
        q = q.filter(Lot.farmer_id == user.id)
    elif user.role == "fpo":
        member_ids = [u.id for u in db.query(User).filter(User.fpo_id == user.fpo_id).all()]
        q = q.filter(Lot.farmer_id.in_(member_ids or [user.id]))
    elif user.role == "buyer":
        q = q.filter(Lot.status.in_(["listed", "offered"]))
    lots = q.order_by(Lot.id.desc()).all()
    return [lot_out(l) for l in lots]


@router.get("/lots/{lot_id}")
def get_lot(lot_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(404, "Lot not found")
    return lot_out(lot)
