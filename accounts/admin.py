from django.contrib import admin

# Register your models here.
from models import Account, AccountSession, EmailConfirmation


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    pass


@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(EmailConfirmation)
class EmailConfirmationAdmin(admin.ModelAdmin):
    pass