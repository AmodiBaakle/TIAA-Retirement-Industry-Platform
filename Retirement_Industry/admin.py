from django.contrib import admin
from Retirement_Industry.models import (
    Profile_Info,
    Transaction_History,
    Current_Investment,
    Goal,
    BehaviorProfile,
    GamificationState,
    BadgeEarned,
    ChallengeProgress,
    SavingsLedger,
)
# Register your models here.

admin.site.register(Profile_Info)
admin.site.register(Transaction_History)
admin.site.register(Current_Investment)
admin.site.register(Goal)
admin.site.register(BehaviorProfile)
admin.site.register(GamificationState)
admin.site.register(BadgeEarned)
admin.site.register(ChallengeProgress)
admin.site.register(SavingsLedger)
