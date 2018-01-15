import random
from django.db import models

# Create your models here.
from base.models import AccountSession


class Account(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=63, null=True, blank=True)
    last_name = models.CharField(max_length=63, null=True, blank=True)
    phone = models.CharField(max_length=15)
    sms_code = models.CharField(max_length=6)
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

    def create_sms_code(self):
        self.sms_code = "".join([random.randrange(1,9) for x in xrange(6)])

    def send_sms_code(self):
        # TODO add sms gateway
        print "send sms code %s" % self.sms_code

    def clean_session(self):
        if AccountSession.objects.filter(account=self).exists():
            account_session = AccountSession.objects.get(account=self)
            account_session.delete()