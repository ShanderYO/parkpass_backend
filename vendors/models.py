from __future__ import unicode_literals

import binascii
import os

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

# Create your models here.
from base.models import BaseAccount, BaseAccountSession


class Vendor(BaseAccount):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
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
