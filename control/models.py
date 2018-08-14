from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from base.models import BaseAccount, BaseAccountSession


class Admin(BaseAccount):
    name = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return "%s" % self.name


class AdminSession(BaseAccountSession):
    admin = models.OneToOneField(Admin)

    @classmethod
    def get_account_by_token(cls, token):
        try:
            session = cls.objects.get(token=token)
            if session.is_expired():
                session.delete()
                return None
            return session.admin

        except ObjectDoesNotExist:
            return None
