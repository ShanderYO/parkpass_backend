from __future__ import unicode_literals

from datetime import timedelta, time

from django.db import models
from django.utils import timezone

from auth.utils import (
    unique_code, create_jwt, create_future_timestamp
)

from parkpass import settings

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
    BASIC = 0
    ADMIN = 1 << 0
    OWNER = 1 << 1
    VENDOR = 1 << 2
    MAX = VENDOR

ALL_GROUPS = [
    Groups.ADMIN, Groups.BASIC,
    Groups.OWNER, Groups.VENDOR
]

GROUP_CHOICES = (
    (Groups.BASIC, "BASIC"),
    (Groups.ADMIN, "ADMIN"),
    (Groups.OWNER, "OWNER"),
    (Groups.VENDOR, "VENDOR"),
)


class Session(models.Model):
    refresh_token = models.CharField(max_length=1024)

    type = models.CharField(max_length=32, choices=TOKEN_TYPE_CHOICES)

    expires_at = models.DateTimeField()

    # user = models.ForeignKey(
    #     User, on_delete=models.CASCADE)

    temp_user_id = models.IntegerField()

    class Meta:
        db_table = 'jwt_session'

    def __str__(self):
        return 'Session for user %s' % self.temp_user_id

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                seconds=settings.REFRESH_TOKEN_LIFETIME_IN_SECONDS)
            self._create_refresh_token()
        super(Session, self).save(*args, **kwargs)

    def is_valid(self):
        return self.expires_at > timezone.now()

    def invalidate(self):
        self.delete()

    def _create_refresh_token(self):
        refresh_claims = {
            "user_id": self.temp_user_id,
            "app": "parkpass",
            "type": self.type,
            "expires_at": self.expires_at,
            "timestamp": int(time.time())
        }
        self.refresh_token = create_jwt(refresh_claims)
        self.save()

    def update_access_token(self, group, app="parkpass"):
        return create_jwt({
            "user_id": self.temp_user_id,
            "app": app,
            "type": self.type,
            "group": group,
            "expires_at": create_future_timestamp(settings.ACCESS_TOKEN_LIFETIME_IN_SECONDS)
        })

        # access_token = encode_access_token(
        #     identity=self._user_identity_callback(identity),
        #     secret=self._encode_key_callback(identity),
        #     algorithm=config.algorithm,
        #     expires_delta=expires_delta,
        #     fresh=fresh,
        #     user_claims=user_claims,
        #     csrf=config.csrf_protect,
        #     identity_claim_key=config.identity_claim_key,
        #     user_claims_key=config.user_claims_key,
        #     json_encoder=config.json_encoder
        # )