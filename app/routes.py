import os
import uuid
from datetime import datetime
from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for, session, flash, g, abort,
                   send_from_directory)
from . import db
from .i18n import T, LANGS
from .models import User, Category, WorkerProfile, Booking, Review
from .services import has_conflict, match, cancel_fee
from config import Config

bp = Blueprint("main", __name__)


@bp.before_request
def load_user():
    g.user = db.session.get(User, session["uid"]) if session.get("uid") else None


def msg(key, cat="info", **kw):
    flash(T(session.get("lang", "en"), key, **kw), cat)


def to_int(v, lo=1, hi=100000):
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def login_required(role=None):
    def deco(f):
        @wraps(f)
        def w(*a, **kw):
            if not g.user:
                return redirect(url_for("main.login", next=request.path))
            if role and g.user.role != role:
                abort(403)
            return f(*a, **kw)
        return w
    return deco


def home_for(u):
    return url_for({"admin": "main.admin", "worker": "main.worker_dash"}.get(u.role, "main.index"))


# ---------- public ----------
@bp.route("/")
def index():
    # Logged-in workers/admins go straight to their page; visitors pick a role first.
    if g.user and g.user.role in ("worker", "admin"):
        return redirect(home_for(g.user))
    if not g.user:
        role = session.get("role")
        if role == "worker":
            return redirect(url_for("main.login", role="worker"))
        if role != "customer":
            return render_template("choose_role.html")
    return render_template("index.html", cats=Category.query.all())


@bp.route("/need/<int:cid>")
def need(cid):
    """Step 2 of tap-to-book: Now (SOS) or Pick a day (browse workers)."""
    cat = db.session.get(Category, cid) or abort(404)
    return render_template("need.html", cat=cat)


@bp.route("/role/<role>")
def choose_role(role):
    """Role picker on the landing page: remembers the choice and sends the visitor to the right page."""
    if role == "reset":
        session.pop("role", None)
        return redirect(url_for("main.index"))
    if role not in ("customer", "worker"):
        abort(404)
    session["role"] = role
    if g.user:
        return redirect(home_for(g.user))
    if role == "worker":
        return redirect(url_for("main.login", role="worker"))
    return redirect(url_for("main.index"))


@bp.route("/lang/<code>")
def set_lang(code):
    if code in LANGS:
        session["lang"] = code
    ref = request.referrer or ""
    return redirect(ref if ref.startswith(request.host_url) else url_for("main.index"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    cats = Category.query.all()
    role = request.values.get("role", "customer")
    role = role if role in ("customer", "worker") else "customer"
    if request.method == "POST":
        f = request.form
        name, email, phone = f.get("name", "").strip(), f.get("email", "").strip().lower(), f.get("phone", "").strip()
        pw = f.get("password", "")
        if not (name and "@" in email and len(pw) >= 6 and phone.isdigit() and len(phone) >= 10):
            msg("invalid_input", "danger")
            return render_template("register.html", cats=cats, role=role)
        if User.query.filter_by(email=email).first():
            msg("email_taken", "danger")
            return render_template("register.html", cats=cats, role=role)
        cat = price = exp = None
        if role == "worker":
            cat = db.session.get(Category, to_int(f.get("category_id"), 1, 10**6) or 0)
            price, exp = to_int(f.get("starting_price")), to_int(f.get("experience"), 0, 60)
            if not (cat and price and exp is not None):
                msg("invalid_input", "danger")
                return render_template("register.html", cats=cats, role=role)
        u = User(role=role, name=name, email=email, phone=phone, city=f.get("city", "").strip(),
                 area=f.get("area", "").strip(), address=f.get("address", "").strip())
        u.set_password(pw)
        db.session.add(u)
        if role == "worker":
            u.profile = WorkerProfile(category=cat, skills=f.get("skills", "").strip()[:250], experience_years=exp,
                                      starting_price=price, city=u.city, service_areas=f.get("service_areas", "")[:250])
        db.session.commit()
        lang = session.get("lang", "en")
        session.clear()
        session["lang"], session["uid"], session["role"] = lang, u.id, u.role
        msg("worker_pending" if role == "worker" else "welcome", "success")
        return redirect(home_for(u))
    return render_template("register.html", cats=cats, role=role)


@bp.route("/login", methods=["GET", "POST"])
def login():
    role = request.args.get("role") or session.get("role") or "customer"
    role = role if role in ("customer", "worker") else "customer"
    if request.method == "POST":
        u = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if u and u.check_password(request.form.get("password", "")):
            lang = session.get("lang", "en")
            session.clear()
            session["lang"], session["uid"] = lang, u.id
            if u.role in ("customer", "worker"):
                session["role"] = u.role
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else home_for(u))
        msg("bad_login", "danger")
    return render_template("login.html", role=role)


@bp.route("/logout")
def logout():
    lang = session.get("lang", "en")
    session.clear()
    session["lang"] = lang
    return redirect(url_for("main.index"))


@bp.route("/workers")
def workers():
    cats = Category.query.all()
    cid = to_int(request.args.get("category"), 1, 10**6)
    # Area comes from the customer's saved profile; no typing needed.
    area = (g.user.area or g.user.city or "") if g.user and g.user.role == "customer" else request.args.get("area", "")
    q = WorkerProfile.query.filter_by(verified=True)
    if cid:
        q = q.filter_by(category_id=cid)
    rows = []
    for wp in q:
        score, reasons = match(wp, area)
        rows.append((wp, score, reasons))
    rows.sort(key=lambda r: (not r[0].available, -r[1]))
    cat = db.session.get(Category, cid) if cid else None
    return render_template("workers.html", rows=rows, cats=cats, cid=cid, cat=cat, area=area)


@bp.route("/w/<int:wid>")
def worker_public(wid):
    wp = db.session.get(WorkerProfile, wid)
    if not wp or not wp.verified:
        abort(404)
    reviews = Review.query.filter_by(worker_id=wid).order_by(Review.created_at.desc()).all()
    return render_template("worker_profile.html", wp=wp, reviews=reviews)


@bp.route("/photo/<name>")
@login_required()
def photo(name):
    b = Booking.query.filter_by(photo=name).first_or_404()
    u = g.user
    wp = u.profile if u.role == "worker" else None
    ok = (u.role == "admin" or b.customer_id == u.id or (wp and (b.worker_id == wp.id or
          (b.status == "sos_open" and b.category_id == wp.category_id))))
    if not ok:
        abort(403)
    return send_from_directory(Config.UPLOAD_FOLDER, name)


# ---------- customer ----------
def save_photo(f):
    if not f or not f.filename:
        return None
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in Config.ALLOWED_UPLOADS:
        raise ValueError
    name = uuid.uuid4().hex + "." + ext
    f.save(os.path.join(Config.UPLOAD_FOLDER, name))
    return name


@bp.route("/book/<int:wid>", methods=["GET", "POST"])
@login_required("customer")
def book(wid):
    wp = db.session.get(WorkerProfile, wid)
    if not wp or not wp.verified or not wp.available:
        abort(404)
    if request.method == "POST":
        f = request.form
        price = to_int(f.get("price"))
        problem = f.get("problem", "").strip()[:1000]
        try:
            start = datetime.strptime(f.get("date", "") + " " + f.get("time", ""), "%Y-%m-%d %H:%M")
        except ValueError:
            start = None
        if not (price and problem and start):
            msg("invalid_input", "danger")
        elif start <= datetime.now():
            msg("past_time", "danger")
        elif has_conflict(wp.id, start):
            msg("msg_conflict", "danger")
        else:
            try:
                photo_name = save_photo(request.files.get("photo"))
            except ValueError:
                msg("bad_photo", "danger")
                return render_template("book.html", wp=wp, today=datetime.now().strftime("%Y-%m-%d"))
            db.session.add(Booking(customer_id=g.user.id, worker_id=wp.id, category_id=wp.category_id,
                                   problem=problem, photo=photo_name, start=start, offered_price=price,
                                   address=(f.get("address") or g.user.address or "")[:250], status="pending"))
            db.session.commit()
            msg("msg_booked", "success")
            return redirect(url_for("main.my_bookings"))
    return render_template("book.html", wp=wp, today=datetime.now().strftime("%Y-%m-%d"))


@bp.route("/bookings")
@login_required("customer")
def my_bookings():
    # Strictly the logged-in customer's own bookings.
    rows = Booking.query.filter_by(customer_id=g.user.id).order_by(Booking.created_at.desc()).all()
    return render_template("my_bookings.html", rows=rows)


@bp.route("/review/<int:bid>", methods=["GET", "POST"])
@login_required("customer")
def review(bid):
    b = Booking.query.filter_by(id=bid, customer_id=g.user.id).first_or_404()
    if b.status not in ("completed", "paid") or b.review or not b.worker_id:
        abort(403)
    if request.method == "POST":
        rating = to_int(request.form.get("rating"), 1, 5)
        if not rating:
            msg("invalid_input", "danger")
        else:
            db.session.add(Review(booking_id=b.id, worker_id=b.worker_id, customer_id=g.user.id, rating=rating,
                                  comment=request.form.get("comment", "").strip()[:500]))
            db.session.commit()
            msg("review_thanks", "success")
            return redirect(url_for("main.my_bookings"))
    return render_template("review.html", b=b)


# ---------- SOS ----------
@bp.route("/sos", methods=["GET", "POST"])
@login_required("customer")
def sos():
    cats = Category.query.all()
    if request.method == "POST":
        cat = db.session.get(Category, to_int(request.form.get("category_id"), 1, 10**6) or 0)
        if not cat:
            msg("invalid_input", "danger")
        else:
            b = Booking(customer_id=g.user.id, category_id=cat.id, problem="SOS", status="sos_open", is_sos=True,
                        start=datetime.now(), address=g.user.address or f"{g.user.area or ''} {g.user.city or ''}".strip())
            db.session.add(b)
            db.session.commit()
            return redirect(url_for("main.sos_status", bid=b.id))
    return render_template("sos.html", cats=cats)


@bp.route("/sos/<int:bid>")
@login_required("customer")
def sos_status(bid):
    b = Booking.query.filter_by(id=bid, customer_id=g.user.id, is_sos=True).first_or_404()
    return render_template("sos_status.html", b=b)


@bp.route("/sos/<int:bid>/accept", methods=["POST"])
@login_required("worker")
def sos_accept(bid):
    wp = g.user.profile
    b = Booking.query.filter_by(id=bid).with_for_update().first_or_404()  # row lock: first acceptance wins
    if (b.status != "sos_open" or b.category_id != wp.category_id or not wp.verified or not wp.available
            or has_conflict(wp.id, b.start)):
        msg("sos_taken", "warning")
    else:
        b.worker_id, b.status = wp.id, "confirmed"
        b.offered_price = b.agreed_price = wp.starting_price
        db.session.commit()
        msg("msg_done", "success")
    return redirect(url_for("main.worker_dash"))


# ---------- worker ----------
@bp.route("/worker")
@login_required("worker")
def worker_dash():
    wp = g.user.profile
    sos_open = []
    if wp.verified and wp.available:
        sos_open = Booking.query.filter_by(status="sos_open", category_id=wp.category_id).order_by(Booking.created_at).all()
    # Strictly bookings assigned to THIS worker.
    rows = Booking.query.filter_by(worker_id=wp.id).order_by(Booking.start).all()
    today = datetime.now().date()
    active = [b for b in rows if b.status in ("confirmed", "travelling", "in_progress")]
    groups = dict(
        requests=[b for b in rows if b.status == "pending"],
        today=[b for b in active if b.start.date() <= today],
        upcoming=[b for b in active if b.start.date() > today],
        waiting=[b for b in rows if b.status in ("countered", "completed")],
    )
    return render_template("worker_dash.html", wp=wp, sos_open=sos_open, groups=groups)


@bp.route("/worker/availability", methods=["POST"])
@login_required("worker")
def worker_availability():
    g.user.profile.available = not g.user.profile.available
    db.session.commit()
    return redirect(url_for("main.worker_dash"))


@bp.route("/worker/money")
@login_required("worker")
def worker_money():
    wp = g.user.profile
    rows = Booking.query.filter(Booking.worker_id == wp.id, Booking.status.in_(("completed", "paid"))).order_by(Booking.start.desc()).all()
    stats = dict(earned=sum(b.total for b in rows if b.status == "paid"),
                 awaiting=sum(b.total for b in rows if b.status == "completed"), done=len(rows))
    return render_template("money.html", wp=wp, rows=rows, stats=stats)


@bp.route("/me", methods=["GET", "POST"])
@login_required()
def me():
    u = g.user
    wp = u.profile if u.role == "worker" else None
    if request.method == "POST":
        f = request.form
        phone = f.get("phone", "").strip()
        ok = phone.isdigit() and 10 <= len(phone) <= 15
        if wp:
            price, exp = to_int(f.get("starting_price")), to_int(f.get("experience"), 0, 60)
            ok = ok and price and exp is not None
        if not ok:
            msg("invalid_input", "danger")
        else:
            u.phone, u.city = phone, f.get("city", "").strip()[:80]
            if wp:
                wp.starting_price, wp.experience_years, wp.city = price, exp, u.city
                wp.skills = f.get("skills", "").strip()[:250]
                wp.service_areas = f.get("service_areas", "").strip()[:250]
            else:
                u.area, u.address = f.get("area", "").strip()[:80], f.get("address", "").strip()[:250]
            db.session.commit()
            msg("profile_saved", "success")
        return redirect(url_for("main.me"))
    return render_template("me.html", wp=wp)


# ---------- booking actions ----------
@bp.route("/booking/<int:bid>/<action>", methods=["POST"])
@login_required()
def act(bid, action):
    b = Booking.query.filter_by(id=bid).with_for_update().first_or_404()
    u = g.user
    wp = u.profile if u.role == "worker" else None
    is_cust = u.role == "customer" and b.customer_id == u.id
    is_work = bool(wp) and b.worker_id == wp.id
    if not (is_cust or is_work):
        abort(403)
    S, f, done = b.status, request.form, False
    if is_work:
        if action == "accept" and S == "pending":
            if has_conflict(wp.id, b.start, b.id):
                msg("msg_conflict", "danger")
                return redirect(url_for("main.worker_dash"))
            b.agreed_price, b.status, done = b.offered_price, "confirmed", True
        elif action == "decline" and S in ("pending", "countered"):
            b.status, done = "declined", True
        elif action == "counter" and S == "pending":
            p = to_int(f.get("price"))
            if p:
                b.counter_price, b.status, done = p, "countered", True
        elif action == "travel" and S == "confirmed":
            b.status, done = "travelling", True
        elif action == "start" and S in ("confirmed", "travelling"):
            b.status, done = "in_progress", True
        elif action == "addon" and S == "in_progress" and b.addon_status != "proposed":
            amt, why = to_int(f.get("amount")), f.get("reason", "").strip()[:250]
            if amt and why:
                b.addon_amount, b.addon_reason, b.addon_status, done = amt, why, "proposed", True
        elif action == "done" and S == "in_progress":
            if b.addon_status == "proposed":
                msg("addon_open", "warning")
                return redirect(url_for("main.worker_dash"))
            b.status, done = "completed", True
        elif action == "wcancel" and S in ("confirmed", "travelling"):
            b.status, b.cancelled_by, b.cancel_reason, done = "cancelled", "worker", f.get("reason", "")[:250], True
    else:
        if action == "accept_counter" and S == "countered":
            if has_conflict(b.worker_id, b.start, b.id):
                msg("msg_conflict", "danger")
                return redirect(url_for("main.my_bookings"))
            b.agreed_price, b.status, done = b.counter_price, "confirmed", True
        elif action == "reject_counter" and S == "countered":
            b.status, b.cancelled_by, done = "cancelled", "customer", True
        elif action in ("accept_addon", "reject_addon") and b.addon_status == "proposed":
            b.addon_status, done = ("accepted" if action == "accept_addon" else "rejected"), True
        elif action == "pay" and S == "completed":
            b.status, done = "paid", True
        elif action == "cancel" and S in ("pending", "countered", "confirmed", "travelling", "sos_open"):
            b.cancel_fee = cancel_fee(b)
            b.status, b.cancelled_by, b.cancel_reason, done = "cancelled", "customer", f.get("reason", "")[:250], True
    if done:
        db.session.commit()
        msg("msg_done", "success")
    else:
        db.session.rollback()
        msg("msg_not_allowed", "warning")
    if is_cust and b.is_sos and b.status == "cancelled" and not b.worker_id:
        return redirect(url_for("main.my_bookings"))
    return redirect(url_for("main.my_bookings") if is_cust else url_for("main.worker_dash"))


# ---------- admin ----------
@bp.route("/admin")
@login_required("admin")
def admin():
    stats = dict(users=User.query.filter_by(role="customer").count(), workers=WorkerProfile.query.count(),
                 bookings=Booking.query.count(),
                 completed=Booking.query.filter(Booking.status.in_(("completed", "paid"))).count())
    return render_template("admin.html", stats=stats, wps=WorkerProfile.query.order_by(WorkerProfile.verified).all())


@bp.route("/admin/verify/<int:wid>", methods=["POST"])
@login_required("admin")
def admin_verify(wid):
    wp = db.session.get(WorkerProfile, wid) or abort(404)
    wp.verified = not wp.verified
    db.session.commit()
    return redirect(url_for("main.admin"))
