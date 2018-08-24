from django.contrib import admin

# Register your models here.
from models import Account, AccountSession


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if not obj.ven_name:
            obj.ven_name = obj.phone
        if obj.password == "stub" and (obj.email != "" or obj.phone != ""):
            obj.create_password_and_send()
        if obj.ven_secret == "":
            obj.generate_secret()
        super(AccountAdmin, self).save_model(request, obj, form, change)
    pass


@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    pass