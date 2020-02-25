import datetime
import time
import uuid
from datetime import timedelta

import jwt

from django.utils import timezone

from parkpass_backend.settings import SECRET_KEY_JWT


def unique_code():
    return str(uuid.uuid4()).replace("-", "")


def get_email_lower_local_part(email):
    parts = email.split("@")
    return "@".join([parts[0].lower(), parts[1]])


def create_jwt(data):
    return jwt.encode(data, SECRET_KEY_JWT, algorithm='HS256').decode("utf-8")


def parse_jwt(access_token):
    try:
        return jwt.decode(
            access_token.encode("utf-8"), SECRET_KEY_JWT,
            algorithms=['HS256'])

    except Exception as e:
        return None


def has_groups(groups, access_token):
    claims = parse_jwt(access_token)
    if claims.get("groups"):
        token_groups = claims["groups"]
        for group in groups:
            if not bool(group & token_groups):
                return False
        return True
    return False


def has_group(group, access_token):
    claims = parse_jwt(access_token)
    if claims.get("groups"):
        token_groups = claims["groups"]
        return bool(group & token_groups)
    return False


def create_future_timestamp(seconds):
    target_datetime = timezone.now() + timedelta(seconds=seconds)
    return datetime_to_timestamp(target_datetime)


def datetime_to_timestamp(datetime_time):
    if isinstance(datetime_time, datetime.datetime):
        if datetime_time.tzinfo:
            datetime_time = datetime_time.astimezone(timezone.get_current_timezone())
        return int(time.mktime(datetime_time.timetuple()))
    return int(time.mktime(datetime_time.timetuple()))