from __future__ import unicode_literals

from datetime import timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import models
from django.db import IntegrityError
from django.template.loader import render_to_string

from django.utils import timezone

from app.utils import (
    unique_code, logger, build_action_url,
    get_client_ip, get_user_agent, get_device_id,
    get_device_type,
    create_jwt, create_future_timestamp)

from dj import settings

class TokenTypes:
    MOBILE = 1 << 0
    WEB = 1 << 1
    MAX = WEB

ALL_TOKEN_TYPES = [
    TokenTypes.MOBILE, TokenTypes.WEB
]

TOKEN_TYPE_CHOICES = (
    (TokenTypes.MOBILE, "MOBILE"),
    (TokenTypes.WEB, "WEB")
)

class Groups:
    ADMIN = 1 << 0
    BASIC = 1 << 1
    OWNER = 1 << 2
    VENDOR = 1 << 3
    MAX = VENDOR

ALL_GROUPS = [
    Groups.ADMIN, Groups.BASIC,
    Groups.OWNER, Groups.VENDOR
]

GROUP_CHOICES = (
    (Groups.ADMIN, "ADMIN"),
    (Groups.BASIC, "BASIC"),
    (Groups.OWNER, "OWNER"),
    (Groups.VENDOR, "VENDOR"),
)


class ConfirmationSecret(models.Model):
    code = models.CharField(
        primary_key=True, max_length=32,
        editable=False, default=unique_code)

    def __str__(self):
        return 'Code %s' % self.code

    def is_valid(self):
        code_expiration_date = self.created_at + timedelta(
            minutes=settings.SECRET_TOKEN_LIFETIME_IN_MINUTE)

        if timezone.now() > code_expiration_date:
            self.delete()
            return False
        return True

    def get_confirm_email_url(self):
        prefix_path = PROXY_HEADER + 'api/v1/' + settings.ACTIVATION_URL_PATH
        query = self.get_query_params(
            settings.REDIRECT_ACTIVATION_SUCCESS_URL,
            settings.REDIRECT_ACTIVATION_ERROR_URL)
        return build_action_url(prefix_path, query)

    def get_reset_password_url(self):
        prefix_path = PROXY_HEADER + 'api/v1/' + settings.RESET_PASSWORD_URL_PATH
        query = self.get_query_params(
            settings.REDIRECT_SET_PASSWORD_SUCCESS_URL,
            settings.REDIRECT_SET_PASSWORD_ERROR_URL)
        return build_action_url(prefix_path, query)

    def get_query_params(self, success_url, error_url):
        return dict(
            code=self.code,
            success_url=success_url,
            error_url=error_url
        )


class UserControlManager(models.Manager):
    def get_activated_user(self, email):
        try:
            return super().get_queryset().get(email=email, is_active=True)
        except ObjectDoesNotExist:
            return None

    def create_by_email(self, email, password):
        if super().get_queryset().filter(email=email, is_active=False).exists():
            user = super().get_queryset().select_related('registration_confirmation').get(email=email)
            if user.registration_confirmation:
                user.registration_confirmation.delete()
        else:
            try:
                user = super().get_queryset().create(email=email)
            except IntegrityError as e:
                logger().warn(e)
                return None

        user.set_password(password)
        user.registration_confirmation = ConfirmationSecret.objects.create()
        user.save()
        if settings.USE_EMAIL:
            user.send_confirm_mail()
        return user

    def create_by_email_and_groups(self, email, groups):
        if super().get_queryset().filter(email=email).exists():
            user = super().get_queryset().get(email=email)
            if not user.is_active:
                user.reset_password_request()
            return None

        user = super().get_queryset().create(
            email=email, groups=groups
        )
        user.reset_password_request()
        return user

    def get_by_regcode(self, code):
        try:
            return super().get_queryset().get(
                registration_confirmation__code = code)
        except ObjectDoesNotExist:
            return None

    def get_by_reset_passcode(self, code):
        try:
            return super().get_queryset().get(
                reset_password_confirmation__code=code)
        except ObjectDoesNotExist:
            return None

    def get_by_access_token(self, token):
        try:
            session = Session.objects.select_related('user').get(access_token=token)
            return session.user if session.is_valid() else None

        except ObjectDoesNotExist:
            return None


class User(models.Model):
    phone = models.CharField(max_length=128, null=True, blank=True)

    email = models.EmailField(null=True, blank=True)

    password = models.CharField(
        max_length=256, null=True)

    groups = models.IntegerField(
        default=Groups.BASIC,
        help_text='ADMIN = 1, BASIC = 2, OWNER=4, VENDOR=8')

    registration_confirmation = models.ForeignKey(
        ConfirmationSecret, null=True, blank=True, on_delete=models.CASCADE,
        related_name = 'registration_confirmation_secret_fk')

    reset_password_confirmation = models.ForeignKey(
        ConfirmationSecret, null=True, blank=True, on_delete=models.CASCADE,
        related_name='reset_password_confirmation_secret_fk')

    is_email_confirmed = models.BooleanField(default=False)

    is_active = models.BooleanField(default=False)

    blocked_at = models.DateTimeField(null=True, blank=True)

    blocked_until = models.DateTimeField(null=True, blank=True)

    block_reason = models.TextField(null=True, blank=True)

    last_online_at = models.DateTimeField(null=True, blank=True)

    objects = models.Manager()

    control = UserControlManager()

    def __str__(self):
        return '%s' % self.email

    @property
    def active(self):
        return self.is_active and self.is_email_confirmed

    def is_superuser(self):
        return bool(self.groups & Groups.ROOT)

    @property
    def blocked(self):
        if self.blocked_at or self.blocked_until:
            if self.blocked_at and self.blocked_until:
                return timezone.now() > self.blocked_at < self.blocked_until
            if self.blocked_at:
                return timezone.now() > self.blocked_at
            if self.blocked_until:
                return timezone.now() < self.blocked_until
        return False

    def save(self, *args, **kwargs):
        super(User, self).save(*args, **kwargs)

    def add_to_group(self, group_mask):
        self.groups |= group_mask

    def revoke_group(self, group_mask):
        self.groups &= group_mask

    def activate(self):
        self.is_email_confirmed = True
        self.is_active = True
        self.registration_confirmation.delete()
        self.registration_confirmation = None
        self.save()

    def login(self, password, info):
        if self.check_password(password):
            remote_ip = get_client_ip(info.context)
            user_agent = get_user_agent(info.context)
            device_id = get_device_id(info.context)
            device_type = get_device_type(info.context)

            session = self.create_session(
                ip=remote_ip,
                platform=device_type,
                user_agent=user_agent)
            return session
        return None

    def create_session(self, **kwargs):
        claims = self.get_required_claims()
        jwt_token = create_jwt(claims)
        session = Session.objects.create(
            access_token=jwt_token,
            platform=kwargs.get('platform', ''),
            last_ip=kwargs.get('ip', ''),
            user_agent=kwargs.get('user_agent', ''),
            user=self
        )
        return session

    def block(self, datetime_at, datetime_until, reason):
        self.blocked_at = datetime_at
        self.blocked_until = datetime_until
        self.block_reason = reason
        self.save()
        # Block user's sessions
        Session.objects.filter(user=self).update(
            expires_at=timezone.now())

    def unblock(self, reason=None):
        self.blocked_at = None
        self.blocked_until = None
        self.block_reason = reason
        self.save()

    def update_last_online(self):
        self.last_online_at = timezone.now()
        self.save()

    def get_required_claims(self):
        expires_at = create_future_timestamp(
            settings.ACCESS_TOKEN_LIFETIME_IN_SECONDS)
        return dict(
            user_id=self.id,
            email=self.email,
            groups=self.groups,
            expires_at=expires_at
        )

    def reset_password_request(self):
        self.update_password_confirmation_code()
        if settings.USE_EMAIL:
            self.send_reset_password_mail()
        self.reset_active_sessions()

    def reset_active_sessions(self):
        Session.objects.filter(user=self).delete()

    def new_password_request(self):
        self.update_password_confirmation_code()
        self.send_set_password_email()

    def update_password_confirmation_code(self):
        if self.reset_password_confirmation:
            self.reset_password_confirmation.delete()
        self.reset_password_confirmation = ConfirmationSecret.objects.create()
        self.save()

    def set_password(self, password):
        hashed_password = make_password(password)
        self.password = hashed_password

    def check_password(self, raw_password):
        def setter(r_password):
            self.set_password(r_password)
        return check_password(raw_password, self.password, setter)

    def change_password(self, password):
        self.set_password(password)
        self.reset_password_confirmation.delete()
        self.reset_password_confirmation = None
        self.save()

    def is_registration_confirmation_valid(self):
        if self.registration_confirmation:
            return self.registration_confirmation.is_valid()
        return False

    def is_reset_password_confirmation_valid(self):
        if self.reset_password_confirmation:
            return self.reset_password_confirmation.is_valid()
        return False

    def send_confirm_mail(self):
        template = 'registration_mail.html'

        context = dict(
            title='Registration completion',
            email=self.email,
            activation_url=self.registration_confirmation.get_confirm_email_url()
        )
        msg_html = render_to_string(template, context)
        send_mail('Welcome to Sberbank', '',
                  settings.EMAIL_HOST_USER,
                  ['%s' % str(self.email)], html_message=msg_html)

    def send_reset_password_mail(self):
        template = 'password_reset_mail.html'

        context = dict(
            title='Password recovery',
            email=self.email,
            recovery_url=self.reset_password_confirmation.get_reset_password_url()
        )
        msg_html = render_to_string(template, context)
        send_mail('Password recovery', '',
                  settings.EMAIL_HOST_USER,
                  ['%s' % str(self.email)], html_message=msg_html)

    def send_set_password_email(self):
        template = 'password_set_mail.html'

        context = dict(
            title='Registration completion',
            email=self.email,
            set_password_url=self.reset_password_confirmation.get_reset_password_url()
        )
        msg_html = render_to_string(template, context)
        send_mail('Welcome to Sberbank', '',
                  settings.EMAIL_HOST_USER,
                  ['%s' % str(self.email)], html_message=msg_html)


class Session(models.Model):
    refresh_token = models.CharField(max_length=1024)

    access_token = models.CharField(max_length=1024, null=True, blank=True)

    expires_at = models.DateTimeField()

    last_ip = models.CharField(
        max_length=256, null=True)

    user = models.ForeignKey(
        User, on_delete=models.CASCADE)

    def __str__(self):
        return 'Session for user %s' % self.user

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                seconds=settings.ACCESS_TOKEN_LIFETIME_IN_SECONDS)
            self.create_refresh_token()
        super(Session, self).save(*args, **kwargs)

    def is_valid(self):
        return self.expires_at > timezone.now()

    def invalidate(self):
        self.delete()

    def create_refresh_token(self, identity, user_claims=None):
        self.refresh_token = "stub"
        self.save()
        # TODO make random refresh_token

    def update_access_token(self, claims):
        self.access_token =

    def _create_access_token(self, identity, fresh=False, expires_delta=None, user_claims=None):
        if expires_delta is None:
            expires_delta = config.access_expires

        if user_claims is None:
            user_claims = self._user_claims_callback(identity)

        access_token = encode_access_token(
            identity=self._user_identity_callback(identity),
            secret=self._encode_key_callback(identity),
            algorithm=config.algorithm,
            expires_delta=expires_delta,
            fresh=fresh,
            user_claims=user_claims,
            csrf=config.csrf_protect,
            identity_claim_key=config.identity_claim_key,
            user_claims_key=config.user_claims_key,
            json_encoder=config.json_encoder
        )


return access_token


def _encode_jwt(additional_token_data, expires_delta, secret, algorithm,
                json_encoder=None):


    uid = _create_csrf_token()
now = datetime.datetime.utcnow()
token_data = {
    'iat': now,
    'nbf': now,
    'jti': uid,
}
# If expires_delta is False, the JWT should never expire
# and the 'exp' claim is not set.
if expires_delta:
    token_data['exp'] = now + expires_delta
token_data.update(additional_token_data)
encoded_token = jwt.encode(token_data, secret, algorithm,
                           json_encoder=json_encoder).decode('utf-8')
return encoded_token