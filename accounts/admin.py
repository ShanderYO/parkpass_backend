from django.contrib import admin

# Register your models here.
from models import Account, AccountSession, AccountParkingSession

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    pass

@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    pass

@admin.register(AccountParkingSession)
class AccountParkingSessionAdmin(admin.ModelAdmin):
    pass