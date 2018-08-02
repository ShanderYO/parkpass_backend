from __future__ import unicode_literals

import binascii
import os

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from base.models import BaseAccount, BaseAccountSession


class Vendor(BaseAccount):
    id = models.AutoField(primary_key=True)
    display_id = models.IntegerField(default=-1, unique=True)
    name = models.CharField(max_length=255, unique=True)
    comission = models.FloatField(default=0.02)
    secret = models.CharField(max_length=255, unique=True, default="stub")

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __unicode__(self):
        return "%s" % self.name

    def save(self, *args, **kwargs):

        if self._state.adding:
            if self.display_id == -1:
                # Get the maximum display_id value from the database
                last_id = Vendor.objects.all().aggregate(largest=models.Max('display_id'))['largest']

                # aggregate can return None! Check it first.
                # If it isn't none, just use the last ID specified (which should be the greatest) and add one to it
                # (From https://stackoverflow.com/questions/41228034/django-non-primary-key-autofield)
                if last_id is not None:
                    self.display_id = last_id + 1

        if not self.pk:
            if not kwargs.get("not_generate_secret", False):
                self.generate_secret()
            else:
                del kwargs["not_generate_secret"]
        super(Vendor, self).save(*args, **kwargs)

    def generate_secret(self):
        self.secret = binascii.hexlify(os.urandom(32)).decode()


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


class Issue(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=13)
    comment = models.CharField(max_length=1023, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=True)


class UpgradeIssue(models.Model):
    types = (
        (0, "Software update"),
        (1, "Install readers")
    )
    statuses = (
        (0, "New"),
        (1, "Viewed"),
        (2, "Processing"),
        (3, "Processed"),
        (-1, "Cancelled")
    )
    id = models.AutoField(primary_key=True)
    vendor = models.ForeignKey(to=Vendor)
    description = models.CharField(max_length=1000)
    type = models.IntegerField(choices=types)
    issued_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(choices=statuses, default=0)

    def __unicode__(self):
        return self.description
