from django.core.exceptions import ObjectDoesNotExist
from django.db import models

# Create your models here.
from accounts.models import Account
from base.utils import get_logger
from parkings.models import ParkingSession
from payments.payment_api import TinkoffAPI


class CreditCard(models.Model):
    id = models.IntegerField(primary_key=True)
    pan = models.CharField(blank=True, max_length=31)
    exp_date = models.CharField(blank=True, max_length=61)
    is_default = models.BooleanField(default=False)
    rebill_id = models.BigIntegerField(unique=True, blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    account = models.ForeignKey(Account, related_name="credit_cards")

    def __unicode__(self):
        return u"Card: %s (%s %s)" % (self.pan,
                             self.account.first_name, self.account.last_name)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'CreditCard'
        verbose_name_plural = 'CreditCards'

    @classmethod
    def get_card_by_account(cls, account):
        return CreditCard.objects.filter(account=account)

    @classmethod
    def bind_request(cls, account):
        # add Init Order
        init_order = Order.objects.create(sum=1, account=account)
        init_payment = TinkoffPayment.objects.create(order=init_order)
        request_data = init_payment.build_init_request_data()

        result = TinkoffAPI().sync_call(
            TinkoffAPI.INIT, request_data
        )

        # Payment success
        if result.get("Success", False):
            order_id = int(result["OrderId"])
            payment_id = int(result["PaymentId"])
            payment_url = result["PaymentURL"]

            raw_status = result["Status"]
            status = PAYMENT_STATUS_NEW if raw_status == u'NEW' \
                else PAYMENT_STATUS_REJECTED

            try:
                payment = TinkoffPayment.objects.get(id=order_id)
                payment.payment_id = payment_id
                payment.status = status
                payment.save()

            except ObjectDoesNotExist:
                TinkoffPayment.objects.create(payment_id=payment_id, status=status)

            finally:
                return {
                    "payment_url": payment_url
                }

        # Payment exception
        elif int(result.get("ErrorCode", -1)) > 0:
            error_code = int(result["ErrorCode"])
            error_message = result.get("Message", "")
            error_details = result.get("Details", "")
            # TODO add to table errors data

            return {
                "exception": {
                    "error_code":error_code,
                    "error_message":error_message,
                    "error_details":error_details
                }
            }

        return None


class Order(models.Model):
    DEFAULT_WITHDRAWAL_AMOUNT = 100  # RUB

    id = models.AutoField(primary_key=True)
    sum = models.DecimalField(max_digits=7, decimal_places=2)
    payment_attempts = models.PositiveSmallIntegerField(default=1)
    paid = models.BooleanField(default=False)
    session = models.ForeignKey(ParkingSession, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    @classmethod
    def get_ordered_sum_by_session(cls, session):
        sessions = Order.objects.filter(session=session)
        sum = 0
        if sessions.exists():
            for session in sessions:
                sum = sum + session.sum
        return sum

    def get_order_description(self):
        if not self.session:
            return "Init payment"
        if self.sum == Order.DEFAULT_WITHDRAWAL_AMOUNT:
            return "Intermediate payment"
        return "Completed payment"

    def try_pay(self):
        get_logger().info("Try make payment #%s", self.id)
        #self.create_payment()

    def get_payment_amount(self):
        return int(self.sum * 100)

    def create_payment(self):
        new_payment = TinkoffPayment.objects.create()
        request_data = new_payment.build_transaction_data(self.get_payment_amount())
        result = TinkoffAPI().sync_call(
            TinkoffAPI.INIT, request_data
        )
        get_logger().info("Init payment:"+result)


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
    (PAYMENT_STATUS_REFUNDED, 'Refunded'),
    (PAYMENT_STATUS_PARTIAL_REFUNDED, 'Partial_refunded'),
)

class TinkoffPayment(models.Model):

    payment_id = models.BigIntegerField(unique=True, blank=True, null=True)
    status = models.SmallIntegerField(choices=PAYMENT_STATUSES, default=PAYMENT_STATUS_INIT)
    order = models.ForeignKey(Order, null=True, blank=True) # TODO DELETE FROM THIS

    # Fields for debug
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

    def build_transaction_data(self, amount):
        data = {
            "Amount": str(amount),
            "OrderId": str(self.id),
            "Description": "Payment #xxx",
            "Recurrent": "Y"
        }
        return data

    def build_charge_request_data(self, payment_id, rebill_id):
        data = {
            "PaymentId":str(payment_id),
            "RebillId": str(rebill_id),
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

        elif new_status == u'REFUNDED':
            self.status = PAYMENT_STATUS_REFUNDED

        self.save()

    def charge_payment(self, rebill_id):
        request_data = self.build_charge_request_data(self.payment_id, rebill_id)
        result = TinkoffAPI().sync_call(
            TinkoffAPI.CHARGE, request_data
        )