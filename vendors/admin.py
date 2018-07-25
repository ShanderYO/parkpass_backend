from django.contrib import admin

# Register your models here.
from vendors.models import Vendor, VendorSession, Issue, UpgradeIssue


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if obj.secret == 'stub':
            obj.generate_secret()
        if obj.password == 'stub':
            obj.create_password_and_send()
        super(VendorAdmin, self).save_model(request, obj, form, change)


@admin.register(VendorSession)
class VendorSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    pass


@admin.register(UpgradeIssue)
class UpgradeIssueAdmin(admin.ModelAdmin):
    pass
