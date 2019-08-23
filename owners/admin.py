from django.contrib import admin
from django.core.exceptions import ValidationError

from base.admin import AccountAdmin
from owners.models import *


@admin.register(Owner)
class OwnerAdmin(AccountAdmin):
    list_display = ['name', 'first_name', 'last_name']
    pass


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    pass


@admin.register(OwnerSession)
class OwnerSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(OwnerApplication)
class OwnerApplicationAdmin(admin.ModelAdmin):
    pass


@admin.register(OwnerIssue)
class IssueAdmin(admin.ModelAdmin):
    actions = ["accept_issue", "reject_issue"]
    list_display = ["name", "email", "phone"]

    def accept_issue(self, request, queryset):
        for issue in queryset:
            try:
                issue.accept()
            except ValidationError:
                self.message_user(request, '%s issue was not accepted: ValidationError' % issue)

    accept_issue.short_description = 'Accept these issues'

    def reject_issue(self, request, queryset):
        queryset.delete()

    reject_issue.short_description = 'Reject these issues'


@admin.register(CompanySettingReports)
class CompanySettingReports(admin.ModelAdmin):
    pass