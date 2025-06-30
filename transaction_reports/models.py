from django.db import models
from parkings.models import Parking

class ReportSettings(models.Model):
    PERIOD_DAILY = 'daily'
    PERIOD_WEEKLY = 'weekly'
    PERIOD_MONTHLY = 'monthly'
    PERIOD_CUSTOM = 'custom'
    PERIOD_CHOICES = [
        (PERIOD_DAILY, 'Daily'),
        (PERIOD_WEEKLY, 'Weekly'),
        (PERIOD_MONTHLY, 'Monthly'),
        (PERIOD_CUSTOM, 'Custom'),
    ]

    parking = models.OneToOneField(Parking, on_delete=models.CASCADE)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2)
    recipient_name = models.CharField(max_length=255)
    inn = models.CharField(max_length=12)
    kpp = models.CharField(max_length=12, blank=True)
    bik = models.CharField(max_length=12)
    account = models.CharField(max_length=64)
    period_type = models.CharField(max_length=16, choices=PERIOD_CHOICES)
    period_days = models.PositiveIntegerField(default=1)
    emails = models.TextField(blank=True)
    auto_send = models.BooleanField(default=False)

    class Meta:
        db_table = 'report_settings_parking'


class TransactionReport(models.Model):
    parking = models.ForeignKey(Parking, on_delete=models.CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField()
    file_path = models.TextField(blank=True)
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_refund = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transaction_report'
        ordering = ['-start']


class TransactionReportItem(models.Model):
    TYPE_SUCCESS = 'success'
    TYPE_REFUND = 'refund'
    TYPE_CHOICES = [
        (TYPE_SUCCESS, 'Success'),
        (TYPE_REFUND, 'Refund'),
    ]

    report = models.ForeignKey(TransactionReport, related_name='items', on_delete=models.CASCADE)
    payment_time = models.DateTimeField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    payable_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'transaction_report_item'
