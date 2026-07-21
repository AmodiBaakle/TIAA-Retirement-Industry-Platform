# TARA — Behavioural Savings & Money Coach

TARA turns everyday spending into saving. It auto-collects transactions, decodes
your **money personality**, nudges you at the moment of spending, and makes
saving a game — XP, streaks, badges and challenges — while an AI coach and
behaviour-aware portfolio keep you on track.

> The app name is configurable in one place: `APP_NAME` in `TIAA/settings.py`.

## The 12-module flow

| # | Module | What it does |
|---|--------|--------------|
| 1 | Smart Financial Profiling | Age, salary, city, fixed expenses, debt, risk appetite, goals |
| 2 | Expense Collection | Auto-collected stream (synthetic seeder) + manual entry |
| 3 | Expense Intelligence | Weekend spikes, salary-day splurges, unused subscriptions, impulse buys |
| 4 | Behaviour Detection | Personality archetypes (Weekend Warrior, Impulse Buyer, …) — like Wrapped |
| 5 | Nudge Engine | "Skipping this order gets you 2 days closer to your Japan Trip" |
| 6 | Gamification | XP, levels, streaks, badges, weekly challenges, leaderboard |
| 7 | Smart Savings | Context-aware round-off (×5 on salary day, ease off in festive season) |
| 8 | Goal Achievement | Progress rings, ETAs, purchase-delay framing |
| 9 | Portfolio AI | Allocation from **financial + behavioural** profile |
| 12 | Financial Coach | Weekly report with week-over-week deltas + recommendations |

All intelligence is heuristic / classical-ML — deterministic and fully offline
(no API keys required).

## Tech stack

Django 6 · SQLite · server-rendered templates (inlined design system) ·
Chart.js (CDN) · scikit-learn / pandas for the ML pieces.

## Setup (base conda environment)

```bash
# from the project root, using the base conda environment
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py retrain_models      # regenerate the ML model for your sklearn
python manage.py create_demo         # build the polished demo account
python runGunicorn.py                # serves on http://localhost:8001
```

`runGunicorn.py` sets `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` (a macOS-only
fork-safety workaround for numpy/sklearn; ignored on Linux).

## Demo login

```
Email:    demo@tara.app
Password: demo123
```

Or register a fresh account and click **"Load sample data"** on the dashboard to
populate a realistic 75-day stream instantly.

## Handy management commands

```bash
python manage.py seed_transactions --pid <id> --clear --goals --days 75
python manage.py create_demo               # polished demo account
python manage.py retrain_models            # retrain the category model
python manage.py dedupe_accounts --apply   # collapse duplicate-email accounts
```
