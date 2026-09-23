import math
import re
from datetime import date, timedelta

COMMODITY_ALIASES = {
    "tomato": ["tomato", "tomatoes", "टमाटर", "टोमॅटो", "tamatar"],
    "onion": ["onion", "onions", "प्याज", "कांदा", "kanda", "pyaz"],
    "soybean": ["soybean", "soy", "सोयाबीन", "soyabean"],
    "cotton": ["cotton", "कपास", "कापूस", "kapas"],
    "wheat": ["wheat", "गेहूं", "गहू", "gehu"],
    "grapes": ["grape", "grapes", "अंगूर", "द्राक्षे", "draksha"],
}

GRADE_ALIASES = {
    "A": ["grade a", "a grade", "ग्रेड ए", "ए ग्रेड", "उत्तम", "premium"],
    "B": ["grade b", "b grade", "ग्रेड बी"],
    "C": ["grade c", "c grade", "ग्रेड सी"],
}

URGENCY = {
    "high": ["urgent", "cash today", "जल्दी", "आज पैसे", "तातडीने"],
    "low": ["can wait", "store", "इंतजार", "साठव"],
}


def parse_voice(text: str, language: str = "en") -> dict:
    raw = (text or "").strip()
    lowered = raw.lower()
    commodity = None
    for key, aliases in COMMODITY_ALIASES.items():
        if any(a.lower() in lowered or a in raw for a in aliases):
            commodity = key
            break

    qty = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilo|किलो|क्विंटल|quintal|qtl)?", lowered)
    if m:
        qty = float(m.group(1))
        unit = (m.group(2) or "kg").lower()
        if unit in ("quintal", "qtl", "क्विंटल"):
            qty *= 100

    grade = "B"
    for g, aliases in GRADE_ALIASES.items():
        if any(a in lowered or a in raw for a in aliases):
            grade = g
            break

    harvest = date.today()
    if any(w in lowered for w in ["yesterday", "कल", "काल"]):
        harvest = date.today() - timedelta(days=1)

    location = "Nashik"
    for loc in ["Nashik", "Pune", "Mumbai", "Nagpur", "Aurangabad", "नाशिक", "पुणे"]:
        if loc.lower() in lowered or loc in raw:
            location = {
                "नाशिक": "Nashik",
                "पुणे": "Pune",
            }.get(loc, loc)
            break

    urgency = "medium"
    for u, aliases in URGENCY.items():
        if any(a in lowered or a in raw for a in aliases):
            urgency = u
            break

    return {
        "commodity": commodity or "tomato",
        "quantity_kg": qty or 100.0,
        "grade": grade,
        "harvest_date": harvest.isoformat(),
        "location_name": location,
        "liquidity_urgency": urgency,
        "voice_original": raw,
        "language": language,
        "confidence": 0.62 if commodity and qty else 0.4,
    }


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
