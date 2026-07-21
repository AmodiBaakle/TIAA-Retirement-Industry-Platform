"""Synthetic expense generator (Module 2 - Expense Collection Layer).

Produces a realistic, auto-collected transaction stream for a user so the
downstream intelligence / behaviour / gamification engines have data to work
with. No manual entry required. Patterns baked in on purpose:

  * weekend spending spikes (~+36%)
  * salary-day bursts (first days of the month)
  * recurring monthly subscriptions (some effectively unused)
  * late-night impulse purchases, heavier after mid-week "stress" days
  * coffee / food / shopping / daily-essentials mix

Deterministic by default (fixed RNG seed) so the pitch demo is repeatable.

Usage:
    python manage.py seed_transactions --mail me@gmail.com --days 75 --clear
    python manage.py seed_transactions --pid 1
    python manage.py seed_transactions --all
"""
import math
import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from Retirement_Industry.models import Profile_Info, Transaction_History, Goal


# (merchant, category, source, low, high, is_subscription, is_impulse_prone)
# categories match the existing classifier vocabulary: Daily / Basic / Luxury / Entertainment
DAILY = [
    ('BigBasket Groceries', 'Daily', 'UPI', 300, 1200, False, False),
    ('More Supermarket', 'Daily', 'Card', 200, 900, False, False),
    ('Milk Basket', 'Daily', 'UPI', 40, 120, False, False),
    ('Metro Card Recharge', 'Daily', 'UPI', 100, 500, False, False),
    ('Pharmacy', 'Daily', 'Card', 120, 700, False, False),
]
FOOD = [
    ('Swiggy', 'Basic', 'UPI', 180, 650, False, True),
    ('Zomato', 'Basic', 'UPI', 200, 700, False, True),
    ('Starbucks', 'Luxury', 'Card', 250, 500, False, True),
    ('Cafe Coffee Day', 'Basic', 'UPI', 120, 280, False, True),
    ('Local Restaurant', 'Basic', 'Card', 300, 1500, False, False),
]
SHOPPING = [
    ('Amazon', 'Luxury', 'Card', 400, 6000, False, True),
    ('Flipkart', 'Luxury', 'Card', 500, 5000, False, True),
    ('Myntra', 'Luxury', 'Card', 600, 4000, False, True),
    ('Nykaa', 'Luxury', 'Card', 300, 2500, False, True),
]
ENTERTAINMENT = [
    ('PVR Cinemas', 'Entertainment', 'Card', 300, 1200, False, False),
    ('BookMyShow', 'Entertainment', 'UPI', 250, 900, False, False),
    ('Uber', 'Basic', 'UPI', 120, 800, False, False),
]
SUBSCRIPTIONS = [
    ('Netflix', 'Entertainment', 'Card', 649, 649, True, False),
    ('Spotify Premium', 'Entertainment', 'Card', 119, 119, True, False),
    ('Amazon Prime', 'Entertainment', 'Card', 299, 299, True, False),
    ('Disney+ Hotstar', 'Entertainment', 'Card', 299, 299, True, False),
    ('Cult.fit Gym', 'Basic', 'Card', 1000, 1000, True, False),
]


def _round_off(amount):
    """Simple round-up-to-nearest-10 spare change (Module 7 refines this later)."""
    return int(math.ceil(amount / 10.0) * 10 - amount)


class Command(BaseCommand):
    help = 'Generate a synthetic, auto-collected transaction stream for a user.'

    def add_arguments(self, parser):
        parser.add_argument('--mail', type=str, help='Target user by email')
        parser.add_argument('--pid', type=int, help='Target user by person_id')
        parser.add_argument('--all', action='store_true', help='Seed every user')
        parser.add_argument('--days', type=int, default=75, help='Days of history (default 75)')
        parser.add_argument('--clear', action='store_true', help='Delete the user\'s existing transactions first')
        parser.add_argument('--seed', type=int, default=42, help='RNG seed for repeatable demos')
        parser.add_argument('--goals', action='store_true', help='Also create sample goals if the user has none')

    def handle(self, *args, **opts):
        if opts['all']:
            people = list(Profile_Info.objects.all())
        elif opts['mail']:
            people = list(Profile_Info.objects.filter(mail=opts['mail']))
        elif opts['pid']:
            people = list(Profile_Info.objects.filter(person_id=opts['pid']))
        else:
            people = list(Profile_Info.objects.all())
            if len(people) != 1:
                raise CommandError(
                    'Specify --mail, --pid, or --all (found %d users).' % len(people))

        if not people:
            raise CommandError('No matching users found.')

        for person in people:
            self._seed_user(person, opts)

    def _seed_user(self, person, opts):
        rng = random.Random(opts['seed'] + person.person_id)
        pid = person.person_id

        if opts['clear']:
            deleted, _ = Transaction_History.objects.filter(person_id=pid).delete()
            self.stdout.write('  cleared %d existing transactions' % deleted)

        days = opts['days']
        now = timezone.now()
        start = now - timedelta(days=days - 1)
        rows = []

        for d in range(days):
            date = start + timedelta(days=d)
            weekday = date.weekday()          # 0=Mon ... 5=Sat, 6=Sun
            is_weekend = weekday >= 5
            dom = date.day
            is_salary_window = dom in (1, 2, 3)

            # baseline daily transaction count, boosted on weekends & salary days
            n = rng.randint(1, 3)
            if is_weekend:
                n += 1                        # ~+36% weekend lift
            if is_salary_window:
                n += rng.randint(1, 3)        # salary-day shopping burst

            for _ in range(n):
                pool = self._pick_pool(rng, is_weekend, is_salary_window)
                merchant, category, source, lo, hi, is_sub, impulse_prone = rng.choice(pool)
                amount = rng.randint(lo, hi)

                hour = rng.randint(9, 21)
                is_impulse = False
                # late-night impulse buys, heavier after mid-week "stress" (Wed/Thu)
                if impulse_prone and rng.random() < (0.28 if weekday in (2, 3) else 0.12):
                    hour = rng.choice([22, 23, 0, 1, 2])
                    is_impulse = True

                ts = date.replace(hour=hour % 24, minute=rng.randint(0, 59),
                                  second=0, microsecond=0)
                rows.append(Transaction_History(
                    person_id=pid,
                    transaction_name=merchant,
                    transaction_amount=amount,
                    expense_category=category,
                    rounded_off_amount=_round_off(amount),
                    timestamp=ts,
                    source=source,
                    merchant=merchant,
                    is_impulse=is_impulse,
                    is_subscription=is_sub,
                ))

            # monthly subscriptions charge on fixed days
            for idx, sub in enumerate(SUBSCRIPTIONS):
                charge_day = 5 + idx * 3
                if dom == charge_day:
                    merchant, category, source, lo, hi, is_sub, _ = sub
                    ts = date.replace(hour=6, minute=0, second=0, microsecond=0)
                    rows.append(Transaction_History(
                        person_id=pid,
                        transaction_name=merchant,
                        transaction_amount=lo,
                        expense_category=category,
                        rounded_off_amount=_round_off(lo),
                        timestamp=ts,
                        source=source,
                        merchant=merchant,
                        is_impulse=False,
                        is_subscription=True,
                    ))

        Transaction_History.objects.bulk_create(rows)
        self.stdout.write(self.style.SUCCESS(
            '%s (pid=%d): created %d transactions over %d days'
            % (person.name or person.mail, pid, len(rows), days)))

        if opts['goals'] and not Goal.objects.filter(person_id=pid).exists():
            self._seed_goals(pid)

    def _pick_pool(self, rng, is_weekend, is_salary_window):
        if is_salary_window:
            weights = [SHOPPING] * 3 + [FOOD] * 2 + [ENTERTAINMENT, DAILY]
        elif is_weekend:
            weights = [FOOD] * 3 + [ENTERTAINMENT] * 2 + [SHOPPING, DAILY]
        else:
            weights = [DAILY] * 3 + [FOOD] * 2 + [SHOPPING, ENTERTAINMENT]
        return rng.choice(weights)

    def _seed_goals(self, pid):
        # (name, emoji, target, months, tier, saved_fraction) - fractions give
        # visible, realistic progress bars for the demo.
        samples = [
            ('MacBook Pro', '\U0001F4BB', 180000, 10, 'major', 0.45),
            ('Japan Trip', '✈️', 250000, 18, 'major', 0.22),
            ('New Headphones', '\U0001F3A7', 25000, 4, 'minor', 0.70),
        ]
        for name, emoji, amount, months, tier, frac in samples:
            Goal.objects.create(person_id=pid, name=name, emoji=emoji,
                                target_amount=amount, target_months=months,
                                saved_amount=int(amount * frac), tier=tier)
        self.stdout.write('  seeded %d sample goals' % len(samples))
