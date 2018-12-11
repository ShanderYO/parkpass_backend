from django.contrib import admin

from models import Admin, AdminSession


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if obj.password == 'stub' and obj.email:
            obj.create_password_and_send()
        super(AdminAdmin, self).save_model(request, obj, form, change)


@admin.register(AdminSession)
class AdminSessionAdmin(admin.ModelAdmin):
    pass
