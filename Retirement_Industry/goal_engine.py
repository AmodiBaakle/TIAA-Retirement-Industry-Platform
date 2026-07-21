"""Module 8 - Goal Achievement Engine.

Makes saving emotional: progress bars, ETAs, and the killer "this purchase
delays your Goa trip by 2 days" nudge that ties every expense back to a goal.

Public API:
    monthly_savings_capacity(pid) -> int          # ₹/month the user can save
    goal_progress(pid)           -> [ {..per goal..} ]
    purchase_delay(pid, amount)  -> {days, goal_name, goal_emoji} | None
"""
import math

from django.db.models import Sum

from Retirement_Industry.models import (
    Profile_Info, Transaction_History, Goal, SavingsLedger,
)


def monthly_savings_capacity(pid):
    """Best estimate of what the user saves per month.

    Priority: their declared monthly goal -> actual auto-saved run-rate ->
    a conservative 8% of salary fallback. Always returns a positive number.
    """
    try:
        person = Profile_Info.objects.get(person_id=pid)
    except Profile_Info.DoesNotExist:
        person = None

    # 1) an explicit target always wins
    if person and person.monthly_savings_goal:
        return int(person.monthly_savings_goal)

    # 2) actual auto-saved run-rate (spare change + Module 7 auto-savings)
    spare = Transaction_History.objects.filter(person_id=pid).aggregate(
        s=Sum('rounded_off_amount'))['s'] or 0
    auto = SavingsLedger.objects.filter(person_id=pid).aggregate(
        s=Sum('amount'))['s'] or 0
    span = Transaction_History.objects.filter(person_id=pid).order_by('timestamp')
    run_rate = 0
    if span.exists():
        days = max((span.last().timestamp - span.first().timestamp).days, 1)
        run_rate = (spare + auto) / days * 30

    # 3) income-based baseline (surplus after fixed expenses, capped at 15% of salary)
    baseline = 0
    if person and person.salary:
        surplus = person.salary - (person.fixed_expenses or 0)
        baseline = max(surplus, 0) * 0.15 if surplus > 0 else person.salary * 0.10

    return int(max(run_rate, baseline, 1000))


def goal_progress(pid):
    goals = Goal.objects.filter(person_id=pid).order_by('-target_amount')
    capacity = monthly_savings_capacity(pid)
    # split capacity evenly across active (unfinished) goals for ETA projection
    active = [g for g in goals if g.saved_amount < g.target_amount]
    per_goal_monthly = capacity / len(active) if active else capacity

    out = []
    for g in goals:
        remaining = max(g.target_amount - g.saved_amount, 0)
        pct = min(round(g.saved_amount / g.target_amount * 100), 100) if g.target_amount else 0
        required_monthly = round(g.target_amount / g.target_months) if g.target_months else 0
        months_at_rate = math.ceil(remaining / per_goal_monthly) if per_goal_monthly and remaining else 0
        on_track = required_monthly <= per_goal_monthly if required_monthly else True

        out.append({
            'id': g.id,
            'name': g.name,
            'emoji': g.emoji,
            'tier': g.tier,
            'target_amount': g.target_amount,
            'saved_amount': g.saved_amount,
            'remaining': remaining,
            'pct': pct,
            'target_months': g.target_months,
            'required_monthly': required_monthly,
            'projected_months': months_at_rate,
            'on_track': on_track,
            'complete': remaining == 0,
        })
    return out


def purchase_delay(pid, amount):
    """How many days a given spend pushes back the user's top active goal."""
    capacity = monthly_savings_capacity(pid)
    daily = capacity / 30.0
    if daily <= 0:
        return None

    active = [g for g in Goal.objects.filter(person_id=pid).order_by('-target_amount')
              if g.saved_amount < g.target_amount]
    if not active:
        return None
    goal = active[0]

    days = math.ceil(amount / daily)
    return {'days': days, 'goal_name': goal.name, 'goal_emoji': goal.emoji}


if __name__ == '__main__':
    import json
    print('capacity/mo:', monthly_savings_capacity(1))
    print(json.dumps(goal_progress(1), indent=2, default=str))
    print('delay for ₹2000:', purchase_delay(1, 2000))
