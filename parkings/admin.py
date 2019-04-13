from django.contrib import admin

# Register your models here.
from .models import (
    Parking, ParkingSession,
    ComplainSession, Wish
)


@admin.register(Parking)
class ParkingModelAdmin(admin.ModelAdmin):
    search_fields = ('name', 'client',)

    list_display = ('name', 'city', 'address',
                    'enabled', 'approved', 'parkpass_status',)

    list_filter = ('city', 'enabled', 'approved',
                   'parkpass_status', 'vendor', 'owner',)

    readonly_fields = ('tariff_download_link',)

    def tariff_download_link(self, obj):
        return obj.get_tariff_link()


@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    search_fields = ('session_id', 'client',)

    list_filter = ('parking', 'started_at',
                   'completed_at', 'client',)

    list_display = ('session_id', 'client', 'parking',
                    'state', 'is_suspended', 'debt', 'duration')

    exclude_fields = ('created_at',)

    readonly_fields = ('duration', 'extra_data')


@admin.register(ComplainSession)
class ComplainSessionAdmin(admin.ModelAdmin):
    list_display = ('type', 'account', 'session',)


@admin.register(Wish)
class WantedParkingAdmin(admin.ModelAdmin):
    list_display = ('parking', 'user',)