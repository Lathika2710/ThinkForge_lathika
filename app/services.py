"""Business rules: matching, double-booking check, cancellation policy."""
from datetime import datetime, timedelta
from config import Config
from .models import Booking

ACTIVE = ("confirmed", "travelling", "in_progress")


def has_conflict(worker_id, start, exclude_id=None):
    """True if the worker already has an active job overlapping [start, start+slot)."""
    end = start + timedelta(minutes=Config.SLOT_MINUTES)
    for b in Booking.query.filter(Booking.worker_id == worker_id, Booking.status.in_(ACTIVE)):
        if b.id != exclude_id and b.start < end and start < b.end:
            return True
    return False


def match(wp, area):
    """Score 0-100 + reason keys. Area 35, rating 30, reliability 20, experience 15."""
    score, reasons = 0, []
    area = (area or "").strip().lower()
    areas = [a.strip().lower() for a in (wp.service_areas or "").split(",") if a.strip()]
    if area and any(area in a or a in area for a in areas):
        score += 35
        reasons.append("why_area")
    elif not area:
        score += 17
    r = wp.avg_rating
    score += r / 5 * 30 if r else 15
    if r >= 4:
        reasons.append("why_rating")
    rel = wp.reliability
    score += rel / 100 * 20
    if rel >= 90:
        reasons.append("why_reliable")
    score += min(wp.experience_years or 0, 10) * 1.5
    if (wp.experience_years or 0) >= 5:
        reasons.append("why_exp")
    return round(min(score, 100)), reasons


def cancel_fee(b):
    """Fee if the CUSTOMER cancels now (simulated, recorded only)."""
    price = b.agreed_price or 0
    if b.status == "travelling":
        return Config.TRAVEL_FEE
    if b.status == "confirmed" and datetime.now() > b.start - timedelta(hours=Config.FREE_CANCEL_HOURS):
        return round(price * Config.LATE_FEE_PERCENT / 100)
    return 0


def policy_text(t, b):
    free_until = b.start - timedelta(hours=Config.FREE_CANCEL_HOURS)
    if b.status == "travelling":
        return t("policy_travel", f=Config.TRAVEL_FEE)
    if b.status in ("pending", "countered", "confirmed"):
        if datetime.now() <= free_until:
            return t("policy_free_until", t=free_until.strftime("%d %b, %I:%M %p"), p=Config.LATE_FEE_PERCENT)
        if b.status == "confirmed":
            return t("policy_late", p=Config.LATE_FEE_PERCENT, f=cancel_fee(b))
        return t("policy_free")
    return ""
