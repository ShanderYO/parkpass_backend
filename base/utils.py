import logging

import datetime
import pytz

from parkpass.settings import BASE_LOGGER_NAME


def get_logger(name=BASE_LOGGER_NAME):
    return logging.getLogger(name)


def parse_int(value):
    try:
        return int(value)
    except Exception:
        return None


def datetime_from_unix_timestamp_tz(value):
    started_at_date = datetime.datetime.fromtimestamp(value)
    return pytz.utc.localize(started_at_date)