from django.contrib import admin
from .models import (
    ParkingReportConfig,
    ParkingPaymentReport,
    ParkingPaymentReportTransaction,
    PayoutHistory,
)


@admin.register(ParkingReportConfig)
class ParkingReportConfigAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "parking",
        "commission_percent",
        "payout_periodicity",
        "auto_send",
    )
    search_fields = ("parking__name", "owner__email", "recipient_name", "inn")
    list_filter = ("payout_periodicity", "auto_send")
    readonly_fields = ("id",)
    list_display_links = ("id", "parking")


@admin.register(ParkingPaymentReport)
class ParkingPaymentReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "period_start",
        "period_end",
        "created_at",
        "last_sent_at",
        "total_amount",
        "total_refunds",
        "total_commission",
        "payout_amount",
        "is_sent",
    )
    search_fields = ("owner__email",)
    list_filter = ("is_sent", "created_at")
    readonly_fields = (
        "id",
        "created_at",
        "last_sent_at",
        "total_amount",
        "total_refunds",
        "total_commission",
        "payout_amount",
    )
    list_display_links = ("id", "owner")


@admin.register(ParkingPaymentReportTransaction)
class ParkingPaymentReportTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "report",
        "parking",
        "tinkoff_payment",
        "date_time",
        "amount",
        "transaction_type",
        "commission_percent",
        "amount_after_commission",
    )
    search_fields = ("report__id", "parking__name", "tinkoff_payment__id")
    list_filter = ("transaction_type", "parking")
    readonly_fields = ("id",)
    list_display_links = ("id", "report")


@admin.register(PayoutHistory)
class PayoutHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "report",
        "invoice_withdraw",
        "sent_at",
        "status",
        "error_message",
    )
    search_fields = ("report__id", "invoice_withdraw__id")
    list_filter = ("status", "sent_at")
    readonly_fields = ("id", "sent_at")
    list_display_links = ("id", "report")
