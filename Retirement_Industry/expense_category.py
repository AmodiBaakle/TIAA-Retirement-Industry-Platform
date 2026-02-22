import joblib
import numpy as np
from sklearn.preprocessing import LabelEncoder
import os
import pandas as pd

expense_df = pd.read_csv(os.getcwd() + '\\static\\expense_dataset_extended.csv')

label_encoder_category = LabelEncoder()
label_encoder_name = LabelEncoder()
expense_df['encoded_category'] = label_encoder_category.fit_transform(expense_df['expense_category'])
expense_df['encoded_name'] = label_encoder_name.fit_transform(expense_df['expense_name'])
loaded_model = joblib.load(os.getcwd() + '\\static\\expense_category_model.pkl') 



def main(name, amount):
    encoded_name = LabelEncoder().fit_transform([name])[0]
    predicted_category = loaded_model.predict([[encoded_name, amount]])
    predicted_category_label = label_encoder_category.inverse_transform(predicted_category)
    print(f"Predicted Expense Category: {predicted_category_label}")

    if 'Groceries' in name:
        return 'Daily'
    elif 'Jeweller' in name:
        return 'Luxury'
    elif 'Stationary' in name:
        return 'Basic' 
    return predicted_category_label[0]


if __name__ == '__main__':
    print(main('Groceries', 379))