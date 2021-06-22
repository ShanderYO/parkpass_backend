from django.contrib import admin

from parkings.models import Parking
from rps_vendor.models import (
    RpsParking, ParkingCard, RpsParkingCardSession, RpsSubscription, Developer, DevelopersLog
)


@admin.register(RpsParking)
class RpsParkingAdmin(admin.ModelAdmin):
    pass


@admin.register(ParkingCard)
class ParkingCardAdmin(admin.ModelAdmin):
    search_fields = ('card_id', 'phone',)

    list_filter = ('created_at',)

    list_display = ('card_id', 'phone', 'created_at',)

    readonly_fields = ('card_id', 'created_at', 'phone',)


@admin.register(RpsParkingCardSession)
class RpsParkingCardSessionAdmin(admin.ModelAdmin):
    search_fields = ('parking_card__card_id',)

    list_filter = ('created_at', 'parking_id',)

    list_display = ('parking_card', 'client_uuid', 'account', 'debt', 'state', 'get_parking')

    readonly_fields = ('parking_id', 'client_uuid', 'created_at',)

    def get_parking(self, obj):
        return Parking.objects.get(id=obj.parking_id)


@admin.register(RpsSubscription)
class RpsSubscriptionAdmin(admin.ModelAdmin):
    search_fields = ('name', 'parking', 'account',)

    list_filter = ('started_at', 'expired_at', 'parking',)

    list_display = ('name', 'parking', 'account', 'active', 'prolongation',)

    readonly_fields = ('name', 'description', 'data',
                       'idts', 'id_transition', 'duration',)


@admin.register(Developer)
class DeveloperAdmin(admin.ModelAdmin):
    search_fields = ('name', 'email', 'is_blocked',)

    list_display = ('name', 'email', 'is_blocked',)

    readonly_fields = ('api_key', 'developer_id',)


@admin.register(DevelopersLog)
class DevelopersLogAdmin(admin.ModelAdmin):
    search_fields = ('parking_card_id',)

    list_display = ('parking', 'parking_card_id', 'developer', 'type', 'debt', 'status', 'created_at', )

    readonly_fields = ('parking', 'parking_card_id', 'developer', 'type', 'debt', 'status', 'created_at', )