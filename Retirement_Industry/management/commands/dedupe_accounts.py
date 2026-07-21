"""Collapse duplicate-email accounts down to one per email.

The legacy database allowed multiple Profile_Info rows to share an email. This
keeps, for each email, the single most useful account (most transactions, then
highest person_id) and deletes the rest along with their orphaned related rows.

Usage:
    python manage.py dedupe_accounts            # show what would change
    python manage.py dedupe_accounts --apply    # actually delete
"""
from collections import defaultdict

from django.core.management.base import BaseCommand

from Retirement_Industry.models import (
    Profile_Info, Transaction_History, Current_Investment, Goal,
    BehaviorProfile, GamificationState, BadgeEarned, ChallengeProgress,
    SavingsLedger,
)

RELATED = [
    Transaction_History, Current_Investment, Goal, BehaviorProfile,
    GamificationState, BadgeEarned, ChallengeProgress, SavingsLedger,
]


class Command(BaseCommand):
    help = 'Keep one account per email; delete duplicates and their data.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Perform the deletion (default is a dry run).')

    def handle(self, *args, **opts):
        by_mail = defaultdict(list)
        for p in Profile_Info.objects.all():
            by_mail[p.mail].append(p)

        to_delete = []
        for mail, people in by_mail.items():
            if len(people) < 2:
                continue
            # rank: most transactions wins, tie-break on highest person_id
            def score(p):
                return (Transaction_History.objects.filter(person_id=p.person_id).count(),
                        p.person_id)
            keeper = max(people, key=score)
            losers = [p for p in people if p.person_id != keeper.person_id]
            self.stdout.write('%s -> keep pid %d (%d txns), drop %s' % (
                mail, keeper.person_id,
                Transaction_History.objects.filter(person_id=keeper.person_id).count(),
                [p.person_id for p in losers]))
            to_delete.extend(losers)

        if not to_delete:
            self.stdout.write(self.style.SUCCESS('No duplicate emails found.'))
            return

        if not opts['apply']:
            self.stdout.write(self.style.WARNING(
                'Dry run - %d accounts would be removed. Re-run with --apply.' % len(to_delete)))
            return

        for p in to_delete:
            pid = p.person_id
            for model in RELATED:
                model.objects.filter(person_id=pid).delete()
            p.delete()
        self.stdout.write(self.style.SUCCESS('Removed %d duplicate accounts.' % len(to_delete)))
