from django.contrib import admin

# Register your models here.
from models import AccountSession


@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    pass