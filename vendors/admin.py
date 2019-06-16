from django.contrib import admin
from django.core.exceptions import ValidationError

from base.admin import AccountAdmin
from vendors.models import Vendor, VendorSession, VendorIssue, VendorNotification


@admin.register(Vendor)
class VendorAdmin(AccountAdmin):
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
            'fields': ('first_name', 'last_name', 'phone' , 'email', 'fetch_extern_user_data_url',)
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


@admin.register(VendorIssue)
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


@admin.register(VendorNotification)
class VendorNotificationAdmin(admin.ModelAdmin):
    search_fields = ('parking_session',)

    list_filter = ('type', 'created_at',)

    list_display = ('type', 'confirmed', 'created_at',)

    readonly_fields = ('type', 'message', 'created_at',)

    def confirmed(self, obj):
        return bool(obj.confirmed_at is not None)