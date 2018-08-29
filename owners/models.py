from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from base.models import BaseAccount, BaseAccountSession


class Owner(BaseAccount):
    name = models.CharField(max_length=255, unique=True)

    @property
    def session_class(self):
        return OwnerSession

    @property
    def type(self):
        return 'owner'


class OwnerSession(BaseAccountSession):
    owner = models.OneToOneField(Owner)

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
    owner = models.ForeignKey(to=Owner)
    description = models.CharField(max_length=1000)
    type = models.IntegerField(choices=types)
    issued_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(choices=statuses, default=0)

    def __unicode__(self):
        return self.description


class Company(models.Model):
    owner = models.ForeignKey(to=Owner)
    name = models.CharField(max_length=256, unique=True)
    inn = models.CharField(max_length=15)
    kpp = models.CharField(max_length=15)
    legal_address = models.CharField(max_length=512)
    actual_address = models.CharField(max_length=512)
    email = models.EmailField()
    phone = models.CharField(max_length=15)

    checking_account = models.CharField(max_length=64)
    checking_kpp = models.CharField(max_length=15)

    def __unicode__(self):
        return self.name
