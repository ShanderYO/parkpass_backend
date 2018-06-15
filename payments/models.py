from django.db import models

# Create your models here.
from dss.Serializer import serializer

from accounts.models import Account
from base.utils import get_logger
from parkings.models import ParkingSession
from payments.payment_api import TinkoffAPI


class FiskalNotification(models.Model):
    fiscal_number = models.IntegerField()
    shift_number = models.IntegerField()
    receipt_datetime = models.DateTimeField()
    fn_number = models.CharField(max_length=20)
    ecr_reg_number = models.CharField(max_length=20)
    fiscal_document_number = models.IntegerField()
    fiscal_document_attribute = models.IntegerField()
    token = models.TextField()
    ofd = models.TextField(null=True, blank=True)
    url = models.TextField(null=True, blank=True)
    qr_code_url = models.URLField(null=True, blank=True)
    receipt = models.TextField()
    type = models.CharField(max_length=15)

    def __unicode__(self):
        return u"Fiskal notification: %s (%s %s)" \
               % (self.fiscal_number, self.shift_number)

    class Meta:
        ordering = ["-receipt_datetime"]


class CreditCard(models.Model):
    id = models.AutoField(primary_key=True)
    card_id = models.IntegerField(default=1)
    pan = models.CharField(blank=True, max_length=31)
    exp_date = models.CharField(blank=True, max_length=61)
    is_default = models.BooleanField(default=False)
    rebill_id = models.BigIntegerField(blank=True, null=True)
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
        init_order = Order.objects.create(sum=1, account=account)
        receipt_data = init_order.generate_receipt_data()
        init_payment = TinkoffPayment.objects.create(order=init_order, receipt_data=receipt_data)
        request_data = init_payment.build_init_request_data(account.id)
        get_logger().info("Init request:")
        get_logger().info(request_data)
        result = TinkoffAPI().sync_call(
            TinkoffAPI.INIT, request_data
        )

        # Tink-off gateway not responded
        if not result:
            return None

        # Payment success
        if result.get("Success", False):
            order_id = int(result["OrderId"])
            payment_id = int(result["PaymentId"])
            payment_url = result["PaymentURL"]

            raw_status = result["Status"]
            status = PAYMENT_STATUS_NEW if raw_status == u'NEW' \
                else PAYMENT_STATUS_REJECTED

            if init_payment.order.id != order_id:
                return None

            init_payment.payment_id = payment_id
            init_payment.status = status
            init_payment.save()

            if status == PAYMENT_STATUS_REJECTED:
                return None

            # Send url to user
            return {
                "payment_url": payment_url
            }

        # Payment exception
        elif int(result.get("ErrorCode", -1)) > 0:
            error_code = int(result["ErrorCode"])
            error_message = result.get("Message", "")
            error_details = result.get("Details", "")

            init_payment.error_code = error_code
            init_payment.error_message = error_message
            init_payment.error_description = error_details
            init_payment.save()

            return {
                "exception": {
                    "error_code":error_code,
                    "error_message":error_message,
                    "error_details":error_details
                }
            }
        return None


class Order(models.Model):

    id = models.AutoField(primary_key=True)
    sum = models.DecimalField(max_digits=7, decimal_places=2)
    payment_attempts = models.PositiveSmallIntegerField(default=1)
    paid = models.BooleanField(default=False)
    session = models.ForeignKey(ParkingSession, null=True, blank=True)
    refund_request = models.BooleanField(default=False)
    refunded_sum = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    # for init payment order
    account = models.ForeignKey(Account, null=True, blank=True)

    fiscal_notification = models.ForeignKey(FiskalNotification, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    @classmethod
    def get_ordered_sum_by_session(cls, session):
        sessions = Order.objects.filter(session=session)
        result_sum = 0
        if sessions.exists():
            for session in sessions:
                result_sum = result_sum + session.sum
        return result_sum

    def generate_receipt_data(self):
        """
        if self.account.email is None or len(self.account.email) == 0:
            return None
        """

        # Init payment receipt
        if self.session is None:
            return dict(
                Email=self.account.email if self.account.email else None,
                Phone=self.account.phone,
                Taxation="osn",
                Items=[{
                    "Name": "Binding card",
                    "Price": 100,
                    "Quantity": 1.00,
                    "Amount": 100,
                    "Tax": "vat10",
                    "Ean13": "0123456789"
                    }]
            )

        # session payment receipt
        return dict(
            Email=self.account.email if self.account.email else None,
            Phone=self.account.phone,
            Taxation="osn",
            Items=[{
                "Name": "Payment for parking session # %s" % self.session.id,
                "Price": self.sum,
                "Quantity": 1.00,
                "Amount": self.sum,
                "Tax": "vat10",
                "Ean13": "0123456789"
            }]
        )

    def is_refunded(self):
        return self.refunded_sum == self.sum

    def get_order_description(self):
        if not self.session:
            return "Init payment"
        if self.sum == self.session.parking.max_client_debt:
            return "Intermediate payment"
        return "Completed payment"

    def try_pay(self):
        get_logger().info("Try make payment #%s", self.id)
        self.create_payment()

    def get_payment_amount(self):
        return int(self.sum * 100)

    def create_payment(self):
        receipt_data = self.generate_receipt_data()
        new_payment = TinkoffPayment.objects.create(order=self, receipt_data=receipt_data)
        request_data = new_payment.build_transaction_data(self.get_payment_amount())
        result = TinkoffAPI().sync_call(
            TinkoffAPI.INIT, request_data
        )
        get_logger().info("Init payment response: ")
        get_logger().info(str(result))

        # Tink-off gateway not responded
        if not result:
            return None

        # Payment success
        if result.get("Success", False):
            payment_id = int(result["PaymentId"])

            raw_status = result["Status"]
            status = PAYMENT_STATUS_NEW if raw_status == u'NEW' \
                else PAYMENT_STATUS_REJECTED
            get_logger().info("Init status: "+ raw_status)
            new_payment.payment_id = payment_id
            new_payment.status = status
            new_payment.save()

            # Credit card bind
            self.charge_payment(new_payment)

        # Payment exception
        elif int(result.get("ErrorCode", -1)) > 0:
            error_code = int(result["ErrorCode"])
            error_message = result.get("Message", "")
            error_details = result.get("Details", "")

            new_payment.error_code = error_code
            new_payment.error_message = error_message
            new_payment.error_description = error_details
            new_payment.save()


    def charge_payment(self, payment):
        get_logger().info("Make charge: ")
        default_account_credit_card = CreditCard.objects.get(account=self.session.client, is_default=True)
        request_data = payment.build_charge_request_data(
            payment.payment_id, default_account_credit_card.rebill_id
        )
        get_logger().info(request_data)
        result = TinkoffAPI().sync_call(
            TinkoffAPI.CHARGE, request_data
        )
        get_logger().info(str(result))


    def get_order_with_fiscal_dict(self):
        order = dict(
            id=self.id,
            sum=float(self.sum)
        )

        fiscal = None
        if self.fiscal_notification:
            fiscal = serializer(self.fiscal_notification)

        return dict(
            order=order,
            fiscal=fiscal
        )

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
    receipt_data = models.TextField(null=True, blank=True)

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

    def build_init_request_data(self, customer_key):
        data = {
            "Amount": str(100),  # 1RUB
            "OrderId": str(self.order.id),
            "Description": "Initial payment",
            "Recurrent": "Y",
            "CustomerKey": str(customer_key)
        }
        if self.receipt_data:
            data["Receipt"] = self.receipt_data
        return data

    def build_transaction_data(self, amount):
        data = {
            "Amount": str(amount),
            "OrderId": str(self.order.id),
            "Description": "Payment for order #%s" % str(self.order.id)
        }
        if self.receipt_data:
            data["Receipt"] = self.receipt_data
        return data

    def build_charge_request_data(self, payment_id, rebill_id):
        data = {
            "PaymentId":str(payment_id),
            "RebillId": str(rebill_id),
        }
        return data

    def build_confirm_request_data(self, payment_id, amount):
        data = {
            "PaymentId": str(payment_id),
            "Amount": str(amount),
        }
        return data

    def build_cancel_request_data(self, refund_amount=None):
        data = {
            "PaymentId":str(self.payment_id)
        }
        if refund_amount:
            data["Amount"] = str(refund_amount)
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