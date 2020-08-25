import time
from decimal import Decimal
import hashlib
import json
import traceback

from datetime import timedelta
from dateutil.parser import *
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

# Create your models here.
from django.utils import timezone
from dss.Serializer import serializer

from accounts.models import Account
from base.utils import get_logger
from payments.models import Order


class RpsParking(models.Model):
    id = models.AutoField(primary_key=True)
    request_update_url = models.URLField(null=True, blank=True)

    request_parking_card_debt_url = models.URLField(
        default="https://parkpass.ru/api/v1/parking/rps/mock/debt/")

    request_payment_authorize_url = models.URLField(
        default="https://parkpass.ru/api/v1/parking/rps/mock/authorized/")

    request_get_subscriptions_list_url = models.URLField(
        default="https://parkpass.ru/api/v1/parking/rps/mock/subscriptions/"
    )

    request_subscription_pay_url = models.URLField(
        default="https://parkpass.ru/api/v1/parking/rps/mock/subscription/pay/"
    )

    polling_enabled = models.BooleanField(default=False)
    last_request_body = models.TextField(null=True, blank=True)
    last_request_date = models.DateTimeField(auto_now_add=True)

    last_response_code = models.IntegerField(default=0)
    last_response_body = models.TextField(null=True, blank=True)
    parking = models.ForeignKey(to='parkings.Parking', on_delete=models.CASCADE)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'RpsParking'
        verbose_name_plural = 'RpsParking'

    def __str__(self):
        return "%s" % (self.parking.name)

    def get_parking_card_debt_url(self, query):
        return self.request_parking_card_debt_url + '?' + query

    def get_parking_card_debt(self, parking_card):
        debt, enter_ts, duration = self._make_http_for_parking_card_debt(parking_card.card_id)
        get_logger("Returns: debt=%s, duration=%s" %(debt, duration,))

        # if Card
        if debt is None:
            return None

        card_session, _ = RpsParkingCardSession.objects.get_or_create(
            parking_card=parking_card,
            parking_id=self.parking.id,
            state=STATE_CREATED,
            defaults={
                "debt": debt,
                "duration": duration
            }
        )

        if debt >= 0:
            card_session.debt = debt
            card_session.duration = duration
            card_session.save()

        resp = serializer(card_session)
        resp["entered_at"] = enter_ts

        return resp

    def _make_http_for_parking_card_debt(self, parking_card):
        connect_timeout = 2

        SECRET_HASH = 'yWQ6pSSSNTDMmRsz3dnS'

        prefix_query_str = "ticket_id=%s&FromPay=ParkPass" % parking_card

        str_for_hash = prefix_query_str + ("&%s" % SECRET_HASH)
        hash_str = hashlib.sha1(str_for_hash.encode('utf-8')).hexdigest()

        query_str = prefix_query_str + '&hash=%s' % hash_str

        self.last_request_date = timezone.now()
        self.last_request_body = query_str

        get_logger().info("SEND REQUEST TO RPS %s" % self.get_parking_card_debt_url(query_str))

        try:
            r = requests.get(
                self.get_parking_card_debt_url(query_str),
                timeout=(connect_timeout, 5.0))

            try:
                self.last_response_code = r.status_code
                get_logger().info("GET RESPONSE FORM RPS %s" % r.status_code)
                get_logger().info(r.content)
                if r.status_code == 200:
                    result = r.json()
                    self.last_response_body = result
                    if result.get("status") == "OK":
                        entered_at = parse(result["entered_at"]).replace(tzinfo=None)
                        server_time = parse(result["server_time"]).replace(tzinfo=None)

                        seconds_ago = int((server_time - entered_at).total_seconds())

                        entered_at_ts = int(time.mktime(entered_at.timetuple()) * 1000 + entered_at.microsecond / 1000)
                        return result["amount"], entered_at_ts, seconds_ago if seconds_ago > 0 else 0

                    elif result.get("status") == "CardNotFound":
                        return None, None, None
                    else:
                        return 0, 0, 0
                else:
                    self.last_response_body = ""
                self.save()
                return 0, 0, 0

            except Exception as e:
                get_logger().warn(e)
                traceback_str = traceback.format_exc()
                self.last_response_code = 998
                self.last_response_body = "Parkpass intenal error: " + str(e) + '\n' + traceback_str
                self.save()

        except Exception as e:
            get_logger().warn(e)
            traceback_str = traceback.format_exc()
            self.last_response_code = 999
            self.last_response_body = "Vendor error: " + str(e) + '\n' + traceback_str
            self.save()

        return 0, 0, 0


class ParkingCard(models.Model):
    card_id = models.CharField(max_length=255, unique=True, primary_key=True)
    phone = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Parking card %s" % self.card_id


STATE_CREATED = 1
STATE_INITED = 2
STATE_AUTHORIZED = 3
STATE_CONFIRMED = 4
STATE_ERROR = 5

CARD_SESSION_STATES = (
    (STATE_CREATED, "Only created"),
    (STATE_INITED, "Inited pay"),
    (STATE_AUTHORIZED, "Authorized pay"),
    (STATE_CONFIRMED, "Confirmed pay"),
    (STATE_ERROR, "Error"),
)


class RpsParkingCardSession(models.Model):
    parking_card = models.ForeignKey(ParkingCard, on_delete=models.CASCADE)
    parking_id = models.IntegerField()
    debt = models.IntegerField(default=0)
    duration = models.IntegerField(default=0)
    state = models.PositiveSmallIntegerField(
        choices=CARD_SESSION_STATES, default=STATE_CREATED)
    account = models.ForeignKey(Account, null=True, default=None, on_delete=models.CASCADE)
    client_uuid = models.UUIDField(null=True, default=None)

    from_datetime = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Parking RPS session %s %s" % (
            self.parking_card,
            self.parking_id
        )

    def get_cool_duration(self):
        if self.duration <= 0:
            return 0

        secs = self.duration % 60
        hours = self.duration / 3600
        mins = (self.duration - hours * 3600 - secs) / 60
        return "%02d:%02d:%02d" % (hours, mins, secs)

    def notify_authorize(self, order):
        self.state = STATE_AUTHORIZED
        self.save()

        SECRET_HASH = 'yWQ6pSSSNTDMmRsz3dnS'

        prefix_query_str = "ticket_id=%s&amount=%s&FromPay=ParkPass" % (self.parking_card.card_id, int(order.sum))

        str_for_hash = prefix_query_str + ("&%s" % SECRET_HASH)
        hash_str = hashlib.sha1(str_for_hash.encode('utf-8')).hexdigest()

        payload = json.dumps({
            "ticket_id": self.parking_card.card_id,
            "amount": int(order.sum),
            "FromPay": "ParkPass",
            "hash": hash_str
        })

        get_logger().info("SEND REQUEST TO RPS")
        get_logger().info(payload)

        self.last_request_date = timezone.now()
        self.last_request_body = payload

        try:
            rps_parking = RpsParking.objects.select_related(
                'parking').get(parking__id=self.parking_id)

            return self._make_http_ok_status(
                rps_parking.request_payment_authorize_url, payload)

        except ObjectDoesNotExist:
            self.state = STATE_ERROR
            self.save()
            get_logger().warn("RPS parking is not found")

        return False

    def notify_confirm(self, order):
        self.state = STATE_CONFIRMED
        self.save()
        return True

    def notify_refund(self, sum, order):
        self.state = STATE_ERROR
        self.save()
        return True

    def _make_http_ok_status(self, url, payload):
        get_logger().log("_make_http_ok_status")
        connect_timeout = 2

        self.last_request_date = timezone.now()
        self.last_request_body = payload

        headers = {
            'Content-type': 'application/json',
        }

        try:
            get_logger().log("Try to make_http_ok")
            r = requests.post(url, data=payload, headers=headers,
                              timeout=(connect_timeout, 30.0)) # TODO make
            try:
                self.last_response_code = r.status_code
                get_logger("GET RESPONSE FORM RPS %s" % r.status_code)
                get_logger(r.content)
                if r.status_code == 200:
                    result = r.json()
                    self.last_response_body = result
                    if result["status"] == "OK":
                        return True
                else:
                    self.last_response_body = ""
                self.save()

                return False

            except Exception as e:
                get_logger().warn(str(e))
                traceback_str = traceback.format_exc()
                self.last_response_code = 998
                self.last_response_body = "Parkpass intenal error: " + str(e) + '\n' + traceback_str
                self.save()

        except Exception as e:
            get_logger().warn(str(e))
            traceback_str = traceback.format_exc()
            self.last_response_code = 999
            self.last_response_body = "Vendor error: " + str(e) + '\n' + traceback_str
            self.save()

        return False


SUBSCRIPTION_PAYMENT_STATUSES = (
    (STATE_CREATED, "Only created"),
    (STATE_INITED, "Inited pay"),
    (STATE_AUTHORIZED, "Authorized pay"),
    (STATE_CONFIRMED, "Confirmed pay"),
    (STATE_ERROR, "Error"),
)

class RpsSubscription(models.Model):
    name = models.CharField(max_length=1024)
    description = models.TextField()
    sum = models.IntegerField()

    unlimited = models.BooleanField(default=False, null=True, blank=True)
    started_at = models.DateTimeField()
    expired_at = models.DateTimeField()
    duration = models.IntegerField()
    parking = models.ForeignKey(to='parkings.Parking', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    prolongation = models.BooleanField(default=True)

    data = models.TextField(help_text="Byte array as base64", null=True, blank=True)
    idts = models.TextField()
    id_transition = models.TextField()

    active = models.BooleanField(default=False)

    state = models.PositiveSmallIntegerField(
        choices=SUBSCRIPTION_PAYMENT_STATUSES, default=STATE_CREATED)

    error_message = models.TextField(null=True, blank=True)

    def authorize(self):
        self.state = STATE_AUTHORIZED
        self.save()

    def activate(self):
        self.disable_current_subscriptions()
        self.active = True
        self.state = STATE_CONFIRMED
        self.save()

    def disable_current_subscriptions(self):
        RpsSubscription.objects.filter(
            account=self.account,
            parking=self.parking,
            active=True,
        ).update(active=False)

    def reset(self, error_message=None):
        self.data = None
        self.error_message = error_message
        self.state = STATE_ERROR
        self.save()

    @classmethod
    def get_subscription(cls, url):
        r = requests.get(url)
        get_logger().info(r.content)

        if r.status_code == 200:
            response_dict = {"result":[], "next": None}
            for item in r.json().get("Data", []):
                idts = item["Id"]
                name = item["Name"]
                description  = item.get("TsDescription")
                for perechod in item.get("Perechods", []):
                    resp_item = {
                        "name": name,
                        "description": description,
                        "idts": idts,
                        "id_transition": perechod.get("Id"),
                        "sum": perechod.get("ConditionAbonementPrice"),
                        "duration": perechod.get("ConditionBackTimeInSecond")
                    }
                    response_dict["result"].append(resp_item)
            return response_dict
        else:
            get_logger().warning("Subscription status code: %s" % r.status_code)
            get_logger().warning(r.content)
            return None

    def save(self, *args, **kwargs):
        super(RpsSubscription, self).save(*args, **kwargs)

    def get_cool_duration(self):
        if self.duration <= 0:
            return 0

        days = self.duration // (3600 * 24)
        if days < 30:
            return "%d д." % days
        if days % 30 == 0:
            return "%d мес." % (days // 30)
        return "%d мес. %d д." % (days // 30, days % 30)

    def check_prolong_payment(self):
        if timezone.now() >= self.expired_at and self.active:
            self.active = False
            self.save()
            if self.prolongation:
                new_subscription = RpsSubscription.objects.create(
                    name=self.name, description=self.description,
                    sum=self.sum, started_at=timezone.now(),
                    duration=self.duration,
                    expired_at=timezone.now() + timedelta(seconds=self.duration),
                    parking=self.parking,
                    data=self.data,
                    account=self.account,
                    prolongation=True,
                    idts=self.idts, id_transition=self.id_transition
                )
                new_subscription.create_order_and_pay()

    def create_order_and_pay(self):
        order = Order.objects.create(
            sum=Decimal(self.sum),
            subscription=self
        )
        self.state = STATE_INITED
        self.save()

        order.try_pay()

    def request_buy(self):
        rps_parking = RpsParking.objects.filter(parking=self.parking).first()
        if not rps_parking:
            return False

        url = rps_parking.request_subscription_pay_url
        payload = {
            "user_id": self.account.id,
            "subscription_id": self.id,
            "sum": str(self.sum),
            "ts_id": self.idts,
            "transation_id": self.id_transition,
        }
        if self.data:
            payload["data"] = self.data

        get_logger().info("Try to RSP send %s" % json.dumps(payload))
        r = requests.post(url, json=payload)
        get_logger().info(r.content)

        if r.status_code == 200 and r.json().get("Status") == 200:
            return True
        return False
