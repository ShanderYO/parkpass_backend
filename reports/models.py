from decimal import Decimal
from django.db import models

from base.validators import comma_separated_emails


class ReportObject(models.Model):
    company = models.ForeignKey('owners.Company', on_delete=models.CASCADE)
    PERIOD_DAILY = 'daily'
    PERIOD_WEEKLY = 'weekly'
    PERIOD_MONTHLY = 'monthly'
    PERIOD_N_DAYS = 'n_days'

    PERIOD_CHOICES = [
        (PERIOD_DAILY, 'Daily'),
        (PERIOD_WEEKLY, 'Weekly'),
        (PERIOD_MONTHLY, 'Monthly'),
        (PERIOD_N_DAYS, 'Every N days'),
    ]

    name = models.CharField(max_length=255)
    commission = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    inn = models.CharField(max_length=15, blank=True)
    kpp = models.CharField(max_length=15, blank=True)
    bic = models.CharField(max_length=20, blank=True)
    account = models.CharField(max_length=64, blank=True)
    recipient = models.CharField(max_length=255, blank=True)
    period_type = models.CharField(max_length=16, choices=PERIOD_CHOICES, default=PERIOD_MONTHLY)
    period_days = models.PositiveIntegerField(default=1)
    report_emails = models.TextField(validators=[comma_separated_emails], blank=True)
    send_without_confirmation = models.BooleanField(default=False)
    last_report_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Reporting object'
        verbose_name_plural = 'Reporting objects'

    def __str__(self):
        return self.name


class Transaction(models.Model):
    TYPE_SUCCESS = 'success'
    TYPE_REFUND = 'refund'
    TYPE_CHOICES = [
        (TYPE_SUCCESS, 'Success'),
        (TYPE_REFUND, 'Refund'),
    ]

    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_CHOICES = [
        (STATUS_CONFIRMED, 'Confirmed'),
    ]

    obj = models.ForeignKey(ReportObject, related_name='transactions', on_delete=models.CASCADE)
    datetime = models.DateTimeField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_SUCCESS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)

    class Meta:
        ordering = ['datetime']

    def commission_amount(self):
        if self.type == self.TYPE_SUCCESS:
            return (self.amount * self.obj.commission / Decimal('100')).quantize(Decimal('0.01'))
        return Decimal('0.00')

    def payout_amount(self):
        if self.type == self.TYPE_REFUND:
            return -self.amount
        return self.amount - self.commission_amount()


class Report(models.Model):
    obj = models.ForeignKey(ReportObject, related_name='reports', on_delete=models.CASCADE)
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='reports/', null=True, blank=True)
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_refunds = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Report {self.obj} {self.from_date.date()}-{self.to_date.date()}'
