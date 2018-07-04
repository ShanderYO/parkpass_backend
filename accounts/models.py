import binascii
import os
import random
import uuid
from datetime import datetime, timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import models
from django.db.models import BigAutoField
from django.template.loader import render_to_string
from django.utils import timezone

from parkpass.settings import EMAIL_HOST_USER, AVATARS_URL


class EmailConfirmation(models.Model):
    TOKEN_EXPIRATION_TIMEDELTA_IN_SECONDS = 60 * 60 * 24 * 30  # One month

    email = models.EmailField()
    code = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "Code %s [%s]" % (self.code, self.email)

    def create_code(self):
        self.code = str(uuid.uuid4()).replace('-', '')

    def is_expired(self):
        created_at = (self.created_at +
                      timedelta(0, self.TOKEN_EXPIRATION_TIMEDELTA_IN_SECONDS)).replace(tzinfo=None)
        return datetime.now() > created_at

    # TODO make async
    def send_confirm_mail(self):
        render_data = {
            "emails": self.email,
            "confirmation_href": self._generate_confirmation_link()
        }
        msg_html = render_to_string('emails/email_confirm_mail.html',
                                    render_data)
        send_mail('Request to bind mail', "", EMAIL_HOST_USER,
                  ['%s' % str(self.email)], html_message=msg_html)

    def _generate_confirmation_link(self):
        return "http://parkpass.ru/account/email/confirm/"+self.code


class Account(models.Model):
    id = BigAutoField(primary_key=True)
    first_name = models.CharField(max_length=63, null=True, blank=True)
    last_name = models.CharField(max_length=63, null=True, blank=True)
    phone = models.CharField(max_length=15)
    sms_code = models.CharField(max_length=6, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    password = models.CharField(max_length=255, default="stub")
    avatar = models.ImageField(upload_to=AVATARS_URL, default='default.jpg')
    email_confirmation = models.ForeignKey(EmailConfirmation, null=True,
                                           blank=True, on_delete=models.CASCADE)
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

    def check_password(self, raw_password):
        def setter(r_password):
            self.set_password(r_password)
        return check_password(raw_password, self.password, setter)

    def update_avatar(self, f):
        """
        #base, sub = f.content_type.split("/")
        #if base != "image" or sub not in ("jpeg", "pjpeg", "gif", "png"):
        #    raise ValidationError("That's not image")
        md5 = hashlib.md5()
        with open(AVATARS_URL + md5(self.phone).hexdigest(), "w") as dest:
            for chunk in f.chunks():
                dest.write(chunk)
        """
        self.avatar = f

    def get_avatar(self):
        return self.avatar

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def make_hashed_password(self):
        raw_password = self.password
        self.password = make_password(raw_password)

    def create_password_and_send(self):
        raw_password = self.generate_random_password()
        self.set_password(raw_password)
        self.save()
        self.send_password_mail(raw_password)

    def send_password_mail(self, raw_password):
        render_data = {
            "password": raw_password,
        }
        msg_html = render_to_string('emails/password_mail.html',
                                    render_data)
        send_mail('Parkpass password', "", EMAIL_HOST_USER,
                  ['%s' % str(self.email)], html_message=msg_html)

    def generate_random_password(self):
        raw_password = User.objects.make_random_password(8)
        return raw_password

    def create_sms_code(self):
        self.sms_code = "".join([str(random.randrange(1,9)) for x in xrange(5)])

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
    account = models.OneToOneField(Account)

    class Meta:
        ordering = ["-expired_at"]

    def __unicode__(self):
        return "Session for %s %s" % (self.account.first_name, self.account.last_name)

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
            if not kwargs.get("not_generate_token", False):
                self.generate_token()
            else:
                del kwargs["not_generate_token"]
            self.set_expire_date()
        super(AccountSession, self).save(*args, **kwargs)

    def generate_token(self):
        self.token = binascii.hexlify(os.urandom(20)).decode()

    def set_expire_date(self):
        self.expired_at = datetime.now() \
                        + timedelta(seconds=self.ACCESS_TOKEN_EXPIRE_SECONDS)

    def is_expired(self):
        print self.expired_at
        return timezone.now() >= self.expired_at
