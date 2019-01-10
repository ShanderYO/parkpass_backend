import uuid
from datetime import datetime, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string

from base.models import BaseAccount, BaseAccountSession
from parkpass.settings import EMAIL_HOST_USER


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
            "email": self.email,
            "confirmation_href": self._generate_confirmation_link()
        }
        msg_html = render_to_string('emails/email_confirm_mail.html',
                                    render_data)
        send_mail('Request to bind mail', "", EMAIL_HOST_USER,
                  ['%s' % str(self.email)], html_message=msg_html)

    def _generate_confirmation_link(self):
        return "https://parkpass.ru/api/v1/account/email/confirm/" + self.code + "/"


class Account(BaseAccount):
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

