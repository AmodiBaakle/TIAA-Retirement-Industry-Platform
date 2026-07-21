"""Module 12 - AI Financial Coach.

A weekly report comparing this week to last week: savings, food spend, impulse
purchases, and goal progress - plus a short list of concrete recommendations.

Public API:
    weekly_report(pid) -> {
        'metrics': [ {label, value, delta_pct, direction, good}, ... ],
        'recommendations': [str, ...],
    }
"""
from django.db.models import Sum
from django.utils import timezone

from Retirement_Industry.models import Transaction_History, SavingsLedger, BehaviorProfile
from Retirement_Industry import expense_intelligence, goal_engine

FOOD_CATEGORIES = ('Basic',)
BEHAVIOUR_TIPS = {
    'The Midnight Shopper': 'Avoid late-night shopping - set a "no orders after 10pm" rule.',
    'Impulse Buyer': 'Add a 24-hour wait before any one-click buy over ₹1000.',
    'Subscription Collector': 'Cancel one unused subscription this week.',
    'Salary Day Hero': 'Shift savings the day salary lands, before it disappears.',
    'The Weekend Warrior': 'Set a weekend spending cap.',
}


def _window_sum(pid, field, start, end, **filters):
    qs = Transaction_History.objects.filter(
        person_id=pid, timestamp__gte=start, timestamp__lt=end, **filters)
    return qs.aggregate(s=Sum(field))['s'] or 0


def _delta(cur, prev):
    if prev == 0:
        return (100 if cur > 0 else 0)
    return round((cur - prev) / prev * 100)


def weekly_report(pid):
    now = timezone.now()
    this_start = now - timezone.timedelta(days=7)
    last_start = now - timezone.timedelta(days=14)

    # savings = spare change + auto-savings ledger
    save_now = _window_sum(pid, 'rounded_off_amount', this_start, now)
    save_now += (SavingsLedger.objects.filter(person_id=pid, created_at__gte=this_start)
                 .aggregate(s=Sum('amount'))['s'] or 0)
    save_prev = _window_sum(pid, 'rounded_off_amount', last_start, this_start)
    save_prev += (SavingsLedger.objects.filter(
        person_id=pid, created_at__gte=last_start, created_at__lt=this_start)
        .aggregate(s=Sum('amount'))['s'] or 0)

    # food spend
    food_now = _window_sum(pid, 'transaction_amount', this_start, now, expense_category__in=FOOD_CATEGORIES)
    food_prev = _window_sum(pid, 'transaction_amount', last_start, this_start, expense_category__in=FOOD_CATEGORIES)

    # impulse purchases (count)
    imp_now = Transaction_History.objects.filter(
        person_id=pid, is_impulse=True, timestamp__gte=this_start, timestamp__lt=now).count()
    imp_prev = Transaction_History.objects.filter(
        person_id=pid, is_impulse=True, timestamp__gte=last_start, timestamp__lt=this_start).count()

    # goal progress (avg % across goals right now)
    goals = goal_engine.goal_progress(pid)
    goal_pct = round(sum(g['pct'] for g in goals) / len(goals)) if goals else 0

    metrics = [
        {'label': 'Savings', 'value': '₹%d' % save_now, 'delta_pct': _delta(save_now, save_prev),
         'direction': 'up' if save_now >= save_prev else 'down',
         'good': save_now >= save_prev},
        {'label': 'Food spending', 'value': '₹%d' % food_now, 'delta_pct': _delta(food_now, food_prev),
         'direction': 'up' if food_now >= food_prev else 'down',
         'good': food_now <= food_prev},
        {'label': 'Impulse purchases', 'value': imp_now, 'delta_pct': _delta(imp_now, imp_prev),
         'direction': 'up' if imp_now >= imp_prev else 'down',
         'good': imp_now <= imp_prev},
        {'label': 'Goal progress', 'value': '%d%%' % goal_pct, 'delta_pct': None,
         'direction': 'up', 'good': True},
    ]

    recommendations = _recommendations(pid)
    return {'metrics': metrics, 'recommendations': recommendations}


def _recommendations(pid):
    recs = []
    intel = expense_intelligence.generate_insights(pid)
    titles = [i['title'] for i in intel['insights']]

    if any('likely unused' in t for t in titles):
        recs.append('Cancel unused subscriptions to free up monthly cash.')
    if any('impulse purchases' in t for t in titles):
        recs.append('Avoid late-night shopping - your impulse buys cluster there.')

    bp = BehaviorProfile.objects.filter(person_id=pid).first()
    if bp and bp.archetype in BEHAVIOUR_TIPS:
        recs.append(BEHAVIOUR_TIPS[bp.archetype])

    # savings run-rate suggestion
    recs.append('Shift any bonus or windfall straight into investments.')
    recs.append('Keep your saving streak alive to bank the XP bonus.')

    # de-dupe while preserving order, cap at 4
    seen, out = set(), []
    for r in recs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out[:4]


if __name__ == '__main__':
    import json
    print(json.dumps(weekly_report(1), indent=2, default=str))
