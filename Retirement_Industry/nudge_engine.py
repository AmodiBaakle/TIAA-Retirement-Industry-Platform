"""Module 5 - Behavioural Nudge Engine.

Where AI becomes psychological. Instead of "You spent ₹800", we say
"Skipping this order today gets you 2 days closer to your MacBook."

Public API:
    purchase_nudge(pid, amount, name='') -> {icon, text, tone}
        The nudge shown at the moment of spending.
    daily_nudges(pid) -> [ {icon, text, tone, xp} ]
        Contextual nudges for the dashboard (streaks, challenge proximity,
        impulse praise, behaviour-based tips).
"""
from django.utils import timezone

from Retirement_Industry import goal_engine, gamification
from Retirement_Industry.models import Transaction_History, BehaviorProfile


def purchase_nudge(pid, amount, name=''):
    """Frame a potential purchase against the user's top goal."""
    delay = goal_engine.purchase_delay(pid, amount)
    label = ('this %s order' % name) if name else 'this purchase'
    if delay:
        return {
            'icon': delay['goal_emoji'], 'tone': 'warn',
            'text': 'Skipping %s today gets you %d day%s closer to your %s.' % (
                label, delay['days'], '' if delay['days'] == 1 else 's', delay['goal_name']),
        }
    return {
        'icon': '\U0001F4B8', 'tone': 'info',
        'text': 'That is ₹%d of spare change you could be saving.' % amount,
    }


def daily_nudges(pid):
    nudges = []
    state = gamification.get_state(pid)

    # 1) Streak encouragement
    if state['streak'] >= 2:
        nudges.append({
            'icon': '\U0001F525', 'tone': 'good', 'xp': None,
            'text': '%d-day saving streak. Keep it alive today!' % state['streak'],
        })

    # 2) Challenge proximity - "you're only ₹450 away..."
    for ch in gamification.active_challenges(pid):
        if not ch['done'] and ch['pct'] >= 50:
            remaining = ch['target'] - ch['progress']
            unit = '₹%d' % remaining if ch['unit'] == 'rupees' else '%d %s' % (remaining, ch['unit'])
            nudges.append({
                'icon': ch['emoji'], 'tone': 'info', 'xp': None,
                'text': "You're only %s away from completing '%s'." % (unit, ch['title']),
            })
            break

    # 3) Impulse-avoidance praise (no impulse buy yesterday)
    yesterday = (timezone.now() - timezone.timedelta(days=1)).date()
    had_impulse = Transaction_History.objects.filter(
        person_id=pid, is_impulse=True,
        timestamp__year=yesterday.year, timestamp__month=yesterday.month,
        timestamp__day=yesterday.day,
    ).exists()
    if not had_impulse:
        nudges.append({
            'icon': '\U0001F44F', 'tone': 'good', 'xp': 50,
            'text': 'Yesterday you avoided an impulse purchase. Amazing consistency. \U0001F525 +50 XP',
        })

    # 4) Behaviour-based tip
    bp = BehaviorProfile.objects.filter(person_id=pid).first()
    tips = {
        'The Midnight Shopper': 'Late-night carts cost more. Try a "sleep on it" rule after 10pm.',
        'Impulse Buyer': 'Add a 24-hour wait before any one-click buy over ₹1000.',
        'Subscription Collector': 'Cancel one overlapping subscription this week to free up cash.',
        'Salary Day Hero': 'Auto-move savings the day salary lands, before it disappears.',
        'The Weekend Warrior': 'Set a weekend spending cap - your weekends run hot.',
    }
    if bp and bp.archetype in tips:
        nudges.append({
            'icon': '\U0001F9E0', 'tone': 'info', 'xp': None,
            'text': tips[bp.archetype],
        })

    return nudges


if __name__ == '__main__':
    import json
    print('purchase:', purchase_nudge(1, 800, 'Amazon'))
    print(json.dumps(daily_nudges(1), indent=2, default=str))
