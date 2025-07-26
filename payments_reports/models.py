from django.db import models
from django.utils.translation import gettext_lazy as _
from enum import Enum

from owners.models import Company


class PayoutPeriodicity(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    N_DAYS = "n_days"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.capitalize()) for tag in cls]


class TransactionType(Enum):
    CONFIRMED = "confirmed"
    REFUND = "refund"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.capitalize()) for tag in cls]


class PayoutStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.capitalize()) for tag in cls]


class ParkingReportConfig(models.Model):
    owner = models.ForeignKey(
        "owners.Owner", on_delete=models.CASCADE, related_name="report_configs"
    )
    parking = models.ForeignKey("parkings.Parking", on_delete=models.CASCADE)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True
    )
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2)

    recipient_name = models.CharField(max_length=255)
    inn = models.CharField(max_length=12, null=True, blank=True)
    kpp = models.CharField(max_length=9, blank=True, null=True)
    bank_bik = models.CharField(max_length=9, null=True, blank=True)
    bank_account = models.CharField(max_length=20, null=True, blank=True)

    payout_periodicity = models.CharField(
        max_length=20,
        choices=PayoutPeriodicity.choices(),
        default=PayoutPeriodicity.MONTHLY.value,
    )
    payout_period_days = models.PositiveIntegerField(null=True, blank=True)

    report_emails = models.TextField(help_text="Список email, через запятую")
    auto_send = models.BooleanField(
        default=False, help_text="Отправлять без подтверждения администратора"
    )

    def __str__(self):
        return f"{self.parking.name} ({self.owner.email})"


class ParkingPaymentReport(models.Model):
    owner = models.ForeignKey(
        "owners.Owner", on_delete=models.CASCADE, related_name="payment_reports"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    total_refunds = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    total_commission = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    payout_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    is_sent = models.BooleanField(default=False)

    def __str__(self):
        if self.owner:
            return f"Config for {self.owner.name} ({self.owner.email})"
        return "Config without owner"


class ParkingPaymentReportTransaction(models.Model):
    report = models.ForeignKey(
        ParkingPaymentReport, related_name="transactions", on_delete=models.CASCADE
    )
    tinkoff_payment = models.ForeignKey(
        "payments.TinkoffPayment", on_delete=models.CASCADE
    )
    parking = models.ForeignKey("parkings.Parking", on_delete=models.CASCADE)

    date_time = models.DateTimeField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(
        max_length=20, choices=TransactionType.choices()
    )
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2)
    amount_after_commission = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return (
            f"Payment {self.tinkoff_payment.id} ({self.amount}) - {self.parking.name}"
        )


class PayoutHistory(models.Model):
    report = models.ForeignKey(ParkingPaymentReport, on_delete=models.CASCADE)
    invoice_withdraw = models.ForeignKey(
        "payments.InvoiceWithdraw", on_delete=models.SET_NULL, null=True, blank=True
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=PayoutStatus.choices())
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.report} - {self.status}"
