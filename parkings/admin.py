from django.contrib import admin

# Register your models here.
from .models import (
    Parking, ParkingSession,
    ComplainSession,
    TopParkingWish)


@admin.register(Parking)
class ParkingModelAdmin(admin.ModelAdmin):
    search_fields = ('name', 'address',)

    list_display = ('name', 'city', 'address',
                    'enabled', 'approved', 'parkpass_status',)

    list_filter = ('approved', 'enabled', 'parkpass_status',
                   'city', 'vendor', 'owner',)

    readonly_fields = ('tariff_download_link',)

    def tariff_download_link(self, obj):
        return obj.get_tariff_link()


@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    search_fields = ('session_id',)

    list_filter = ('parking', 'started_at',
                   'completed_at', 'client',)

    list_display = ('session_id', 'client', 'parking',
                    'client_state', 'debt', 'duration',)

    exclude_fields = ('created_at',)

    readonly_fields = ('started_at', 'duration', 'extra_data',)

    def duration(self, obj):
        return "%d:%02d" % (obj.duration // 60, obj.duration % 60)


@admin.register(ComplainSession)
class ComplainSessionAdmin(admin.ModelAdmin):
    list_display = ('type', 'account', 'session',)


@admin.register(TopParkingWish)
class TopParkingWishAdmin(admin.ModelAdmin):
    list_display = ('parking', 'count',)
