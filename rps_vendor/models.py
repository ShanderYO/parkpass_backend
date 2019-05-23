import hashlib
import hmac
import json
import traceback

from dateutil.parser import *
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

# Create your models here.
from django.utils import timezone
from dss.Serializer import serializer

from accounts.models import Account
from base.utils import get_logger
from parkings.models import Parking


class RpsParking(models.Model):
    id = models.AutoField(primary_key=True)
    request_update_url = models.URLField(null=True, blank=True)

    request_parking_card_debt_url = models.URLField(
        default="https://parkpass.ru/api/v1/parking/rps/mock/debt/")

    request_payment_authorize_url = models.URLField(
        default="https://parkpass.ru/api/v1/parking/rps/mock/authorized/")

    polling_enabled = models.BooleanField(default=False)
    last_request_body = models.TextField(null=True, blank=True)
    last_request_date = models.DateTimeField(auto_now_add=True)

    last_response_code = models.IntegerField(default=0)
    last_response_body = models.TextField(null=True, blank=True)
    parking = models.ForeignKey(Parking)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'RpsParking'
        verbose_name_plural = 'RpsParking'

    def __unicode__(self):
        return "%s" % (self.parking.name)

    def get_parking_card_debt_url(self, query):
        return self.request_parking_card_debt_url + '?' + query

    def get_parking_card_debt(self, parking_card):
        debt, duration = self._make_http_for_parking_card_debt(parking_card.card_id)
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

        return serializer(card_session)

    def _make_http_for_parking_card_debt(self, parking_card):
        connect_timeout = 2

        SECRET_HASH = 'yWQ6pSSSNTDMmRsz3dnS'

        prefix_query_str = "ticket_id=%s&FromPay=ParkPass" % parking_card

        str_for_hash = prefix_query_str + ("&%s" % SECRET_HASH)
        hash_str = hashlib.sha1(str_for_hash).hexdigest()

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

                        seconds_ago = (server_time - entered_at).seconds

                        return result["amount"], seconds_ago if seconds_ago > 0 else 0

                    elif result.get("status") == "CardNotFound":
                        return None, None
                    else:
                        return 0,0
                else:
                    self.last_response_body = ""
                self.save()
                return 0,0

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

        return 0, 0


class ParkingCard(models.Model):
    card_id = models.CharField(max_length=255, unique=True, primary_key=True)
    phone = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
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
    parking_card = models.ForeignKey(ParkingCard)
    parking_id = models.IntegerField()
    debt = models.IntegerField(default=0)
    duration = models.IntegerField(default=0)
    state = models.PositiveSmallIntegerField(
        choices=CARD_SESSION_STATES, default=STATE_CREATED)
    account = models.ForeignKey(Account, null=True, default=None)
    client_uuid = models.UUIDField(null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "Parking RPS session %s %s" % (
            self.parking_card,
            self.parking_id
        )

    def notify_authorize(self, order):
        self.state = STATE_AUTHORIZED
        self.save()

        SECRET_HASH = 'yWQ6pSSSNTDMmRsz3dnS'

        prefix_query_str = "ticket_id=%s&amount=%s&FromPay=ParkPass" % (self.parking_card.card_id, int(order.sum))

        str_for_hash = prefix_query_str + ("&%s" % SECRET_HASH)
        hash_str = hashlib.sha1(str_for_hash).hexdigest()

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
                'parking').get(id=self.parking_id)

            return self._make_http_ok_status(
                rps_parking.request_payment_authorize_url, payload)

        except ObjectDoesNotExist:
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
        connect_timeout = 2

        self.last_request_date = timezone.now()
        self.last_request_body = payload

        headers = {
            'Content-type': 'application/json',
        }

        try:
            r = requests.post(url, data=payload, headers=headers,
                              timeout=(connect_timeout, 5.0))
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
                traceback_str = traceback.format_exc()
                self.last_response_code = 998
                self.last_response_body = "Parkpass intenal error: " + str(e) + '\n' + traceback_str
                self.save()

        except Exception as e:
            traceback_str = traceback.format_exc()
            self.last_response_code = 999
            self.last_response_body = "Vendor error: " + str(e) + '\n' + traceback_str
            self.save()

        return False

