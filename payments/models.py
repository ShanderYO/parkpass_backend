from django.db import models

# Create your models here.
from accounts.models import Account


class CreditCard(models.Model):
    id = models.AutoField(primary_key=True)
    #type = models.CharField("Type", blank=True, max_length=30)
    #owner = models.CharField("Owner", blank=True, max_length=100)
    number = models.CharField("Number", blank=True, max_length=30)
    #expiration_date_month = models.IntegerField(blank=True, null=True)
    #expiration_date_year = models.IntegerField(blank=True, null=True)

    is_default = models.BooleanField(default=False)
    created_at = models.DateField(auto_now_add=True)
    account = models.ForeignKey(Account, related_name = "credit_cards")

    def __unicode__(self):
        return u"%s / %s" % (self.number, "")# self.owner)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'CreditCard'
        verbose_name_plural = 'CreditCards'

    @classmethod
    def get_card_by_account(cls, account):
        return CreditCard.objects.filter(account=account)

PAYMENT_STATUS_INIT = 0
PAYMENT_STATUS_NEW = 1
PAYMENT_STATUS_CANCEL = 2
PAYMENT_STATUS_FORMSHOWED = 3
PAYMENT_STATUS_REJECTED = 4
PAYMENT_STATUS_AUTH_FAIL = 5
PAYMENT_STATUS_AUTHORIZED = 6
PAYMENT_STATUS_CONFIRMED = 7
PAYMENT_STATUS_REVERSED = 8
PAYMENT_STATUS_REFUNDED = 9
PAYMENT_STATUS_PARTIAL_REFUNDED = 10

PAYMENT_STATUSES = (
    (PAYMENT_STATUS_INIT, 'Init'),
    (PAYMENT_STATUS_NEW, 'New'),
    (PAYMENT_STATUS_CANCEL, 'Cancel'),
    (PAYMENT_STATUS_FORMSHOWED, 'Form showed'),
    (PAYMENT_STATUS_REJECTED, 'Rejected'),
    (PAYMENT_STATUS_AUTH_FAIL, 'Auth fail'),
    (PAYMENT_STATUS_AUTHORIZED, 'Authorized'),
    (PAYMENT_STATUS_CONFIRMED, 'Confirmed'),
)

class TinkoffPayment(models.Model):
    payment_id = models.BigIntegerField(unique=True, blank=True, null=True)
    status = models.SmallIntegerField(choices=PAYMENT_STATUSES, default=PAYMENT_STATUS_INIT)
    rebill_id = models.BigIntegerField(unique=True, blank=True, null=True)
    card_id = models.BigIntegerField(unique=True, blank=True, null=True)
    pan = models.CharField(max_length=31, blank=True, null=True)

    error_code = models.IntegerField(default=-1)
    error_message = models.CharField(max_length=127, blank=True, null=True)
    error_description = models.TextField(max_length=511, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = 'Tinkoff Payment'
        verbose_name_plural = 'Tinkoff Payments'

    def build_init_request_data(self):
        data = {
            "Amount": str(100),  # 1RUB
            "OrderId": str(self.id),
            "Description": "initial_payment",
            "Recurrent": "Y"
        }
        return data

    def build_charge_request_data(self):
        data = {
            "PaymentId":str(self.payment_id),
            "RebillId": str(self.rebill_id),
        }
        return data

    def build_cancel_request_data(self):
        data = {
            "PaymentId":str(self.payment_id)
        }
        return data

    def set_new_status(self, new_status):
        if new_status == u'CANCEL':
            self.status = PAYMENT_STATUS_CANCEL

        elif new_status == u'AUTHORIZED' and self.status != PAYMENT_STATUS_CONFIRMED:
            self.status = PAYMENT_STATUS_AUTHORIZED

        elif new_status == u'CONFIRMED':
            self.status = PAYMENT_STATUS_CONFIRMED

        elif new_status == u'REJECTED':
            self.status = PAYMENT_STATUS_REJECTED

        elif new_status == u'AUTH_FAIL':
            self.status = PAYMENT_STATUS_AUTH_FAIL

        self.save()