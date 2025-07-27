from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from django.utils.html import format_html

from payments_reports.models import (
    ParkingPaymentReport,
    ParkingPaymentReportTransaction,
)
from payments_reports.services import OwnersPaymentsReports


@admin.register(ParkingPaymentReport)
class ParkingPaymentReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "parking",
        "company",
        "period_start",
        "period_end",
        "payout_amount",
        "is_sent",
        "download_xls_link",
    )
    readonly_fields = ("download_xls_link",)
    inlines = []

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:report_id>/download_xls/",
                self.admin_site.admin_view(self.download_xls),
                name="download_report_xls",
            ),
        ]
        return custom_urls + urls

    def download_xls_link(self, obj):
        return format_html(
            '<a class="button" href="{}">Скачать XLS</a>',
            f"{obj.id}/download_xls/",
        )

    download_xls_link.short_description = "Экспорт в XLS"
    download_xls_link.allow_tags = True

    def download_xls(self, request, report_id):
        report = self.get_object(request, report_id)
        xls_path = OwnersPaymentsReports.export_report_to_xls(report)
        with open(xls_path, "rb") as f:
            xls_data = f.read()
        response = HttpResponse(xls_data, content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = (
            f'attachment; filename="report_{report_id}.xls"'
        )
        return response


@admin.register(ParkingPaymentReportTransaction)
class ParkingPaymentReportTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "report",
        "parking",
        "amount",
        "commission_percent",
        "amount_after_commission",
        "date_time",
        "transaction_type",
    )
    list_filter = ("parking", "transaction_type")
