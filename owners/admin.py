from django.contrib import admin
from django.core.exceptions import ValidationError

from base.admin import AccountAdmin
from owners.models import *


def accept_issue(issue):
    owner = Owner(
        phone=issue.phone,
        email=issue.email,
        name=issue.name,
    )
    owner.full_clean()
    owner.save()
    owner.create_password_and_send()
    issue.delete()
    return owner


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    actions = ["accept_issue", "reject_issue"]
    list_display = ["name", "email", "phone"]

    def accept_issue(self, request, queryset):
        for issue in queryset:
            try:
                accept_issue(issue)
            except ValidationError:
                self.message_user(request, '%s issue was not accepted: ValidationError' % issue)

    accept_issue.short_description = 'Accept these issues'

    def reject_issue(self, request, queryset):
        queryset.delete()

    reject_issue.short_description = 'Reject these issues'


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


@admin.register(UpgradeIssue)
class UpgradeIssueAdmin(admin.ModelAdmin):
    pass
