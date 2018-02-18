from django.contrib import admin

# Register your models here.
from models import Parking, ParkingSession

@admin.register(Parking)
class ParkingAdmin(admin.ModelAdmin):
    pass

@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    pass