from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Lot, Offer, Transaction, User
from app.schemas import OfferCounter, OfferCreate

router = APIRouter(tags=["offers"])


def offer_out(o: Offer) -> dict:
    return {
        "id": o.id,
        "lot_id": o.lot_id,
        "buyer_id": o.buyer_id,
        "buyer_name": o.buyer.name if o.buyer else None,
        "commodity": o.lot.commodity if o.lot else None,
        "quantity_kg": o.lot.quantity_kg if o.lot else None,
        "price_offered": o.price_offered,
        "status": o.status,
        "created_at": o.created_at.isoformat(),
        "farmer_id": o.lot.farmer_id if o.lot else None,
        "unit": "Rs/quintal",
    }


@router.post("/offers")
def place_offer(
    body: OfferCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("buyer")),
):
    lot = db.get(Lot, body.lot_id)
    if not lot or lot.status not in ("listed", "offered"):
        raise HTTPException(400, "Lot is not open for offers")
    offer = Offer(lot_id=lot.id, buyer_id=user.id, price_offered=body.price_offered, status="pending")
    lot.status = "offered"
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer_out(offer)


@router.get("/offers")
def list_offers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Offer)
    if user.role == "buyer":
        q = q.filter(Offer.buyer_id == user.id)
    elif user.role in ("farmer", "fpo"):
        lot_ids = [l.id for l in db.query(Lot).filter(Lot.farmer_id == user.id).all()]
        if user.role == "fpo":
            members = [u.id for u in db.query(User).filter(User.fpo_id == user.fpo_id).all()]
            lot_ids = [l.id for l in db.query(Lot).filter(Lot.farmer_id.in_(members)).all()]
        q = q.filter(Offer.lot_id.in_(lot_ids or [0]))
    return [offer_out(o) for o in q.order_by(Offer.id.desc()).all()]


@router.post("/offers/{offer_id}/accept")
def accept_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("farmer", "fpo")),
):
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer.status = "accepted"
    offer.lot.status = "sold"
    for other in db.query(Offer).filter(Offer.lot_id == offer.lot_id, Offer.id != offer.id).all():
        other.status = "rejected"
    amount = (offer.lot.quantity_kg / 100.0) * offer.price_offered
    txn = Transaction(
        offer_id=offer.id,
        escrow_status="held",
        amount=round(amount, 2),
        payment_ref=f"UPI-ESCROW-{offer.id:05d}",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return {"offer": offer_out(offer), "transaction_id": txn.id, "escrow_status": txn.escrow_status, "amount": txn.amount}


@router.post("/offers/{offer_id}/reject")
def reject_offer(offer_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("farmer", "fpo"))):
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer.status = "rejected"
    db.commit()
    return offer_out(offer)


@router.post("/offers/{offer_id}/counter")
def counter(
    offer_id: int,
    body: OfferCounter,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("farmer", "fpo")),
):
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer.price_offered = body.price_offered
    offer.status = "countered"
    db.commit()
    return offer_out(offer)
