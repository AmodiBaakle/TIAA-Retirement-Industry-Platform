from django.db import models
from django.utils import timezone


# Create your models here.
class Profile_Info(models.Model):
    person_id = models.AutoField(primary_key = True)
    mail = models.EmailField(max_length=254, unique = True)
    name = models.CharField(max_length = 122)
    age = models.CharField(max_length = 122)
    work_class = models.CharField(max_length = 122)
    marital_status = models.CharField(max_length = 122)
    occupation = models.CharField(max_length = 122)
    gender = models.CharField(max_length = 122)
    salary = models.IntegerField()
    password = models.CharField(max_length = 122)

    # Module 1 - Smart Financial Profiling additions
    city = models.CharField(max_length = 122, default = '')
    fixed_expenses = models.IntegerField(default = 0)
    existing_investments = models.IntegerField(default = 0)
    debt = models.IntegerField(default = 0)
    risk_appetite = models.CharField(max_length = 20, default = 'Medium')  # Low / Medium / High
    monthly_savings_goal = models.IntegerField(default = 0)

    def __str__(self):
        return self.name


class Transaction_History(models.Model):
    transaction_id = models.AutoField(primary_key = True)
    person_id = models.IntegerField()
    transaction_name = models.CharField(max_length=122)
    transaction_amount = models.IntegerField()
    expense_category = models.CharField(max_length = 122)
    rounded_off_amount = models.IntegerField()

    # Module 2/3 - richer expense metadata for the intelligence & behaviour engines
    timestamp = models.DateTimeField(default = timezone.now)
    source = models.CharField(max_length = 20, default = 'Manual')  # UPI / Bank / SMS / Email / Card / Manual
    merchant = models.CharField(max_length = 122, default = '')
    is_impulse = models.BooleanField(default = False)
    is_subscription = models.BooleanField(default = False)

    def __str__(self):
        return self.transaction_name


class Current_Investment(models.Model):
    person_id = models.IntegerField()
    scheme_name = models.CharField(max_length=122)
    investment_amount = models.IntegerField()
    policy_term = models.CharField(max_length=500)
    date_of_investment = models.CharField(max_length = 122)
    rate_of_interest = models.IntegerField()

    def __str__(self):
        return self.scheme_name


# Module 1 / 8 - Goals (major & minor)
class Goal(models.Model):
    person_id = models.IntegerField()
    name = models.CharField(max_length = 122)
    emoji = models.CharField(max_length = 8, default = '\U0001F3AF')  # 🎯
    target_amount = models.IntegerField()
    target_months = models.IntegerField(default = 0)
    saved_amount = models.IntegerField(default = 0)
    tier = models.CharField(max_length = 10, default = 'major')  # major / minor
    created_at = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return self.name


# Module 4 - Behaviour Detection AI
class BehaviorProfile(models.Model):
    person_id = models.IntegerField()
    archetype = models.CharField(max_length = 60, default = '')
    traits_json = models.TextField(default = '{}')  # per-trait scores as JSON
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self):
        return f'{self.person_id}: {self.archetype}'


# Module 6 - Gamification Engine
class GamificationState(models.Model):
    person_id = models.IntegerField()
    xp = models.IntegerField(default = 0)
    level = models.IntegerField(default = 1)
    streak_days = models.IntegerField(default = 0)
    last_active = models.DateField(null = True, blank = True)

    def __str__(self):
        return f'{self.person_id}: L{self.level} ({self.xp} XP)'


class BadgeEarned(models.Model):
    person_id = models.IntegerField()
    badge_key = models.CharField(max_length = 60)
    earned_at = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return self.badge_key


class ChallengeProgress(models.Model):
    person_id = models.IntegerField()
    challenge_key = models.CharField(max_length = 60)
    status = models.CharField(max_length = 12, default = 'active')  # active / completed / failed
    progress = models.IntegerField(default = 0)
    target = models.IntegerField(default = 0)
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self):
        return f'{self.challenge_key} ({self.status})'


# Module 7 - Smart Savings Automation ledger
class SavingsLedger(models.Model):
    person_id = models.IntegerField()
    amount = models.IntegerField()
    multiplier = models.FloatField(default = 1.0)
    reason = models.CharField(max_length = 122, default = '')
    goal_id = models.IntegerField(null = True, blank = True)
    created_at = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return f'{self.person_id}: +{self.amount} ({self.reason})'
