from django.contrib import admin

# Register your models here.
from models import CreditCard


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    pass