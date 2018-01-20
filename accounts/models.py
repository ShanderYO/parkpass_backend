import random
import binascii
import os

from datetime import datetime, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone


class Account(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=63, null=True, blank=True)
    last_name = models.CharField(max_length=63, null=True, blank=True)
    phone = models.CharField(max_length=15)
    sms_code = models.CharField(max_length=6, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'

    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)

    def login(self):
        if AccountSession.objects.filter(account=self).exists():
            old_session = AccountSession.objects.get(account=self)
            old_session.delete()
        new_session = AccountSession(account=self)
        new_session.save()
        self.sms_code = None
        self.save()

    def create_sms_code(self):
        self.sms_code = "".join([str(random.randrange(1,9)) for x in xrange(6)])

    def send_sms_code(self):
        # TODO add sms gateway
        print "send sms code %s" % self.sms_code

    def get_session(self):
        return AccountSession.objects.get(account=self)

    def clean_session(self):
        if AccountSession.objects.filter(account=self).exists():
            account_session = AccountSession.objects.get(account=self)
            account_session.delete()


class AccountSession(models.Model):
    ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 180

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
                return None
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
        print self.expired_at
        return timezone.now() >= self.expired_at