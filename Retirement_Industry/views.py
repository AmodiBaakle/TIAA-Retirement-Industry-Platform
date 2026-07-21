import json
import os

import pandas as pd
from django.core.management import call_command
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.utils import timezone

from Retirement_Industry.models import (
    Profile_Info, Transaction_History, Current_Investment, Goal,
)
from Retirement_Industry.auto_roundoff import main as am
from Retirement_Industry.expense_category import main as cm
from Retirement_Industry.personalized_recommendation import main as pm
from Retirement_Industry import (
    expense_intelligence, behavior_detection, goal_engine, nudge_engine,
    gamification, smart_savings, portfolio_ai, financial_coach,
)


def _pid(request):
    return request.session.get('pid')


# ------------------------------------------------------------------ auth
def index(request):
    if _pid(request):
        return redirect('/dashboard')
    return render(request, 'landing.html')


def enter_info(request):
    if request.method == 'POST':
        mail = request.POST.get('mail')
        if Profile_Info.objects.filter(mail=mail).exists():
            return render(request, 'register.html',
                          {'error': 'An account with %s already exists. Please log in.' % mail,
                           'data': request.POST})
        try:
            person = Profile_Info.objects.create(
                name=request.POST.get('name'), mail=mail,
                password=request.POST.get('password'),
                age=str(request.POST.get('age') or ''),
                city=request.POST.get('city') or '',
                occupation=request.POST.get('occupation') or '',
                work_class=request.POST.get('work_class') or 'Private',
                marital_status=request.POST.get('marital_status') or 'Single',
                gender=request.POST.get('gender') or '',
                salary=int(request.POST.get('salary') or 0),
                fixed_expenses=int(request.POST.get('fixed_expenses') or 0),
                existing_investments=int(request.POST.get('existing_investments') or 0),
                debt=int(request.POST.get('debt') or 0),
                risk_appetite=request.POST.get('risk_appetite') or 'Medium',
                monthly_savings_goal=int(request.POST.get('monthly_savings_goal') or 0),
            )
        except IntegrityError:
            return render(request, 'register.html',
                          {'error': 'An account with %s already exists. Please log in.' % mail})

        # optional first goal
        gname = request.POST.get('goal_name')
        if gname:
            Goal.objects.create(
                person_id=person.person_id, name=gname, emoji=request.POST.get('goal_emoji') or '🎯',
                target_amount=int(request.POST.get('goal_amount') or 0),
                target_months=int(request.POST.get('goal_months') or 0),
                tier='major')

        request.session['pid'] = person.person_id
        request.session['mail'] = mail
        return redirect('/dashboard')
    return render(request, 'register.html', {'data': {}})


def login(request):
    if request.method == 'POST':
        mail = request.POST.get('mail')
        pwd = request.POST.get('pwd')
        people = Profile_Info.objects.filter(mail=mail).order_by('-person_id')
        if not people:
            return render(request, 'login.html', {'error': 'No account found for that email.'})
        match = next((p for p in people if p.password == pwd), None)
        if match:
            request.session['pid'] = match.person_id
            request.session['mail'] = mail
            return redirect('/dashboard')
        return render(request, 'login.html', {'error': 'Incorrect password.'})
    return render(request, 'login.html')


def logout(request):
    request.session.flush()
    return redirect('/')


def load_sample(request):
    """Populate the current user with a synthetic transaction stream + goals."""
    pid = _pid(request)
    if not pid:
        return redirect('/')
    call_command('seed_transactions', '--pid', str(pid), '--clear', '--goals', '--days', '75')
    behavior_detection.detect(pid)
    return redirect('/dashboard')


# ------------------------------------------------------------------ app pages
def dashboard(request):
    pid = _pid(request)
    if not pid:
        return redirect('/')
    intel = expense_intelligence.generate_insights(pid)
    goals = goal_engine.goal_progress(pid)
    savings = smart_savings.savings_summary(pid)
    portfolio = portfolio_ai.recommend_allocation(pid)
    ctx = {
        'summary': intel['summary'],
        'insights': intel['insights'][:3],
        'goals': goals[:3],
        'nudges': nudge_engine.daily_nudges(pid),
        'savings_total': savings['total'],
        'archetype': behavior_detection.detect(pid),
        'allocation': portfolio['allocation'],
        'has_data': intel['summary'] != {},
    }
    return render(request, 'dashboard.html', ctx)


def expenses(request):
    """Merged add-expense + transaction history on a single page."""
    pid = _pid(request)
    if not pid:
        return redirect('/')

    if request.method == 'POST':
        name = request.POST.get('name')
        try:
            ta = int(request.POST.get('transaction_amount'))
        except (TypeError, ValueError):
            return redirect('/expenses')
        category = cm(name, ta)
        rm = am(name, ta, category)
        Transaction_History.objects.create(
            person_id=pid, transaction_name=name, transaction_amount=ta,
            expense_category=category, rounded_off_amount=rm,
            timestamp=timezone.now(), source='Manual', merchant=name)
        smart_savings.apply_savings(pid, rm)
        gamification.record_activity(pid)
        gamification.award_xp(pid, 10, 'Logged an expense')
        request.session['last_nudge'] = nudge_engine.purchase_nudge(pid, ta, name)
        return redirect('/expenses')

    txns = Transaction_History.objects.filter(person_id=pid).order_by('-timestamp', '-transaction_id')
    rows, total_spent, total_saved = [], 0, 0
    for t in txns:
        total_spent += t.transaction_amount
        total_saved += t.rounded_off_amount
        rows.append(t)
    ctx = {
        'txns': rows,
        'total_spent': total_spent,
        'total_saved': total_saved,
        'count': len(rows),
        'nudge': request.session.pop('last_nudge', None),
    }
    return render(request, 'expenses.html', ctx)


def intelligence(request):
    pid = _pid(request)
    if not pid:
        return redirect('/')
    intel = expense_intelligence.generate_insights(pid)
    ctx = {
        'summary': intel['summary'],
        'insights': intel['insights'],
        'charts_json': json.dumps(intel['charts']),
        'has_data': bool(intel['insights']),
    }
    return render(request, 'intelligence.html', ctx)


def personality(request):
    pid = _pid(request)
    if not pid:
        return redirect('/')
    return render(request, 'personality.html', {'profile': behavior_detection.detect(pid)})


def goals(request):
    pid = _pid(request)
    if not pid:
        return redirect('/')
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Goal.objects.create(
                person_id=pid, name=name, emoji=request.POST.get('emoji') or '🎯',
                target_amount=int(request.POST.get('target_amount') or 0),
                target_months=int(request.POST.get('target_months') or 0),
                saved_amount=int(request.POST.get('saved_amount') or 0),
                tier=request.POST.get('tier') or 'major')
        return redirect('/goals')
    ctx = {
        'goals': goal_engine.goal_progress(pid),
        'capacity': goal_engine.monthly_savings_capacity(pid),
    }
    return render(request, 'goals.html', ctx)


def challenges(request):
    pid = _pid(request)
    if not pid:
        return redirect('/')
    ctx = {
        'state': gamification.get_state(pid),
        'badges': gamification.evaluate_badges(pid),
        'challenges': gamification.active_challenges(pid),
        'leaderboard': gamification.leaderboard(10),
    }
    return render(request, 'challenges.html', ctx)


def portfolio(request):
    pid = _pid(request)
    if not pid:
        return redirect('/')

    if request.method == 'POST':
        scheme_name = request.POST.get('scheme_name')
        inv_amt = request.POST.get('investment_amount') or 0
        roi = request.POST.get('roi') or 0
        Current_Investment.objects.create(
            person_id=pid, scheme_name=scheme_name, investment_amount=inv_amt,
            policy_term='Not Applicable', date_of_investment=str(timezone.now()),
            rate_of_interest=roi)
        return redirect('/portfolio')

    rec = portfolio_ai.recommend_allocation(pid)
    try:
        schemes = pm(pid)
    except Exception:
        schemes = {}
    investments = Current_Investment.objects.filter(person_id=pid)
    ctx = {
        'allocation': rec['allocation'],
        'equity_appetite': rec['equity_appetite'],
        'rationale': rec['rationale'],
        'drivers': rec['drivers'],
        'alloc_json': json.dumps([{'label': a['label'], 'pct': a['pct'], 'color': a['color']}
                                  for a in rec['allocation']]),
        'schemes': schemes.get('Salary', [])[:3] if schemes else [],
        'investments': investments,
    }
    return render(request, 'portfolio.html', ctx)


def coach(request):
    pid = _pid(request)
    if not pid:
        return redirect('/')
    return render(request, 'coach.html', financial_coach.weekly_report(pid))


def profile(request):
    pid = _pid(request)
    if not pid:
        return redirect('/')
    person = Profile_Info.objects.filter(person_id=pid).first()
    if not person:
        return redirect('/')
    return render(request, 'profile.html', {'p': person, 'behavior': behavior_detection.detect(pid)})
