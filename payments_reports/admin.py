from django.contrib import admin, messages
from django import forms
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.http import HttpResponse

from .models import (
    ParkingReportConfig,
    ParkingPaymentReport,
    ParkingPaymentReportTransaction,
    PayoutHistory,
)
from .services import OwnersPaymentsReports


# --- Форма для отчёта ParkingPaymentReport ---
class ParkingPaymentReportForm(forms.ModelForm):
    class Meta:
        model = ParkingPaymentReport
        fields = "__all__"
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "owner" in self.fields:
            self.fields["owner"].widget = forms.HiddenInput()
            self.fields["owner"].required = False

        if "company" in self.fields:
            self.fields["company"].widget = forms.HiddenInput()

        if "commission_percent" in self.fields:
            self.fields["commission_percent"].widget = forms.HiddenInput()

        from payments_reports.models import ParkingReportConfig

        allowed_parkings = ParkingReportConfig.objects.values_list(
            "parking_id", flat=True
        )
        if "parking" in self.fields:
            self.fields["parking"].queryset = self.fields["parking"].queryset.filter(
                id__in=allowed_parkings
            )


# --- Форма для конфигурации ParkingReportConfig ---
class ParkingReportConfigForm(forms.ModelForm):
    class Meta:
        model = ParkingReportConfig
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].widget = forms.HiddenInput()
        self.fields["company"].widget = forms.HiddenInput()


class ParkingPaymentReportTransactionInline(admin.TabularInline):
    model = ParkingPaymentReportTransaction
    extra = 0
    readonly_fields = (
        "parking",
        "tinkoff_payment",
        "date_time",
        "amount",
        "transaction_type",
        "commission_percent",
        "amount_after_commission",
    )
    can_delete = False
    show_change_link = False


@admin.register(ParkingReportConfig)
class ParkingReportConfigAdmin(admin.ModelAdmin):
    form = ParkingReportConfigForm

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
    change_form_template = "admin/parkingreportconfig_change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/generate-report/",
                self.admin_site.admin_view(self.generate_report),
                name="payments_reports_parkingreportconfig_generate_report",
            ),
        ]
        return custom_urls + urls

    def generate_report(self, request, pk, *args, **kwargs):
        config = self.get_object(request, pk)
        if not config:
            self.message_user(request, "Config not found.", level=messages.ERROR)
            return redirect("..")

        report = OwnersPaymentsReports.generate_report_for_parking(
            parking=config.parking,
            period_start=None,
            period_end=None,
        )

        if report:
            self.message_user(
                request, f"Отчет успешно создан: {report.id}", level=messages.SUCCESS
            )
        else:
            self.message_user(
                request, "Не удалось создать отчет.", level=messages.WARNING
            )
        return redirect("..")

    def render_change_form(self, request, context, *args, **kwargs):
        obj = context.get("original")
        if obj:
            context["additional_button"] = format_html(
                '<a class="button" href="{}">Сформировать отчет</a>',
                f"{obj.pk}/generate-report/",
            )
        return super().render_change_form(request, context, *args, **kwargs)

    def save_model(self, request, obj, form, change):
        if obj.parking:
            obj.owner = obj.parking.owner
            obj.company = obj.parking.company
        else:
            self.message_user(request, "Выберите парковку", level=messages.ERROR)
            return
        super().save_model(request, obj, form, change)


@admin.register(ParkingPaymentReport)
class ParkingPaymentReportAdmin(admin.ModelAdmin):
    form = ParkingPaymentReportForm
    inlines = [ParkingPaymentReportTransactionInline]

    list_display = (
        "id",
        "parking",
        "commission_percent",
        "period_start",
        "period_end",
        "last_sent_at",
        "total_amount",
        "total_refunds",
        "total_commission",
        "payout_amount",
        "is_sent",
        "download_xls_link",
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
        "is_sent",
        "owner",
        "commission_percent",
        "company",
        "download_xls_link",
    )
    list_display_links = ("id", "parking")

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj is None:
            fields = [f for f in fields if f != "is_sent"]
        return fields

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        return super().get_inline_instances(request, obj=obj)

    def save_model(self, request, obj, form, change):
        config = ParkingReportConfig.objects.filter(parking=obj.parking).first()
        if config:
            obj.commission_percent = config.commission_percent
            obj.company = config.company
            if not obj.owner_id and obj.parking:
                obj.owner = obj.parking.owner

            super().save_model(request, obj, form, change)

            if not change:
                OwnersPaymentsReports._process_parking_config(
                    config=config,
                    report=obj,
                    period_start=obj.period_start,
                    period_end=obj.period_end,
                )
                obj.save()
        else:
            messages.warning(
                request,
                "⚠️ Не найден конфиг ParkingReportConfig для выбранной парковки. Данные не подставлены.",
            )
            super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return False
        return True

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [f.name for f in self.model._meta.fields] + ["download_xls_link"]
        return self.readonly_fields

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
        if obj.pk:
            url = reverse("admin:download_report_xls", args=[obj.pk])
            return format_html('<a class="button" href="{}">Скачать XLS</a>', url)
        return "Сначала сохраните отчёт"

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
