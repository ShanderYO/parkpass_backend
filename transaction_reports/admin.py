import os
import calendar
import datetime

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from parkings.models import Parking
from .models import ReportSettings, TransactionReport, TransactionReportItem
from .service import TransactionReportService

@admin.register(ReportSettings)
class ReportSettingsAdmin(admin.ModelAdmin):
    list_display = ('parking', 'commission_percent', 'period_type', 'period_days', 'auto_send')
    search_fields = ('parking__name',)

class TransactionReportItemInline(admin.TabularInline):
    model = TransactionReportItem
    extra = 0
    can_delete = False
    readonly_fields = (
        'payment_time',
        'amount',
        'type',
        'commission_percent',
        'payable_amount',
    )


@admin.register(TransactionReport)
class TransactionReportAdmin(admin.ModelAdmin):
    list_display = ('parking', 'start', 'end', 'last_sent', 'download_link')
    search_fields = ('parking__name',)
    readonly_fields = ('created_at', 'updated_at', 'download_link')
    inlines = [TransactionReportItemInline]

    change_list_template = 'admin/transaction_reports/change_list.html'

    class ManualReportForm(forms.Form):
        parking = forms.ModelChoiceField(queryset=Parking.objects.all())
        month = forms.DateField(widget=forms.DateInput(attrs={'type': 'month'}))

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('generate/', self.admin_site.admin_view(self.generate_report_view), name='transactionreport-generate'),
        ]
        return custom + urls

    def generate_report_view(self, request):
        if request.method == 'POST':
            form = self.ManualReportForm(request.POST)
            if form.is_valid():
                parking = form.cleaned_data['parking']
                date = form.cleaned_data['month']
                start = datetime.datetime(date.year, date.month, 1, tzinfo=timezone.utc)
                last_day = calendar.monthrange(date.year, date.month)[1]
                end = datetime.datetime(date.year, date.month, last_day, 23, 59, 59, tzinfo=timezone.utc)
                service = TransactionReportService(parking)
                service.generate(start, end)
                messages.success(request, 'Report created')
                return redirect(reverse('admin:transaction_reports_transactionreport_changelist'))
        else:
            form = self.ManualReportForm()
        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'form': form,
        }
        return render(request, 'admin/transaction_reports/generate.html', context)

    def download_link(self, obj):
        if not obj.file_path:
            return '-'
        rel = os.path.relpath(obj.file_path, settings.MEDIA_ROOT)
        url = settings.MEDIA_URL + rel.replace(os.sep, '/')
        return format_html('<a href="{}">Download</a>', url)

    download_link.short_description = 'Excel file'
