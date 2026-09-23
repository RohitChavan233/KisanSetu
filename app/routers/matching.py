from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Lot, User
from app.services.matching import match_buyers

router = APIRouter(tags=["matching"])


@router.get("/buyers/matches")
def matches(
    lot_id: int = Query(...),
    radius_km: float = Query(250),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(404, "Lot not found")
    buyers = db.query(User).filter(User.role == "buyer", User.verified.is_(True)).all()
    return match_buyers(lot, buyers, radius_km)
