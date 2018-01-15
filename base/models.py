import binascii
import os

from datetime import datetime, timedelta
from time import timezone

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

# Create your models here.
from accounts.models import Account

class AccountSession(models.Model):
    id = models.AutoField(primary_key=True)
    token = models.CharField(max_length=63)
    expired_at = models.DateTimeField()
    created_at = models.DateField(auto_now_add=True)
    account = models.ForeignKey(Account, unique=True)

    class Meta:
        ordering = ["-expired_at"]

        def __unicode__(self):
            return "Session for %s %s" % (self.account.fistname, self.account.lastname)

    @classmethod
    def get_account_by_token(cls, token):
        try:
            session = cls.objects.get(token=token)
            if session.is_expired():
                session.delete()
                raise Exception("Session expired")
            return session.account

        except ObjectDoesNotExist:
            return None

    def save(self, *args, **kwargs):
        if not self.pk:
            self.generate_token()
            self.set_expire_date()
        super(AccountSession, self).save(args, kwargs)

    def generate_token(self):
        self.token = binascii.hexlify(os.urandom(20)).decode()

    def set_expire_date(self):
        self.expired_at = datetime.now() \
                        + timedelta(seconds=self.ACCESS_TOKEN_EXPIRE_SECONDS)

    def is_expired(self):
        return timezone.now() >= self.expired_at