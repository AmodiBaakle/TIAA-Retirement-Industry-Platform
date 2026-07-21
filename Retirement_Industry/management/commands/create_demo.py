"""Create a polished, coherent demo account for the pitch.

Idempotent: deletes any existing demo account and rebuilds it with a realistic
financial profile, a seeded 75-day transaction stream, goals with progress, a
detected money personality, and a lively gamification state (XP, streak, badges).

Usage:
    python manage.py create_demo
Credentials printed on completion.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from Retirement_Industry.models import (
    Profile_Info, Transaction_History, Current_Investment, Goal,
    BehaviorProfile, GamificationState, BadgeEarned, ChallengeProgress,
    SavingsLedger,
)
from Retirement_Industry import behavior_detection, gamification

DEMO_MAIL = 'demo@tara.app'
DEMO_PASSWORD = 'demo123'

RELATED = [
    Transaction_History, Current_Investment, Goal, BehaviorProfile,
    GamificationState, BadgeEarned, ChallengeProgress, SavingsLedger,
]

# a few auto-savings ledger entries so the "Auto-saved" stat reads non-zero
LEDGER = [
    (40, 5.0, 'Salary just landed - saving 5x the spare change'),
    (8, 1.0, 'Steady month - standard round-off'),
    (6, 1.0, 'Steady month - standard round-off'),
    (16, 2.0, 'New Headphones is almost funded - doubling your round-off'),
    (9, 1.0, 'Steady month - standard round-off'),
    (35, 5.0, 'Salary just landed - saving 5x the spare change'),
    (7, 1.0, 'Steady month - standard round-off'),
    (14, 2.0, 'New Headphones is almost funded - doubling your round-off'),
]


class Command(BaseCommand):
    help = 'Create a polished demo account for the pitch.'

    def handle(self, *args, **opts):
        # wipe any existing demo account + data
        existing = list(Profile_Info.objects.filter(mail=DEMO_MAIL))
        for p in existing:
            for model in RELATED:
                model.objects.filter(person_id=p.person_id).delete()
            p.delete()

        person = Profile_Info.objects.create(
            name='Aarav Mehta', mail=DEMO_MAIL, password=DEMO_PASSWORD,
            age='28', city='Mumbai', occupation='Product Manager',
            work_class='Private', marital_status='Single', gender='Male',
            salary=90000, fixed_expenses=38000, monthly_savings_goal=15000,
            existing_investments=150000, debt=0, risk_appetite='Medium',
        )
        pid = person.person_id

        # 75-day synthetic stream + goals with progress
        call_command('seed_transactions', '--pid', str(pid), '--clear', '--goals', '--days', '75')

        # money personality
        result = behavior_detection.detect(pid)

        # gamification: lively but believable
        state, _ = GamificationState.objects.get_or_create(person_id=pid)
        state.xp = 2100
        state.streak_days = 12
        state.last_active = timezone.now().date()
        state.level = gamification.level_info(state.xp)[0]
        state.save()

        # auto-savings ledger
        for amount, mult, reason in LEDGER:
            SavingsLedger.objects.create(person_id=pid, amount=amount,
                                         multiplier=mult, reason=reason)

        badges = [b['label'] for b in gamification.evaluate_badges(pid) if b['earned']]

        self.stdout.write(self.style.SUCCESS('\nDemo account ready!'))
        self.stdout.write('  Email:    %s' % DEMO_MAIL)
        self.stdout.write('  Password: %s' % DEMO_PASSWORD)
        self.stdout.write('  Personality: %s %s' % (result['emoji'], result['archetype']))
        self.stdout.write('  Level %d · %d XP · %d-day streak' % (state.level, state.xp, state.streak_days))
        self.stdout.write('  Badges: %s' % ', '.join(badges))
        self.stdout.write('  Transactions: %d · Goals: %d'
                          % (Transaction_History.objects.filter(person_id=pid).count(),
                             Goal.objects.filter(person_id=pid).count()))
