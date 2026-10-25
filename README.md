# LocalHands – Hyperlocal Blue-Collar Services (demo build)

Flask + SQLAlchemy + Bootstrap 5. Story: **a customer in trouble gets the right worker at a fair price.**
Languages: English / தமிழ் / हिन्दी (switch in the top bar – the whole site changes).

## Run (Windows / VS Code)
```
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python seed.py --sample
python run.py
```
Open http://127.0.0.1:5000. Default DB is SQLite (no setup). For MySQL set `DB_ENGINE=mysql` and the DB_* values in `.env`.

Logins: admin `admin@example.com` / `ChangeMe123` (from `.env`); customer `customer.sample@example.com`;
workers `ravi.sample@example.com` (Plumber), `sunita.sample@example.com` (Electrician),
`imran.sample@example.com` (Carpenter), `meena.sample@example.com` (Cleaner) – password `Sample123`.

## How it looks
* Home asks **Customer or Worker** → register (or login) → lands on the matching dashboard.
* Top navigation: **Home · Notifications · Profile**, plus Bookings (customer) or Earnings (worker). Notifications are derived
  from bookings (new requests, SOS, counter-offers, payments, reviews) and the red badge counts items that need a response.
* Customer home: service icons → **Now** (SOS) or **Pick a day** (worker list → Book → short form), plus active bookings.
* Worker home: availability switch, summary strip (today / new requests / earned), SOS, Today, Upcoming, New requests.
* Every booking card shows **one** primary button; counter-offer, extra charge, decline and cancel sit under "More",
  where the cancellation rule is shown as one sentence.

## 5-minute demo order
1. Home: type the problem, pick the service → Find workers (match % + reasons)
2. Book: photo + your offered price → worker counters → customer accepts
3. SOS: choose ONE thing (worker type) → open the Electrician worker's dashboard → Accept (first wins)
4. Worker: On the way → Start → propose extra charge (with reason) → customer accepts → Complete
5. Customer: Confirm & pay (simulated) → rate & review (shows on worker profile)

## Rules (all in `config.py` / `app/services.py`)
* Free cancellation until `FREE_CANCEL_HOURS` (2h) before start; then `LATE_FEE_PERCENT` (20%);
  if the worker is already "on the way": flat `TRAVEL_FEE` (₹100). Shown on customer AND worker pages. Fees are simulated.
* Worker cancelling lowers the **reliability** score (completed ÷ (completed + worker cancels)).
* Double-booking: overlapping 2-hour slots are rejected; SOS acceptance and booking actions lock the row.
* Customers only see their own bookings; workers only see bookings assigned to them (plus open SOS for their trade).
* Payments are simulated.
* Hidden on purpose (not built): complaints, disputes, no-show reports, review moderation, document upload.
