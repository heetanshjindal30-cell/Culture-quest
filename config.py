import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = "llama-3.1-8b-instant"
    MAX_TOKENS      = 2000

    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
    ORS_API_KEY     = os.getenv("ORS_API_KEY", "")

    CSV_FILE_PATH   = os.path.join(os.path.dirname(__file__), "data", "locations.csv")
    ADMIN_PASSWORD  = "Heetansh@123"
    SECRET_KEY      = "tripquests-secret-2026"
    DEBUG           = False
    HOST            = "0.0.0.0"
    PORT            = 5000
