import binascii
import os

from django.core.exceptions import ObjectDoesNotExist
from django.db import models


class Vendor(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    secret = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __unicode__(self):
        return "%s" % (self.name)

    def save(self, *args, **kwargs):
        if not self.pk:
            if not kwargs.get("not_generate_secret", False):
                self.generate_secret()
            else:
                del kwargs["not_generate_secret"]
        super(Vendor, self).save(*args, **kwargs)

    def generate_secret(self):
        self.secret = binascii.hexlify(os.urandom(32)).decode()


class ParkingManager(models.Manager):
    def find_between_point(self, lt_point, rb_point):
        return self.filter(
            latitude__range=[rb_point[0], lt_point[0]],
            longitude__range=[lt_point[1], rb_point[1]],
            enabled=True
        )


class Parking(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=63, null=True, blank=True)
    description = models.TextField()
    address = models.CharField(max_length=63, null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    enabled = models.BooleanField(default=True)
    free_places = models.IntegerField()
    max_client_debt = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    vendor = models.ForeignKey(Vendor, null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)

    objects = models.Manager()
    parking_manager = ParkingManager()

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Parking'
        verbose_name_plural = 'Parkings'

    def __unicode__(self):
        return "%s [%s]" % (self.name, self.id)


class ParkingSession(models.Model):

    # States mask
    STARTED_BY_CLIENT_MASK = 1 << 0 # 1
    STARTED_BY_VENDOR_MASK = 1 << 1 # 2
    COMPLETED_BY_CLIENT_MASK = 1 << 2 # 4
    COMPLETED_BY_VENDOR_MASK = 1 << 3 # 8

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

    SESSION_STATES = [
        STATE_CANCELED,
        STATE_STARTED_BY_CLIENT, STATE_COMPLETED_BY_VENDOR, STATE_STARTED, # Stage 1
        STATE_COMPLETED_BY_CLIENT, STATE_COMPLETED_BY_CLIENT_FULLY, # Stage 2
        STATE_COMPLETED_BY_VENDOR, STATE_COMPLETED_BY_VENDOR_FULLY, # Stage 2
        STATE_COMPLETED, STATE_COMPLETED_FULLY, # Stage 3
        STATE_CLOSED # Stage 4
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

    created_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Parking Session'
        verbose_name_plural = 'Parking Sessions'
        unique_together = ("session_id", "parking")

    def __unicode__(self):
        return "%s [%s]" % (self.parking.id, self.client.id)

    @classmethod
    def get_session_by_id(cls, id):
        try:
            return ParkingSession.objects.get(id=id)
        except ObjectDoesNotExist:
            return None

    @classmethod
    def get_active_session(cls, account):
        try:
            return ParkingSession.objects.get(client=account, state__gt=0, is_suspended=False)
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

    def is_cancelable(self):
        return self.state in [
            self.STATE_STARTED_BY_CLIENT,
            self.STATE_STARTED_BY_VENDOR,
            self.STATE_STARTED
        ]