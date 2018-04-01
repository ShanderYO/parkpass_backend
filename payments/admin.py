from django.contrib import admin

# Register your models here.
from models import CreditCard, TinkoffPayment, Order


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    pass

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    pass

@admin.register(TinkoffPayment)
class TinkoffPaymentAdmin(admin.ModelAdmin):
    pass