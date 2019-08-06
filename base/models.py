# -*- coding: utf-8 -*-
import binascii
import datetime
import os
import random
import time
import uuid
from datetime import timedelta
from hashlib import md5
from io import BytesIO

from jose import jwt

from PIL import Image
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import models
from django.db.models import BigAutoField
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.validators import validate_name
from base.exceptions import ValidationException
from base.validators import validate_phone_number
from parkpass import settings
from parkpass.settings import EMAIL_HOST_USER, AVATARS_URL, AVATARS_ROOT, ZENDESK_CHAT_SECRET


class Terminal(models.Model):
    name = models.CharField(max_length=255, unique=True, null=True)
    terminal_key = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    is_selected = models.BooleanField(default=False)

    def __unicode__(self):
        return "Terminal %s" % self.terminal_key

    def save(self, *args, **kwargs):
        if self.is_selected:
            old_active_terminals = Terminal.objects.filter(is_selected=True).exclude(id=self.id)

            for old_active_terminal in old_active_terminals:
                old_active_terminal.is_selected = False
                old_active_terminal.save()

            settings.TINKOFF_TERMINAL_KEY = self.terminal_key
            settings.TINKOFF_TERMINAL_PASSWORD = self.password

        if len(Terminal.objects.all()) == 0 and not kwargs.get('prevent_recursion', False):
            self.is_selected = True
            self.save(prevent_recursion=True)

        super(Terminal, self).save()


class EmailConfirmation(models.Model):
    TOKEN_EXPIRATION_TIMEDELTA_IN_SECONDS = 60 * 60 * 24 * 30  # One month

    email = models.EmailField()
    code = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    account_type = models.CharField(max_length=40,
                                    default="account",
                                    choices=(
                                        ("User", "account"),
                                        ("Vendor", "vendor"),
                                        ("Owner", "owner")
                                    )
                                    )

    def __unicode__(self):
        return "Code %s [%s]" %(self.code, self.email)

    def create_code(self):
        self.code = str(uuid.uuid4()).replace('-', '')

    def is_expired(self):
        created_at = (self.created_at +
                      timedelta(0, self.TOKEN_EXPIRATION_TIMEDELTA_IN_SECONDS)).replace(tzinfo=timezone.utc)
        return timezone.now() > created_at

    # TODO make async
    def send_confirm_mail(self):
        render_data = {
            "email": self.email,
            "confirmation_href": self._generate_confirmation_link()
        }
        msg_html = render_to_string('emails/account_activation.html',
                                    render_data)
        send_mail('Подтвердите e-mail', "", EMAIL_HOST_USER,
                  ['%s' % str(self.email)], html_message=msg_html)

    def _generate_confirmation_link(self):
        return ("https://parkpass.ru/api/v1/%s/email/confirm/" % self.account_type) + self.code + "/"


class BaseAccount(models.Model):
    id = BigAutoField(primary_key=True)
    first_name = models.CharField(max_length=63, null=True, blank=True)
    last_name = models.CharField(max_length=63, null=True, blank=True)
    phone = models.CharField(max_length=15)
    sms_code = models.CharField(max_length=6, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    password = models.CharField(max_length=255, default="stub")
    email_confirmation = models.ForeignKey(EmailConfirmation, null=True, blank=True, on_delete=models.CASCADE)
    avatar = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        abstract = True

    def __unicode__(self):
        return "%s %s [ID: %s]" % (self.first_name, self.last_name, self.id)

    @property
    def session_class(self):
        return self.__class__

    @property
    def type(self):
        return 'baseaccount'

    def check_password(self, raw_password):
        def setter(r_password):
            self.set_password(r_password)
        return check_password(raw_password, self.password, setter)

    def update_avatar(self, f):
        path = md5(self.phone + str(random.randint(1,1000))).hexdigest() + '.jpg'
        write_path = '/' + AVATARS_ROOT + '/' + path
        url_path = AVATARS_URL + path

        im = Image.open(BytesIO(f))
        width, height = im.size
        format = im.format
        im.close()

        if width > 300 or height > 300 or format != 'JPEG':
            raise ValidationException(
                    ValidationException.INVALID_IMAGE,
                    "Image must be JPEG and not be larger than 300x300 px"
                   )
        with open(write_path, "w") as dest:
            dest.write(f)

        self.avatar = url_path
        self.save()

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def make_hashed_password(self):
        raw_password = self.password
        self.password = make_password(raw_password)

    def create_password_and_send(self, is_recovery=False):
        raw_password = self.generate_random_password()
        self.set_password(raw_password)
        self.save()
        if is_recovery:
            self.send_recovery_password_mail(raw_password)
        else:
            self.send_password_mail(raw_password)

    def send_recovery_password_mail(self, raw_password):
        if not self.email:
            return

        render_data = {
            "email": self.email,
            "password": raw_password,
        }
        msg_html = render_to_string('emails/password_recovery.html',
                                    render_data)
        send_mail('Восстановление пароля', "", EMAIL_HOST_USER,
                  [str(self.email)], html_message=msg_html)

    def send_password_mail(self, raw_password):
        if not self.email:
            return
        render_data = {
            "email": self.email,
            "password": raw_password,
        }
        msg_html = render_to_string('emails/password_set.html',
                                    render_data)
        send_mail('E-mail подтвержден', "", EMAIL_HOST_USER,
                  [str(self.email)], html_message=msg_html)

    def generate_random_password(self):
        raw_password = User.objects.make_random_password(8)
        return raw_password

    def create_sms_code(self, stub=False):
        self.sms_code = "".join([str(random.randrange(1,9)) for x in range(5)])
        if stub:
            self.sms_code = "12345"

    def login(self):
        d = {self.type: self}
        if self.session_class.objects.filter(**d).exists():
            old_session = self.session_class.objects.get(**d)
            old_session.delete()
        new_session = self.session_class(**d)
        new_session.save()
        self.sms_code = None
        self.save()

    def get_session(self):
        return self.session_class.objects.get(**{self.type: self})

    def clean_session(self):
        if self.session_class.objects.filter(**{self.type: self}).exists():
            account_session = self.session_class.objects.get(**{self.type: self})
            account_session.delete()

    def send_deactivated_email(self):
        if not self.email:
            return
        msg_html = render_to_string('emails/account_deactivated.html', {})
        send_mail('Банковские карты удалены', "", EMAIL_HOST_USER,
                  [str(self.email)], html_message=msg_html)

    def send_wellcome_email(self):
        pass

    def get_or_create_jwt_for_zendesk_chat(self):
        timestamp = int(time.mktime(datetime.datetime.now().timetuple()))
        payload = {
            'name': self.get_represent_name(),
            'email': self.email,
            'external_id': "user_%s" % self.id,
            'iat': timestamp,
            'exp':timestamp + 120
        }
        return jwt.encode(payload, ZENDESK_CHAT_SECRET)

    def get_represent_name(self):
        if hasattr(self, "name") and getattr(self, "name"):
            return getattr(self, "name")

        if self.first_name or self.last_name:
            if self.first_name:
                if self.last_name:
                    return self.first_name + " "+ self.last_name
                return self.first_name
            return self.last_name


class BaseAccountSession(models.Model):
    ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 180
    id = models.AutoField(primary_key=True)
    token = models.CharField(max_length=63)
    expired_at = models.DateTimeField()
    created_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-expired_at"]
        abstract = True

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
        super(BaseAccountSession, self).save(*args, **kwargs)

    def generate_token(self):
        self.token = binascii.hexlify(os.urandom(20)).decode()

    def set_expire_date(self):
        self.expired_at = timezone.now() \
                          + timedelta(seconds=self.ACCESS_TOKEN_EXPIRE_SECONDS)

    def is_expired(self):
        return timezone.now() >= self.expired_at


class NotifyIssue(models.Model):
    phone = models.CharField(max_length=15)


class BaseAccountIssue(models.Model):
    OWNER_ISSUE_TYPE = 1
    VENDOR_ISSUE_TYPE = 2

    types = (
        (OWNER_ISSUE_TYPE, "Type owner"),
        (VENDOR_ISSUE_TYPE, "Type vendor"),
    )

    id = models.AutoField(primary_key=True)
    type = models.PositiveSmallIntegerField(choices=types)
    name = models.CharField(max_length=255, validators=(validate_name,))
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=13, validators=(validate_phone_number,))
    comment = models.CharField(max_length=1023, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return '%s %s' % (self.name, self.created_at)

    def send_mail(self, email):
        msg_html = render_to_string('emails/issue_accepted.html',
                                    {'number': str(self.id)})
        send_mail('Новое обращение в поддержу', "", EMAIL_HOST_USER,
                  ['%s' % str(email)], html_message=msg_html)

