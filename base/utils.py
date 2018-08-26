import datetime
import logging

import pytz

from parkpass.settings import BASE_LOGGER_NAME


def get_logger(name=BASE_LOGGER_NAME):
    return logging.getLogger(name)


def parse_int(value, raise_exception=False, allow_none=True, only_positive=False):
    if not allow_none and value is None:
        raise ValueError('Required field isn\'t specified')
    if value is None and raise_exception:
        return None
    try:
        if int(value) < 0 and only_positive:
            raise ValueError("Only positive integers allowed")
        return int(value)
    except Exception:
        if raise_exception:
            raise
        return None


def parse_bool(value, raise_exception=False, allow_none=True):
    if not allow_none and value is None:
        raise ValueError('Required field isn\'t specified')
    if value is None and raise_exception:
        return None
    v = str(value).lower()
    if v in ('1', 'true'):
        return True
    elif v in ('0', 'false'):
        return False
    if raise_exception:
        raise ValueError('Boolean value must be `1`, `0`, `true` or `false`')
    return None


def parse_float(value, raise_exception=False, allow_none=True, only_positive=False):
    if not allow_none and value is None:
        raise ValueError('Required field isn\'t specified')
    if value is None and raise_exception:
        return None
    try:
        if float(value) < 0 and only_positive:
            raise ValueError("Only positive floats allowed")
        return float(value)
    except Exception:
        if raise_exception:
            raise
        return None


def datetime_from_unix_timestamp_tz(value):
    if value is None:
        return None
    started_at_date = datetime.datetime.fromtimestamp(value)
    return pytz.utc.localize(started_at_date)