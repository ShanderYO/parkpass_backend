from django.contrib import admin

from rps_vendor.models import (
    RpsParking, ParkingCard, RpsParkingCardSession, RpsSubscription
)


@admin.register(RpsParking)
class RpsParkingAdmin(admin.ModelAdmin):
    pass


@admin.register(ParkingCard)
class ParkingCardAdmin(admin.ModelAdmin):
    pass


@admin.register(RpsParkingCardSession)
class RpsParkingCardSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(RpsSubscription)
class RpsSubscriptionAdmin(admin.ModelAdmin):
    pass
