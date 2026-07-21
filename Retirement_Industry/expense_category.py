"""Expense categoriser (Daily / Basic / Luxury / Entertainment).

Real merchant names are matched with keyword rules first (the ML model was
trained on a tiny synthetic vocabulary that doesn't include names like Swiggy
or Amazon). For names that ARE in the training vocabulary we fall back to the
RandomForest model; otherwise we default to 'Basic'. Robust to a missing or
incompatible model file - it will simply lean on the rules.
"""
import os

import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder

_STATIC = os.path.join(os.getcwd(), 'static')

try:
    _df = pd.read_csv(os.path.join(_STATIC, 'expense_dataset_extended.csv'))
    _cat_enc = LabelEncoder().fit(_df['expense_category'])
    _name_enc = LabelEncoder().fit(_df['expense_name'])
    _known_names = set(_df['expense_name'])
except Exception:
    _cat_enc = _name_enc = None
    _known_names = set()

try:
    _model = joblib.load(os.path.join(_STATIC, 'expense_category_model.pkl'))
except Exception:
    _model = None

# keyword -> category for real-world merchant names used across the app
_RULES = [
    (('grocer', 'bigbasket', 'more supermarket', 'milk', 'supermarket', 'kirana',
      'vegetable', 'pharmacy', 'medical', 'metro', 'fuel', 'petrol', 'electricity',
      'rent', 'utilit', 'recharge'), 'Daily'),
    (('swiggy', 'zomato', 'restaurant', 'dining', 'cafe', 'coffee', 'starbucks',
      'food', 'uber', 'ola', 'stationary', 'insurance', 'education'), 'Basic'),
    (('amazon', 'flipkart', 'myntra', 'nykaa', 'jewell', 'electronics', 'apple',
      'shopping', 'gadget'), 'Luxury'),
    (('netflix', 'spotify', 'prime', 'hotstar', 'pvr', 'bookmyshow', 'movie',
      'game', 'cinema', 'disney'), 'Entertainment'),
]


def _rule_category(name):
    low = (name or '').lower()
    for keys, cat in _RULES:
        if any(k in low for k in keys):
            return cat
    return None


def main(name, amount):
    cat = _rule_category(name)
    if cat:
        return cat
    if _model is not None and name in _known_names:
        try:
            enc = _name_enc.transform([name])[0]
            pred = _model.predict([[enc, amount]])
            return _cat_enc.inverse_transform(pred)[0]
        except Exception:
            pass
    return 'Basic'


if __name__ == '__main__':
    for n in ['Swiggy', 'Amazon', 'BigBasket Groceries', 'Netflix', 'Unknown Shop']:
        print(n, '->', main(n, 500))
