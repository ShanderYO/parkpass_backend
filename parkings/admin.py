from django.contrib import admin

# Register your models here.
from .models import (
    Parking, ParkingSession,
    ComplainSession, Wish
)


@admin.register(Parking)
class ParkingModelAdmin(admin.ModelAdmin):
    readonly_fields = ('tariff_download_link',)

    def tariff_download_link(self, obj):
        return obj.get_tariff_link()


@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(ComplainSession)
class ComplainSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(Wish)
class WantedParkingAdmin(admin.ModelAdmin):
    pass