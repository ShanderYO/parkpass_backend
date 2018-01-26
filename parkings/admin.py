from django.contrib import admin

# Register your models here.
from models import Parking

@admin.register(Parking)
class ParkingAdmin(admin.ModelAdmin):
    pass