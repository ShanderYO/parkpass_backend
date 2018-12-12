from django.contrib import admin

# Register your models here.
from models import Terminal, EmailConfirmation


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    pass


@admin.register(EmailConfirmation)
class EmailConfirmationAdmin(admin.ModelAdmin):
    pass


class AccountAdmin(admin.ModelAdmin):
    actions = ['make_hashed_password']

    def save_model(self, request, obj, form, change):
        if obj.password == 'stub' and obj.email:
            obj.create_password_and_send()
        super(AccountAdmin, self).save_model(request, obj, form, change)

    def make_hashed_password(self, request, queryset):
        for account in queryset:
            account.make_hashed_password()
            account.save()
