from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Dispute, Transaction, User
from app.schemas import DisputeCreate
from app.services import haversine_km
from app.models import ColdStorage, Lot

router = APIRouter(tags=["transactions"])


def txn_out(t: Transaction) -> dict:
    lot = t.offer.lot if t.offer else None
    return {
        "id": t.id,
        "offer_id": t.offer_id,
        "escrow_status": t.escrow_status,
        "amount": t.amount,
        "payment_ref": t.payment_ref,
        "delivery_confirmed_at": t.delivery_confirmed_at.isoformat() if t.delivery_confirmed_at else None,
        "commodity": lot.commodity if lot else None,
        "quantity_kg": lot.quantity_kg if lot else None,
        "buyer_name": t.offer.buyer.name if t.offer and t.offer.buyer else None,
        "farmer_name": lot.farmer.name if lot and lot.farmer else None,
        "created_at": t.created_at.isoformat(),
        "has_dispute": t.dispute is not None,
    }


@router.get("/transactions")
def list_txns(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Transaction).order_by(Transaction.id.desc()).all()
    if user.role == "admin":
        return [txn_out(t) for t in rows]
    out = []
    for t in rows:
        lot = t.offer.lot
        if user.role == "buyer" and t.offer.buyer_id == user.id:
            out.append(txn_out(t))
        elif user.role == "farmer" and lot.farmer_id == user.id:
            out.append(txn_out(t))
        elif user.role == "fpo" and lot.farmer.fpo_id == user.fpo_id:
            out.append(txn_out(t))
    return out


@router.post("/transactions/{txn_id}/confirm-delivery")
def confirm_delivery(
    txn_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t = db.get(Transaction, txn_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    t.escrow_status = "released"
    t.delivery_confirmed_at = datetime.utcnow()
    t.offer.lot.status = "delivered"
    db.commit()
    return txn_out(t)


@router.post("/disputes")
def open_dispute(
    body: DisputeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t = db.get(Transaction, body.transaction_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    d = Dispute(transaction_id=t.id, reason=body.reason, evidence_url=body.evidence_url, status="open")
    db.add(d)
    t.escrow_status = "disputed"
    db.commit()
    db.refresh(d)
    return {"id": d.id, "status": d.status, "mediation": "FPO manager notified"}


@router.get("/disputes")
def list_disputes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Dispute).order_by(Dispute.id.desc()).all()
    return [
        {
            "id": d.id,
            "transaction_id": d.transaction_id,
            "reason": d.reason,
            "evidence_url": d.evidence_url,
            "status": d.status,
            "created_at": d.created_at.isoformat(),
        }
        for d in rows
    ]


@router.get("/logistics")
def logistics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lots = db.query(Lot).filter(Lot.status.in_(["listed", "offered"])).all()
    stores = db.query(ColdStorage).all()
    pools = []
    used = set()
    for i, a in enumerate(lots):
        if a.id in used:
            continue
        group = [a]
        used.add(a.id)
        for b in lots[i + 1 :]:
            if b.id in used:
                continue
            if haversine_km(a.geo_lat, a.geo_lng, b.geo_lat, b.geo_lng) <= 25 and a.commodity == b.commodity:
                group.append(b)
                used.add(b.id)
        if len(group) >= 1:
            pools.append(
                {
                    "commodity": a.commodity,
                    "hub": a.location_name,
                    "lots": [
                        {"id": l.id, "qty": l.quantity_kg, "farmer": l.farmer.name if l.farmer else ""}
                        for l in group
                    ],
                    "total_kg": sum(l.quantity_kg for l in group),
                    "suggested_vehicle": "Mini-truck (Tata Ace)" if sum(l.quantity_kg for l in group) < 800 else "10-tyre truck",
                    "est_cost_share_inr": round(1800 / max(1, len(group)), 0),
                }
            )
    return {
        "pools": pools,
        "cold_storage": [
            {
                "id": s.id,
                "name": s.name,
                "district": s.district,
                "available_mt": s.available_mt,
                "cost_per_kg_day": s.cost_per_kg_day,
            }
            for s in stores
        ],
    }
