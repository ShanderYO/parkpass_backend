import secrets
import time
import uuid
from decimal import Decimal
import hashlib
import json
import traceback

from datetime import timedelta
from urllib.parse import urlparse

from dateutil.parser import *
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

# Create your models here.
from django.utils import timezone
from django.utils.crypto import get_random_string
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from integration.services import RpsIntegrationService

from dss.Serializer import serializer

from accounts.models import Account
from base.utils import get_logger, elastic_log, send_request_with_retries
from parkpass_backend.settings import ES_APP_CARD_PAY_LOGS_INDEX_NAME
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
    
    domain = models.CharField(max_length=255, null=True, blank=True)
    token = models.CharField(max_length=255, null=True, blank=True)
    token_expired = models.DateTimeField(null=True, blank=True)
    integrator_id = models.CharField(max_length=255, null=True, blank=True)
    integrator_password = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'RpsParking'
        verbose_name_plural = 'RpsParking'

    def __str__(self):
        return "%s" % (self.parking.name)
    
    def ensure_token(self):
        if self.token_expired is None or self.token_expired <= timezone.now():
            token, expired_date = RpsIntegrationService.get_token(self)
            if token:
                self.token = token
                self.token_expired = expired_date
                self.save()
            return token
        return self.token

    def make_rps_request(self, endpoint, payload):
        return RpsIntegrationService.make_rps_request(self, endpoint, payload)

    def get_parking_card_debt_url(self, query):
        return self.request_parking_card_debt_url + '?' + query

    def get_parking_card_debt(self, parking_card, debt=None, duration=None, enter_ts=None):
        if debt is None or duration is None or enter_ts is None:
            get_logger(f"get_parking_card_debt: debt={str(debt)} or duration={str(duration)} call make_http from rps")
            debt, enter_ts, duration = self._make_http_for_parking_card_debt(parking_card.card_id)
        get_logger("Returns: debt=%s, duration=%s" %(debt, duration,))

        # if Card
        if debt is None or (debt == 0 and enter_ts == 0 and duration == 0):
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
        source_hostname = None
        if self.request_parking_card_debt_url:
            parsed_uri = urlparse(self.request_parking_card_debt_url)
            source_hostname = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)

        resp["source_hostname"] = source_hostname
        return resp

    def get_parking_card_debt_for_developers(self, parking_card, developer_id):
        debt, enter_ts, duration = self._make_http_for_parking_card_debt(parking_card.card_id, developer_id)
        get_logger("Returns: debt=%s, duration=%s" % (debt, duration,))

        # if Card
        if debt is None or (debt == 0 and enter_ts == 0 and duration == 0):
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

        resp = serializer(card_session, exclude_attr=(
            "account_id", "created_at", "id", "state", "client_uuid", "from_datetime", "leave_at"))
        resp["entered_at"] = enter_ts
        resp["card_session_id"] = card_session.id

        return resp

    def _make_http_for_parking_card_debt(self, parking_card, developer_id=None):
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
            # r = requests.get(
            #     self.get_parking_card_debt_url(query_str),
            #     timeout=(connect_timeout, 5.0))
            #
            session = requests.Session()
            retry = Retry(connect=5, backoff_factor=0.5)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            r = session.get(self.get_parking_card_debt_url(query_str), verify=False)


            try:
                self.last_response_code = r.status_code
                get_logger().info("GET RESPONSE FORM RPS %s" % r.status_code)
                get_logger().info(r.content)

                if developer_id:
                    DevelopersLog.objects.create(
                        parking_card_id=parking_card,
                        developer=Developer.objects.get(developer_id=developer_id),
                        type=DEVELOPER_LOG_RPS_GET_DEBT,
                        status=DEVELOPER_STATUS_SUCCESS,
                        parking=self,
                        message=f'{self.get_parking_card_debt_url(query_str)} \n status_code: {r.status_code} \n response: {r.content}'
                    )

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
    (STATE_CREATED, "created"),
    (STATE_INITED, "inited_pay"),
    (STATE_AUTHORIZED, "authorized_pay"),
    (STATE_CONFIRMED, "confirmed_pay"),
    (STATE_ERROR, "error"),
)

CARD_SESSION_STATE_DICT = {state[0]:state[1] for state in CARD_SESSION_STATES}


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
    leave_at = models.DateTimeField(null=True, blank=True)
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

    def get_parking(self):
        from parkings.models import Parking
        return Parking.objects.get(id=self.parking_id)

    def notify_authorize(self, order, developer_id=None, rps_parking=None):
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
        if order.payload:
            url = order.payload["parking_payment_url"]
            data = {"regularCustomerId": order.payload["card_id"],
                    "amount": int(order.sum)}
            send_request_with_retries(url, 'POST', retries=5, data=data)
            return True
        else:
            try:
                rps_parking = RpsParking.objects.select_related(
                    'parking').get(parking__id=self.parking_id)

                result = self._make_http_ok_status(
                    rps_parking.request_payment_authorize_url, payload, developer_id, rps_parking)

                if result['success']:
                    if result['leave_at'] is not None:
                        order.parking_card_session.leave_at = result['leave_at']
                        order.parking_card_session.save()
                    else:
                        get_logger().info("Get `leave_at` is None from RPS")
                        # return False

                    elastic_log(ES_APP_CARD_PAY_LOGS_INDEX_NAME, "Send authorized request to rps", {
                        'rps_request_data': result['leave_at'] if result['leave_at'] else '',
                        'order': serializer(order, foreign=False, include_attr=("id", "sum", "authorized", "paid")),
                        'payload': payload
                    })

                    return True
                else:
                    return False

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

    def _make_http_ok_status(self, url, payload, developer_id=None, rps_parking=None):
        get_logger().info("_make_http_ok_status")
        connect_timeout = 2

        self.last_request_date = timezone.now()
        self.last_request_body = payload

        headers = {
            'Content-type': 'application/json',
        }

        try:
            get_logger().info("Try to make_http_ok")

            session = requests.Session()
            retry = Retry(connect=5, backoff_factor=0.5)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)


            # r = requests.post(url, data=payload, headers=headers,
            #                   timeout=(connect_timeout, 30.0))  # TODO make
            #
            r = session.post(url, data=payload, headers=headers, verify=False)

            try:
                if developer_id:
                    DevelopersLog.objects.create(
                        parking_card_id=self.parking_card.card_id,
                        developer=Developer.objects.get(developer_id=developer_id),
                        type=DEVELOPER_LOG_RPS_CONFIRM,
                        status=DEVELOPER_STATUS_SUCCESS,
                        parking=rps_parking,
                        message=f'{url} \n status_code: {r.status_code} \n response: {r.content}'
                    )
                self.last_response_code = r.status_code
                get_logger().info("GET RESPONSE FORM RPS %s" % r.status_code)
                get_logger().info(r.content)
                if r.status_code == 200:
                    result = r.json()
                    self.last_response_body = result
                    if result["status"] == "OK":
                        if result["leave_at"] is None or result["leave_at"] == '':
                            return {'success': True, 'leave_at': None}
                        else:
                            return {'success': True, 'leave_at': parse(result["leave_at"]).replace(tzinfo=None)}
                else:
                    self.last_response_body = ""
                self.save()

                return {'success': False, 'leave_at': ''}

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

        return None

    def get_debt(self):
        parking = self.get_parking()
        debt = self.debt
        if parking and parking.commission_client and parking.card_commission_client_value:
            debt = (parking.card_commission_client_value * self.debt / 100) + self.debt
        return debt


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
    duration = models.IntegerField(default=0)
    parking = models.ForeignKey(to='parkings.Parking', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    prolongation = models.BooleanField(default=True)

    data = models.TextField(help_text="Byte array as base64", null=True, blank=True)
    idts = models.TextField()
    id_transition = models.TextField()

    active = models.BooleanField(default=False)

    push_notified_about_expired = models.BooleanField(default=False, null=True, blank=True)
    push_notified_about_soon_expired = models.BooleanField(default=False, null=True, blank=True)

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
            response_dict = {"result": [], "next": None}
            for item in r.json().get("Data", []):
                idts = item["Id"]
                name = item["Name"]
                description = item.get("TsDescription")
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
            subscription=self,
            acquiring=self.parking.acquiring
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


class Developer(models.Model):
    name = models.CharField(max_length=256)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    api_key = models.CharField(max_length=256, default=secrets.token_hex(24), unique=True)
    developer_id = models.CharField(max_length=128, default=str(uuid.uuid1()), unique=True)
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return "%s" % (self.name)


DEVELOPER_LOG_GET_DEBT = 0
DEVELOPER_LOG_CONFIRM = 1
DEVELOPER_LOG_RPS_GET_DEBT = 2
DEVELOPER_LOG_RPS_CONFIRM = 4
DEVELOPER_STATUS_ERROR = 0
DEVELOPER_STATUS_SUCCESS = 1
DEVELOPER_LOG_TYPES = [(DEVELOPER_LOG_GET_DEBT, 'Получение задолженности'),
                       (DEVELOPER_LOG_CONFIRM, 'Оплата задолженности'),
                       (DEVELOPER_LOG_RPS_GET_DEBT, 'РПС ответ на получение задолженности'),
                       (DEVELOPER_LOG_RPS_CONFIRM, 'РПС ответ на оплату задолженности')
                       ]
DEVELOPER_STATUS_TYPES = [(DEVELOPER_STATUS_ERROR, 'Error'), (DEVELOPER_STATUS_SUCCESS, 'Success')]


class DevelopersLog(models.Model):
    parking = models.ForeignKey(to=RpsParking, on_delete=models.CASCADE, blank=True, null=True)
    parking_card_id = models.BigIntegerField()
    developer = models.ForeignKey(to=Developer, on_delete=models.CASCADE)
    type = models.IntegerField(choices=DEVELOPER_LOG_TYPES)
    debt = models.IntegerField(null=True, blank=True)
    status = models.IntegerField(choices=DEVELOPER_STATUS_TYPES, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(max_length=2048, blank=True, null=True)
