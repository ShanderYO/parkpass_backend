from django.contrib import admin

# Register your models here.
from payments.models import (
    CreditCard, TinkoffPayment, Order,
    FiskalNotification, InvoiceWithdraw,
    HomeBankPayment, HomeBankFiskalNotification)

@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    search_fields = ('account', 'id', 'card_id',)

    list_display = ('id', 'account', 'card_id',
                     'pan', 'exp_date',)

    readonly_fields = ('account','card_id', 'pan',
                       'exp_date', 'rebill_id', 'created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    search_fields = ('session__session_id', 'id',)

    list_display = ('id', 'session', 'sum',
                    'authorized', 'paid',)

    readonly_fields = ('sum', 'session',
                       'fiscal_notification', 'created_at',)


@admin.register(TinkoffPayment)
class TinkoffPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'status', 'order',
                    'error_code', 'created_at',)


@admin.register(HomeBankPayment)
class HomeBankPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'status', 'order',
                    'reason_code', 'created_at',)

@admin.register(HomeBankFiskalNotification)
class HomeBankFiskalNotificationAdmin(admin.ModelAdmin):
    pass

@admin.register(FiskalNotification)
class FiskalNotificationAdmin(admin.ModelAdmin):
    pass


@admin.register(InvoiceWithdraw)
class InvoiceWithdrawAdmin(admin.ModelAdmin):
    pass

