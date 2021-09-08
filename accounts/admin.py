from django.contrib import admin
from django.utils.html import format_html

from base.admin import AccountAdmin
from payments.models import CreditCard
from .models import Account, AccountSession


@admin.register(Account)
class AccountAdmin(AccountAdmin):
    search_fields = ('id', 'phone', 'last_name', 'email')

    list_display = ('id', 'first_name', 'last_name',
                    'phone', 'email', 'sms_verified', 'bank_card')

    readonly_fields = ('phone', 'email', 'sms_code', 'created_at', )

    exclude_fields = ('avatar', 'email_confirmation')

    def bank_card(self, obj):
        credit_cards = CreditCard.objects.filter(account_id=obj.id)

        if credit_cards:
            str = ''
            for card in credit_cards:
                str += "<a target='_blank' href='/api/admin/payments/creditcard/%s'>%s</a><br>" % (card.id, card.pan)
            return format_html(str)
        # return credit_cards

@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'expired_at',)
