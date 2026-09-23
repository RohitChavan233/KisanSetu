from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ColdStorage, PriceAlert, PriceRecord, User
from app.schemas import AlertCreate
from app.services.forecast import forecast as run_forecast
from app.services.forecast import latest_by_commodity
from app.services.recommend import sell_now_vs_store

router = APIRouter(tags=["prices"])


@router.get("/prices/{commodity}")
def get_prices(commodity: str, mandi: str = Query("Nashik"), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rec = (
        db.query(PriceRecord)
        .filter(PriceRecord.commodity == commodity, PriceRecord.mandi == mandi)
        .order_by(PriceRecord.date.desc())
        .first()
    )
    if not rec:
        raise HTTPException(404, "No prices for this mandi/commodity")
    hist = (
        db.query(PriceRecord)
        .filter(PriceRecord.commodity == commodity, PriceRecord.mandi == mandi)
        .order_by(PriceRecord.date.desc())
        .limit(30)
        .all()
    )
    return {
        "commodity": commodity,
        "mandi": mandi,
        "date": rec.date.isoformat(),
        "min_price": rec.min_price,
        "max_price": rec.max_price,
        "modal_price": rec.modal_price,
        "arrival_volume": rec.arrival_volume,
        "source": rec.source,
        "trend_7": [
            {"date": r.date.isoformat(), "modal": r.modal_price}
            for r in sorted(hist[:7], key=lambda x: x.date)
        ],
        "history": [
            {"date": r.date.isoformat(), "min": r.min_price, "max": r.max_price, "modal": r.modal_price}
            for r in sorted(hist, key=lambda x: x.date)
        ],
    }


@router.get("/prices")
def board(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return latest_by_commodity(db)


@router.get("/forecast/{commodity}")
def get_forecast(
    commodity: str,
    mandi: str = Query("Nashik"),
    horizon: int = Query(14, ge=7, le=21),
    urgency: str = Query("medium"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        data = run_forecast(db, commodity, mandi, horizon)
    except ValueError as e:
        raise HTTPException(404, str(e))
    store = (
        db.query(ColdStorage)
        .filter(ColdStorage.district == mandi)
        .first()
    )
    cost = store.cost_per_kg_day if store else 0.35
    last = data["forecast"][-1]
    data["recommendation"] = sell_now_vs_store(
        current=data["current_modal"],
        predicted=last["predicted"],
        low=last["low"],
        high=last["high"],
        storage_cost_per_kg_day=cost,
        horizon_days=horizon,
        urgency=urgency,
    )
    data["cold_storage"] = (
        {
            "name": store.name,
            "available_mt": store.available_mt,
            "cost_per_kg_day": store.cost_per_kg_day,
        }
        if store
        else None
    )
    return data


@router.post("/alerts")
def create_alert(body: AlertCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = PriceAlert(
        user_id=user.id,
        commodity=body.commodity,
        mandi=body.mandi,
        threshold=body.threshold,
        direction=body.direction,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": "armed"}


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    latest = latest_by_commodity(db)
    rows = db.query(PriceAlert).filter(PriceAlert.user_id == user.id).all()
    out = []
    for a in rows:
        modal = None
        for m in latest.get(a.commodity, []):
            if m["mandi"] == a.mandi:
                modal = m["modal"]
        triggered = False
        if modal is not None:
            triggered = modal >= a.threshold if a.direction == "above" else modal <= a.threshold
            if triggered:
                a.triggered = True
        out.append(
            {
                "id": a.id,
                "commodity": a.commodity,
                "mandi": a.mandi,
                "threshold": a.threshold,
                "direction": a.direction,
                "current": modal,
                "triggered": triggered,
                "channel": "in-app (SMS/push in production)",
            }
        )
    db.commit()
    return out
