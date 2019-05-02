import json
import traceback

import requests
from django.db import models, transaction

# Create your models here.
from django.utils import timezone
from dss.Serializer import serializer

from accounts.models import Account
from parkings.models import Parking
from payments.models import Order


class RpsParking(models.Model):
    id = models.AutoField(primary_key=True)
    request_update_url = models.URLField(null=True, blank=True)
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

    def get_parking_card_debt(self, parking_card):
        debt, duration = self._make_http_for_parking_card_debt(parking_card)
        card_session, _ = RpsParkingCardSession.object.get_or_create(
            parking_card=parking_card,
            parking_id=self.id,
            defaults={"debt": debt, "duration":duration}
        )
        if debt > 0:
            card_session.debt = debt
            card_session.save()

        return serializer(card_session)

    def _make_http_for_parking_card_debt(self, parking_card):
        connect_timeout = 2

        payload = json.dumps({
            "card_id": parking_card.card_id,
            "phone": parking_card.phone
        })

        headers = {'Content-type': 'application/json'}
        self.last_request_date = timezone.now()
        self.last_request_body = payload

        url = "http://127.0.0.1:8000/rps/mock/"

        try:
            r = requests.post(url, data=payload, headers=headers,
                              timeout=(connect_timeout, 5.0))
            try:
                self.last_response_code = r.status_code
                if r.status_code == 200:
                    result = r.json()
                    self.last_response_body = result
                else:
                    self.last_response_body = ""
                self.save()

                return result["debt"], result["duration"]

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

        return 0, 0


class ParkingCard(models.Model):
    card_id = models.CharField(max_length=255, unique=True, primary_key=True)
    phone = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_created=True)

    def __unicode__(self):
        return "Parking card %s" % (self.card_id)


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
    state = models.PositiveSmallIntegerField(choices=CARD_SESSION_STATES, default=STATE_CREATED)
    account = models.ForeignKey(Account, null=True, default=None)
    client_uuid = models.UUIDField(null=True, default=None)
    created_at = models.DateTimeField(auto_created=True)

    def __unicode__(self):
        return "Parking RPS session %s %s" % (
            self.parking_card,
            self.parking_id
        )

    def notify_authorize(self, order):
        self.state = STATE_AUTHORIZED
        self.save()

        url = "127.0.0.1:8000/rps/mock/authorize/"

        payload = json.dump({
            "card_id": self.parking_card.card_id,
            "order_id": order.id,
            "sum":order.sum
        })
        return self._make_http_ok_status(url, payload)

    def notify_confirm(self, order):
        self.state = STATE_CONFIRMED
        self.save()

        url = "127.0.0.1:8000/rps/mock/confirm/"

        payload = json.dump({
            "card_id": self.parking_card.card_id,
            "order_id": order.id,
            "sum": order.sum
        })
        return self._make_http_ok_status(url, payload)

    def notify_refund(self, sum, order):
        self.state = STATE_ERROR
        self.save()

        url = "127.0.0.1:8000/rps/mock/confirm/"

        payload = json.dump({
            "card_id": self.parking_card.card_id,
            "order_id": order.id,
            "refund_sum": sum,
            "refund_reason": "Undefinded" # TODO add clear reason
        })
        return self._make_http_ok_status(url, payload)

    def _make_http_ok_status(self, url, payload):
        connect_timeout = 2

        headers = {'Content-type': 'application/json'}
        self.last_request_date = timezone.now()
        self.last_request_body = payload

        try:
            r = requests.post(url, data=payload, headers=headers,
                              timeout=(connect_timeout, 5.0))
            try:
                self.last_response_code = r.status_code
                if r.status_code == 200:
                    result = r.json()
                    self.last_response_body = result
                else:
                    self.last_response_body = ""
                self.save()

                return r.status_code == 200

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


    """    @transaction.atomic
    def start_pay(self, account):
        new_order = Order.objects.create(

        )
        self.state = STATE_INITED
    """

