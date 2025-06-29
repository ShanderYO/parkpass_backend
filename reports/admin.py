from django.contrib import admin
from .models import ReportObject, Transaction, Report


@admin.register(ReportObject)
class ReportObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'commission', 'period_type', 'last_report_sent')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('obj', 'datetime', 'amount', 'type', 'status')
    list_filter = ('obj', 'type', 'status')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('obj', 'from_date', 'to_date', 'created_at', 'last_sent_at')
    readonly_fields = ('created_at', 'total_income', 'total_refunds', 'total_commission', 'total_payout')
