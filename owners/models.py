from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from base.models import BaseAccount, BaseAccountSession


class Owner(BaseAccount):
    name = models.CharField(max_length=255, unique=True)
    pass


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
