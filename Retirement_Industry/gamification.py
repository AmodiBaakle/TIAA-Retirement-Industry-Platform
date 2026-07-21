"""Module 6 - Gamification Engine (Duolingo for money).

XP, levels, badges, saving streaks, weekly challenges, and a leaderboard.

Public API:
    get_state(pid)                 -> {xp, level, xp_into, xp_needed, pct, streak}
    award_xp(pid, amount, reason)  -> new state
    record_activity(pid)           -> updates the saving streak (call daily/on action)
    evaluate_badges(pid)           -> [ {key, label, emoji, desc, earned} ]
    active_challenges(pid)         -> [ {key, title, emoji, progress, target, pct, done} ]
    leaderboard(limit=10)          -> [ {rank, name, xp, level} ]
"""
import json

from django.db.models import Sum
from django.utils import timezone

from Retirement_Industry.models import (
    Profile_Info, Transaction_History, GamificationState,
    BadgeEarned, ChallengeProgress, SavingsLedger, BehaviorProfile,
)

XP_STEP = 200  # level L requires L * XP_STEP xp (cumulative grows each level)

# key -> (label, emoji, description)
BADGES = {
    'first_save':        ('First Save', '\U0001F331', 'Logged your first saving.'),
    'coffee_controller': ('Coffee Controller', '☕', 'Cut coffee spending month-over-month.'),
    'weekend_warrior':   ('Weekend Warrior', '\U0001F3C6', 'Recognised your weekend spending pattern.'),
    'subscription_slayer':('Subscription Slayer', '\U0001F5E1️', 'Has unused subscriptions to cancel.'),
    'money_ninja':       ('Money Ninja', '\U0001F977', 'Reached level 5.'),
    'emergency_fund_hero':('Emergency Fund Hero', '\U0001F6E1️', 'Completed a savings goal.'),
    'ninety_day_saver':  ('90-Day Saver', '\U0001F525', 'Maintained a 90-day saving streak.'),
    'streak_7':          ('Week Streak', '\U0001F4C5', 'Saved 7 days in a row.'),
}

# key -> (title, emoji, target, unit) ; progress computed from recent activity
CHALLENGES = {
    'no_swiggy_week':   ('No Swiggy Week', '\U0001F35C', 7, 'days'),
    'under_1000':       ('Spend Less Than ₹1000 Today', '\U0001F4B0', 1000, 'rupees'),
    'no_impulse_sunday':('No Impulse Sunday', '\U0001F6AB', 1, 'sunday'),
    'save_500':         ('Save ₹500 This Week', '\U0001F3AF', 500, 'rupees'),
    'walk_instead_uber':('Walk Instead of Uber', '\U0001F6B6', 3, 'rides cut'),
}


# ---------------------------------------------------------------- XP / levels
def level_info(xp):
    level, cum = 1, 0
    while xp >= cum + level * XP_STEP:
        cum += level * XP_STEP
        level += 1
    xp_into = xp - cum
    xp_needed = level * XP_STEP
    return level, xp_into, xp_needed


def _state_row(pid):
    row, _ = GamificationState.objects.get_or_create(person_id=pid)
    return row


def get_state(pid):
    row = _state_row(pid)
    level, xp_into, xp_needed = level_info(row.xp)
    if row.level != level:
        row.level = level
        row.save(update_fields=['level'])
    return {
        'xp': row.xp, 'level': level, 'xp_into': xp_into, 'xp_needed': xp_needed,
        'pct': round(xp_into / xp_needed * 100) if xp_needed else 0,
        'streak': row.streak_days,
    }


def award_xp(pid, amount, reason=''):
    row = _state_row(pid)
    row.xp += int(amount)
    row.level = level_info(row.xp)[0]
    row.save(update_fields=['xp', 'level'])
    return get_state(pid)


def record_activity(pid):
    """Advance the saving streak. +1 if consecutive day, reset if a day missed."""
    row = _state_row(pid)
    today = timezone.now().date()
    if row.last_active == today:
        return row.streak_days
    if row.last_active and (today - row.last_active).days == 1:
        row.streak_days += 1
    else:
        row.streak_days = 1
    row.last_active = today
    row.save(update_fields=['streak_days', 'last_active'])
    return row.streak_days


# ------------------------------------------------------------------- badges
def evaluate_badges(pid):
    from Retirement_Industry.expense_intelligence import generate_insights

    earned_keys = set(BadgeEarned.objects.filter(person_id=pid).values_list('badge_key', flat=True))
    state = get_state(pid)
    intel = generate_insights(pid)
    titles = {i['title'] for i in intel['insights']}

    # behaviour trait scores
    traits = {}
    bp = BehaviorProfile.objects.filter(person_id=pid).first()
    if bp:
        try:
            traits = json.loads(bp.traits_json)
        except ValueError:
            traits = {}

    rules = {
        'first_save': SavingsLedger.objects.filter(person_id=pid).exists()
                      or (Transaction_History.objects.filter(person_id=pid)
                          .aggregate(s=Sum('rounded_off_amount'))['s'] or 0) > 0,
        'coffee_controller': any('Coffee spending dropped' in t for t in titles),
        'weekend_warrior': traits.get('weekend_warrior', 0) >= 60,
        'subscription_slayer': any('likely unused' in t for t in titles),
        'money_ninja': state['level'] >= 5,
        'emergency_fund_hero': Goal_complete(pid),
        'ninety_day_saver': state['streak'] >= 90,
        'streak_7': state['streak'] >= 7,
    }

    out = []
    for key, (label, emoji, desc) in BADGES.items():
        qualifies = rules.get(key, False)
        if qualifies and key not in earned_keys:
            BadgeEarned.objects.create(person_id=pid, badge_key=key)
            earned_keys.add(key)
        out.append({'key': key, 'label': label, 'emoji': emoji,
                    'desc': desc, 'earned': key in earned_keys})
    return out


def Goal_complete(pid):
    from Retirement_Industry.models import Goal
    return any(g.saved_amount >= g.target_amount for g in Goal.objects.filter(person_id=pid))


# --------------------------------------------------------------- challenges
def _week_start(now):
    d = now - timezone.timedelta(days=now.weekday())
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def active_challenges(pid):
    now = timezone.now()
    week_start = _week_start(now)
    week_txns = Transaction_History.objects.filter(person_id=pid, timestamp__gte=week_start)
    today_txns = Transaction_History.objects.filter(
        person_id=pid, timestamp__year=now.year, timestamp__month=now.month, timestamp__day=now.day)

    # No Swiggy Week: days this week without a Swiggy/Zomato order
    food_days = {t.timestamp.date() for t in week_txns
                 if t.merchant in ('Swiggy', 'Zomato')}
    swiggy_free_days = max((now.date() - week_start.date()).days + 1 - len(food_days), 0)

    # Spend < ₹1000 today
    today_spend = today_txns.aggregate(s=Sum('transaction_amount'))['s'] or 0

    # No Impulse Sunday: impulse buys on the most recent Sunday
    impulse_sun = week_txns.filter(is_impulse=True, timestamp__week_day=1).count()

    # Save ₹500 this week (spare change + auto savings)
    saved_week = ((week_txns.aggregate(s=Sum('rounded_off_amount'))['s'] or 0)
                  + (SavingsLedger.objects.filter(person_id=pid, created_at__gte=week_start)
                     .aggregate(s=Sum('amount'))['s'] or 0))

    # Walk Instead of Uber: fewer Uber rides is better (target: <=cut)
    uber_rides = week_txns.filter(merchant='Uber').count()

    progress = {
        'no_swiggy_week': (swiggy_free_days, 7),
        'under_1000': (max(1000 - today_spend, 0), 1000),
        'no_impulse_sunday': (0 if impulse_sun else 1, 1),
        'save_500': (min(saved_week, 500), 500),
        'walk_instead_uber': (max(3 - uber_rides, 0), 3),
    }

    out = []
    for key, (title, emoji, target, unit) in CHALLENGES.items():
        cur, tgt = progress[key]
        pct = min(round(cur / tgt * 100), 100) if tgt else 0
        out.append({'key': key, 'title': title, 'emoji': emoji, 'unit': unit,
                    'progress': int(cur), 'target': int(tgt), 'pct': pct,
                    'done': cur >= tgt})
    return out


# --------------------------------------------------------------- leaderboard
def leaderboard(limit=10):
    rows = GamificationState.objects.order_by('-xp')[:limit]
    names = {p.person_id: (p.name or p.mail) for p in Profile_Info.objects.all()}
    out = []
    for rank, row in enumerate(rows, start=1):
        out.append({'rank': rank, 'name': names.get(row.person_id, 'User %d' % row.person_id),
                    'xp': row.xp, 'level': row.level})
    return out


if __name__ == '__main__':
    print('state:', get_state(1))
    print('challenges:', active_challenges(1))
    print('badges:', evaluate_badges(1))
