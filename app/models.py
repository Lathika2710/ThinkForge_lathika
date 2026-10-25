from datetime import datetime, timedelta
from sqlalchemy.orm import backref
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from . import db
from config import Config


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)  # customer / worker / admin
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    city = db.Column(db.String(80))
    area = db.Column(db.String(80))
    address = db.Column(db.String(255))
    password_hash = db.Column(db.String(255), nullable=False)
    is_sample = db.Column(db.Boolean, default=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    icon = db.Column(db.String(40))


class WorkerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    user = db.relationship("User", backref=backref("profile", uselist=False))
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    category = db.relationship("Category")
    skills = db.Column(db.String(255))
    experience_years = db.Column(db.Integer, default=0)
    starting_price = db.Column(db.Integer, default=0)
    city = db.Column(db.String(80))
    service_areas = db.Column(db.String(255))
    available = db.Column(db.Boolean, default=True)
    verified = db.Column(db.Boolean, default=False)

    @property
    def avg_rating(self):
        r = db.session.query(func.avg(Review.rating)).filter_by(worker_id=self.id).scalar()
        return round(float(r), 1) if r else 0

    @property
    def review_count(self):
        return Review.query.filter_by(worker_id=self.id).count()

    @property
    def reliability(self):
        """Completed jobs / (completed + worker cancellations). 100 when there is no history."""
        done = Booking.query.filter(Booking.worker_id == self.id, Booking.status.in_(("completed", "paid"))).count()
        cancels = Booking.query.filter_by(worker_id=self.id, cancelled_by="worker").count()
        return 100 if done + cancels == 0 else round(done / (done + cancels) * 100)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    customer = db.relationship("User", foreign_keys=[customer_id])
    worker_id = db.Column(db.Integer, db.ForeignKey("worker_profile.id"), nullable=True)  # empty for open SOS
    worker = db.relationship("WorkerProfile", backref="bookings")
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    category = db.relationship("Category")
    problem = db.Column(db.Text)
    photo = db.Column(db.String(80))
    address = db.Column(db.String(255))
    start = db.Column(db.DateTime, nullable=False)
    offered_price = db.Column(db.Integer)      # what the customer offered
    counter_price = db.Column(db.Integer)      # worker's counter-offer
    agreed_price = db.Column(db.Integer)       # set only when both sides agree
    addon_amount = db.Column(db.Integer)
    addon_reason = db.Column(db.String(255))
    addon_status = db.Column(db.String(20))    # proposed / accepted / rejected
    status = db.Column(db.String(20), default="pending", index=True)
    is_sos = db.Column(db.Boolean, default=False)
    cancelled_by = db.Column(db.String(20))
    cancel_reason = db.Column(db.String(255))
    cancel_fee = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)

    @property
    def end(self):
        return self.start + timedelta(minutes=Config.SLOT_MINUTES)

    @property
    def total(self):
        return (self.agreed_price or 0) + (self.addon_amount if self.addon_status == "accepted" else 0)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), unique=True, nullable=False)
    booking = db.relationship("Booking", backref=backref("review", uselist=False))
    worker_id = db.Column(db.Integer, db.ForeignKey("worker_profile.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    customer = db.relationship("User")
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now)
