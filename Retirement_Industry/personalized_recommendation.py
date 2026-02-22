from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import LabelEncoder
from Retirement_Industry.models import Profile_Info, Transaction_History, Current_Investment
import pandas as pd
import os
from datetime import datetime
import random

schemes_data = pd.read_csv(os.getcwd()+'\\static\\Schemes.csv', encoding='unicode_escape')

features = schemes_data[['Entry_Age_min', 'Enty_Age_max', 'Exit_Age', 'Minimum_amount_to_Invest _yearly', 'Return_rate']]
target = schemes_data['Pension_Plans_in_India']

knn_model = NearestNeighbors(n_neighbors=5)
knn_model.fit(features, target)

def calculate_age(birthdate):
    birthdate = datetime.strptime(birthdate, '%Y-%m-%d')
    current_date = datetime.now()
    age = current_date.year - birthdate.year - ((current_date.month, current_date.day) < (birthdate.month, birthdate.day))
    return age

def recommend_schemes(age, salary, occupation, work_class, gender):
    query = [[age, salary, occupation, work_class, gender]]

    distances, indices = knn_model.kneighbors(query)
    recommended_schemes = schemes_data.iloc[indices[0]]['Pension_Plans_in_India'].tolist()

    output = []
    for i in recommended_schemes:
        filtered_rows = (schemes_data[schemes_data['Pension_Plans_in_India'] == i]).values.tolist()
        data = dict()
        data['scheme_name'] = i 
        data['min_entry_age'] = filtered_rows[0][1]
        data['max_entry_age'] = filtered_rows[0][2]
        data['policy_term'] = filtered_rows[0][4]
        data['minimum_investment'] = filtered_rows[0][5]
        data['return_rate'] = filtered_rows[0][7]
        data['url'] = filtered_rows[0][-1]
        output.append(data)
        random.shuffle(output) 
    return output

def main(pid):
    person = (Profile_Info.objects.get(person_id = pid))
    age = calculate_age(str(person.age))
    salary = int(person.salary)
    occupation = person.occupation
    work_class = person.work_class
    gender = person.gender
    recommended_age_based = recommend_schemes(age=age, salary=salary, occupation=2, work_class = 0, gender =0)  
    recommended_salary_based = recommend_schemes(age=age, salary=salary, occupation=3, work_class = 0, gender =0)
    recommended_occupation_based = recommend_schemes(age=age, salary=salary, occupation=4, work_class = 0, gender =0)
    # Format Output
    output = {
        'Age': recommended_age_based,
        'Salary': recommended_salary_based,
        'Occupation': recommended_occupation_based
    }
    # Print or return the output in the specified format
    print(output)
    return output


# def main(pid):
#     return {'Salary':[{'scheme_name':'Scheme 1', 
#                         'min_entry_age': 18,
#                         'max_entry_age': 60,
#                         'policy_term': 'this is gibberish',
#                         'minimum_investment': 500,
#                         'return_rate': 8}],
#             'Occupation':[{'scheme_name':'Scheme 2', 
#                         'min_entry_age': 18,
#                         'max_entry_age': 60,
#                         'policy_term': 'this is gibberish',
#                         'minimum_investment': 500,
#                         'return_rate': 8}],
#             'Age': [{'scheme_name':'Scheme 3', 
#                         'min_entry_age': 18,
#                         'max_entry_age': 60,
#                         'policy_term': 'this is gibberish',
#                         'minimum_investment': 500,
#                         'return_rate': 8}]}

