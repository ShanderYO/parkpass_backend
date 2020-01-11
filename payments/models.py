# -*- coding: utf-8 -*-
import json
import os
import urllib.parse

import requests
from datetime import timedelta
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

from dss.Serializer import serializer

from accounts.models import Account
from base.models import Terminal
from base.utils import get_logger
from parkpass_backend.settings import EMAIL_HOST_USER, TINKOFF_API_REFRESH_TOKEN, PARKPASS_INN
from payments.payment_api import TinkoffAPI


class FiskalNotification(models.Model):
    fiscal_number = models.IntegerField()
    shift_number = models.IntegerField()
    receipt_datetime = models.DateTimeField()
    fn_number = models.CharField(max_length=20)
    ecr_reg_number = models.CharField(max_length=20)
    fiscal_document_number = models.IntegerField()
    fiscal_document_attribute = models.BigIntegerField()
    ofd = models.TextField(null=True, blank=True)
    url = models.TextField(null=True, blank=True)
    qr_code_url = models.URLField(null=True, blank=True)
    receipt = models.TextField()
    card_pan = models.CharField(max_length=31)
    type = models.CharField(max_length=15)

    def __str__(self):
        return u"Fiscal notification: %s (%s)" \
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
    account = models.ForeignKey(Account, related_name="credit_cards",
                                on_delete=models.CASCADE)

    def __str__(self):
        return u"Card: %s (%s %s)" % (self.pan,
                                      self.account.first_name,
                                      self.account.last_name)

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
        #get_logger().info(request_data)
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
    sum = models.DecimalField(max_digits=8, decimal_places=2)
    payment_attempts = models.PositiveSmallIntegerField(default=1)
    authorized = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    paid_card_pan = models.CharField(max_length=31, default="")
    session = models.ForeignKey(to='parkings.ParkingSession',
                                null=True, blank=True, on_delete=models.CASCADE)
    refund_request = models.BooleanField(default=False)
    refunded_sum = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fiscal_notification = models.ForeignKey(FiskalNotification,
                                            null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    # for init payment order
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.CASCADE)

    # for parking card
    parking_card_session = models.ForeignKey(to='rps_vendor.RpsParkingCardSession',
                                             null=True, blank=True, on_delete=models.CASCADE)
    paid_notified_at = models.DateTimeField(null=True, blank=True)

    # for subscription
    subscription = models.ForeignKey(to='rps_vendor.RpsSubscription',
                                     null=True, blank=True, on_delete=models.CASCADE)

    # for non-accounts payments
    client_uuid = models.UUIDField(null=True, default=None)

    # use multiple terminals
    terminal = models.ForeignKey(Terminal, null=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    @classmethod
    def retrieve_order_with_fk(cls, order_id, fk=[]):
        qs = Order.objects.filter(id=order_id)
        for related_model in fk:
            qs = qs.select_related(related_model)
        return qs.first()

    @classmethod
    def get_ordered_sum_by_session(cls, session):
        sessions = Order.objects.filter(session=session)
        result_sum = 0
        if sessions.exists():
            for session in sessions:
                result_sum = result_sum + session.sum
        return result_sum

    def generate_receipt_data(self):
        if self.subscription:
            email = self.subscription.account.email if self.subscription.account else None
            phone = self.subscription.account.phone if self.subscription.account else None

            return dict(
                Email=email,
                Phone=phone,
                Taxation="usn_income",
                Items=[{
                    "Name": "Оплата парковочного абонемента",
                    "Price": str(int(self.sum * 100)),
                    "Quantity": 1.00,
                    "Amount": str(int(self.sum * 100)),
                    "Tax": "none",
                    "Ean13": "0123456789"
                }]
            )

        if self.parking_card_session or self.client_uuid:
            email = self.parking_card_session.account.email if self.parking_card_session.account else None
            phone = self.parking_card_session.account.phone \
                if self.parking_card_session.account else self.parking_card_session.parking_card.phone

            return dict(
                Email=email,
                Phone=phone,
                Taxation="usn_income",
                Items=[{
                    "Name": "Оплата парковочной карты" if self.parking_card_session else "Оплата услуг Parkpass",
                    "Price": str(int(self.sum*100)),
                    "Quantity": 1.00,
                    "Amount": str(int(self.sum*100)),
                    "Tax": "none",
                    "Ean13": "0123456789"
                }]
            )

        # Init payment receipt
        if self.session is None:
            return dict(
                Email=None, # not send to email
                Phone=self.account.phone,
                Taxation="usn_income",
                Items=[{
                    "Name": "Привязка карты",
                    "Price": 100,
                    "Quantity": 1.00,
                    "Amount": 100,
                    "Tax": "none",
                    "Ean13": "0123456789"
                }]
            )

        # session payment receipt
        return dict(
            Email=str(self.session.client.email) if self.session.client.email else None,
            Phone=str(self.session.client.phone),
            Taxation="usn_income",
            Items=[{
                "Name": "Оплата парковки # %s" % self.session.id,
                "Price": str(int(self.sum*100)),
                "Quantity": 1.00,
                "Amount": str(int(self.sum*100)),
                "Tax": "none",
                "Ean13": "0123456789"
            }]
        )

    def is_refunded(self):
        return self.refunded_sum == self.sum

    def try_pay(self):
        get_logger().info("Try make payment #%s", self.id)
        self.create_payment()

    def get_payment_amount(self):
        return int(self.sum * 100)

    def get_tinkoff_api(self):
        if not self.terminal or self.terminal == 'main':
            return TinkoffAPI()
        else:
            return TinkoffAPI(with_terminal=self.terminal.name)

    def create_non_recurrent_payment(self):
        receipt_data = self.generate_receipt_data()
        init_payment = TinkoffPayment.objects.create(
            order=self,
            receipt_data=receipt_data
        )
        customer_key = str(self.client_uuid) if self.client_uuid \
            else self.parking_card_session.client_uuid

        request_data = init_payment.build_non_recurrent_request_data(
            self.get_payment_amount(),
            customer_key)

        get_logger().info("Init non recurrent request:")
        get_logger().info(request_data)

        result = self.get_tinkoff_api().sync_call(
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
                    "error_code": error_code,
                    "error_message": error_message,
                    "error_details": error_details
                }
            }
        return None

    def create_payment(self):
        receipt_data = self.generate_receipt_data()
        new_payment = TinkoffPayment.objects.create(
            order=self,
            receipt_data=receipt_data)

        request_data = new_payment.build_transaction_data(self.get_payment_amount())
        result = self.get_tinkoff_api().sync_call(
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
        account = None

        if self.session:
            account = self.session.client
        elif self.parking_card_session:
            account = self.parking_card_session.account
        else:
            account = self.subscription.account

        if account is None:
            get_logger().warn("Payment was broken. You try pay throw credit card unknown account")
            return

        default_account_credit_card = CreditCard.objects.filter(
                account=account, is_default=True).first()

        if not default_account_credit_card:
            get_logger().warn("Payment was broken. Account should has bind card")
            return

        request_data = payment.build_charge_request_data(
            payment.payment_id, default_account_credit_card.rebill_id
        )
        get_logger().info(request_data)
        result = self.get_tinkoff_api().sync_call(
            TinkoffAPI.CHARGE, request_data
        )
        if result[u'Status'] == u'AUTHORIZED':
            payment.status = PAYMENT_STATUS_AUTHORIZED
            payment.save()

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

    def confirm_payment(self, payment):
        get_logger().info("Make confirm order: %s" % self.id)
        request_data = payment.build_confirm_request_data(self.get_payment_amount())
        get_logger().info(request_data)
        result = self.get_tinkoff_api().sync_call(
            TinkoffAPI.CONFIRM, request_data
        )
        get_logger().info(str(result))

    def send_receipt_to_email(self):
        email = self.session.client.email
        render_data = {
            "order": self,
            "email": email
        }
        msg_html = render_to_string('emails/receipt.html', render_data)
        send_mail('Электронная копия чека', "", EMAIL_HOST_USER,
                  ['%s' % str(email)], html_message=msg_html)


PAYMENT_STATUS_UNKNOWN = -1
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
PAYMENT_STATUS_RECEIPT = 11

PAYMENT_STATUSES = (
    (PAYMENT_STATUS_UNKNOWN, 'Unknown'),
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
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.CASCADE)  # TODO DELETE FROM THIS
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

    def build_non_recurrent_request_data(self, amount, customer_key):
        data = {
            "Amount": str(amount),
            "OrderId": str(self.order.id),
            "Description": "Платеж #%s" % str(self.order.id),
            "CustomerKey": str(customer_key)
        }
        if self.receipt_data:
            data["Receipt"] = self.receipt_data
        return data

    def build_init_request_data(self, customer_key):
        data = {
            "Amount": str(100),  # 1 RUB
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
            "Description": "Платеж #%s" % str(self.order.id)
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

    def build_confirm_request_data(self, amount):
        data = {
            "PaymentId": str(self.payment_id),
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


class TinkoffSession(models.Model):
    refresh_token = models.TextField()
    access_token = models.TextField(null=True, blank=True)
    expires_in = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tinkoff_session'

    def is_session_valid(self):
        return timezone.now() < self.expires_in


class InvoiceWithdraw(models.Model):

    URL_UPDATE_TOKEN = "https://openapi.tinkoff.ru/sso//secure/token"
    URL_WITHDRAW = "https://openapi.tinkoff.ru/sme/api/v1/partner/company/%s/payment"

    documentNumber = models.TextField(null=True, blank=True, help_text="Номер документа")
    documentDate = models.DateField(null=True, blank=True, help_text="Дата документа")
    amount = models.IntegerField(help_text="Сумма платежа")
    recipientName = models.TextField(help_text="Получатель")
    inn = models.TextField()
    kpp = models.TextField()

    accountNumber = models.TextField(help_text="Номер счета получателя")
    bankAcnt = models.TextField(null=True, blank=True, help_text="Банк получателя")
    bankBik = models.TextField(null=True, blank=True, help_text="БИК банка получателя")

    paymentPurpose = models.TextField(default="", blank=True, help_text="Назначение платежа")
    executionOrder = models.IntegerField(default=0, help_text="Очередность платежа")

    taxPayerStatus = models.TextField(null=True, blank=True, help_text="Статус составителя расчетного документа")
    kbk = models.TextField(null=True, blank=True, help_text="Код бюджетной классификации")
    oktmo = models.TextField(null=True, blank=True, help_text="Код ОКТМО территории, на которой мобилизуютсяденежные "
                                                              "средства от уплаты налога, сбора и иного платежа")

    taxEvidence = models.TextField(null=True, blank=True, help_text="Основание налогового платежа")
    taxPeriod = models.TextField(null=True, blank=True, help_text="Налоговый период / код таможенного органа")
    uin = models.TextField(null=True, blank=True, help_text="Уникальный идентификатор платежа")

    taxDocNumber = models.TextField(null=True, blank=True, help_text="Номер налогового документа")
    taxDocDate = models.TextField(null=True, blank=True, help_text="Дата налогового документа")

    is_send = models.BooleanField(default=False)
    is_requested = models.BooleanField(default=False)
    error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'invoice_withdraw'

    def __str__(self):
        return "(%s) %s" % (self.amount, self.accountNumber)

    def save(self, *args, **kwargs):
        if not self.is_send and not self.is_requested:
            self.is_requested = True
            super(InvoiceWithdraw, self).save(*args, **kwargs)
            self.is_send = self.send_withdraw_request()

        self.is_requested = False
        super(InvoiceWithdraw, self).save(*args, **kwargs)

    def _get_saved_access_token(self):
        active_session = TinkoffSession.objects.all().order_by('-created_at').first()
        if active_session and active_session.is_session_valid():
            print("Get token from store")
            return active_session.access_token
        return None

    def send_withdraw_request(self):
        print("send_withdraw_request")
        token, error = self.get_or_update_token()
        print("Obtained token %s" % token)
        if error:
            self.error = "Fetch token %s" % str(error)
            self.is_send = False
            return False

        status, error = self._withdraw_request(token)
        if error:
            self.error = "Withdraw %s" % str(error)
            self.is_send = False
            return False

        return True

    def get_or_update_token(self):
        access_token = self._get_saved_access_token()
        if access_token is None:
            try:
                value = urllib.parse.quote(TINKOFF_API_REFRESH_TOKEN, safe='')
                body = "grant_type=refresh_token&refresh_token=%s" % value
                print(body)
                headers = {
                    "Content-Type":"application/x-www-form-urlencoded"
                }
                res = requests.post(InvoiceWithdraw.URL_UPDATE_TOKEN, body, headers=headers)
                print(res.status_code, res.content)

                if res.status_code == 200:
                    json_data = res.json()

                    refresh_token = json_data["refresh_token"]
                    access_token = json_data["access_token"]
                    expires_in = timezone.now() + timedelta(seconds=int(json_data["expires_in"]))
                    sessionId = json_data["sessionId"]

                    TinkoffSession.objects.create(
                        refresh_token=refresh_token,
                        access_token=access_token,
                        expires_in=expires_in
                    )
                    # {
                    #     "access_token": "6pg5FjCleGtoV_5uni-chWvIg_dYur_EbnjvBVyj_NYKYYc8fGdobUh9KzNRQx1W_zHX6O0iS2hqRL6p6GDHpw",
                    #     "token_type": "Bearer",
                    #     "expires_in": 1800,
                    #     "refresh_token": "7ErUSl5Nc1l/PImQ8zLYJ9TV25FGtkxvoqbJKbenhRBVT9N81ATNyroMFmKZsfu+cWzfT/C12Zo6dDoV/0YUQg==",
                    #     "sessionId": "eb5F-G4AUb9S0t4ZXhUiHGIpHDzQuaEOFzX8KTaGIELUQauiZrjxyDzFajeARDy4IEJ4nkZGxinkfkwlOCWwqg"
                    # }
                    #
                    return access_token, None

            except Exception as e:
                print(str(e))
                return None, str(e)

            return None, "Status not 200 %s" % res.content

        return access_token, None

    def _withdraw_request(self, token):
        headers = {
            "Authorization": "Bearer %s" % token,
            "Content-Type": "application/json"
        }
        try:
            body = {
                "documentNumber": self.documentNumber,
                "date": None,
                "amount": self.amount,
                "recipientName": self.recipientName,
                "inn": self.inn,
                "kpp": self.kpp,
                "bankAcnt": self.bankAcnt,
                "bankBik": self.bankBik,
                "accountNumber": self.accountNumber,
                "paymentPurpose": self.paymentPurpose,
                "executionOrder": self.executionOrder,
                "taxPayerStatus": self.taxPayerStatus,
                "kbk": self.kbk,
                "oktmo": self.oktmo,
                "taxEvidence": self.taxEvidence,
                "taxPeriod": self.taxPeriod,
                "uin": self.uin,
                # "taxDocNumber": self.taxDocNumber,
                # "taxDocDate": None
            }

            print(body)
            res = requests.post(InvoiceWithdraw.URL_WITHDRAW % PARKPASS_INN, json.dumps(body), headers=headers)
            print(res.content)

            if res.status_code == 200:
                json_data = res.json()
                if json_data.get("result") == "OK":
                    return True, None

            return False, "Status not 200 %s" % res.content

        except Exception as e:
            print(str(e))
            return False, str(e)