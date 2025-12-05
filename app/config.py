import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR))

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    # Paths
    JSON_PATH = DATA_DIR / "pfsense_benchmark.json"
    CKL_PATH = DATA_DIR / "pfsense_benchmark.ckl"
    DB_PATH = DATA_DIR / os.getenv("DB_PATH", "reviews.db")

    # SSH
    SSH_TIMEOUT = int(os.getenv("SSH_TIMEOUT", "30"))
    SSH_KNOWN_HOSTS_CHECK = os.getenv("SSH_KNOWN_HOSTS_CHECK", "True").lower() == "true"

    # Session
    SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "10"))

    # Authentication
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this-password")

    # Constants
    MAX_SESSION_TIMEOUT_MINUTES = 10

    STATUS_MAP = {
        "NotAFinding": "Compliant",
        "Open": "Non Compliant",
        "Not_Applicable": "Non Applicable",
        "Not_Reviewed": "Not Reviewed",
    }
