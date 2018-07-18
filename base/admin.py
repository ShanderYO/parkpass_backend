from django.contrib import admin

# Register your models here.
from models import Terminal, EmailConfirmation


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    pass


@admin.register(EmailConfirmation)
class EmailConfirmationAdmin(admin.ModelAdmin):
    pass