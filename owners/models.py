import time

import datetime

from django.dispatch import receiver
from jose import jwt

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from base.models import BaseAccount, BaseAccountSession, BaseAccountIssue
from base.validators import validate_phone_number, comma_separated_emails
from owners.validators import validate_inn, validate_kpp
from parkings.models import Parking
from parkpass_backend.settings import ZENDESK_WIDGET_SECRET
from payments.models import InvoiceWithdraw


class Owner(BaseAccount):
    name = models.CharField(max_length=255, unique=True)

    @property
    def session_class(self):
        return OwnerSession

    @property
    def type(self):
        return 'owner'

    def get_or_create_jwt_for_zendesk_widget(self):
        return self.get_or_create_jwt_for_zendesk(ZENDESK_WIDGET_SECRET)

    def get_or_create_jwt_for_zendesk(self, secret):
        timestamp = int(time.mktime(datetime.datetime.now().timetuple()))
        payload = {
            'name': self.name,
            'email': self.email,
            'jti':self.id,
            'iat':timestamp
        }
        return jwt.encode(payload, secret, algorithm='HS256')

    def create_password_and_send_mail(self):
        raw_password = self.generate_random_password()
        self.set_password(raw_password)
        self.save()
        self.send_recovery_password_owner_mail(raw_password)

    def save(self, *args, **kwargs):
        if not self.id and Owner.objects.filter(email=self.email).exists():
            try:
                1 / 0
            except ZeroDivisionError as e:
                raise Exception('Owner with this email exists') from e
        else:
            super(Owner, self).save(*args, **kwargs)

# @receiver(models.signals.post_save, sender=Owner)
# def execute_after_save(sender, instance, created, *args, **kwargs):
#     if created:
#         if instance.email:
#             raw_password = instance.generate_random_password()
#             instance.set_password(raw_password)
#             instance.save()
#             instance.send_owner_password_mail(raw_password)

class OwnerSession(BaseAccountSession):
    owner = models.OneToOneField(Owner, on_delete=models.CASCADE)

    @classmethod
    def get_account_by_token(cls, token):
        try:
            session = cls.objects.get(token=token)
            if session.is_expired():
                session.delete()
                return None
            return session.owner

        except ObjectDoesNotExist:
            return None


class OwnerIssue(BaseAccountIssue):
    def save(self, *args, **kwargs):
        if not self.id:
            self.type = BaseAccountIssue.OWNER_ISSUE_TYPE
        super(OwnerIssue, self).save(*args, **kwargs)

    def accept(self):
        owner = Owner(
            phone=self.phone,
            email=self.email,
            name=self.name,
        )
        owner.full_clean()
        owner.save()
        owner.create_password_and_send()
        self.delete()
        return owner


class Company(models.Model):
    owner = models.ForeignKey(to=Owner, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    inn = models.CharField(max_length=15, validators=(validate_inn,), null=True, blank=True)
    kpp = models.CharField(max_length=15, validators=(validate_kpp,), null=True, blank=True)

    bic = models.CharField(max_length=20, null=True, blank=True)
    bank = models.CharField(max_length=256, null=True, blank=True)
    account = models.CharField(max_length=64, null=True, blank=True)

    legal_address = models.CharField(max_length=512)
    actual_address = models.CharField(max_length=512)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True, validators=(validate_phone_number,))
    use_profile_contacts = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def get_parking_queryset(self):
        return Parking.objects.filter(company=self)


class OwnerApplication(models.Model):
    TYPE_CONNECT_PARKING = 1
    TYPE_SOFTWARE_UPDATE = 2
    TYPE_INSTALL_READER = 3

    types = (
        (TYPE_CONNECT_PARKING, "Connect parking"),
        (TYPE_SOFTWARE_UPDATE, "Software update"),
        (TYPE_INSTALL_READER, "Install readers")
    )
    statuses = (
        (1, "New"),
        (2, "Processing"),
        (3, "Processed"),
        (4, "Cancelled")
    )
    type = models.PositiveSmallIntegerField(choices=types)

    owner = models.ForeignKey(to=Owner, on_delete=models.CASCADE, null=True, blank=True)
    parking = models.ForeignKey(to='parkings.Parking', on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey(to='vendors.Vendor', on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(to=Company, on_delete=models.CASCADE, null=True, blank=True)

    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=13, null=True, blank=True)

    description = models.CharField(max_length=1000)
    status = models.PositiveSmallIntegerField(choices=statuses, default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Application #%s " % self.pk


class CompanySettingReports(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    parking = models.ForeignKey(Parking, on_delete=models.CASCADE)
    available = models.BooleanField(default=True)
    report_emails = models.TextField(validators=(comma_separated_emails,), null=True, blank=True)
    period_in_days = models.IntegerField(default=30)
    last_send_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_settings'

    def __str__(self):
        return "Report settings for %s %s" % (self.company, self.parking)


class CompanyReport(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    filename = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    invoice_withdraw = models.ForeignKey(
        to=InvoiceWithdraw, on_delete=models.CASCADE,
        null=True, blank=True)

    class Meta:
        db_table = 'owner_report'

    def __str__(self):
        return "Report for %s [%s]" % (self.company, self.created_at)