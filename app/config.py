from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'kisansetu.db'}"
SECRET_KEY = "kisansetu-mvp-dev-secret-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480
OTP_TTL_SECONDS = 300
DEMO_OTP = "123456"
IDLE_TIMEOUT_MINUTES = 15
FRONTEND_DIR = BASE_DIR / "frontend"
COMMODITIES = ["tomato", "onion", "soybean", "cotton", "wheat", "grapes"]
MANDIS = ["Nashik", "Pune", "Mumbai", "Nagpur", "Aurangabad"]
LANGUAGES = ["mr", "hi", "en"]
