"""Retrain the expense-category model under the currently-installed scikit-learn.

The shipped .pkl was trained on scikit-learn 1.3.2 and raises
'... object has no attribute monotonic_cst' when predicted under newer
versions. This regenerates a compatible model from the CSV that ships with the
repo. Run once after changing the scikit-learn version.

Usage:
    python manage.py retrain_models
"""
import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Retrain the expense-category model for the current scikit-learn.'

    def handle(self, *args, **opts):
        static = os.path.join(os.getcwd(), 'static')
        df = pd.read_csv(os.path.join(static, 'expense_dataset_extended.csv'))

        cat_enc = LabelEncoder()
        name_enc = LabelEncoder()
        df['encoded_category'] = cat_enc.fit_transform(df['expense_category'])
        df['encoded_name'] = name_enc.fit_transform(df['expense_name'])

        X = df[['encoded_name', 'expense_amount']]
        y = df['encoded_category']

        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X, y)

        out = os.path.join(static, 'expense_category_model.pkl')
        joblib.dump(clf, out)
        self.stdout.write(self.style.SUCCESS(
            'Retrained expense-category model (%d rows, %d classes) -> %s'
            % (len(df), len(cat_enc.classes_), out)))
