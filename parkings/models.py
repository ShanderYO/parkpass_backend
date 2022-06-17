import calendar
import datetime
import time
import uuid

import pytz
from PIL import Image

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.utils import timezone
from rest_framework import serializers

from accounts.models import Account
from base.utils import get_logger
from base.validators import comma_separated_emails
from parkpass_backend.settings import ALLOWED_HOSTS, ACQUIRING_LIST, MEDIA_ROOT, BASE_DOMAIN, VALETAPP_DOMAIN
from payments.models import Order
from rps_vendor.models import RpsParking, ParkingCard, RpsParkingCardSession
from valet.utils.valet_notification_center import VALET_NOTIFICATION_REQUEST_FOR_DELIVERY, ValetNotificationCenter, \
    VALET_NOTIFICATION_REQUEST_CANCEL, VALET_NOTIFICATION_SET_RESPONSIBLE, VALET_NOTIFICATION_REQUEST_ACCEPT
from vendors.models import Vendor


class ParkingManager(models.Manager):
    def find_between_point(self, lt_point, rb_point):
        return self.filter(
            latitude__range=[rb_point[0], lt_point[0]],
            longitude__range=[lt_point[1], rb_point[1]],
            enabled=True
        )


DEFAULT_PARKING_TIMEZONE = 'Europe/Moscow'
ALL_TIMEZONES = sorted((item, item) for item in pytz.all_timezones)


class Service(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    desc = models.TextField(null=True, blank=True)
    icon = models.FileField(validators=[FileExtensionValidator(['png', 'jpg', 'svg'])])
    created_at = models.DateTimeField(auto_now_add=True, editable=True)

    def __str__(self):
        return self.name


class ParkingValetTelegramChat(models.Model):
    parking = models.ForeignKey('parkings.Parking', on_delete=models.CASCADE)
    chat_id = models.CharField(max_length=63)
    created_at = models.DateTimeField(auto_now_add=True)
    valet_telegram_secret_key = models.CharField(max_length=64, null=True)


class Parking(models.Model):
    DISCONNECTED = 0
    PENDING = 1
    CONNECTED = 2

    PARKPASS_STATUSES = (
        (DISCONNECTED, "Disconnected"),
        (PENDING, "Pending"),
        (CONNECTED, "Connected")
    )

    CURRENCY_LIST = (
        ('RUB', "RUB"),
        ('KZT', "KZT"),
        ('USD', "USD")
    )

    name = models.CharField(max_length=63, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    address = models.CharField(max_length=63, null=True, blank=True)
    city = models.CharField(max_length=63, null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    enabled = models.BooleanField(default=True)
    parkpass_status = models.IntegerField(choices=PARKPASS_STATUSES, default=DISCONNECTED)
    free_places = models.IntegerField(default=0)
    max_places = models.IntegerField(default=0)
    max_permitted_time = models.IntegerField(default=3600, help_text="Max offline time in minutes")
    max_client_debt = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.CASCADE)
    owner = models.ForeignKey("owners.Owner", null=True, blank=True, on_delete=models.CASCADE)
    company = models.ForeignKey(to='owners.Company', null=True, blank=True, on_delete=models.CASCADE)
    valet_email = models.CharField(max_length=200, null=True, blank=True)
    valet_telegram_secret_key = models.CharField(max_length=128, blank=True, null=True, default=uuid.uuid4)

    created_at = models.DateField(auto_now_add=True)
    software_updated_at = models.DateField(blank=True, null=True)
    approved = models.BooleanField(default=False, verbose_name="Is approved by administrator")
    tariff = models.CharField(max_length=2000, default='{}', verbose_name="Tariff object JSON")
    currency = models.CharField(max_length=10, choices=CURRENCY_LIST, default='RUB')
    acquiring = models.CharField(max_length=20, choices=ACQUIRING_LIST, default='tinkoff')

    rps_parking_card_available = models.BooleanField(default=False)
    rps_subscriptions_available = models.BooleanField(default=False)
    tariff_file_name = models.TextField(null=True, blank=True)
    tariff_file_content = models.TextField(null=True, blank=True)

    commission_client = models.BooleanField(default=False, verbose_name="Комиссию оплачивает клиент")
    commission_client_value = models.IntegerField(default=0, verbose_name="Размер комиссии в процентах")
    card_commission_client_value = models.IntegerField(default=0, verbose_name="Размер комиссии в процентах (карты)")

    hide_parking_coordinates = models.BooleanField(default=False, verbose_name="Скрыть парковку с карты")

    picture = models.ImageField(upload_to='object_images', null=True, blank=True)

    services = models.ManyToManyField(Service, blank=True)

    tz_name = models.CharField(
        choices=ALL_TIMEZONES,
        max_length=64,
        default=DEFAULT_PARKING_TIMEZONE)

    objects = models.Manager()
    parking_manager = ParkingManager()

    def save(self, *args, **kwargs):
        if self.free_places is None:
            self.free_places = self.max_places
        super(Parking, self).save(*args, **kwargs)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Parking'
        verbose_name_plural = 'Parkings'

    def __str__(self):
        return "%s [%s]" % (self.name, self.id)

    def get_utc_parking_datetime(self, timezone_timestamp):
        try:
            dt = datetime.datetime.fromtimestamp(float(timezone_timestamp))
            tzh = pytz.timezone(self.tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            get_logger().warn("Invalid timezone in parking %s" % str(self.id))

        tz_datetime = tzh.localize(dt)
        return tzh.normalize(tz_datetime).astimezone(pytz.utc)

    def get_tariff_link(self):
        template_url = "https://" + ALLOWED_HOSTS[0] + "/api/v1/parking/get/%s/tariff/"
        return template_url % self.id if self.tariff_file_content else "-"

    def set_valet_telegram_chat(self, chat_id):
        chat = ParkingValetTelegramChat.objects.get_or_create(
            parking=self,
            chat_id=chat_id,
        )
        chat.valet_telegram_secret_key = self.valet_telegram_secret_key
        chat.save()

        self.valet_telegram_secret_key = uuid.uuid4()
        self.save()

    def send_valet_notification(self, message, photos=[]):
        from parkings.tasks import send_message_by_valet_bots_task

        chats_ids = []
        chats = self.parkingvalettelegramchat_set.all()

        if chats:
            for chat in chats:
                chats_ids.append(chat.chat_id)

            send_message_by_valet_bots_task.delay(message, chats_ids, None, photos)


class ParkingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parking
        fields = [
            'id', 'name', 'address', 'city', 'picture'
        ]


class ParkingSerializerForView(serializers.ModelSerializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

    class Meta:
        model = Parking
        exclude = ("vendor", "company", "max_client_debt",
                   "tariff", "tariff_file_name", "tariff_file_content")



class Wish(models.Model):
    class Meta:
        verbose_name_plural = 'Wishes'

    id = models.BigAutoField(primary_key=True)
    parking = models.ForeignKey(to=Parking, null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(to=Account, default=None, on_delete=models.CASCADE)

    def __str__(self):
        return "[User %s wants %s parking]" % (self.user.phone, self.parking.name)

    @classmethod
    def get_wanted_count(cls, parking):
        return len(cls.objects.all().filter(parking=parking))

    def add_account(self, account):
        count = Wish.get_wanted_count(self.parking)

        try:
            top_parking_wish = TopParkingWish.objects.get(parking=self.parking)
            top_parking_wish.count += 1
            top_parking_wish.users.add(account)
            top_parking_wish.save()

        except ObjectDoesNotExist:
            top_parking_wish = TopParkingWish(parking=self.parking, count=count)
            top_parking_wish.save()
            for wish in Wish.objects.filter(parking=self.parking).select_related('user'):
                top_parking_wish.users.add(wish.user)
            top_parking_wish.save()


class TopParkingWish(models.Model):
    parking = models.OneToOneField(to=Parking, on_delete=models.CASCADE)
    users = models.ManyToManyField(Account)
    count = models.IntegerField(default=0)

    def __str__(self):
        return self.parking.name


class ParkingSession(models.Model):
    # States mask
    STARTED_BY_CLIENT_MASK = 1 << 0  # 1
    STARTED_BY_VENDOR_MASK = 1 << 1  # 2
    COMPLETED_BY_CLIENT_MASK = 1 << 2  # 4
    COMPLETED_BY_VENDOR_MASK = 1 << 3  # 8

    # States
    STATE_CANCELED = -1
    STATE_CLOSED = 0
    STATE_STARTED_BY_CLIENT = 1
    STATE_STARTED_BY_VENDOR = 2
    STATE_STARTED = 3  # (STARTED_BY_CLIENT_MASK + STARTED_BY_VENDOR_MASK)

    STATE_COMPLETED_BY_CLIENT = 6  # (STATE_STARTED_BY_VENDOR + COMPLETED_BY_CLIENT_MASK)
    STATE_COMPLETED_BY_CLIENT_FULLY = 7  # (STATE_STARTED + COMPLETED_BY_CLIENT_MASK)

    STATE_COMPLETED_BY_VENDOR = 10  # (STATE_STARTED_BY_VENDOR + COMPLETED_BY_VENDOR_MASK)
    STATE_COMPLETED_BY_VENDOR_FULLY = 11  # (STATE_STARTED + COMPLETED_BY_VENDOR_MASK)

    STATE_COMPLETED = 14  # (STARTED_BY_VENDOR_MASK + COMPLETED_BY_VENDOR_MASK + COMPLETED_BY_CLIENT_MASK)
    STATE_COMPLETED_FULLY = 15  # (STATE_STARTED + COMPLETED_BY_VENDOR_MASK + COMPLETED_BY_CLIENT_MASK)

    STATE_VERIFICATION_REQUIRED = 21

    SESSION_STATES = [
        STATE_CANCELED,
        STATE_STARTED_BY_CLIENT, STATE_COMPLETED_BY_VENDOR, STATE_STARTED,  # Stage 1
        STATE_COMPLETED_BY_CLIENT, STATE_COMPLETED_BY_CLIENT_FULLY,  # Stage 2
        STATE_COMPLETED_BY_VENDOR, STATE_COMPLETED_BY_VENDOR_FULLY,  # Stage 2
        STATE_COMPLETED, STATE_COMPLETED_FULLY,  # Stage 3
        STATE_CLOSED,  # Stage 4
        STATE_VERIFICATION_REQUIRED  # Stage 5
    ]

    ACTUAL_COMPLETED_STATES = [
        STATE_COMPLETED_BY_VENDOR,
        STATE_COMPLETED_BY_VENDOR_FULLY,
        STATE_COMPLETED,
        STATE_COMPLETED_FULLY
    ]

    STATE_CHOICES = (
        (STATE_CANCELED, 'Canceled'),
        (STATE_STARTED_BY_CLIENT, 'Started_by_client'),
        (STATE_STARTED_BY_VENDOR, 'Started_by_vendor'),
        (STATE_STARTED, 'Started'),
        (STATE_COMPLETED_BY_CLIENT, 'Completed_by_client'),
        (STATE_COMPLETED_BY_CLIENT_FULLY, 'Completed_by_client_fully'),
        (STATE_COMPLETED_BY_VENDOR, 'Completed_by_vendor'),
        (STATE_COMPLETED_BY_VENDOR_FULLY, 'Completed_by_vendor_fully'),
        (STATE_COMPLETED, 'Completed without client start'),
        (STATE_COMPLETED_FULLY, 'Completed'),
        (STATE_CLOSED, 'Closed'),
        (STATE_VERIFICATION_REQUIRED, 'Verification required')
    )

    CLIENT_STATE_CANCELED = -1
    CLIENT_STATE_CLOSED = 0
    CLIENT_STATE_ACTIVE = 1
    CLIENT_STATE_SUSPENDED = 2
    CLIENT_STATE_COMPLETED = 3

    CLIENT_STATES = (
        (CLIENT_STATE_CANCELED, 'Canceled'),
        (CLIENT_STATE_CLOSED, 'Closed'),
        (CLIENT_STATE_ACTIVE, 'Active'),
        (CLIENT_STATE_SUSPENDED, 'Suspended'),
        (CLIENT_STATE_COMPLETED, 'Completed'),
    )

    id = models.AutoField(unique=True, primary_key=True)
    session_id = models.CharField(max_length=128)

    client = models.ForeignKey('accounts.Account', on_delete=models.CASCADE)
    parking = models.ForeignKey(Parking, on_delete=models.CASCADE)

    debt = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    state = models.IntegerField(choices=STATE_CHOICES)
    client_state = models.IntegerField(choices=CLIENT_STATES, editable=False, default=CLIENT_STATE_ACTIVE)

    started_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0)

    is_suspended = models.BooleanField(default=False)
    suspended_at = models.DateTimeField(null=True, blank=True)

    try_refund = models.BooleanField(default=False)
    target_refund_sum = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    current_refund_sum = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    canceled_sum = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    extra_data = models.TextField(null=True, blank=True)
    vendor_id = models.IntegerField(default=0)

    is_send_warning_non_closed_message = models.BooleanField(default=False)
    created_at = models.DateField(auto_now_add=True)

    manual_close = models.BooleanField(default=False)

    comment = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Parking Session'
        verbose_name_plural = 'Parking Sessions'
        unique_together = ("session_id", "parking")

    def __str__(self):
        return "%s [%s] session %s" % (self.parking.id, self.client.id, self.session_id)

    def save(self, *args, **kwargs):
        # if self.try_refund:
        #    self.start_refund_process()
        #    self.try_refund = False
        self.duration = self.get_calculated_duration()
        self.resolve_client_status()
        super(ParkingSession, self).save(*args, **kwargs)

    @classmethod
    def get_session_by_id(cls, id):
        try:
            return ParkingSession.objects.get(id=id)
        except ObjectDoesNotExist:
            return None

    @classmethod
    def get_active_session(cls, account):
        try:
            return ParkingSession.objects.get(
                client=account, state__gt=0,
                state__lt=ParkingSession.STATE_VERIFICATION_REQUIRED, is_suspended=False)

        except ObjectDoesNotExist:
            return None

    def get_session_orders(self):
        return Order.objects.filter(session=self.pk, )

    def get_session_orders_holding_sum(self):
        sum = 0
        for order in self.get_session_orders():
            if order.authorized:
                sum = sum + order.sum
        return sum

    def get_cool_duration(self):
        if self.duration <= 0:
            return 0

        secs = self.duration % 60
        hours = self.duration // 3600
        mins = (self.duration - hours * 3600 - secs) // 60
        return "%02d:%02d:%02d" % (hours, mins, secs)

    def resolve_client_status(self):
        if self.state < 0:
            self.client_state = self.CLIENT_STATE_CANCELED
        if self.state >= 1 and self.state <= 3:
            self.client_state = self.CLIENT_STATE_ACTIVE
        if self.state >= 6 and self.state <= 15:
            self.client_state = self.CLIENT_STATE_COMPLETED
        if self.is_suspended:
            self.client_state = self.CLIENT_STATE_SUSPENDED
        if self.state == 0:
            self.client_state = self.CLIENT_STATE_CLOSED

    def get_calculated_duration(self):
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        if self.is_suspended and self.suspended_at:
            return (self.suspended_at - self.started_at).total_seconds()
        if self.updated_at:
            return (self.updated_at - self.started_at).total_seconds()
        return 0

    def add_client_start_mark(self):
        self.state += self.STARTED_BY_CLIENT_MASK \
            if not (self.state & self.STARTED_BY_CLIENT_MASK) else self.state

    def add_vendor_start_mark(self):
        self.state += self.STARTED_BY_VENDOR_MASK \
            if not (self.state & self.STATE_STARTED_BY_VENDOR) else self.state

    def add_client_complete_mark(self):
        self.state += self.COMPLETED_BY_CLIENT_MASK \
            if not (self.state & self.COMPLETED_BY_CLIENT_MASK) else self.state

    def add_vendor_complete_mark(self):
        self.state += self.COMPLETED_BY_VENDOR_MASK \
            if not (self.state & self.COMPLETED_BY_VENDOR_MASK) else self.state

    def is_started_by_vendor(self):
        return bool(self.state & self.STARTED_BY_VENDOR_MASK)

    def is_completed_by_vendor(self):
        return bool(self.state & self.COMPLETED_BY_VENDOR_MASK)

    def is_completed_by_client(self):
        return bool(self.state & self.COMPLETED_BY_CLIENT_MASK)

    def is_closed(self):
        return self.state == self.STATE_CLOSED

    def is_active(self):
        return self.state not in [
            self.STATE_CANCELED,
            self.STATE_COMPLETED,
            self.STATE_CLOSED,
        ]

    def is_available_for_vendor_update(self):
        return self.state not in [self.STATE_CANCELED, self.STATE_COMPLETED_BY_VENDOR,
                                  self.STATE_COMPLETED_BY_VENDOR_FULLY, self.STATE_COMPLETED, self.STATE_CLOSED]

    def reset_client_completed_state(self):
        self.state -= self.state & self.COMPLETED_BY_CLIENT_MASK

    def is_cancelable(self):
        return self.state in [
            self.STATE_STARTED_BY_CLIENT,
            self.STATE_STARTED_BY_VENDOR,
            self.STATE_STARTED,
            self.STATE_COMPLETED_BY_CLIENT,
            self.STATE_COMPLETED_BY_CLIENT_FULLY
        ]

    def get_debt(self):
        debt = self.debt
        if self.parking and self.parking.commission_client and self.parking.commission_client_value:
            debt = (self.parking.commission_client_value * self.debt / 100) + self.debt
        return debt


class ComplainSession(models.Model):
    COMPLAIN_TYPE_CHOICES = (
        (1, 'Complain_1'),
        (2, 'Complain_2'),
        (3, 'Complain_3'),
        (4, 'Complain_4'),
        (5, 'Complain_5'),
    )
    type = models.PositiveSmallIntegerField(choices=COMPLAIN_TYPE_CHOICES)
    message = models.TextField(max_length=1023)
    session = models.ForeignKey(ParkingSession, on_delete=models.CASCADE)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE)


def create_test_parking(sender, instance, created, **kwargs):
    if not created:
        return
    parking = Parking(
        description='Test parking',
        latitude=1,
        longitude=2,
        free_places=5,
        max_places=5,
        vendor=instance,
        enabled=False,
        approved=True
    )
    parking.save()
    instance.test_parking = parking
    instance.save()


signals.post_save.connect(receiver=create_test_parking, sender=Vendor)  # Test parking creation, when vendor


# is being created

class ProblemParkingSessionNotifierSettings(models.Model):
    available = models.BooleanField(default=True)
    report_emails = models.TextField(validators=(comma_separated_emails,), null=True, blank=True)
    last_email_send_date = models.DateTimeField()
    interval_in_mins = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'problem_parking_session_notifier_settings'


PHOTOS_AT_THE_RECEPTION = 1
PHOTOS_FROM_PARKING = 2

VALET_SESSION_RECEIVED_THE_CAR = 1
VALET_SESSION_PARKING_THE_CAR = 2
VALET_SESSION_THE_CAR_IS_PARKED = 3
VALET_SESSION_REQUESTING_A_CAR_DELIVERY = 4
VALET_SESSION_IN_THE_PROCESS = 5
VALET_SESSION_THE_PERSON_IN_CHARGE = 6
VALET_SESSION_THE_CAR_IS_WAITING = 7
VALET_SESSION_THE_CAR_IS_ISSUED = 8
VALET_SESSION_COMPLETED = 9
VALET_SESSION_COMPLETED_AND_PAID = 10

VALET_SESSION_STATE_CHOICES = (
    (VALET_SESSION_RECEIVED_THE_CAR, 'Принял автомобиль'),
    (VALET_SESSION_PARKING_THE_CAR, 'Парковка автомобиля'),
    (VALET_SESSION_THE_CAR_IS_PARKED, 'Автомобиль припаркован'),
    (VALET_SESSION_REQUESTING_A_CAR_DELIVERY, 'Запрошена подача автомобиля'),
    (VALET_SESSION_IN_THE_PROCESS, 'В процессе подачи'),
    (VALET_SESSION_THE_PERSON_IN_CHARGE, 'Назначен ответственный'),
    (VALET_SESSION_THE_CAR_IS_WAITING, 'Машина ожидает'),
    (VALET_SESSION_THE_CAR_IS_ISSUED, 'Машина выдана'),
    (VALET_SESSION_COMPLETED, 'Валет сессия завершена'),
    (VALET_SESSION_COMPLETED_AND_PAID, 'Сессия завершена и оплачена'),
)


class ParkingValetSession(models.Model):
    # id = models.CharField(primary_key=True, unique=True, max_length=50)
    id = models.AutoField(primary_key=True)
    client_id = models.CharField(max_length=50, null=True)
    parking = models.ForeignKey(Parking, on_delete=models.CASCADE)
    company = models.ForeignKey('owners.Company', on_delete=models.CASCADE, null=True)
    state = models.PositiveSmallIntegerField(choices=VALET_SESSION_STATE_CHOICES,
                                             default=VALET_SESSION_RECEIVED_THE_CAR)
    car_number = models.CharField(max_length=20)
    car_color = models.CharField(max_length=100, null=True)
    car_model = models.CharField(max_length=100)
    debt = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    duration = models.IntegerField(default=0)
    valet_card_id = models.CharField(max_length=100)
    pcid = models.CharField(max_length=100, blank=True, null=True)
    parking_card = models.CharField(max_length=30, null=True, blank=True)
    parking_place = models.CharField(max_length=256, null=True, blank=True)
    parking_floor = models.SmallIntegerField(default=1)
    parking_space_number = models.CharField(max_length=20, null=True)
    created_by_user = models.ForeignKey('owners.CompanyUser', on_delete=models.SET_NULL, null=True,
                                        related_name='created_by_user_relate_table')
    responsible_for_reception = models.ForeignKey('owners.CompanyUser', on_delete=models.SET_NULL, null=True,
                                                  related_name='responsible_relate_table')
    responsible_for_delivery = models.ForeignKey('owners.CompanyUser', on_delete=models.SET_NULL, null=True,
                                                 related_name='responsible_for_delivery_relate_table', blank=True)
    parking_card_get_at = models.CharField(null=True, blank=True, max_length=100)
    car_delivery_time = models.DateTimeField(null=True, blank=True)
    car_delivered_at = models.DateTimeField(null=True, blank=True)
    car_delivered_by = models.ForeignKey('owners.CompanyUser', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='car_delivered_by_relate_table')
    paid_at = models.DateTimeField(null=True, blank=True)
    parking_card_session = models.ForeignKey('rps_vendor.RpsParkingCardSession', on_delete=models.SET_NULL, null=True)
    manual_close = models.BooleanField(default=False)
    comment = models.TextField(null=True, blank=True, max_length=1024)
    started_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def request(self):
        return self.parkingvaletsessionrequest_set.last()

    def get_debt_from_remote(self):
        parking_card_model = ParkingCard.objects.filter(card_id=self.parking_card)
        if self.parking_card and parking_card_model.exists():
            rps_parking = RpsParking.objects.get(parking=self.parking)
            response = rps_parking.get_parking_card_debt(parking_card_model.first())
            if response:
                self.duration = response['duration']
                self.debt = response['debt']
                self.parking_card_get_at = datetime.datetime.fromtimestamp(response['entered_at'] / 1000.0,
                                                                           pytz.timezone('Europe/Moscow')).strftime(
                    '%d.%m.%Y в %H:%M')
                self.set_parking_card_session(response['id'])
                self.save()

    def set_parking_card_session(self, card_session_id):
        if card_session_id:
            try:
                card_session = RpsParkingCardSession.objects.get(id=card_session_id)
                self.parking_card_session = card_session
            except Exception as e:
                get_logger().error('Не удалось сохранить парковочную сессию')
                get_logger().error(str(e))

    # клиент заказал авто
    def book(self, delivery_date):
        self.state = VALET_SESSION_REQUESTING_A_CAR_DELIVERY
        self.car_delivery_time = delivery_date

        # создаем запрос авто
        ParkingValetSessionRequest.objects.create(
            valet_session=self,
            car_delivery_time=delivery_date,
            company=self.company
        )
        self.save()

        # Уведомления в телеграмм
        # _______________________________________________________________________________
        current_session = ParkingValetSession.objects.get(
            id=self.id)  # хак для того чтобы не обрабатывать значение даты в ручную, sorry

        now = datetime.datetime.now(timezone.utc)
        now_plus_30 = now + datetime.timedelta(minutes=30)

        if current_session.car_delivery_time and (current_session.car_delivery_time <= now_plus_30): # проверка на время < 30min
            ValetNotificationCenter(
                type=VALET_NOTIFICATION_REQUEST_FOR_DELIVERY,
                session=current_session
            ).run()

            request = ParkingValetSessionRequest.objects.get(id=current_session.request.id)
            request.notificated_about_car_book = True
            request.save()
        # _______________________________________________________________________________


    def cancel_request_if_status_changed(self, state):
        from owners.models import CompanyUser
        # Если меняю статус сессии
        # С Запрошена подача или В процессе подачи или Назначен ответственный
        # На Автомобиль припаркован
        # То Отменять связанный запрос на подачу и сбарсывать Дату/Время подачи + ответственного за подачу
        if int(state) == VALET_SESSION_THE_CAR_IS_PARKED and self.state in [VALET_SESSION_REQUESTING_A_CAR_DELIVERY,
                                                                            VALET_SESSION_IN_THE_PROCESS,
                                                                            VALET_SESSION_THE_PERSON_IN_CHARGE]:
            old_responsible_user = None
            if self.responsible_for_delivery_id:
                old_responsible_user = CompanyUser.objects.get(id=self.responsible_for_delivery_id)

            self.responsible_for_delivery = None
            self.car_delivery_time = None
            self.save()

            if self.request:
                request = ParkingValetSessionRequest.objects.get(id=self.request.id)
                request.status = VALET_REQUEST_CANCELED
                request.canceled_at = datetime.datetime.now(timezone.utc)
                request.notificated_about_car_book = False
                request.accepted_by = None
                request.accepted_at = None
                request.save()

            # Уведомления в телеграмм
            # _______________________________________________________________________________
            if old_responsible_user and old_responsible_user.telegram_id:
                ValetNotificationCenter(
                    type=VALET_NOTIFICATION_REQUEST_CANCEL,
                    session=self,
                    chats=[old_responsible_user.telegram_id]
                ).run()
            # _______________________________________________________________________________

            return True

        return False

    def create_request_if_status_changed(self, state, add_time_by_backend):
        # Если статус Сессии меняется
        # С Припаркован
        # На Запрошена Подача автомобиля или Назначен ответственный
        # То Создавать запрос на подачу, если запроса на подачу по данной сессии еще нет.
        if self.state == VALET_SESSION_THE_CAR_IS_PARKED and int(state) in [VALET_SESSION_REQUESTING_A_CAR_DELIVERY,
                                                                            VALET_SESSION_THE_PERSON_IN_CHARGE]:

            if not self.request or self.request.status == VALET_REQUEST_CANCELED:
                now = datetime.datetime.now(timezone.utc)
                now_plus_10 = now + datetime.timedelta(minutes=10)

                date = self.car_delivery_time

                if add_time_by_backend:
                    date = now_plus_10

                self.book(date)

                return True

        return False

    def __str__(self):
        return f'{self.client_id} {self.car_model} {self.parking.name}'


class ParkingValetSessionImages(models.Model):
    id = models.AutoField(primary_key=True)
    valet_session = models.ForeignKey(ParkingValetSession, on_delete=models.CASCADE)
    type = models.PositiveSmallIntegerField(
        choices=((PHOTOS_AT_THE_RECEPTION, 'Фото при приеме'), (PHOTOS_FROM_PARKING, 'Фото с парковки')),
        default=PHOTOS_AT_THE_RECEPTION)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    img = models.CharField(max_length=128)

    def __str__(self):
        return f'{self.id} {self.valet_session}'


@receiver(models.signals.post_save, sender=ParkingValetSessionImages)
def execute_after_save_image(sender, instance, created, *args, **kwargs):
    pass
    if created:
        img = Image.open(MEDIA_ROOT + instance.img)  # Open image using self

        if img.height > 1920 or img.width > 1920:
            new_img = (1920, 1920)
            img.thumbnail(new_img)
            img.save(MEDIA_ROOT + instance.img)  # saving image at the same path


class ParkingValetSessionImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingValetSessionImages
        fields = [
            'id', 'valet_session', 'type', 'created_at', 'img'
        ]


VALET_REQUEST_ACTIVE = 1
VALET_REQUEST_ACCEPTED = 2
VALET_REQUEST_CANCELED = 3

VALET_REQUESTS_STATE_CHOICES = (
    (VALET_REQUEST_ACTIVE, 'Ожидает принятия'),
    (VALET_REQUEST_ACCEPTED, 'Запрос принят'),
    (VALET_REQUEST_CANCELED, 'Запрос отменен'),
)


class ParkingValetSessionRequest(models.Model):
    company = models.ForeignKey('owners.Company', on_delete=models.CASCADE, null=True)
    id = models.AutoField(primary_key=True)
    valet_session = models.ForeignKey(ParkingValetSession, on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=VALET_REQUESTS_STATE_CHOICES, default=VALET_REQUEST_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    car_delivery_time = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey('owners.CompanyUser', on_delete=models.SET_NULL, null=True)
    finish_time = models.DateTimeField(null=True, blank=True)
    notificated_about_car_book = models.BooleanField(default=False)

    def set_responsible(self, valet_user_id):
        from owners.models import CompanyUser

        self.accepted_by_id = valet_user_id
        self.car_delivery_time = self.valet_session.car_delivery_time

        if valet_user_id:
            self.valet_session.state = VALET_SESSION_THE_PERSON_IN_CHARGE
            self.valet_session.save()

            # Уведомления в телеграмм
            # _______________________________________________________________________________
            ValetNotificationCenter(
                type=VALET_NOTIFICATION_SET_RESPONSIBLE,
                session=self.valet_session,
                valet_user_id=valet_user_id
            ).run()
        # _______________________________________________________________________________

        else:
            self.accepted_at = None
            self.status = VALET_REQUEST_ACTIVE
            # self.valet_session.state = VALET_SESSION_THE_CAR_IS_PARKED
        self.save()

    def accept(self, valet_user_id):
        self.accepted_by_id = valet_user_id
        self.car_delivery_time = self.valet_session.car_delivery_time

        if valet_user_id:
            self.accepted_at = datetime.datetime.now(timezone.utc)
            self.status = VALET_REQUEST_ACCEPTED
            self.valet_session.state = VALET_SESSION_IN_THE_PROCESS
            self.valet_session.save()

            # Уведомления в телеграмм
            # _______________________________________________________________________________
            ValetNotificationCenter(
                type=VALET_NOTIFICATION_REQUEST_ACCEPT,
                session=self.valet_session,
                valet_user_id=valet_user_id
            ).run()
            # _______________________________________________________________________________

        else:
            self.accepted_at = None
            self.status = VALET_REQUEST_ACTIVE
            # self.valet_session.state = VALET_SESSION_THE_CAR_IS_PARKED

        self.save()

    def __str__(self):
        return f'{self.id} {self.valet_session}'


class ParkingValetSessionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingValetSessionRequest
        fields = [
            'id', 'status', 'car_delivery_time', 'accepted_by', 'accepted_at', 'created_at'
        ]


class ParkingValetSessionSerializer(serializers.ModelSerializer):
    from owners.models import CompanyUserSerializer

    responsible_for_reception = CompanyUserSerializer(read_only=True)
    responsible_for_delivery = CompanyUserSerializer(read_only=True)

    parking = ParkingSerializer(read_only=True)
    request = ParkingValetSessionRequestSerializer(read_only=True)
    photos = ParkingValetSessionImagesSerializer(source='parkingvaletsessionimages_set', many=True)

    class Meta:
        model = ParkingValetSession
        fields = [
            'id', 'state', 'client_id', 'parking', 'car_number', 'car_color',
            'car_model', 'debt', 'valet_card_id','pcid' ,'parking_card',
            'parking_place', 'created_by_user', 'responsible_for_reception', 'responsible_for_delivery', 'car_color',
            'parking_card_get_at', 'car_delivery_time', 'car_delivered_at', 'car_delivered_by', 'paid_at',
            'parking_card_session', 'comment', 'started_at', 'duration', 'request', 'photos'
        ]


class ParkingValetSessionWithoutRelativesSerializer(serializers.ModelSerializer):
    photos = ParkingValetSessionImagesSerializer(source='parkingvaletsessionimages_set', many=True)

    class Meta:
        model = ParkingValetSession
        fields = [
            'id', 'state', 'client_id', 'car_number', 'car_color',
            'car_model', 'debt', 'valet_card_id','pcid', 'parking_card',
            'parking_place', 'created_by_user', 'car_color',
            'parking_card_get_at', 'car_delivery_time', 'car_delivered_at', 'car_delivered_by', 'paid_at',
            'parking_card_session', 'comment', 'started_at', 'duration', 'photos', 'responsible_for_reception',
            'responsible_for_delivery'
        ]


class ParkingValetRequestIncludeSessionSerializer(serializers.ModelSerializer):
    valet_session = ParkingValetSessionSerializer(read_only=True)

    class Meta:
        model = ParkingValetSessionRequest
        fields = [
            'id', 'status', 'car_delivery_time', 'accepted_by', 'accepted_at', 'valet_session', 'finish_time'
        ]

# class ParkingValetSessionForLkListSerializer(serializers.ModelSerializer):
#     from owners.models import CompanyUserSerializer
#
#     photos = ParkingValetSessionImagesSerializer(source='parkingvaletsessionimages_set', many=True)
#     responsible_for_reception = CompanyUserSerializer(read_only=True)
#     # parking_card_number = serializers.SlugRelatedField(
#     #     read_only=True,
#     #     source='parking_card',
#     #     slug_field='slug'
#     # )
#     class Meta:
#         model = ParkingValetSession
#         fields = [
#             'id', 'state', 'client_id', 'parking', 'car_number', 'car_color',
#             'car_model', 'debt', 'valet_card_id', 'parking_card',
#             'parking_floor', 'parking_space_number', 'created_by_user', 'responsible_for_reception', 'responsible_for_delivery', 'car_color',
#             'parking_card_get_at', 'car_delivery_time', 'car_delivered_at', 'car_delivered_by', 'paid_at',
#             'parking_card_session', 'comment', 'started_at', 'photos', 'duration'
#         ]
