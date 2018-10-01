from django.contrib import admin

from owners.models import *


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if obj.password == 'stub' and obj.email:
            obj.create_password_and_send()
        super(OwnerAdmin, self).save_model(request, obj, form, change)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    pass


@admin.register(OwnerSession)
class OwnerSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(UpgradeIssue)
class UpgradeIssueAdmin(admin.ModelAdmin):
    pass
