from django.contrib import admin

# Register your models here.
from notifications.models import AccountDevice


@admin.register(AccountDevice)
class AccountDeviceAdmin(admin.ModelAdmin):
    search_fields = ('account',)

    list_display = ('account', 'type', 'active',)

    readonly_fields = ('type',)

    exclude_fields = ('user', 'name',)
