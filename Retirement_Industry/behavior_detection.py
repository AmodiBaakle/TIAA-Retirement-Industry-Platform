"""Module 4 - Behaviour Detection AI.

Instead of categorising transactions, we categorise personalities. Every user
gets a behavioural profile (think Spotify Wrapped) built from rule-based trait
scores over their transaction history. Deterministic and explainable.

Public API:
    detect(pid, persist=True) -> {
        'archetype': str, 'emoji': str, 'blurb': str,
        'secondary': str,
        'traits': [ {key, label, score, note}, ... ],   # score 0-100, sorted desc
    }
"""
import json

import pandas as pd

from Retirement_Industry.models import Transaction_History, BehaviorProfile

# key -> (label, emoji, one-line description)
ARCHETYPES = {
    'weekend_warrior':        ('The Weekend Warrior', '\U0001F3C3', 'Overspends on weekends.'),
    'salary_day_hero':        ('Salary Day Hero', '\U0001F4B8', 'Spends everything within three days of payday.'),
    'midnight_shopper':       ('The Midnight Shopper', '\U0001F319', 'Late-night one-click orders.'),
    'emotional_buyer':        ('Emotional Buyer', '\U0001F62E', 'High spending after stressful weekdays.'),
    'subscription_collector': ('Subscription Collector', '\U0001F4FA', 'Pays for services never used.'),
    'incremental_overspender':('Incremental Overspender', '\U0001F4C8', 'Spending slowly increases every month.'),
    'impulse_buyer':          ('Impulse Buyer', '⚡', 'One-click purchases, little hesitation.'),
    'disciplined_saver':      ('Disciplined Saver', '\U0001F9D8', 'Maintains consistent, low-impulse habits.'),
}


def _clip(x):
    return int(max(0, min(100, round(x))))


def _load_df(pid):
    qs = Transaction_History.objects.filter(person_id=pid).values(
        'transaction_amount', 'expense_category', 'timestamp',
        'is_impulse', 'is_subscription', 'merchant',
    )
    df = pd.DataFrame(list(qs))
    if df.empty:
        return df
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df['amount'] = df['transaction_amount']
    df['dow'] = df['timestamp'].dt.dayofweek
    df['hour'] = df['timestamp'].dt.hour
    df['day'] = df['timestamp'].dt.day
    df['month'] = df['timestamp'].dt.tz_convert(None).dt.to_period('M')
    return df


def _score_traits(df):
    total = df['amount'].sum()
    scores = {}

    # Weekend Warrior: share of spend on Sat/Sun vs the 2/7 uniform baseline
    weekend_share = df[df['dow'] >= 5]['amount'].sum() / total
    scores['weekend_warrior'] = _clip((weekend_share - 2 / 7) / (2 / 7) * 140)

    # Salary Day Hero: share of spend in first 3 days vs the ~3/30 baseline
    salary_share = df[df['day'] <= 3]['amount'].sum() / total
    scores['salary_day_hero'] = _clip((salary_share - 0.1) / 0.1 * 120)

    # Midnight Shopper: share of transactions between 22:00 and 03:00
    night = df[(df['hour'] >= 22) | (df['hour'] <= 2)]
    scores['midnight_shopper'] = _clip(len(night) / len(df) * 600)

    # Emotional Buyer: spend concentration on mid-week "stress" days (Wed/Thu)
    stress_share = df[df['dow'].isin([2, 3])]['amount'].sum() / total
    scores['emotional_buyer'] = _clip((stress_share - 2 / 7) / (2 / 7) * 150)

    # Subscription Collector: number of distinct subscriptions
    n_subs = df[df['is_subscription']]['merchant'].nunique()
    scores['subscription_collector'] = _clip(n_subs / 5 * 100)

    # Impulse Buyer: share of spend flagged impulse
    impulse_share = df[df['is_impulse']]['amount'].sum() / total
    scores['impulse_buyer'] = _clip(impulse_share * 500)

    # Incremental Overspender: positive month-over-month spend trend
    monthly = df.groupby('month')['amount'].sum().sort_index()
    if len(monthly) >= 2:
        first, last = monthly.iloc[0], monthly.iloc[-1]
        growth = (last / first - 1) * 100 if first > 0 else 0
        scores['incremental_overspender'] = _clip(growth * 2)
    else:
        scores['incremental_overspender'] = 0

    # Disciplined Saver: inverse of the "risky" traits above
    risk = max(scores['impulse_buyer'], scores['midnight_shopper'],
               scores['incremental_overspender'], scores['salary_day_hero'])
    scores['disciplined_saver'] = _clip(100 - risk)

    return scores


def detect(pid, persist=True):
    df = _load_df(pid)
    if df.empty:
        return {'archetype': 'Newcomer', 'emoji': '\U0001F423', 'secondary': '',
                'blurb': 'Not enough spending data yet - add or import a few transactions.',
                'traits': []}

    scores = _score_traits(df)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    primary_key = ranked[0][0]
    secondary_key = ranked[1][0]

    label, emoji, blurb = ARCHETYPES[primary_key]
    sec_label = ARCHETYPES[secondary_key][0]

    traits = [{
        'key': k,
        'label': ARCHETYPES[k][0],
        'emoji': ARCHETYPES[k][1],
        'score': v,
        'note': ARCHETYPES[k][2],
    } for k, v in ranked]

    result = {
        'archetype': label,
        'emoji': emoji,
        'blurb': blurb,
        'secondary': sec_label,
        'traits': traits,
    }

    if persist:
        BehaviorProfile.objects.update_or_create(
            person_id=pid,
            defaults={'archetype': label, 'traits_json': json.dumps(scores)},
        )

    return result


if __name__ == '__main__':
    print(json.dumps(detect(1, persist=False), indent=2, default=str))
