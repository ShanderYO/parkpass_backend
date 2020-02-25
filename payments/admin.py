from django.contrib import admin

# Register your models here.
<<<<<<< HEAD
from .models import CreditCard, TinkoffPayment, Order, FiskalNotification
=======
from payments.models import (
    CreditCard, TinkoffPayment, Order,
    FiskalNotification, InvoiceWithdraw
)
>>>>>>> 7fdbb28b0983c82f55bf488c7b4dd7cad1b0aba3


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    search_fields = ('account', 'id', 'card_id',)

    list_display = ('id', 'account', 'card_id',
                     'pan', 'exp_date',)

    readonly_fields = ('account','card_id', 'pan',
                       'exp_date', 'rebill_id', 'created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    search_fields = ('session',)

    list_display = ('id', 'session', 'sum',
                    'authorized', 'paid',)

    readonly_fields = ('sum', 'session',
                       'fiscal_notification', 'created_at',)


@admin.register(TinkoffPayment)
class TinkoffPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'status', 'order',
                    'error_code', 'created_at',)


@admin.register(FiskalNotification)
class FiskalNotificationAdmin(admin.ModelAdmin):
    pass


@admin.register(InvoiceWithdraw)
class InvoiceWithdrawAdmin(admin.ModelAdmin):
    pass