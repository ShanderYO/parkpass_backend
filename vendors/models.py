from __future__ import unicode_literals

import binascii
import hashlib
import hmac
import json
import os

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone

from base.utils import get_logger, clear_phone
from owners.validators import validate_inn, validate_kpp
from accounts.models import Account as User, Account
from base.models import BaseAccount, BaseAccountSession, BaseAccountIssue
from rps_vendor.models import RpsSubscription, RpsParkingCardSession


class VendorIssue(BaseAccountIssue):
    def save(self, *args, **kwargs):
        if not self.id:
            self.type = BaseAccountIssue.VENDOR_ISSUE_TYPE
        super(VendorIssue, self).save(*args, **kwargs)

    def accept(self):
        vendor = Vendor(
            phone=self.phone,
            email=self.email,
            name=self.name,
        )
        vendor.full_clean()
        vendor.save()
        vendor.create_password_and_send()
        self.delete()
        return vendor


class Vendor(BaseAccount):
    display_id = models.IntegerField()

    @property
    def session_class(self):
        return VendorSession

    @property
    def type(self):
        return 'vendor'

    class ACCOUNT_STATE:
        DISABLED = 0
        NORMAL = 1
        TEST = 2

    account_states = (
        (ACCOUNT_STATE.DISABLED, "Disabled"),
        (ACCOUNT_STATE.NORMAL, "Normal"),
        (ACCOUNT_STATE.TEST, "Test only")
    )
    org_name = models.CharField(max_length=255, null=True, blank=True)
    account_state = models.IntegerField(choices=account_states, default=ACCOUNT_STATE.NORMAL)
    name = models.CharField(max_length=255, unique=True)
    comission = models.FloatField(default=0.02)
    secret = models.CharField(max_length=255, unique=True, default="stub")

    test_parking = models.ForeignKey(to='parkings.Parking', on_delete=models.CASCADE, blank=True, null=True,
                                     related_name='parking_vendor')
    test_user = models.ForeignKey(to=User, on_delete=models.CASCADE, blank=True, null=True)

    inn = models.CharField(max_length=15, blank=True, null=True, validators=(validate_inn,))
    kpp = models.CharField(max_length=15, blank=True, null=True, validators=(validate_kpp,))
    bic = models.CharField(max_length=15, blank=True, null=True)
    legal_address = models.CharField(max_length=512, blank=True, null=True)
    actual_address = models.CharField(max_length=512, blank=True, null=True)
    checking_account = models.CharField(max_length=64, blank=True, null=True)
    checking_kpp = models.CharField(max_length=15, blank=True, null=True)

    fetch_extern_user_data_url = models.URLField(max_length=1024, null=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __unicode__(self):
        return "%s" % self.name

    def save(self, *args, **kwargs):

        if self.display_id == -1:
            # Get the maximum display_id value from the database
            last_id = Vendor.objects.all().aggregate(largest=models.Max('display_id'))['largest']

            # aggregate can return None! Check it first.
            # If it isn't none, just use the last ID specified (which should be the greatest) and add one to it
            # (From https://stackoverflow.com/questions/41228034/django-non-primary-key-autofield)
            if last_id is not None:
                self.display_id = last_id + 1
        if self._state.adding:
            number = 0
            user = User(
                first_name='%s\'s Test User' % self.first_name,
                last_name='%s\'s Test User' % self.last_name,
                phone=number,
                email='%s@test.com' % self.display_id,
                password='1234567890',
            )
            user.save()
            #  Test parking will be created by post_save signal in parkings/models.py
            self.test_user = user

        if not self.pk:
            if not kwargs.get("not_generate_secret", False):
                self.generate_secret()
            else:
                del kwargs["not_generate_secret"]
        super(Vendor, self).save(*args, **kwargs)

    def generate_secret(self):
        self.secret = binascii.hexlify(os.urandom(32)).decode()

    def sign(self, data):
        return hmac.new(str(self.secret), data, hashlib.sha512)

    def is_external_user(self, external_id):
        if not self.fetch_extern_user_data_url:
            return False

        data = self.make_sign_request(
            self.fetch_extern_user_data_url,
            body=dict(
                id=external_id
            )
        )
        if data and type(data) == dict:
            raw_phone = data.get("phone")
            first_name = data.get("name")
            last_name = data.get("surname")
            email = data.get("email")

            qs = Account.objects.filter(
                external_vendor_id=self.id,
                extern_id=external_id)

            if not qs.exists():
                Account.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    phone=clear_phone(raw_phone),
                    email=email,
                    external_vendor_id=self.id,
                    external_id=external_id
                )
            return True
        else:
            get_logger("Invalid response onlogin %s" % str(data))
        return False

    def make_sign_request(self, url, body):
        payload = json.dumps(body)
        signature = self.sign(payload)

        get_logger().info("SEND REQUEST TO VENDOR")
        get_logger().info("%s | %s to %s" % (payload, signature, url))

        connect_timeout = 2
        headers = {
            'Content-type': 'application/json',
            "x-signature": signature
        }
        try:
            r = requests.post(url, data=payload, headers=headers,
                                  timeout=(connect_timeout, 5.0))
            get_logger.info("GET RESPONSE FORM VENDOR %s" % r.status_code)
            get_logger.info(r.content)
            if r.status_code == 200:
                return r.json()

        except Exception as e:
            get_logger.info(str(e))

        return None


class VendorSession(BaseAccountSession):
    vendor = models.OneToOneField(Vendor)

    @classmethod
    def get_account_by_token(cls, token):
        try:
            session = cls.objects.get(token=token)
            if session.is_expired():
                session.delete()
                return None
            return session.vendor

        except ObjectDoesNotExist:
            return None


VENDOR_NOTIFICATION_TYPE_SESSION_CREATED = 1
VENDOR_NOTIFICATION_TYPE_SESSION_COMPLETED = 2
VENDOR_NOTIFICATION_TYPE_SESSION_CLOSED = 3
VENDOR_NOTIFICATION_TYPE_SUBSCRIPTION_PAID = 4
VENDOR_NOTIFICATION_TYPE_PARKING_CARD_SESSION_PAID = 5


VENDOR_NOTIFICATION_TYPES = (
    (0, "Unknown"),
    (VENDOR_NOTIFICATION_TYPE_SESSION_CREATED, "Session created"),
    (VENDOR_NOTIFICATION_TYPE_SESSION_COMPLETED, "Session completed"),
    (VENDOR_NOTIFICATION_TYPE_SESSION_CLOSED, "Session closed"),
    (VENDOR_NOTIFICATION_TYPE_SUBSCRIPTION_PAID, "Subscription paid"),
    (VENDOR_NOTIFICATION_TYPE_PARKING_CARD_SESSION_PAID, "Parking card session paid"),
)


class VendorNotification(models.Model):
    parking_session = models.ForeignKey(to='parkings.ParkingSession', null=True)
    parking_card_session = models.ForeignKey(RpsParkingCardSession, null=True)
    rps_subscription = models.ForeignKey(RpsSubscription, null=True)
    type = models.PositiveSmallIntegerField(
        choices=VENDOR_NOTIFICATION_TYPES, default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def process(self):
        if self.confirmed_at:
            return

        if type == VENDOR_NOTIFICATION_TYPE_SESSION_CREATED:
            self.on_session_created()
        elif type == VENDOR_NOTIFICATION_TYPE_SESSION_COMPLETED:
            self.on_session_completed()
        elif type == VENDOR_NOTIFICATION_TYPE_SESSION_CLOSED:
            self.on_session_closed()
        elif type == VENDOR_NOTIFICATION_TYPE_SUBSCRIPTION_PAID:
            self.on_subscription_paid()
        elif type == VENDOR_NOTIFICATION_TYPE_PARKING_CARD_SESSION_PAID:
            self.on_parking_card_paid()
        else:
            get_logger("Unknown notification type : id=%s " % self.id)

    def on_session_created(self):
        if self.parking_session:
            url = "https://example.com"
            data = {
                "client_id": self.parking_session.client.id,
                "session_id": self.parking_session.session_id,
                "parking_id": self.parking_session.parking.id,
                "started_at": self.parking_session.started_at
            }
            self._notify_request(url, data)

    def on_session_completed(self):
        if self.parking_session:
            url = "https://example.com"
            data = {
                "client_id": self.parking_session.client.id,
                "session_id": self.parking_session.session_id,
                "debt": self.parking_session.debt,
                "parking_id": self.parking_session.parking.id,
                "completed_at": self.parking_session.completed_at
            }
            self._notify_request(url, data)

    def on_session_closed(self):
        if self.parking_session:
            url = "https://example.com"
            data = {
                "client_id": self.parking_session.client.id,
                "session_id": self.parking_session.session_id,
                "debt": self.parking_session.debt,
                "parking_id": self.parking_session.parking.id,
                "paid_at": self.created_at
            }
            self._notify_request(url, data)

    def on_parking_card_paid(self):
        if self.parking_card_session:
            url = "https://example.com"
            data = {
                "client_id": self.parking_card_session.client.id,
                "parking_card_id": self.parking_card_session.parking_card.card_id,
                "sum": self.parking_card_session.debt,
                "parking_id": self.parking_session.parking.id,
                "paid_at": self.created_at
            }
            self._notify_request(url, data)

    def on_subscription_paid(self):
        if self.rps_subscription:
            url = "https://example.com"
            data = {
                "client_id": self.rps_subscription.account.id,
                "subscription_id": self.rps_subscription.id,
                "sum": self.rps_subscription.sum,
                "parking_id": self.rps_subscription.parking.id,
                "paid_at": self.created_at
            }
            self._notify_request(url, data)

    def _notify_request(self, data):
        self.confirmed_at = timezone.now()
        self.message = "All is OK"
        self.save()