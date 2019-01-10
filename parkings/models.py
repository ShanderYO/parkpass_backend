from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import models
from django.db.models import signals
from django.template.loader import render_to_string

from accounts.models import Account
from parkpass.settings import EMAIL_HOST_USER
from vendors.models import Vendor


class ParkingManager(models.Manager):
    def find_between_point(self, lt_point, rb_point):
        return self.filter(
            latitude__range=[rb_point[0], lt_point[0]],
            longitude__range=[lt_point[1], rb_point[1]],
            enabled=True, approved=True
        )


class Parking(models.Model):

    DISCONNECTED = 0
    PENDING = 1
    CONNECTED = 2

    PARKPASS_STATUSES = (
        (DISCONNECTED, "Disconnected"),
        (PENDING, "Pending"),
        (CONNECTED, "Connected")
    )
    name = models.CharField(max_length=63, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    address = models.CharField(max_length=63, null=True, blank=True)
    city = models.CharField(max_length=63, null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    enabled = models.BooleanField(default=True)
    parkpass_status = models.IntegerField(choices=PARKPASS_STATUSES, default=DISCONNECTED)
    free_places = models.IntegerField()
    max_places = models.IntegerField(default=0)
    max_permitted_time = models.IntegerField(default=3600, help_text="Max offline time in minutes")
    max_client_debt = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    vendor = models.ForeignKey(Vendor, null=True, blank=True)
    owner = models.ForeignKey("owners.Owner", null=True, blank=True)
    company = models.ForeignKey(to='owners.Company', null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    software_updated_at = models.DateField(blank=True, null=True)
    approved = models.BooleanField(default=False, verbose_name="Is approved by administrator")
    tariff = models.CharField(max_length=2000, default='{}', verbose_name="Tariff object JSON")
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

    def __unicode__(self):
        return "%s [%s]" % (self.name, self.id)


class Wish(models.Model):
    class Meta:
        verbose_name_plural = 'Wishes'

    id = models.BigAutoField(primary_key=True)
    parking = models.OneToOneField(to=Parking)
    user = models.ForeignKey(to=Account, default=None)

    def __unicode__(self):
        return "[User %s wants %s parking]" % (self.user.phone, self.parking.name)

    @classmethod
    def get_wanted_count(cls, parking):
        return len(cls.objects.all().filter(parking=parking))


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
    STATE_STARTED = 3 # (STARTED_BY_CLIENT_MASK + STARTED_BY_VENDOR_MASK)

    STATE_COMPLETED_BY_CLIENT = 6 # (STATE_STARTED_BY_VENDOR + COMPLETED_BY_CLIENT_MASK)
    STATE_COMPLETED_BY_CLIENT_FULLY = 7 # (STATE_STARTED + COMPLETED_BY_CLIENT_MASK)

    STATE_COMPLETED_BY_VENDOR = 10 # (STATE_STARTED_BY_VENDOR + COMPLETED_BY_VENDOR_MASK)
    STATE_COMPLETED_BY_VENDOR_FULLY = 11 # (STATE_STARTED + COMPLETED_BY_VENDOR_MASK)

    STATE_COMPLETED = 14 # (STARTED_BY_VENDOR_MASK + COMPLETED_BY_VENDOR_MASK + COMPLETED_BY_CLIENT_MASK)
    STATE_COMPLETED_FULLY = 15  # (STATE_STARTED + COMPLETED_BY_VENDOR_MASK + COMPLETED_BY_CLIENT_MASK)

    STATE_VERIFICATION_REQUIRED = 21

    SESSION_STATES = [
        STATE_CANCELED,
        STATE_STARTED_BY_CLIENT, STATE_COMPLETED_BY_VENDOR, STATE_STARTED, # Stage 1
        STATE_COMPLETED_BY_CLIENT, STATE_COMPLETED_BY_CLIENT_FULLY, # Stage 2
        STATE_COMPLETED_BY_VENDOR, STATE_COMPLETED_BY_VENDOR_FULLY, # Stage 2
        STATE_COMPLETED, STATE_COMPLETED_FULLY, # Stage 3
        STATE_CLOSED, # Stage 4
        STATE_VERIFICATION_REQUIRED # Stage 5
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
        (STATE_COMPLETED, 'Completed'),
        (STATE_CLOSED, 'Closed'),
        (STATE_VERIFICATION_REQUIRED, 'Verification required')
    )

    id = models.AutoField(unique=True, primary_key=True)
    session_id = models.CharField(max_length=128)

    client = models.ForeignKey('accounts.Account')
    parking = models.ForeignKey(Parking)

    debt = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    state = models.IntegerField(choices=STATE_CHOICES)

    started_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    is_suspended = models.BooleanField(default=False)
    suspended_at = models.DateTimeField(null=True, blank=True)

    try_refund = models.BooleanField(default=False)
    target_refund_sum = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    current_refund_sum = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    extra_data = models.TextField(null=True, blank=True)

    created_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Parking Session'
        verbose_name_plural = 'Parking Sessions'
        unique_together = ("session_id", "parking")

    def __unicode__(self):
        return "%s [%s]" % (self.parking.id, self.client.id)
    """
    def save(self, *args, **kwargs):
        if self.try_refund:
            self.start_refund_process()
            self.try_refund = False
        return super(ParkingSession, self).save(*args, **kwargs)
    """

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

    def add_client_start_mark(self):
        self.state = self.state + self.STARTED_BY_CLIENT_MASK \
            if not (self.state & self.STARTED_BY_CLIENT_MASK) else self.state

    def add_vendor_start_mark(self):
        self.state = self.state + self.STARTED_BY_VENDOR_MASK \
            if not (self.state & self.STATE_STARTED_BY_VENDOR) else self.state

    def add_client_complete_mark(self):
        self.state = self.state + self.COMPLETED_BY_CLIENT_MASK \
            if not (self.state & self.COMPLETED_BY_CLIENT_MASK) else self.state

    def add_vendor_complete_mark(self):
        self.state = self.state + self.COMPLETED_BY_VENDOR_MASK \
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
        return self.state not in [self.STATE_CANCELED, self.STATE_COMPLETED, self.STATE_CLOSED]

    def reset_client_completed_state(self):
        self.state = self.state - (self.state & self.COMPLETED_BY_CLIENT_MASK)

    def is_cancelable(self):
        return self.state in [
            self.STATE_STARTED_BY_CLIENT,
            self.STATE_STARTED_BY_VENDOR,
            self.STATE_STARTED,
            self.STATE_COMPLETED_BY_CLIENT,
            self.STATE_COMPLETED_BY_CLIENT_FULLY
        ]


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
    session = models.ForeignKey(ParkingSession)
    account = models.ForeignKey('accounts.Account')


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
