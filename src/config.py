import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "TELEGRAM_TOKEN",
    "GEMINI_API_KEY",
    "OPENWEATHER_API_KEY"
]

missing = [
    var for var in REQUIRED_VARS
    if not os.getenv(var)
]

if missing:
    raise RuntimeError(
        f"Missing environment variables: {', '.join(missing)}"
    )

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

LATITUDE = -31.58044
LONGITUDE = -60.07581