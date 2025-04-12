# src/config/config.py

# Default values (kosong untuk keamanan)
MEASUREMENT_ID = ""
API_SECRET = ""
ANALYTICS_URL = ""

try:
    from src.config.firebase_config import MEASUREMENT_ID, API_SECRET
    if MEASUREMENT_ID and API_SECRET:
        ANALYTICS_URL = f"https://www.google-analytics.com/mp/collect?measurement_id={MEASUREMENT_ID}&api_secret={API_SECRET}"
except ImportError:
    print("Firebase config tidak ditemukan, analytics tidak akan berfungsi")