from django.contrib import admin

# Register your models here.
from models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    pass
