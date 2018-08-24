from django.contrib import admin

# Register your models here.
from vendors.models import Vendor, VendorSession


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    pass


@admin.register(VendorSession)
class VendorSessionAdmin(admin.ModelAdmin):
    pass