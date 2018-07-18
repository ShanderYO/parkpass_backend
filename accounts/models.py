from django.db import models

from base.models import BaseAccount, BaseAccountSession


class Account(BaseAccount):
    pass


class AccountSession(BaseAccountSession):
    account = models.OneToOneField(Account)
