from django.db import models

from base.models import BaseAccount, BaseAccountSession


class Account(BaseAccount):
    @property
    def session_class(self):
        return AccountSession

    @property
    def type(self):
        return 'account'


class AccountSession(BaseAccountSession):
    account = models.OneToOneField(Account)
