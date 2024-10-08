from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from base.models import BaseAccount, BaseAccountSession


class Admin(BaseAccount):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return "%s" % self.name

    @property
    def session_class(self):
        return AdminSession

    @property
    def type(self):
        return 'admin'


class AdminSession(BaseAccountSession):
    admin = models.OneToOneField(Admin, on_delete=models.CASCADE)

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
