from django.contrib import admin

from base.admin import AccountAdmin
# Register your models here.
from models import Account, AccountSession


@admin.register(Account)
class AccountAdmin(AccountAdmin):
    pass


@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    pass