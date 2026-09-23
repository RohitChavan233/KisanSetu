from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

from app import models  # noqa: F401  registers all tables
from app.config import COMMODITIES, FRONTEND_DIR, MANDIS
from app.database import Base, SessionLocal, engine
from app.models import PriceRecord
from app.routers import auth, lots, matching, offers, prices, reports, trade
from app.seed import seed_if_empty

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="KisanSetu API",
    version="1.0.0",
    description="Market linkages & price discovery for Maharashtra farmers (SIH26132).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(prices.router)
app.include_router(lots.router)
app.include_router(matching.router)
app.include_router(offers.router)
app.include_router(trade.router)
app.include_router(reports.router)


def _boot():
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


def _tick_prices():
    """Mock AGMARKNET batch sync — nudges today's modal slightly."""
    db = SessionLocal()
    try:
        today = datetime.utcnow().date()
        recs = db.query(PriceRecord).filter(PriceRecord.date == today).all()
        for r in recs:
            r.modal_price = round(r.modal_price * 1.0, 2)
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup():
    _boot()
    sched = BackgroundScheduler()
    sched.add_job(_tick_prices, "interval", hours=6, id="agmarknet-sync")
    sched.start()
    app.state.scheduler = sched


@app.get("/health")
def health():
    return {"ok": True, "service": "kisansetu", "commodities": COMMODITIES, "mandis": MANDIS}


@app.get("/meta")
def meta():
    return {
        "problem": "SIH26132",
        "owner": "Government of Maharashtra (MSInS)",
        "languages": ["mr", "hi", "en"],
        "commodities": COMMODITIES,
        "mandis": MANDIS,
        "demo_phones": {
            "farmer": "9876543210",
            "fpo": "9876543211",
            "buyer": "9876543212",
            "admin": "9876543213",
        },
        "demo_otp": "123456",
    }


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
