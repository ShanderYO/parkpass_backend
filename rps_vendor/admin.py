from django.contrib import admin
from import_export import resources
from import_export.admin import ExportActionMixin
from import_export.fields import Field

from parkings.models import Parking
from rps_vendor.models import (
    RpsParking, ParkingCard, RpsParkingCardSession, RpsSubscription, Developer, DevelopersLog, DEVELOPER_LOG_TYPES,
    DEVELOPER_STATUS_TYPES
)


@admin.register(RpsParking)
class RpsParkingAdmin(admin.ModelAdmin):
    list_display = ('parking', 'domain', 'token', 'token_expired', 'integrator_id', 'integrator_password')
    search_fields = ('parking__name', 'domain', 'integrator_id')


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
    search_fields = ('name', 'account__id',)

    list_filter = ('started_at', 'expired_at', 'parking',)

    list_display = ('name', 'parking', 'account', 'active', 'prolongation',)

    readonly_fields = ('name', 'description', 'data',
                       'idts', 'id_transition', 'duration',)


@admin.register(Developer)
class DeveloperAdmin(admin.ModelAdmin):
    search_fields = ('name', 'email', 'is_blocked',)

    list_display = ('name', 'email', 'is_blocked',)

    readonly_fields = ('api_key', 'developer_id',)


class DevelopersLogResource(resources.ModelResource):

    type = Field()
    status = Field()

    class Meta:

        model = DevelopersLog

        export_order = ( 'parking__parking__name', 'developer__name', 'type', 'debt', 'status', 'created_at')

        fields = ( 'parking__parking__name', 'developer__name', 'type', 'debt', 'status', 'created_at')

    def dehydrate_type(self, item):
        type = getattr(item, "type", "unknown")
        return str(next((x for x in DEVELOPER_LOG_TYPES
                                          if x[0] == int(type)), ['', '-'])[1])


    def dehydrate_status(self, item):
        status = getattr(item, "status", "unknown")
        return str(next((x for x in DEVELOPER_STATUS_TYPES
                                          if x[0] == int(status)), ['', '-'])[1])

@admin.register(DevelopersLog)
class DevelopersLogAdmin(ExportActionMixin, admin.ModelAdmin):

    resource_class = DevelopersLogResource

    search_fields = ('parking_card_id',)

    list_display = ('parking', 'parking_card_id', 'developer', 'type', 'debt', 'status', 'created_at', )

    readonly_fields = ('parking', 'parking_card_id', 'developer', 'type', 'debt', 'status', 'created_at', )

    list_filter = (
        ('parking', admin.RelatedOnlyFieldListFilter),
        'type'
    )

    list_per_page = 100