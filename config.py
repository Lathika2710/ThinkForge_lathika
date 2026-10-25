"""Application configuration. Secrets come from environment variables (.env)."""
import os
import secrets
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)


def _db_uri():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if os.environ.get("DB_ENGINE", "sqlite").lower() == "mysql":
        user = os.environ.get("DB_USER", "root")
        pw = quote_plus(os.environ.get("DB_PASSWORD", ""))
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "3306")
        name = os.environ.get("DB_NAME", "blue_collar")
        return f"mysql+pymysql://{user}:{pw}@{host}:{port}/{name}?charset=utf8mb4"
    return "sqlite:///" + os.path.join(BASE_DIR, "instance", "localhands.db")


class Config:
    APP_NAME = "LocalHands"
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")  # outside static/, served only to allowed users
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_UPLOADS = {"png", "jpg", "jpeg"}
    # Booking & cancellation rules (server-local time)
    SLOT_MINUTES = 120        # every job reserves a 2-hour slot
    FREE_CANCEL_HOURS = 2     # customer cancels free until this many hours before start
    LATE_FEE_PERCENT = 20     # fee after that window (recorded only; simulated)
    TRAVEL_FEE = 100          # flat compensation (Rs) if worker is already on the way
