from datetime import date, datetime, timedelta
from math import sin
from random import Random

from sqlalchemy.orm import Session

from app.config import COMMODITIES, DEMO_OTP, MANDIS
from app.models import ColdStorage, FPO, Lot, Offer, OtpCode, PriceAlert, PriceRecord, Transaction, User
from app.services.qr import lot_certificate_qr

BASE = {
    "tomato": 1400,
    "onion": 1800,
    "soybean": 4300,
    "cotton": 6800,
    "wheat": 2400,
    "grapes": 5200,
}

MANDI_BIAS = {
    "Nashik": 1.04,
    "Pune": 1.02,
    "Mumbai": 1.08,
    "Nagpur": 0.96,
    "Aurangabad": 0.98,
}

COORDS = {
    "Nashik": (19.9975, 73.7898),
    "Pune": (18.5204, 73.8567),
    "Mumbai": (19.0760, 72.8777),
    "Nagpur": (21.1458, 79.0882),
    "Aurangabad": (19.8762, 75.3433),
}


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        _seed_demo_activity(db)
        db.commit()
        return
    rng = Random(42)

    fpo = FPO(
        name="Godavari Agro FPO",
        registration_no="MH-FPO-2019-0441",
        member_count=214,
        district="Nashik",
    )
    db.add(fpo)
    db.flush()

    users = [
        User(
            name="Sunita Patil",
            phone="9876543210",
            role="farmer",
            language="mr",
            district="Nashik",
            geo_lat=20.011, geo_lng=73.79,
            fpo_id=fpo.id,
            trust_score=81,
        ),
        User(
            name="Ramesh Jadhav",
            phone="9876543211",
            role="fpo",
            language="mr",
            district="Nashik",
            geo_lat=19.99, geo_lng=73.80,
            fpo_id=fpo.id,
            trust_score=90,
        ),
        User(
            name="Priya Deshmukh",
            phone="9876543212",
            role="buyer",
            language="en",
            district="Pune",
            geo_lat=18.53, geo_lng=73.86,
            trust_score=92,
            on_time_payment_pct=96,
            quality_accept_pct=91,
            dispute_count=1,
        ),
        User(
            name="MSInS Admin",
            phone="9876543213",
            role="admin",
            language="en",
            district="Mumbai",
            geo_lat=19.07, geo_lng=72.87,
            trust_score=100,
        ),
        User(
            name="Kalyani Foods Pvt Ltd",
            phone="9876543214",
            role="buyer",
            language="hi",
            district="Nashik",
            geo_lat=19.98, geo_lng=73.77,
            trust_score=88,
            on_time_payment_pct=89,
            quality_accept_pct=94,
            dispute_count=0,
        ),
        User(
            name="Deccan Fresh Wholesale",
            phone="9876543215",
            role="buyer",
            language="en",
            district="Mumbai",
            geo_lat=19.10, geo_lng=72.88,
            trust_score=74,
            on_time_payment_pct=78,
            quality_accept_pct=82,
            dispute_count=4,
        ),
        User(
            name="Anil More",
            phone="9876543216",
            role="farmer",
            language="hi",
            district="Nashik",
            geo_lat=20.04, geo_lng=73.82,
            fpo_id=fpo.id,
            trust_score=76,
        ),
    ]
    db.add_all(users)
    db.flush()
    sunita, ramesh, priya = users[0], users[1], users[2]

    today = date.today()
    for commodity in COMMODITIES:
        for mandi in MANDIS:
            for i in range(120, -1, -1):
                d = today - timedelta(days=i)
                seasonal = 1 + 0.12 * sin((d.timetuple().tm_yday / 365) * 6.28)
                noise = 1 + rng.uniform(-0.06, 0.06)
                modal = BASE[commodity] * MANDI_BIAS[mandi] * seasonal * noise
                if d.month in (3, 4) and commodity in ("onion", "tomato"):
                    modal *= 0.82
                spread = modal * 0.08
                db.add(
                    PriceRecord(
                        commodity=commodity,
                        mandi=mandi,
                        date=d,
                        min_price=round(modal - spread, 2),
                        max_price=round(modal + spread, 2),
                        modal_price=round(modal, 2),
                        arrival_volume=round(rng.uniform(80, 420), 1),
                        source="AGMARKNET",
                    )
                )

    db.add_all(
        [
            ColdStorage(
                name="Nashik APMC Cold Chain",
                district="Nashik",
                available_mt=180,
                cost_per_kg_day=0.35,
                geo_lat=COORDS["Nashik"][0],
                geo_lng=COORDS["Nashik"][1],
            ),
            ColdStorage(
                name="Pune Market Yard Store",
                district="Pune",
                available_mt=90,
                cost_per_kg_day=0.42,
                geo_lat=COORDS["Pune"][0],
                geo_lng=COORDS["Pune"][1],
            ),
            ColdStorage(
                name="Nagpur Orange Belt Unit",
                district="Nagpur",
                available_mt=60,
                cost_per_kg_day=0.30,
                geo_lat=COORDS["Nagpur"][0],
                geo_lng=COORDS["Nagpur"][1],
            ),
        ]
    )

    lot = Lot(
        farmer_id=sunita.id,
        commodity="tomato",
        quantity_kg=420,
        grade="A",
        harvest_date=today - timedelta(days=1),
        geo_lat=sunita.geo_lat,
        geo_lng=sunita.geo_lng,
        location_name="Nashik",
        status="listed",
        voice_original="420 किलो ग्रेड ए टोमॅटो, काल कापणी, नाशिक",
        created_via_voice=True,
        liquidity_urgency="high",
    )
    db.add(lot)
    db.flush()
    lot.qr_code = lot_certificate_qr(lot.id, lot.commodity, lot.quantity_kg, lot.grade)

    lot2 = Lot(
        farmer_id=users[6].id,
        commodity="onion",
        quantity_kg=900,
        grade="B",
        harvest_date=today,
        geo_lat=users[6].geo_lat,
        geo_lng=users[6].geo_lng,
        location_name="Nashik",
        status="offered",
        liquidity_urgency="medium",
    )
    db.add(lot2)
    db.flush()
    lot2.qr_code = lot_certificate_qr(lot2.id, lot2.commodity, lot2.quantity_kg, lot2.grade)

    offer = Offer(lot_id=lot2.id, buyer_id=priya.id, price_offered=1850, status="pending")
    db.add(offer)

    closed_lot = Lot(
        farmer_id=sunita.id,
        commodity="grapes",
        quantity_kg=250,
        grade="A",
        harvest_date=today - timedelta(days=18),
        geo_lat=sunita.geo_lat,
        geo_lng=sunita.geo_lng,
        location_name="Nashik",
        status="sold",
        liquidity_urgency="low",
    )
    db.add(closed_lot)
    db.flush()
    closed_lot.qr_code = lot_certificate_qr(closed_lot.id, closed_lot.commodity, closed_lot.quantity_kg, closed_lot.grade)
    closed_offer = Offer(lot_id=closed_lot.id, buyer_id=users[4].id, price_offered=5600, status="accepted")
    db.add(closed_offer)
    db.flush()
    db.add(
        Transaction(
            offer_id=closed_offer.id,
            escrow_status="released",
            amount=250 * 5600 / 100,
            payment_ref="UPI-KS-88421",
            delivery_confirmed_at=datetime.utcnow() - timedelta(days=12),
        )
    )

    db.add(
        OtpCode(
            phone="0000000000",
            code=DEMO_OTP,
            expires_at=datetime.utcnow() + timedelta(days=365),
            used=False,
        )
    )
    _seed_demo_activity(db)
    db.commit()


def _seed_demo_activity(db: Session) -> None:
    """Add a compact, repeatable marketplace snapshot to an existing demo database."""
    if db.query(Lot).count() >= 9:
        return

    fpo = db.query(FPO).first()
    farmers = db.query(User).filter(User.role == "farmer").all()
    buyers = db.query(User).filter(User.role == "buyer").all()
    if not fpo or len(farmers) < 2 or len(buyers) < 2:
        return

    new_users = [
        User(name="Meena Shinde", phone="9876543220", role="farmer", language="mr", district="Nashik", geo_lat=20.02, geo_lng=73.81, fpo_id=fpo.id, trust_score=84),
        User(name="Vilas Pawar", phone="9876543221", role="farmer", language="mr", district="Pune", geo_lat=18.56, geo_lng=73.82, fpo_id=fpo.id, trust_score=79),
        User(name="Asha Gaikwad", phone="9876543222", role="farmer", language="hi", district="Aurangabad", geo_lat=19.88, geo_lng=75.34, fpo_id=fpo.id, trust_score=87),
        User(name="Sharad Borse", phone="9876543223", role="farmer", language="mr", district="Nashik", geo_lat=20.00, geo_lng=73.78, fpo_id=fpo.id, trust_score=82),
        User(name="Western Harvest Traders", phone="9876543224", role="buyer", language="en", district="Pune", geo_lat=18.54, geo_lng=73.85, trust_score=86, on_time_payment_pct=93, quality_accept_pct=90),
        User(name="Sahyadri Retail Link", phone="9876543225", role="buyer", language="en", district="Mumbai", geo_lat=19.08, geo_lng=72.88, trust_score=91, on_time_payment_pct=97, quality_accept_pct=95),
    ]
    db.add_all(new_users)
    db.flush()
    farmers.extend(new_users[:4])
    buyers.extend(new_users[4:])

    today = date.today()
    lot_specs = [
        (farmers[3], "onion", 640, "A", "Pune", "offered", 2, "medium"),
        (farmers[4], "tomato", 280, "A", "Nashik", "sold", 6, "low"),
        (farmers[5], "soybean", 1150, "B", "Aurangabad", "listed", 1, "high"),
        (farmers[1], "grapes", 360, "A", "Pune", "delivered", 11, "low"),
        (farmers[2], "wheat", 780, "B", "Aurangabad", "offered", 3, "medium"),
        (farmers[0], "cotton", 520, "A", "Nashik", "listed", 0, "medium"),
        (farmers[3], "onion", 410, "B", "Nashik", "sold", 16, "low"),
    ]
    created_lots = []
    for farmer, commodity, quantity, grade, location, status, age, urgency in lot_specs:
        lot = Lot(
            farmer_id=farmer.id,
            commodity=commodity,
            quantity_kg=quantity,
            grade=grade,
            harvest_date=today - timedelta(days=max(1, age + 1)),
            geo_lat=farmer.geo_lat,
            geo_lng=farmer.geo_lng,
            location_name=location,
            status=status,
            liquidity_urgency=urgency,
            created_at=datetime.utcnow() - timedelta(days=age, hours=2),
            voice_original="",
            created_via_voice=commodity in ("tomato", "soybean", "cotton"),
        )
        db.add(lot)
        db.flush()
        lot.qr_code = lot_certificate_qr(lot.id, lot.commodity, lot.quantity_kg, lot.grade)
        created_lots.append(lot)

    prices = {"onion": 1920, "tomato": 1510, "soybean": 4480, "grapes": 5720, "wheat": 2520, "cotton": 7010}
    for index, lot in enumerate(created_lots):
        buyer = buyers[index % len(buyers)]
        accepted = lot.status in ("sold", "delivered")
        offer = Offer(
            lot_id=lot.id,
            buyer_id=buyer.id,
            price_offered=prices[lot.commodity] + (index * 15),
            status="accepted" if accepted else "pending",
            created_at=lot.created_at + timedelta(hours=5),
        )
        db.add(offer)
        db.flush()
        if accepted:
            db.add(
                Transaction(
                    offer_id=offer.id,
                    escrow_status="released" if lot.status == "delivered" else "held",
                    amount=round(lot.quantity_kg / 100 * offer.price_offered, 2),
                    payment_ref=f"UPI-KS-{91000 + lot.id}",
                    delivery_confirmed_at=datetime.utcnow() - timedelta(days=max(1, index)) if lot.status == "delivered" else None,
                    created_at=offer.created_at + timedelta(hours=8),
                )
            )

    db.add_all(
        [
            PriceAlert(user_id=farmers[3].id, commodity="onion", mandi="Nashik", threshold=2050, direction="above", triggered=False),
            PriceAlert(user_id=farmers[4].id, commodity="tomato", mandi="Nashik", threshold=1600, direction="above", triggered=True),
            PriceAlert(user_id=farmers[5].id, commodity="soybean", mandi="Aurangabad", threshold=4400, direction="below", triggered=False),
        ]
    )
    db.flush()
