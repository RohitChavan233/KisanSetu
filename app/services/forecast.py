from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from math import sqrt
from statistics import mean, pstdev

from sqlalchemy.orm import Session

from app.models import Forecast, PriceRecord


def _rows(db: Session, commodity: str, mandi: str) -> list[PriceRecord]:
    return (
        db.query(PriceRecord)
        .filter(PriceRecord.commodity == commodity, PriceRecord.mandi == mandi)
        .order_by(PriceRecord.date.asc())
        .all()
    )


def _quantile(vals: list[float], q: float) -> float:
    if not vals:
        return 0.0
    xs = sorted(vals)
    i = max(0, min(len(xs) - 1, int(q * (len(xs) - 1))))
    return xs[i]


def forecast(db: Session, commodity: str, mandi: str, horizon: int = 14) -> dict:
    recs = _rows(db, commodity, mandi)
    if not recs:
        raise ValueError("No price history")
    series = [r.modal_price for r in recs]
    last = recs[-1]
    current = last.modal_price
    diffs = [series[i] - series[i - 1] for i in range(1, len(series))]
    drift = mean(diffs[-14:]) if len(diffs) >= 2 else 0.0
    vol = pstdev(diffs[-21:]) if len(diffs) >= 5 else current * 0.04
    # Seasonal weekly echo (same weekday 7 days ago)
    weekly = 0.0
    if len(series) >= 8:
        weekly = (series[-1] - series[-8]) / 7.0
    step = 0.55 * drift + 0.45 * weekly
    points = []
    price = current
    for h in range(1, horizon + 1):
        price = max(1.0, price + step)
        band = 1.28 * vol * sqrt(h)  # ~80% interval
        nxt = last.date + timedelta(days=h)
        points.append(
            {
                "day": h,
                "date": nxt.isoformat(),
                "predicted": round(price, 2),
                "low": round(max(1.0, price - band), 2),
                "high": round(price + band, 2),
            }
        )
    target = points[-1]
    db.add(
        Forecast(
            commodity=commodity,
            mandi=mandi,
            horizon_days=horizon,
            predicted_price=target["predicted"],
            confidence_low=target["low"],
            confidence_high=target["high"],
        )
    )
    db.commit()
    return {
        "commodity": commodity,
        "mandi": mandi,
        "current_modal": round(current, 2),
        "min_price": last.min_price,
        "max_price": last.max_price,
        "arrival_volume": last.arrival_volume,
        "as_of": last.date.isoformat(),
        "trend_7": [{"date": recs[i].date.isoformat(), "modal": recs[i].modal_price} for i in range(-min(7, len(recs)), 0)],
        "history_30": [
            {
                "date": r.date.isoformat(),
                "min": r.min_price,
                "max": r.max_price,
                "modal": r.modal_price,
                "arrival": r.arrival_volume,
            }
            for r in recs[-30:]
        ],
        "horizon_days": horizon,
        "forecast": points,
        "model": "seasonal-drift quantile baseline (XGBoost-ready adapter)",
    }


def latest_by_commodity(db: Session) -> dict[str, list[dict]]:
    grouped: dict[str, list] = defaultdict(list)
    recs = db.query(PriceRecord).order_by(PriceRecord.date.desc()).all()
    seen = set()
    for r in recs:
        key = (r.commodity, r.mandi)
        if key in seen:
            continue
        seen.add(key)
        grouped[r.commodity].append(
            {
                "mandi": r.mandi,
                "date": r.date.isoformat(),
                "min": r.min_price,
                "max": r.max_price,
                "modal": r.modal_price,
                "arrival": r.arrival_volume,
            }
        )
    return grouped
