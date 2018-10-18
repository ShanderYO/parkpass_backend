from django.contrib import admin

from parkings.models import UpgradeIssue
from vendors.models import Vendor, VendorSession, Issue


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["display_id", "first_name", "last_name"]
    list_filter = ["account_state", "created_at"]
    fieldsets = (
        ('General', {
            'fields': ('display_id', 'account_state',)
        }),
        ('Finance', {
            'fields': ('comission', )
        }),
        ('Security', {
            'fields': ('name', 'secret',)
        }),
        ('More', {
            'fields': ('first_name', 'last_name', 'phone' , 'email',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.secret == 'stub':
            obj.generate_secret()
        if obj.password == 'stub':
            obj.create_password_and_send()
        super(VendorAdmin, self).save_model(request, obj, form, change)


@admin.register(VendorSession)
class VendorSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(UpgradeIssue)
class UpgradeIssueAdmin(admin.ModelAdmin):
    list_display = ["id", "type", "status", "description"]
    list_filter = ["type", "status", "vendor", "owner"]


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "comment"]
