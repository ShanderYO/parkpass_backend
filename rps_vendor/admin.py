from django.contrib import admin

# Register your models here.
from models import RpsParking

@admin.register(RpsParking)
class RpsParkingAdmin(admin.ModelAdmin):
    pass