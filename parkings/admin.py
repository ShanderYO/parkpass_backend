from django.contrib import admin

# Register your models here.
from models import Parking, ParkingSession, Vendor


@admin.register(Parking)
class ParkingAdmin(admin.ModelAdmin):
    pass

@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    pass

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    pass