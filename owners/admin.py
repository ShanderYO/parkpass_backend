from django.contrib import admin

from owners.models import Owner, OwnerSession


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    pass


@admin.register(OwnerSession)
class OwnerSessionAdmin(admin.ModelAdmin):
    pass
