from django.contrib import admin

from models import Admin, AdminSession


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    actions = ['make_hashed_password']
    def save_model(self, request, obj, form, change):
        if obj.password == 'stub' and obj.email:
            obj.create_password_and_send()
        super(AdminAdmin, self).save_model(request, obj, form, change)

    def make_hashed_password(self, request, queryset):
        for account in queryset:
            account.make_hashed_password()
            account.save()


@admin.register(AdminSession)
class AdminSessionAdmin(admin.ModelAdmin):
    pass
