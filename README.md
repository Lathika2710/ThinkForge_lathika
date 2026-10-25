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

## Landing page
The first visit asks **Customer or Worker**. Customer → home page with voice/text search and SOS. Worker → worker login,
then the dashboard. The choice is remembered until logout; "Switch role" in the top bar resets it.

## Worker dashboard
Stats (today's jobs, upcoming, completed, earnings, awaiting payment, reliability), jobs grouped into
**New requests / Active jobs / History**, recent reviews, tips, and an **Edit profile** form (phone, city, experience,
price, skills, service areas). Workers do not see "Find workers" or SOS in the navigation.

## 5-minute demo order
1. Home: speak or type the problem (mic fills text + picks the service) → Find workers (match % + reasons)
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
* Payments are simulated. Voice uses the browser's speech recognition (Chrome/Edge, needs internet) – typing always works.
* Hidden on purpose (not built): complaints, disputes, no-show reports, review moderation, document upload.
