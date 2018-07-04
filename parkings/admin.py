from django.contrib import admin

# Register your models here.
from models import Parking, ParkingSession, ComplainSession, WantedParking


@admin.register(Parking)
class ParkingAdmin(admin.ModelAdmin):
    pass


@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(ComplainSession)
class ComplainSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(WantedParking)
class WantedParkingAdmin(admin.ModelAdmin):
    pass