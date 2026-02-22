from django.shortcuts import render, redirect, HttpResponse
from Retirement_Industry.models import Profile_Info, Transaction_History, Current_Investment
from Retirement_Industry.auto_roundoff import main as am
from Retirement_Industry.expense_category import main as cm
from Retirement_Industry.personalized_recommendation import main as pm
import pandas as pd
from django.utils import timezone
import os

def index(request):
    if request.method == 'POST':
        print('login' in request.POST)
        if 'login' in request.POST:
            return redirect('/login')
        else: 
            return redirect('/enter_info')
    return render(request, 'index.html')

def enter_info(request):
    if request.method == 'GET':
        global mail
        mail = request.GET.get('mail')
        if mail:
            p_name = request.GET.get('name')
            age = str(request.GET.get('age'))
            wc = request.GET.get('work_class')
            ms = request.GET.get('marital_status')
            occ = request.GET.get('occupation')
            gender = request.GET.get('gender')
            salary = int(request.GET.get('salary'))
            pwd = request.GET.get('password')
            details = Profile_Info(name = p_name, mail = mail, age = age, work_class = wc, marital_status = ms, occupation = occ, gender = gender, salary = salary, password = pwd)
            details.save()
            return redirect('/dashboard')
        else:
            return render(request, 'enter_info.html')

def login(request):
    if request.method == 'POST':
        global mail
        mail = request.POST.get('mail')
        entered_password = request.POST.get('pwd')
        pwd = (Profile_Info.objects.get(mail = mail)).password
        if pwd == entered_password:
            return redirect('/dashboard')
    return render(request, 'login.html')

def pay(request):
    global mail
    try: 
        pid = (Profile_Info.objects.get(mail = mail)).person_id
        if request.method == 'POST':
            pid = (Profile_Info.objects.get(mail = mail)).person_id
            name = request.POST.get('name')
            ta = int(request.POST.get('transaction_amount'))
            category = cm(name, ta)
            rm = am(name, ta, category)
            details = Transaction_History(person_id=pid, transaction_name = name, transaction_amount = ta, expense_category=category, rounded_off_amount = rm)
            details.save()
            return redirect('/wallet')
        return render(request, 'pay.html')
    except Exception as e:
        print(e) 
        return redirect('/')

def dashboard(request):
    global mail
    try:
        pid = (Profile_Info.objects.get(mail = mail)).person_id
        df = pd.read_csv(os.getcwd() + '\\static\\Schemes.csv', encoding='unicode_escape')
        context = dict()
        if request.method == 'POST':
            scheme_name = request.POST.get('scheme_name')
            inv_amt = str(request.POST.get('investment_amount'))
            roi = request.POST.get('roi')
            print(scheme_name)
            for index, row in df.iterrows():
                try: 
                    if scheme_name in row['Pension_Plans_in_India']:
                        pt = row.Policy_Term
                except: pt = 'Not Applicable'
            details = Current_Investment(person_id = pid, scheme_name = scheme_name, investment_amount = inv_amt, policy_term = pt, date_of_investment = str(timezone.now()),rate_of_interest = roi)
            details.save()

        context['Current_data'] = []
        try:
            current_inv = (Current_Investment.objects.filter(person_id = pid))
            for row in current_inv:
                data = dict()
                data['name'] = row.scheme_name
                data['inv_amt'] = row.investment_amount
                data['tenure'] = row.policy_term
                data['id'] = row.date_of_investment
                context['Current_data'].append(data)     
        except Exception as e:
            print("inner: ", e)
            context['Current_data'].append({'name':'No Schemes', 'inv_amt':'-', 'tenure':'-', 'id':'-'})
        context['Recommendation'] = pm(pid)

        return render(request, 'dashboard.html', context)
    except Exception as e:
        print('outer: ', e) 
        return redirect('/')

def wallet(request):
    global mail
    try:
        pid = (Profile_Info.objects.get(mail = mail)).person_id
        transaction_details = (Transaction_History.objects.filter(person_id = pid))
        context = dict()
        save = 0
        for i in transaction_details:
            save+= i.rounded_off_amount
        context['Savings'] = save
        context['Data'] = []
        for row in transaction_details:
            data = dict()
            data['tn'] = row.transaction_name
            data['ta'] = row.transaction_amount
            data['ec'] = row.expense_category
            data['ro'] = row.rounded_off_amount
            context['Data'].append(data)     
        print(context)
        return render(request, 'wallet.html', context)
    except: return redirect('/')

def profile(request):
    global mail
    try:
        person_data = Profile_Info.objects.get(mail = mail)
        data = dict()
        data['name'] = person_data.name
        data['mail'] = person_data.mail
        data['dob'] = person_data.age
        data['wc'] = person_data.work_class
        data['ms'] = person_data.marital_status
        data['occ'] = person_data.occupation
        data['gender'] = person_data.gender
        data['salary'] = person_data.salary
        context = {'Data': data}
        return render(request, 'profile.html', context)
    except: return redirect('/')