from app.models import Lot, User
from app.services import haversine_km


def buyer_trust(user: User) -> dict:
    score = (
        0.45 * user.on_time_payment_pct
        + 0.35 * user.quality_accept_pct
        + 0.20 * max(0, 100 - user.dispute_count * 12)
    )
    return {
        "buyer_id": user.id,
        "name": user.name,
        "district": user.district,
        "verified": user.verified,
        "trust_score": round(score, 1),
        "on_time_payment_pct": user.on_time_payment_pct,
        "quality_accept_pct": user.quality_accept_pct,
        "dispute_count": user.dispute_count,
    }


def match_buyers(lot: Lot, buyers: list[User], radius_km: float = 250) -> list[dict]:
    out = []
    for b in buyers:
        dist = haversine_km(lot.geo_lat, lot.geo_lng, b.geo_lat, b.geo_lng)
        if dist > radius_km:
            continue
        card = buyer_trust(b)
        card["distance_km"] = round(dist, 1)
        card["match_reason"] = f"{lot.commodity.title()} within {int(dist)} km · grade {lot.grade}"
        out.append(card)
    out.sort(key=lambda x: (-x["trust_score"], x["distance_km"]))
    return out
