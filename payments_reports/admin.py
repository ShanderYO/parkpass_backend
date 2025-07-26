from django.contrib import admin
from django import forms
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.html import format_html

from .models import (
    ParkingReportConfig,
    ParkingPaymentReport,
    ParkingPaymentReportTransaction,
    PayoutHistory,
)
from .services import OwnersPaymentsReports


# 🔹 Кастомная форма для выбора дат в виде календаря
class ParkingPaymentReportForm(forms.ModelForm):
    class Meta:
        model = ParkingPaymentReport
        fields = "__all__"
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
        }


# 🔹 Inline-транзакции для отображения в отчёте
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

        report = OwnersPaymentsReports.generate_report_for_owner(
            config.owner,
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


@admin.register(ParkingPaymentReport)
class ParkingPaymentReportAdmin(admin.ModelAdmin):
    form = ParkingPaymentReportForm
    inlines = [ParkingPaymentReportTransactionInline]  # 🔹 отображение транзакций

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

    def save_model(self, request, obj, form, change):
        config = ParkingReportConfig.objects.filter(owner=obj.owner).first()
        if config:
            obj.commission_percent = config.commission_percent
            obj.company = config.company
            obj.parking = config.parking
            super().save_model(request, obj, form, change)

            if not change:
                OwnersPaymentsReports.generate_report_for_owner(
                    owner=obj.owner,
                    period_start=obj.period_start,
                    period_end=obj.period_end,
                )
        else:
            messages.warning(
                request,
                "⚠️ Не найден конфиг ParkingReportConfig для выбранного Owner. Данные не подставлены.",
            )
            super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return False
        return True

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields


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
