from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from base.models import BaseAccount, BaseAccountSession


class Account(BaseAccount):
    external_vendor_id = models.IntegerField(null=True)
    external_id = models.CharField(max_length=1024, null=True, blank=True)

    @property
    def session_class(self):
        return AccountSession

    def save(self, *args, **kwargs):
        if self.password == 'stub' and self.email:
            self.create_password_and_send()
        super(Account, self).save(*args, **kwargs)

    @property
    def type(self):
        return 'account'


class AccountSession(BaseAccountSession):
    ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 180
    id = models.AutoField(primary_key=True)
    token = models.CharField(max_length=63)
    expired_at = models.DateTimeField()
    created_at = models.DateField(auto_now_add=True)
    account = models.OneToOneField(Account)

    def __unicode__(self):
        return "Session for %s %s [ID: %s]" % (
            self.account.first_name, self.account.last_name, self.account.id)

    @classmethod
    def get_account_by_token(cls, token):
        try:
            session = cls.objects.get(token=token)
            if session.is_expired():
                session.delete()
                return None
            return session.account

        except ObjectDoesNotExist:
            return None

