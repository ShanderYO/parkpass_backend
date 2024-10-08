from django.contrib import admin

# Register your models here.
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Parking, ParkingSession,
    ComplainSession,
    TopParkingWish, ProblemParkingSessionNotifierSettings, Service, ParkingValetSession, ParkingValetSessionRequest)


@admin.register(Parking)
class ParkingModelAdmin(admin.ModelAdmin):
    search_fields = ('name', 'address',)

    list_display = ('name', 'city', 'address', 'domain',
                    'enabled', 'approved', 'parkpass_status',)

    list_filter = ('approved', 'enabled', 'parkpass_status',
                   'city', 'vendor', 'owner', 'domain')

    readonly_fields = ('tariff_download_link',)

    def tariff_download_link(self, obj):
        return obj.get_tariff_link()


@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    search_fields = ('session_id',)

    list_filter = ('parking', 'started_at',
                   'completed_at', 'client',)

    list_display = ('session_id', 'client', 'parking',
                    'state', 'is_suspended', 'get_debt', 'duration',)

    exclude_fields = ('created_at',)

    readonly_fields = ('started_at', 'duration', 'extra_data', 'is_send_warning_non_closed_message', 'paid')

    def get_debt(self, obj):
        return obj.get_debt()

    def duration(self, obj):
        return "%d:%02d" % (obj.duration // 60, obj.duration % 60)


@admin.register(ComplainSession)
class ComplainSessionAdmin(admin.ModelAdmin):
    list_display = ('type', 'account', 'session',)


@admin.register(TopParkingWish)
class TopParkingWishAdmin(admin.ModelAdmin):
    list_display = ('parking', 'count',)


@admin.register(ProblemParkingSessionNotifierSettings)
class ProblemParkingSessionNotifierSettingsAdmin(admin.ModelAdmin):
    list_display = ("report_emails", "last_email_send_date", "available")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(ParkingValetSession)
class ParkingValetSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'parking', 'state', 'car_number', 'car_model', 'valet_card_id', 'parking_card', 'parking_place', 'debt', 'started_at')
    search_fields = ( 'id', 'valet_card_id', 'car_number')
    readonly_fields = ["started_at", "updated_at"]
    # readonly_fields = ["started_at", "updated_at", "parking_card_session", 'car_delivered_by', 'responsible', 'created_by_user', 'parking_card', 'parking']

@admin.register(ParkingValetSessionRequest)
class ParkingValetSessionRequestAdmin(admin.ModelAdmin):

    def link_to_session(self, obj):
        link = reverse("admin:parkings_parkingvaletsession_change", args=[obj.valet_session_id])
        return format_html('<a href="{}">Valet session №{}</a>', link, obj.valet_session.id)

    list_display = ('__str__', 'link_to_session', 'status', 'created_at')
    search_fields = ('id', 'valet_session')