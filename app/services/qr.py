from io import BytesIO
from pathlib import Path
import base64

import qrcode


def lot_certificate_qr(lot_id: int, commodity: str, qty: float, grade: str) -> str:
    payload = f"KISANSETU|LOT:{lot_id}|{commodity}|{qty}kg|GRADE:{grade}"
    img = qrcode.make(payload)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def ensure_media_dir(base: Path) -> Path:
    d = base / "frontend" / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d
