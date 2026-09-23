# KisanSetu

Market linkages and price discovery for Maharashtra farmers (SIH26132 / MSInS).

## Run locally

```powershell
cd $HOME\KisanSetu
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Demo login (OTP always `123456`)

| Role | Phone |
| --- | --- |
| Farmer (Sunita) | 9876543210 |
| FPO (Ramesh) | 9876543211 |
| Buyer (Priya) | 9876543212 |
| Admin | 9876543213 |

## What’s in the MVP

- OTP + JWT roles (farmer / FPO / buyer / admin)
- AGMARKNET-style cached prices + quantile GBRT forecast (7–21 days)
- Sell-now vs store recommendation
- Voice or form lot listing, QR lot certificate
- Buyer matching with trust scores
- Offer → UPI escrow hold → delivery release → FPO dispute
- Pooled logistics + cold-storage mock
- Farmer CSV / print report and admin GMV desk
- Marathi / Hindi / English UI + Web Speech API

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
