from django.contrib import admin

from base.admin import AccountAdmin
from models import Admin, AdminSession


@admin.register(Admin)
class AdminAdmin(AccountAdmin):
    pass


@admin.register(AdminSession)
class AdminSessionAdmin(admin.ModelAdmin):
    pass
