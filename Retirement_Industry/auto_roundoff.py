"""Spare-change round-off (the base amount Module 7's smart-savings scales).

Rounding up to the nearest ₹10 and saving the difference is deterministic
arithmetic, so this needs no model - which also removes a slow per-call
joblib.load of a large pickle. Signature kept as (name, amount, expense_category)
for backwards compatibility with existing callers.
"""
import math


def main(name, amount, expense_category=None):
    amount = float(amount)
    spare = int(math.ceil(amount / 10.0) * 10 - amount)
    # if the amount is already a round ₹10, still nudge a small saving
    return spare if spare > 0 else 10


if __name__ == '__main__':
    for a in [216, 379, 500, 649]:
        print(a, '-> spare', main('Test', a))
