from django.contrib import admin

from models import Admin, AdminSession


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    pass


@admin.register(AdminSession)
class AdminSessionAdmin(admin.ModelAdmin):
    pass
