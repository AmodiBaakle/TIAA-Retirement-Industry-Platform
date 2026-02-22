from django.contrib import admin
from Retirement_Industry.models import Profile_Info, Transaction_History, Current_Investment
# Register your models here.

admin.site.register(Profile_Info)
admin.site.register(Transaction_History)
admin.site.register(Current_Investment)
