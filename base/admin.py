from django.contrib import admin

# Register your models here.
from models import Terminal


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    pass
