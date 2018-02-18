from django.contrib import admin

# Register your models here.
from models import Account, AccountSession, AccountParkingSession, PaidDebt

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    pass

@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    pass

@admin.register(AccountParkingSession)
class AccountParkingSessionAdmin(admin.ModelAdmin):
    pass

@admin.register(PaidDebt)
class PaidDebtAdmin(admin.ModelAdmin):
    pass