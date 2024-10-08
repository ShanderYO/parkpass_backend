# -*- coding: utf-8 -*-
import json
import logging
import os
import urllib.parse
from decimal import Decimal

import requests
from datetime import timedelta
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.postgres.fields import JSONField

import payments
from dss.Serializer import serializer

from accounts.models import Account
from base.models import Terminal
from base.utils import get_logger, elastic_log
from notifications.models import AccountDevice
from parkpass_backend import settings
from parkpass_backend.settings import (
    EMAIL_HOST_USER,
    PARKPASS_INN,
    ES_APP_PAYMENTS_LOGS_INDEX_NAME,
    ACQUIRING_LIST,
    REQUESTS_LOGGER_NAME,
    EMAILS_HOST_ALERT,
)
from payments.payment_api import TinkoffAPI, HomeBankAPI

logger = get_logger(REQUESTS_LOGGER_NAME)


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
        return "Fiscal notification: %s (%s)" % (self.fiscal_number, self.shift_number)

    class Meta:
        ordering = ["-receipt_datetime"]


class HomeBankFiskalNotification(models.Model):
    check_number = models.BigIntegerField()
    shift_number = models.IntegerField()
    sum = models.IntegerField()
    date_time_string = models.CharField(max_length=50)
    address = models.CharField(max_length=100)
    ofd_name = models.CharField(max_length=100)
    identity_number = models.IntegerField()
    registration_number = models.CharField(max_length=100)
    unique_number = models.CharField(max_length=100)
    ticket_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Homebank fiscal notification: %s (%s)" % (
            self.check_number,
            self.shift_number,
        )

    class Meta:
        ordering = ["-created_at"]


class CreditCard(models.Model):
    id = models.AutoField(primary_key=True)
    card_id = models.IntegerField(default=1, blank=True)
    card_char_id = models.CharField(max_length=100, blank=True, null=True)
    pan = models.CharField(blank=True, max_length=31)
    exp_date = models.CharField(blank=True, max_length=61, null=True)
    is_default = models.BooleanField(default=False)
    rebill_id = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    acquiring = models.CharField(
        max_length=61,
        default="tinkoff",
        choices=(
            ("tinkoff", "Тинькофф"),
            ("homebank", "HomeBank"),
        ),
    )
    account = models.ForeignKey(
        Account, related_name="credit_cards", on_delete=models.CASCADE
    )

    def __str__(self):
        return "Card: %s (%s %s)" % (
            self.pan,
            self.account.first_name,
            self.account.last_name,
        )

    class Meta:
        ordering = ["-id"]
        verbose_name = "CreditCard"
        verbose_name_plural = "CreditCards"

    @classmethod
    def get_card_by_account(cls, account):
        return CreditCard.objects.filter(account=account)

    @classmethod
    def bind_request(cls, account, acquiring):
        if acquiring == "homebank":
            init_order = Order.objects.create(
                sum=10, account=account, acquiring="homebank"
            )
            receipt_data = init_order.generate_receipt_data()
            init_payment = HomeBankPayment.objects.create(
                order=init_order, receipt_data=json.dumps(receipt_data)
            )
            get_logger().info("bind homebank card request:")
            # Send url to user
            return {
                "payment_url": "https://%s/api/v1/payments/homebank?order_id=%s"
                % (settings.BASE_DOMAIN, init_order.id)
            }
        else:
            init_order = Order.objects.create(sum=1, account=account)
            receipt_data = init_order.generate_receipt_data()
            init_payment = TinkoffPayment.objects.create(
                order=init_order, receipt_data=receipt_data
            )
            request_data = init_payment.build_init_request_data(account.id)
            get_logger().info("Init request:")
            elastic_log(
                ES_APP_PAYMENTS_LOGS_INDEX_NAME, "Bind card request", request_data
            )
            result = TinkoffAPI().sync_call(TinkoffAPI.INIT, request_data)

            # Tink-off gateway not responded
            if not result:
                return None

            elastic_log(
                ES_APP_PAYMENTS_LOGS_INDEX_NAME, "Result bind card", request_data
            )

            # Payment success
            if result.get("Success", False):
                order_id = int(result["OrderId"])
                payment_id = int(result["PaymentId"])
                payment_url = result["PaymentURL"]

                raw_status = result["Status"]
                status = (
                    PAYMENT_STATUS_NEW
                    if raw_status == "NEW"
                    else PAYMENT_STATUS_REJECTED
                )

                if init_payment.order.id != order_id:
                    return None

                init_payment.payment_id = payment_id
                init_payment.status = status
                init_payment.save()

                if status == PAYMENT_STATUS_REJECTED:
                    return None

                # Send url to user
                return {"payment_url": payment_url}

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
                        "error_details": error_details,
                    }
                }
            return None


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    sum = models.DecimalField(max_digits=16, decimal_places=2)
    payment_attempts = models.PositiveSmallIntegerField(default=1)
    authorized = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    paid_card_pan = models.CharField(max_length=31, default="")
    session = models.ForeignKey(
        to="parkings.ParkingSession", null=True, blank=True, on_delete=models.CASCADE
    )
    refund_request = models.BooleanField(default=False)
    refunded_sum = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fiscal_notification = models.ForeignKey(
        FiskalNotification, null=True, blank=True, on_delete=models.CASCADE
    )
    homebank_fiscal_notification = models.ForeignKey(
        HomeBankFiskalNotification, null=True, blank=True, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # for init payment order
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.CASCADE
    )

    # for parking card
    parking_card_session = models.ForeignKey(
        to="rps_vendor.RpsParkingCardSession",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    paid_notified_at = models.DateTimeField(null=True, blank=True)

    # for subscription
    subscription = models.ForeignKey(
        to="rps_vendor.RpsSubscription", null=True, blank=True, on_delete=models.CASCADE
    )

    # for non-accounts payments
    client_uuid = models.UUIDField(null=True, default=None)

    # use multiple terminals
    terminal = models.ForeignKey(Terminal, null=True, on_delete=models.CASCADE)
    payload = JSONField(null=False, default=dict)

    acquiring = models.CharField(
        max_length=20, choices=ACQUIRING_LIST, default="tinkoff"
    )

    canceled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

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

    def generate_receipt_data(self, email=None):
        if self.subscription:
            email = (
                self.subscription.account.email if self.subscription.account else None
            )
            phone = (
                self.subscription.account.phone if self.subscription.account else None
            )

            if self.acquiring == "homebank":
                return {
                    "invoiceId": str(self.id).zfill(9),
                    "amount": int(self.sum),
                    "terminalId": settings.HOMEBANK_TERMINAL_ID,
                    "currency": "KZT",
                    "description": self.get_payment_description(),
                    "backLink": "",
                    "failureBackLink": "",
                    "postLink": "https://%s/api/v1/payments/homebank-callback/"
                    % settings.BASE_DOMAIN,
                    "failurePostLink": "https://%s/api/v1/payments/homebank-callback/"
                    % settings.BASE_DOMAIN,
                    "language": "rus",
                    "paymentType": "cardId",
                    "cardId": {"id": ""},
                    "email": email,
                    "phone": phone,
                }
            else:
                return dict(
                    Email=email,
                    Phone=phone,
                    Taxation="usn_income",
                    Items=[
                        {
                            "Name": self.get_payment_description(),
                            "Price": str(int(self.sum * 100)),
                            "Quantity": 1.00,
                            "Amount": str(int(self.sum * 100)),
                            "Tax": "none",
                        }
                    ],
                )

        if self.parking_card_session or self.client_uuid:
            if email is None:
                email = (
                    self.parking_card_session.account.email
                    if self.parking_card_session.account
                    else None
                )
            phone = (
                self.parking_card_session.account.phone
                if self.parking_card_session.account
                else self.parking_card_session.parking_card.phone
            )

            if phone and len(phone) == 1:
                phone = ""

            if self.acquiring == "homebank":
                return {
                    "invoiceId": str(self.id).zfill(9),
                    "amount": int(self.sum),
                    "terminalId": settings.HOMEBANK_TERMINAL_ID,
                    "currency": "KZT",
                    "description": self.get_payment_description(),
                    "backLink": "",
                    "failureBackLink": "",
                    "postLink": "https://%s/api/v1/payments/homebank-callback/"
                    % settings.BASE_DOMAIN,
                    "failurePostLink": "https://%s/api/v1/payments/homebank-callback/"
                    % settings.BASE_DOMAIN,
                    "language": "rus",
                    "paymentType": "cardId",
                    "cardId": {"id": ""},
                    "email": email,
                    "phone": phone,
                }
            else:
                return dict(
                    Email=email,
                    Phone=phone,
                    Taxation="usn_income",
                    Items=[
                        {
                            "Name": self.get_payment_description(),
                            "Price": str(int(self.sum * 100)),
                            "Quantity": 1.00,
                            "Amount": str(int(self.sum * 100)),
                            "Tax": "none",
                        }
                    ],
                )

        # Init payment receipt
        if self.session is None:
            if self.acquiring == "homebank":
                return {
                    "invoiceId": str(self.id).zfill(9),
                    "amount": 10,
                    "terminalId": settings.HOMEBANK_TERMINAL_ID,
                    "currency": "KZT",
                    "description": "Привязка карты",
                    "backLink": "",
                    "failureBackLink": "",
                    "postLink": "https://%s/api/v1/payments/homebank-callback/"
                    % settings.BASE_DOMAIN,
                    "failurePostLink": "https://%s/api/v1/payments/homebank-callback/"
                    % settings.BASE_DOMAIN,
                    "language": "rus",
                    "paymentType": "cardId",
                    "cardId": {"id": ""},
                    "phone": self.account.phone,
                }
            else:
                return dict(
                    Email=None,  # not send to email
                    Phone=self.account.phone,
                    Taxation="usn_income",
                    Items=[
                        {
                            "Name": "Привязка карты",
                            "Price": 100,
                            "Quantity": 1.00,
                            "Amount": 100,
                            "Tax": "none",
                        }
                    ],
                )

        # session payment receipt
        if self.acquiring == "homebank":
            return {
                "invoiceId": str(self.id).zfill(9),
                "amount": int(self.sum),
                "terminalId": settings.HOMEBANK_TERMINAL_ID,
                "currency": "KZT",
                "description": "Оплата услуг парковки %s" % self.session.parking.name,
                "backLink": "",
                "failureBackLink": "",
                "postLink": "https://%s/api/v1/payments/homebank-callback/"
                % settings.BASE_DOMAIN,
                "failurePostLink": "https://%s/api/v1/payments/homebank-callback/"
                % settings.BASE_DOMAIN,
                "language": "rus",
                "paymentType": "cardId",
                "cardId": {"id": ""},
                "email": (
                    str(self.session.client.email)
                    if self.session.client.email
                    else None
                ),
                "phone": str(self.session.client.phone),
            }
        else:
            return dict(
                Email=(
                    str(self.session.client.email)
                    if self.session.client.email
                    else None
                ),
                Phone=str(self.session.client.phone),
                Taxation="usn_income",
                Items=[
                    {
                        "Name": "Оплата услуг парковки %s" % self.session.parking.name,
                        "Price": str(int(self.sum * 100)),
                        "Quantity": 1.00,
                        "Amount": str(int(self.sum * 100)),
                        "Tax": "none",
                    }
                ],
            )

    def get_payment_description(self):
        if self.subscription:
            return "Оплата абонемента, %s" % self.subscription.parking.name

        if self.parking_card_session or self.client_uuid:
            parking = self.parking_card_session.get_parking()
            return "Оплата парковочной карты, %s" % parking.name

        if self.session is None:
            return "Привязка карты"

        return "Оплата парковочной сессии, %s" % self.session.parking.name

    def get_parking(self):
        if self.subscription:
            return self.subscription.parking

        if self.parking_card_session or self.client_uuid:
            parking = self.parking_card_session.get_parking()
            return parking

        return self.session.parking

    def get_parking_max_client_debt(self):
        if self.subscription:
            return self.subscription.parking.max_client_debt

        if self.parking_card_session or self.client_uuid:
            parking = self.parking_card_session.get_parking()
            return parking.max_client_debt

        return self.session.parking.max_client_debt

    def is_refunded(self):
        return self.refunded_sum == self.sum

    def try_pay(self):
        get_logger().info("Try make payment #%s", self.id)

        try:
            if self.acquiring == "homebank":
                return self.create_payment_homebank()
            else:
                self.create_payment()
        except Exception as e:
            import traceback

            trace_back = traceback.format_exc()
            message = str(e) + " " + str(trace_back)
            send_mail(
                "Ошибка на сайте. try_pay", message, EMAIL_HOST_USER, EMAILS_HOST_ALERT
            )
            logger.error(message)

    def get_payment_amount(self):
        if self.acquiring == "homebank":
            return int(self.sum)
        else:
            return int(self.sum * 100)

    def get_tinkoff_api(self):
        if not self.terminal or self.terminal == "main":
            return TinkoffAPI()
        else:
            return TinkoffAPI(with_terminal=self.terminal.name)

    def create_non_recurrent_payment(self, email, only_for_payment_object_return=False):
        if self.acquiring == "homebank":
            get_logger().info("recurrent payment for homebank")
            receipt_data = self.generate_receipt_data()
            HomeBankPayment.objects.create(
                order=self, receipt_data=json.dumps(receipt_data)
            )
            if only_for_payment_object_return:
                return HomeBankPayment
            else:
                return {
                    "payment_url": "https://%s/api/v1/payments/homebank?order_id=%s&back_link=%s&email=%s"
                    % (
                        settings.BASE_DOMAIN,
                        self.id,
                        settings.PARKPASS_PAY_APP_LINK + "?success=1",
                        email,
                    )
                }

        receipt_data = self.generate_receipt_data()
        receipt_data["Email"] = email

        init_payment = TinkoffPayment.objects.create(
            order=self, receipt_data=receipt_data
        )

        if only_for_payment_object_return:
            get_logger().info("only_for_payment_object_return")

            return init_payment

        customer_key = (
            str(self.client_uuid)
            if self.client_uuid
            else self.parking_card_session.client_uuid
        )

        request_data = init_payment.build_non_recurrent_request_data(
            self.get_payment_amount(),
            customer_key,
        )

        get_logger().info("Init non recurrent request")
        elastic_log(
            ES_APP_PAYMENTS_LOGS_INDEX_NAME,
            "Make card non recurrent payment",
            request_data,
        )

        result = self.get_tinkoff_api().sync_call(TinkoffAPI.INIT, request_data)

        # Tink-off gateway not responded
        if not result:
            return None

        elastic_log(
            ES_APP_PAYMENTS_LOGS_INDEX_NAME,
            "Response card non recurrent payment",
            result,
        )
        get_logger().info("Response card non recurrent payment")
        get_logger().info(result)

        # Payment success
        if result.get("Success", False):

            order_id = int(result["OrderId"])
            payment_id = int(result["PaymentId"])
            payment_url = result["PaymentURL"]

            raw_status = result["Status"]
            status = (
                PAYMENT_STATUS_NEW if raw_status == "NEW" else PAYMENT_STATUS_REJECTED
            )

            if init_payment.order.id != order_id:
                return None

            init_payment.payment_id = payment_id
            init_payment.status = status
            init_payment.save()

            if status == PAYMENT_STATUS_REJECTED:
                return None

            # Send url to user
            return {
                "payment_url": payment_url,
                "payment_id": payment_id,
                "order_id": order_id,
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
                    "error_details": error_details,
                }
            }
        return None

    def create_payment(self):

        try:
            receipt_data = self.generate_receipt_data()
            new_payment = TinkoffPayment.objects.create(
                order=self, receipt_data=receipt_data
            )

            request_data = new_payment.build_transaction_data(self.get_payment_amount())
            result = self.get_tinkoff_api().sync_call(TinkoffAPI.INIT, request_data)
            get_logger().info("Make init session payment")
            get_logger().info(request_data)

            elastic_log(
                ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                "Make init session payment",
                request_data,
            )

            # Tink-off gateway not responded
            if not result:
                return None

            elastic_log(
                ES_APP_PAYMENTS_LOGS_INDEX_NAME, "Response session payment", result
            )

            get_logger().info("Response session payment")
            get_logger().info(result)

            # Payment success
            if result.get("Success", False):
                payment_id = int(result["PaymentId"])

                raw_status = result["Status"]
                status = (
                    PAYMENT_STATUS_NEW
                    if raw_status == "NEW"
                    else PAYMENT_STATUS_REJECTED
                )
                get_logger().info("Init status: " + raw_status)
                new_payment.payment_id = payment_id
                new_payment.status = status
                new_payment.save()

                # Credit card bind

                # Событие холдирования
                if self.get_account():
                    device_for_push_notification = AccountDevice.objects.filter(
                        account=self.get_account(), active=True
                    )[0]
                    # if device_for_push_notification:
                    #     device_for_push_notification.send_message(title='Сделали промежуточный платеж %s руб.' % int(
                    #                                                   self.sum * 100),
                    #                                               body='Парковка установила промежуточное списание по достижениюю (% руб) задолженности за парковку. Подробности внутри.' % self.get_parking_max_client_debt())

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

                # Событие ошибки холда
                if self.get_account():
                    device_for_push_notification = AccountDevice.objects.filter(
                        account=self.get_account(), active=True
                    )[0]
                    if device_for_push_notification:
                        device_for_push_notification.send_message(
                            title="Не получилось сделать промежуточный платеж %s руб."
                            % int(self.sum * 100),
                            body="Мы не смогли сделать промежуточный платёж за парковку. Подробности внутри.",
                        )

        except Exception as e:
            import traceback

            trace_back = traceback.format_exc()
            message = str(e) + " " + str(trace_back)
            send_mail(
                "Ошибка на сайте. create_payment",
                message,
                EMAIL_HOST_USER,
                EMAILS_HOST_ALERT,
            )
            logger.error(message)

    def create_payment_homebank(self):

        receipt_data = self.generate_receipt_data()
        get_logger().info("instant payment start:")
        get_logger().info(json.dumps(receipt_data))

        elastic_log(
            ES_APP_PAYMENTS_LOGS_INDEX_NAME, "instant payment start", receipt_data
        )

        new_payment = HomeBankPayment.objects.create(
            order=self, receipt_data=receipt_data
        )

        account = None

        if self.session:
            account = self.session.client
        elif self.parking_card_session:
            account = self.parking_card_session.account
        else:
            account = self.subscription.account

        if account is None:
            get_logger().warn(
                "Payment was broken. You try pay throw credit card unknown account"
            )
            return

        default_account_credit_card = CreditCard.objects.filter(
            account=account, acquiring="homebank"
        ).first()

        if not default_account_credit_card:
            get_logger().warn("Payment was broken. Account should has bind card")
            return

        receipt_data["cardId"]["id"] = default_account_credit_card.card_char_id

        result = HomeBankAPI().authorize(data=receipt_data)

        if not result:
            return None

        error_code = result.get("code", False)

        if not error_code:
            payment_id = result["id"]
            new_payment.payment_id = payment_id
            new_payment.status = PAYMENT_STATUS_AUTHORIZED
            new_payment.save()

        return result

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
            get_logger().warn(
                "Payment was broken. You try pay throw credit card unknown account"
            )
            return

        default_account_credit_card = CreditCard.objects.filter(
            account=account, is_default=True, acquiring="tinkoff"
        ).first()

        if not default_account_credit_card:
            get_logger().warn("Payment was broken. Account should has bind card")
            return

        request_data = payment.build_charge_request_data(
            payment.payment_id, default_account_credit_card.rebill_id
        )
        get_logger().info("Make charge session payment")
        get_logger().info(request_data)
        elastic_log(
            ES_APP_PAYMENTS_LOGS_INDEX_NAME, "Make charge session payment", request_data
        )

        # Add
        payment.status = PAYMENT_STATUS_PREPARED_AUTHORIZED
        payment.save()
        result = self.get_tinkoff_api().sync_call(TinkoffAPI.CHARGE, request_data)
        elastic_log(
            ES_APP_PAYMENTS_LOGS_INDEX_NAME, "Response charge session payment", result
        )
        get_logger().info("Response charge session payment")
        get_logger().info(result)

        if result["Status"] == "AUTHORIZED":
            payment.status = (
                PAYMENT_STATUS_AUTHORIZED
                if payment.status != PAYMENT_STATUS_CONFIRMED
                else PAYMENT_STATUS_CONFIRMED
            )
            payment.save()

        get_logger().info(str(result))

    def get_order_with_fiscal_dict(self):
        order = dict(id=self.id, sum=float(self.sum))

        fiscal = None
        if self.acquiring == "homebank":
            if self.homebank_fiscal_notification:
                fiscal = serializer(self.homebank_fiscal_notification)
        else:
            if self.fiscal_notification:
                fiscal = serializer(self.fiscal_notification)

        return dict(order=order, fiscal=fiscal)

    def get_order_with_fiscal_check_url_dict(self):
        order = dict(id=self.id, sum=float(self.sum))

        url = None
        if self.acquiring == "homebank":
            if self.homebank_fiscal_notification:
                url = self.homebank_fiscal_notification.ticket_url
        else:
            if self.fiscal_notification:
                url = self.fiscal_notification.url

        return dict(order=order, url=url)

    def confirm_payment(self, payment):
        try:
            get_logger().info("Make confirm order: %s" % self.id)
            request_data = payment.build_confirm_request_data(self.get_payment_amount())
            elastic_log(
                ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                "Make confirm session payment",
                request_data,
            )

            result = self.get_tinkoff_api().sync_call(TinkoffAPI.CONFIRM, request_data)

            elastic_log(
                ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                "Response confirm session payment",
                result,
            )

            if not result.get("Success", False):
                # Событие ошибки оплаты
                if self.get_account():
                    device_for_push_notification = AccountDevice.objects.filter(
                        account=self.get_account(), active=True
                    )[0]
                    if device_for_push_notification:
                        parking_name = "-"
                        parking = self.get_parking()
                        if parking:
                            parking_name = parking.name
                        device_for_push_notification.send_message(
                            title="Оплата не прошла",
                            body="Не получилось оплатить %s руб. за паркововку в %s. Подробности внутри."
                            % (self.get_payment_amount(), parking_name),
                        )

                pass

        except Exception as e:
            import traceback

            trace_back = traceback.format_exc()
            message = str(e) + " " + str(trace_back)
            send_mail(
                "Ошибка на сайте. confirm_payment",
                message,
                EMAIL_HOST_USER,
                EMAILS_HOST_ALERT,
            )
            logger.error(message)

    def confirm_payment_homebank(self, payment):
        try:
            get_logger().info("Make confirm homebank order: %s" % self.id)
            account = None

            if self.session:
                account = self.session.client
            elif self.parking_card_session:
                account = self.parking_card_session.account
            else:
                account = self.subscription.account

            if account is None:
                get_logger().warn(
                    "Payment was broken. You try pay throw credit card unknown account"
                )
                return

            default_account_credit_card = CreditCard.objects.filter(
                account=account, acquiring="homebank"
            ).first()

            if not default_account_credit_card:
                get_logger().warn("Payment was broken. Account should has bind card")
                return

            result = HomeBankAPI().confirm(payment.payment_id)

            if result:
                payments.views.HomeBankCallbackView().payment_set(
                    self, payment, PAYMENT_STATUS_CONFIRMED, None
                )
                payment.status = PAYMENT_STATUS_CONFIRMED
                payment.save()
        except Exception as e:
            import traceback

            trace_back = traceback.format_exc()
            message = str(e) + " " + str(trace_back)
            send_mail(
                "Ошибка на сайте. confirm_payment_homebank",
                message,
                EMAIL_HOST_USER,
                EMAILS_HOST_ALERT,
            )
            logger.error(message)

    def send_receipt_to_email(self):
        email = self.session.client.email
        render_data = {"order": self, "email": email}
        if self.acquiring == "homebank":
            msg_html = render_to_string("emails/homebank-receipt.html", render_data)
        else:
            msg_html = render_to_string("emails/receipt.html", render_data)

        send_mail(
            "Электронная копия чека",
            "",
            EMAIL_HOST_USER,
            ["%s" % str(email)],
            html_message=msg_html,
        )

    def get_account(self):
        account = None
        if self.session:
            account = self.session.client
        elif self.parking_card_session:
            account = self.parking_card_session.account
        else:
            account = self.subscription.account

        return account


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
PAYMENT_STATUS_PREPARED_AUTHORIZED = 12

PAYMENT_STATUSES = (
    (PAYMENT_STATUS_UNKNOWN, "Unknown"),
    (PAYMENT_STATUS_INIT, "Init"),
    (PAYMENT_STATUS_NEW, "New"),
    (PAYMENT_STATUS_CANCEL, "Cancel"),
    (PAYMENT_STATUS_FORMSHOWED, "Form showed"),
    (PAYMENT_STATUS_REJECTED, "Rejected"),
    (PAYMENT_STATUS_AUTH_FAIL, "Auth fail"),
    (PAYMENT_STATUS_AUTHORIZED, "Authorized"),
    (PAYMENT_STATUS_CONFIRMED, "Confirmed"),
    (PAYMENT_STATUS_REFUNDED, "Refunded"),
    (PAYMENT_STATUS_PARTIAL_REFUNDED, "Partial_refunded"),
    (PAYMENT_STATUS_PREPARED_AUTHORIZED, "Authorization prepared"),
)


class TinkoffPayment(models.Model):
    payment_id = models.BigIntegerField(unique=True, blank=True, null=True)
    status = models.SmallIntegerField(
        choices=PAYMENT_STATUSES, default=PAYMENT_STATUS_INIT
    )
    order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.CASCADE
    )  # TODO DELETE FROM THIS
    receipt_data = models.TextField(null=True, blank=True)

    # Fields for debug
    error_code = models.IntegerField(default=-1)
    error_message = models.CharField(max_length=127, blank=True, null=True)
    error_description = models.TextField(max_length=511, blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tinkoff Payment"
        verbose_name_plural = "Tinkoff Payments"

    def build_non_recurrent_request_data(self, amount, customer_key):
        data = {
            "Amount": str(amount),
            "OrderId": str(self.order.id),
            "Description": self.order.get_payment_description(),
            "CustomerKey": str(customer_key),
        }
        if self.order.payload:
            data["SuccessURL"] = self.order.payload.get("parking_redirect_url")

        if self.receipt_data:
            data["Receipt"] = self.receipt_data
        return data

    def build_init_request_data(self, customer_key):
        data = {
            "Amount": str(100),  # 1 RUB
            "OrderId": str(self.order.id),
            "Description": "Initial payment",
            "Recurrent": "Y",
            "CustomerKey": str(customer_key),
        }
        if self.order.payload:
            data["SuccessURL"] = self.order.payload.get("parking_redirect_url")
        if self.receipt_data:
            data["Receipt"] = self.receipt_data
        return data

    def build_transaction_data(self, amount):
        data = {
            "Amount": str(amount),
            "OrderId": str(self.order.id),
            "Description": self.order.get_payment_description(),
        }
        if self.order.payload:
            data["SuccessURL"] = self.order.payload.get("parking_redirect_url")
        if self.receipt_data:
            data["Receipt"] = self.receipt_data
        return data

    def build_charge_request_data(self, payment_id, rebill_id):
        data = {
            "PaymentId": str(payment_id),
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
        data = {"PaymentId": str(self.payment_id)}
        if refund_amount:
            data["Amount"] = str(refund_amount)
        return data

    def set_new_status(self, new_status):
        if new_status == "CANCEL":
            self.status = PAYMENT_STATUS_CANCEL

        elif new_status == "AUTHORIZED" and self.status != PAYMENT_STATUS_CONFIRMED:
            self.status = PAYMENT_STATUS_AUTHORIZED

        elif new_status == "CONFIRMED":
            self.status = PAYMENT_STATUS_CONFIRMED

        elif new_status == "REJECTED":
            self.status = PAYMENT_STATUS_REJECTED

        elif new_status == "AUTH_FAIL":
            self.status = PAYMENT_STATUS_AUTH_FAIL

        elif new_status == "REFUNDED":
            self.status = PAYMENT_STATUS_REFUNDED

        self.save()


class TinkoffSession(models.Model):
    refresh_token = models.TextField()
    access_token = models.TextField(null=True, blank=True)
    expires_in = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tinkoff_session"

    def is_session_valid(self):
        return timezone.now() < self.expires_in


class InvoiceWithdraw(models.Model):
    URL_UPDATE_TOKEN = "https://openapi.tinkoff.ru/sso/secure/token"
    URL_WITHDRAW = "https://openapi.tinkoff.ru/sme/api/v1/partner/company/%s/payment"

    documentNumber = models.TextField(
        null=True, blank=True, help_text="Номер документа"
    )
    documentDate = models.DateField(null=True, blank=True, help_text="Дата документа")
    amount = models.IntegerField(help_text="Сумма платежа")
    recipientName = models.TextField(help_text="Получатель")
    inn = models.TextField()
    kpp = models.TextField()

    accountNumber = models.TextField(help_text="Номер счета получателя")
    bankAcnt = models.TextField(null=True, blank=True, help_text="Банк получателя")
    bankBik = models.TextField(null=True, blank=True, help_text="БИК банка получателя")

    paymentPurpose = models.TextField(
        default="", blank=True, help_text="Назначение платежа"
    )
    executionOrder = models.IntegerField(default=0, help_text="Очередность платежа")

    taxPayerStatus = models.TextField(
        null=True, blank=True, help_text="Статус составителя расчетного документа"
    )
    kbk = models.TextField(
        null=True, blank=True, help_text="Код бюджетной классификации"
    )
    oktmo = models.TextField(
        null=True,
        blank=True,
        help_text="Код ОКТМО территории, на которой мобилизуютсяденежные "
        "средства от уплаты налога, сбора и иного платежа",
    )

    taxEvidence = models.TextField(
        null=True, blank=True, help_text="Основание налогового платежа"
    )
    taxPeriod = models.TextField(
        null=True, blank=True, help_text="Налоговый период / код таможенного органа"
    )
    uin = models.TextField(
        null=True, blank=True, help_text="Уникальный идентификатор платежа"
    )

    taxDocNumber = models.TextField(
        null=True, blank=True, help_text="Номер налогового документа"
    )
    taxDocDate = models.TextField(
        null=True, blank=True, help_text="Дата налогового документа"
    )

    is_send = models.BooleanField(default=False)
    is_requested = models.BooleanField(default=False)
    error = models.TextField(null=True, blank=True)

    responseDocumentId = models.TextField(
        null=True, blank=True, help_text="Идентифиакор созданного платежного поручения"
    )

    class Meta:
        db_table = "invoice_withdraw"

    def __str__(self):
        return "(%s) %s" % (self.amount, self.accountNumber)

    def init_send(self):
        if not self.is_send and not self.is_requested:
            self.is_requested = True
            self.save()

            self.is_send = self.send_withdraw_request()
        self.is_requested = False
        self.save()

    def _get_saved_access_token(self):
        active_session = TinkoffSession.objects.all().order_by("-created_at").first()
        if active_session:
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
        if not access_token:
            return None, "Empty access_token"
        return access_token, None

    def _withdraw_request(self, token):
        headers = {
            "Authorization": "Bearer %s" % token,
            "Content-Type": "application/json",
        }
        try:
            body = {
                "documentNumber": str(self.id),
                "date": None,  # right now
                "amount": self.amount,
                "recipientName": self.recipientName,
                "inn": self.inn,
                "kpp": self.kpp,
                "bankAcnt": self.bankAcnt,
                "bankBik": self.bankBik,
                "accountNumber": self.accountNumber,
                "paymentPurpose": self.paymentPurpose,
                "executionOrder": self.executionOrder,
                "taxPayerStatus": self.taxPayerStatus if self.taxPayerStatus else 0,
                "kbk": self.kbk if self.kbk else "0",
                "oktmo": self.oktmo if self.oktmo else "0",
                "taxEvidence": self.taxEvidence if self.taxEvidence else "0",
                "taxPeriod": self.taxPeriod if self.taxPeriod else "0",
                "uin": self.uin if self.uin else "0",
                "taxDocNumber": self.taxDocNumber if self.taxDocNumber else "0",
                "taxDocDate": self.taxDocDate if self.taxDocDate else "0",
            }

            print(body)
            res = requests.post(
                InvoiceWithdraw.URL_WITHDRAW % PARKPASS_INN,
                json.dumps(body),
                headers=headers,
            )
            print(res.content)

            if res.status_code == 200:
                json_data = res.json()
                if json_data.get("documentId"):
                    self.responseDocumentId = str(json_data["documentId"])
                    return True, None

            return False, "Status not 200 %s" % res.content

        except Exception as e:
            print(str(e))
            return False, str(e)


class HomeBankPayment(models.Model):
    payment_id = models.CharField(max_length=60, unique=True, blank=True, null=True)
    status = models.SmallIntegerField(default=PAYMENT_STATUS_UNKNOWN)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.CASCADE)
    reason_code = models.SmallIntegerField(default=-1)
    receipt_data = models.TextField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "HomeBank Payment"
        verbose_name_plural = "HomeBank Payments"

    def cancel_payment(self):
        logging.info("Cancel payment response: ")

        result = HomeBankAPI().cancel_payment(self.payment_id)

        get_logger().info("home bank log 10")

        if result:
            get_logger().info("home bank log 11")
            self.status = PAYMENT_STATUS_CANCEL
            self.save()

            order = self.order
            get_logger().info(order)
            get_logger().info(order.id)
            get_logger().info(Decimal(float(order.get_payment_amount())))

            order.refund_request = True
            order.refunded_sum = Decimal(float(order.get_payment_amount()))
            order.save()
