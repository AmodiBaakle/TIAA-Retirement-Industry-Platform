"""Module 7 - Smart Savings Automation.

An improved auto round-off: instead of always rounding to ₹10, the AI decides
how aggressively to save based on context.

    Salary day          -> Round-Off x5   (money just landed)
    Goal almost done    -> Round-Off x2   (push it over the line)
    High-spending month -> Round-Off x0.5 (ease off)
    Festival season     -> Round-Off x0.5 (ease off)
    otherwise           -> Round-Off x1

Public API:
    decide_multiplier(pid, when=None) -> {multiplier, reason}
    apply_savings(pid, base_round, when=None) -> {saved, multiplier, reason, goal}
    savings_summary(pid) -> {total, by_reason, count}
"""
from django.db.models import Sum, Avg
from django.utils import timezone

from Retirement_Industry.models import Transaction_History, Goal, SavingsLedger

FESTIVAL_MONTHS = (10, 11)  # Diwali / festive season - ease off saving


def _this_month_spend(pid, ref):
    return Transaction_History.objects.filter(
        person_id=pid, timestamp__year=ref.year, timestamp__month=ref.month,
    ).aggregate(s=Sum('transaction_amount'))['s'] or 0


def _avg_month_spend(pid):
    txns = Transaction_History.objects.filter(person_id=pid)
    if not txns.exists():
        return 0
    total = txns.aggregate(s=Sum('transaction_amount'))['s'] or 0
    months = txns.dates('timestamp', 'month')
    n = max(len(list(months)), 1)
    return total / n


def _nearest_goal(pid):
    """Incomplete goal closest to completion (highest %), for satisfying wins."""
    active = [g for g in Goal.objects.filter(person_id=pid) if g.saved_amount < g.target_amount]
    if not active:
        return None
    return max(active, key=lambda g: g.saved_amount / g.target_amount if g.target_amount else 0)


def decide_multiplier(pid, when=None):
    when = when or timezone.now()

    # Salary day window - be aggressive
    if when.day in (1, 2, 3):
        return {'multiplier': 5.0, 'reason': 'Salary just landed - saving 5x the spare change'}

    # Goal almost complete - push it over the line
    g = _nearest_goal(pid)
    if g and g.target_amount and (g.saved_amount / g.target_amount) >= 0.85:
        return {'multiplier': 2.0, 'reason': '%s is almost funded - doubling your round-off' % g.name}

    # Festival season - ease off
    if when.month in FESTIVAL_MONTHS:
        return {'multiplier': 0.5, 'reason': 'Festival season - easing off deductions'}

    # High-spending month - ease off
    this_m = _this_month_spend(pid, when)
    avg_m = _avg_month_spend(pid)
    if avg_m and this_m > avg_m * 1.15:
        return {'multiplier': 0.5, 'reason': 'Higher spending this month - reducing deductions'}

    return {'multiplier': 1.0, 'reason': 'Steady month - standard round-off'}


def apply_savings(pid, base_round, when=None):
    """Compute the smart-saved amount, log it, and fund the nearest goal."""
    when = when or timezone.now()
    decision = decide_multiplier(pid, when)
    saved = int(round(base_round * decision['multiplier']))

    goal = _nearest_goal(pid)
    goal_id = goal.id if goal else None
    if goal and saved > 0:
        goal.saved_amount = min(goal.saved_amount + saved, goal.target_amount)
        goal.save(update_fields=['saved_amount'])

    if saved > 0:
        SavingsLedger.objects.create(
            person_id=pid, amount=saved, multiplier=decision['multiplier'],
            reason=decision['reason'], goal_id=goal_id,
        )

    return {'saved': saved, 'multiplier': decision['multiplier'],
            'reason': decision['reason'],
            'goal': goal.name if goal else None}


def savings_summary(pid):
    qs = SavingsLedger.objects.filter(person_id=pid)
    total = qs.aggregate(s=Sum('amount'))['s'] or 0
    by_reason = {}
    for row in qs.values('reason').annotate(s=Sum('amount')):
        by_reason[row['reason']] = row['s']
    return {'total': int(total), 'by_reason': by_reason, 'count': qs.count()}


if __name__ == '__main__':
    import json
    print(json.dumps(savings_summary(1), indent=2, default=str))
