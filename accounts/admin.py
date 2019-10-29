from django.contrib import admin

from base.admin import AccountAdmin
from .models import Account, AccountSession


@admin.register(Account)
class AccountAdmin(AccountAdmin):
    search_fields = ('id', 'phone', 'last_name',)

    list_display = ('id', 'first_name', 'last_name',
                    'phone', 'email')

    readonly_fields = ('phone', 'email', 'sms_code', 'created_at', )

    exclude_fields = ('avatar', 'email_confirmation')


@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'expired_at',)