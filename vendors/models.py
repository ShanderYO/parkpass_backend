from __future__ import unicode_literals

import binascii
import os

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from base.models import BaseAccount, BaseAccountSession


class Vendor(BaseAccount):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    comission = models.FloatField(default=0.02)
    secret = models.CharField(max_length=255, unique=True, default="stub")

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
        ("Software update", 0),
        ("Install readers", 1)
    )
    statuses = (
        ("New", 0),
        ("Viewed", 1),
        ("Processing", 2),
        ("Processed", 3),
        ("Cancelled", -1)
    )
    id = models.AutoField(primary_key=True)
    vendor = models.ForeignKey(to=Vendor)
    description = models.CharField(max_length=1000)
    type = models.IntegerField(choices=types)
    issued_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(choices=statuses, default=0)
