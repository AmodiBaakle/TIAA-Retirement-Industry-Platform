"""Module 9 - AI Portfolio Recommendation.

Unlike a traditional robo-advisor, the allocation is driven by BOTH the
financial profile (age, salary, debt, risk appetite) AND the behavioural
profile (saving discipline vs impulse/overspending). This makes the portfolio
dynamic: the same salary/age produces a safer mix for an impulsive spender and
a more aggressive mix for a disciplined saver.

Public API:
    recommend_allocation(pid) -> {
        'allocation': [ {label, pct, color, note}, ... ],  # sums to 100
        'equity_appetite': int, 'drivers': {...}, 'rationale': [str, ...],
    }
"""
from Retirement_Industry.models import Profile_Info
from Retirement_Industry import behavior_detection
from Retirement_Industry.personalized_recommendation import calculate_age

BUCKETS = [
    ('Emergency Fund', '#f59e0b'),
    ('Index Funds', '#3b82f6'),
    ('Gold ETF', '#eab308'),
    ('Liquid Fund', '#14b8a6'),
    ('Stocks', '#8b5cf6'),
]

NOTES = {
    'Emergency Fund': 'Safety net for 3-6 months of expenses.',
    'Index Funds': 'Low-cost, diversified long-term growth.',
    'Gold ETF': 'Inflation hedge and diversifier.',
    'Liquid Fund': 'Instant-access cash for short-term needs.',
    'Stocks': 'Higher-risk, higher-reward equity exposure.',
}

RISK_BASE = {'Low': 0.25, 'Medium': 0.50, 'High': 0.80}


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def recommend_allocation(pid):
    person = Profile_Info.objects.get(person_id=pid)
    age = calculate_age(person.age)
    risk = person.risk_appetite if person.risk_appetite in RISK_BASE else 'Medium'
    salary = int(person.salary or 0)
    debt = int(person.debt or 0)

    # behavioural signal (0-100 trait scores)
    traits = {t['key']: t['score'] for t in behavior_detection.detect(pid, persist=False)['traits']}
    discipline = traits.get('disciplined_saver', 50)
    risky = max(traits.get('impulse_buyer', 0),
                traits.get('midnight_shopper', 0),
                traits.get('incremental_overspender', 0),
                traits.get('salary_day_hero', 0))
    behavior_tilt = (discipline - risky) / 100.0            # -1 .. 1

    # equity appetite blends risk appetite, age (younger => more), behaviour
    risk_factor = RISK_BASE[risk]
    age_factor = _clamp((100 - age) / 100.0)
    behavior_factor = _clamp(0.5 + behavior_tilt / 2)
    equity_appetite = _clamp((risk_factor + age_factor + behavior_factor) / 3)

    # debt raises the need for safety
    annual = salary * 12 if salary else 0
    debt_ratio = _clamp(debt / annual, 0, 1) if annual else (0.3 if debt else 0)
    safety_need = _clamp(1 - equity_appetite + debt_ratio * 0.3)

    weights = {
        'Stocks': equity_appetite * 35,
        'Index Funds': equity_appetite * 40 + 8,
        'Gold ETF': 12 + (4 if risk == 'Low' else 0),
        'Emergency Fund': safety_need * 28 + debt_ratio * 10 + 8,
        'Liquid Fund': safety_need * 14 + 4,
    }

    total = sum(weights.values())
    pcts = {k: round(v / total * 100) for k, v in weights.items()}
    # fix rounding drift so it sums to exactly 100
    drift = 100 - sum(pcts.values())
    if drift:
        biggest = max(pcts, key=pcts.get)
        pcts[biggest] += drift

    allocation = [{
        'label': label, 'pct': pcts[label], 'color': color, 'note': NOTES[label],
    } for label, color in BUCKETS]

    rationale = []
    rationale.append('%s risk appetite at age %d sets a %d%% equity tilt.' % (
        risk, age, round(equity_appetite * 100)))
    if behavior_tilt > 0.15:
        rationale.append('Strong saving discipline earns a higher Index/Stocks weight.')
    elif behavior_tilt < -0.15:
        rationale.append('Impulsive spending pattern shifts weight to Emergency & Liquid funds.')
    else:
        rationale.append('Balanced spending behaviour keeps a middle-of-the-road mix.')
    if debt_ratio > 0.2:
        rationale.append('Outstanding debt increases the safety allocation.')

    return {
        'allocation': allocation,
        'equity_appetite': round(equity_appetite * 100),
        'drivers': {
            'risk': risk, 'age': age, 'debt_ratio': round(debt_ratio * 100),
            'discipline': discipline, 'risky': risky,
        },
        'rationale': rationale,
    }


if __name__ == '__main__':
    import json
    print(json.dumps(recommend_allocation(1), indent=2, default=str))
