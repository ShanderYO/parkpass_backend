from django.contrib import admin

# Register your models here.
from models import Account, AccountSession


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if obj.password == 'stub':
            obj.create_password_and_send()
        super(AccountAdmin, self).save_model(request, obj, form, change)


@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    pass