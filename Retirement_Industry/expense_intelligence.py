"""Module 3 - Expense Intelligence Engine ("Expense Explorer AI").

Turns the raw auto-collected transaction stream into human insights and the
aggregates the dashboard charts need. Pure pandas heuristics - deterministic,
offline, no API calls.

Public API:
    generate_insights(pid) -> {
        'summary': {...},
        'insights': [ {icon, title, detail, tone}, ... ],
        'charts':   {category, day_of_week, monthly_trend, source},
    }
"""
import pandas as pd

from Retirement_Industry.models import Transaction_History

DOW_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
COFFEE_MERCHANTS = ('Starbucks', 'Cafe Coffee Day')


def _load_df(pid):
    qs = Transaction_History.objects.filter(person_id=pid).values(
        'transaction_amount', 'expense_category', 'timestamp',
        'is_impulse', 'is_subscription', 'merchant', 'source', 'rounded_off_amount',
    )
    df = pd.DataFrame(list(qs))
    if df.empty:
        return df
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df['amount'] = df['transaction_amount']
    df['date'] = df['timestamp'].dt.date
    df['dow'] = df['timestamp'].dt.dayofweek
    df['hour'] = df['timestamp'].dt.hour
    df['day'] = df['timestamp'].dt.day
    df['is_weekend'] = df['dow'] >= 5
    df['month'] = df['timestamp'].dt.tz_convert(None).dt.to_period('M')
    return df


def _avg_daily(sub):
    """Mean spend per active day for a subset."""
    if sub.empty:
        return 0.0
    return float(sub.groupby('date')['amount'].sum().mean())


def generate_insights(pid):
    df = _load_df(pid)
    if df.empty:
        return {'summary': {}, 'insights': [], 'charts': {}}

    insights = []
    months = sorted(df['month'].unique())
    this_month = months[-1]
    last_month = months[-2] if len(months) > 1 else None
    tm = df[df['month'] == this_month]

    # 1) Weekend vs weekday spending lift
    wk = _avg_daily(df[df['is_weekend']])
    wd = _avg_daily(df[~df['is_weekend']])
    if wd > 0:
        lift = (wk / wd - 1) * 100
        if abs(lift) >= 5:
            insights.append({
                'icon': '\U0001F4C5', 'tone': 'warn' if lift > 0 else 'good',
                'title': 'Weekend spending %s %.0f%%' % ('increased' if lift > 0 else 'dropped', abs(lift)),
                'detail': 'You spend ₹%.0f/day on weekends vs ₹%.0f on weekdays.' % (wk, wd),
            })

    # 2) Top spending day of week
    by_dow = df.groupby('dow')['amount'].sum()
    if not by_dow.empty:
        top_dow = int(by_dow.idxmax())
        occurrences = max(df[df['dow'] == top_dow]['date'].nunique(), 1)
        avg_on_day = by_dow[top_dow] / occurrences
        insights.append({
            'icon': '\U0001F4C6', 'tone': 'info',
            'title': 'You spend most on %ss' % DOW_NAMES[top_dow],
            'detail': '₹%.0f on an average %s - your highest of the week.' % (avg_on_day, DOW_NAMES[top_dow]),
        })

    # 3) Shopping peaks after salary day (first 3 days of month)
    luxury = df[df['expense_category'] == 'Luxury']
    if not luxury.empty:
        sal_share = luxury[luxury['day'] <= 3]['amount'].sum() / luxury['amount'].sum() * 100
        if sal_share >= 15:
            insights.append({
                'icon': '\U0001F6CD️', 'tone': 'warn',
                'title': 'Shopping peaks after salary day',
                'detail': '%.0f%% of your shopping spend lands in the first 3 days of the month.' % sal_share,
            })

    # 4) Coffee spending trend (this vs last month)
    if last_month is not None:
        coffee = df[df['merchant'].isin(COFFEE_MERCHANTS)]
        c_now = coffee[coffee['month'] == this_month]['amount'].sum()
        c_prev = coffee[coffee['month'] == last_month]['amount'].sum()
        if c_prev > 0:
            delta = (c_now / c_prev - 1) * 100
            if abs(delta) >= 10:
                insights.append({
                    'icon': '☕', 'tone': 'warn' if delta > 0 else 'good',
                    'title': 'Coffee spending %s %.0f%%' % ('increased' if delta > 0 else 'dropped', abs(delta)),
                    'detail': '₹%.0f on coffee this month vs ₹%.0f last month.' % (c_now, c_prev),
                })

    # 5) Redundant / unused subscriptions (keep the priciest per category, flag the rest)
    subs = df[df['is_subscription']].drop_duplicates('merchant')
    unused_total = 0
    unused_names = []
    for cat, grp in subs.groupby('expense_category'):
        ordered = grp.sort_values('amount', ascending=False)
        for _, row in ordered.iloc[1:].iterrows():
            unused_total += int(row['amount'])
            unused_names.append(row['merchant'])
    if unused_total > 0:
        insights.append({
            'icon': '\U0001F4B8', 'tone': 'warn',
            'title': 'Subscriptions worth ₹%d likely unused' % unused_total,
            'detail': 'Overlapping services: %s. Cancelling frees ₹%d/month.' % (
                ', '.join(unused_names), unused_total),
        })

    # 6) Impulse purchases (this month)
    impulse_count = int(tm['is_impulse'].sum())
    if impulse_count > 0:
        insights.append({
            'icon': '⚡', 'tone': 'warn',
            'title': '%d impulse purchases this month' % impulse_count,
            'detail': '₹%.0f spent on late-night / one-click buys.' % tm[tm['is_impulse']]['amount'].sum(),
        })

    summary = {
        'total_spent': int(df['amount'].sum()),
        'this_month_spent': int(tm['amount'].sum()),
        'tx_count': int(len(df)),
        'avg_daily': round(df.groupby('date')['amount'].sum().mean(), 0),
        'spare_change_saved': int(df['rounded_off_amount'].sum()),
        'impulse_count': impulse_count,
        'subscription_monthly': int(subs['amount'].sum()),
    }

    charts = {
        'category': df.groupby('expense_category')['amount'].sum().round(0).astype(int).to_dict(),
        'day_of_week': [int(by_dow.get(i, 0)) for i in range(7)],
        'monthly_trend': {str(m): int(df[df['month'] == m]['amount'].sum()) for m in months},
        'source': df.groupby('source')['amount'].sum().round(0).astype(int).to_dict(),
    }

    return {'summary': summary, 'insights': insights, 'charts': charts}


if __name__ == '__main__':
    import json
    print(json.dumps(generate_insights(1), indent=2, default=str))
