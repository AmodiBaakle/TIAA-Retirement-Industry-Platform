import joblib
import numpy as np
import os

def main(name, amount, expense_category):
    loaded_model = joblib.load(os.getcwd() +'\\static\\auto_round_off_model.pkl') 

    if expense_category == 'Daily':
        expense_category = 0
    elif expense_category == 'Basic':
        expense_category = 1
    elif expense_category == 'Luxury':
        expense_category = 2
    elif expense_category == 'Entertainment':
        expense_category = 3
    input_data = np.array([[amount]])
    rounded_amount = loaded_model.predict(input_data)

    print(f"Predicted Rounded-off Amount: {rounded_amount[0]}")

    return rounded_amount[0]

if __name__ =='__main__':
    print(main('Groceries', 379, 'Daily'))