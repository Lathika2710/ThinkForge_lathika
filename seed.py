"""Create tables, categories, admin and 4 sample workers + 1 sample customer.
Usage:  python seed.py            (categories + admin)
        python seed.py --sample   (also adds 4 verified, available sample workers and a sample customer)
Sample workers have NO fake reviews: ratings only appear after real (demo) reviews.
"""
import os
import sys
from app import create_app, db
from app.models import User, Category, WorkerProfile

CATEGORIES = [("Plumber", "bi-droplet"), ("Electrician", "bi-lightning-charge"), ("Carpenter", "bi-hammer"),
              ("Painter", "bi-palette"), ("Cleaner", "bi-stars"), ("Cook", "bi-egg-fried"),
              ("Home Maintenance", "bi-house-gear")]

SAMPLES = [("Sample Ravi (Plumber)", "ravi.sample@example.com", "Plumber", 600, 8, "Pipe repair, leak fixing, bathroom fittings"),
           ("Sample Sunita (Electrician)", "sunita.sample@example.com", "Electrician", 700, 6, "Wiring, fan and light installation, MCB"),
           ("Sample Imran (Carpenter)", "imran.sample@example.com", "Carpenter", 900, 12, "Furniture repair, door and window fitting"),
           ("Sample Meena (Cleaner)", "meena.sample@example.com", "Cleaner", 500, 3, "Deep home cleaning, kitchen and bathroom")]


def main(sample=False):
    app = create_app()
    with app.app_context():
        db.create_all()
        for name, icon in CATEGORIES:
            if not Category.query.filter_by(name=name).first():
                db.session.add(Category(name=name, icon=icon))
        db.session.commit()
        email = os.environ.get("ADMIN_EMAIL", "admin@example.com").lower()
        if not User.query.filter_by(email=email).first():
            a = User(role="admin", name="Platform Admin", email=email, phone="0000000000", city="-")
            a.set_password(os.environ.get("ADMIN_PASSWORD", "ChangeMe123"))
            db.session.add(a)
            db.session.commit()
            print(f"Admin created: {email}")
        if sample and not User.query.filter_by(email="ravi.sample@example.com").first():
            for name, mail, cat, price, yrs, skills in SAMPLES:
                u = User(role="worker", name=name, email=mail, phone="9000000000", city="Bengaluru", is_sample=True)
                u.set_password("Sample123")
                u.profile = WorkerProfile(category=Category.query.filter_by(name=cat).first(), skills=skills,
                                          experience_years=yrs, starting_price=price, city="Bengaluru",
                                          service_areas="Indiranagar, Koramangala, 560038, 560034",
                                          available=True, verified=True)
                db.session.add(u)
            c = User(role="customer", name="Sample Customer", email="customer.sample@example.com", phone="9111111111",
                     city="Bengaluru", area="Indiranagar", address="12 Sample Street, Indiranagar, Bengaluru", is_sample=True)
            c.set_password("Sample123")
            db.session.add(c)
            db.session.commit()
            print("Sample data added (password for all sample users: Sample123).")
        print("Seed complete.")


if __name__ == "__main__":
    main("--sample" in sys.argv)
