import re

from django.core.exceptions import ValidationError


def validate_latitude(value):
    # value is float
    regex = "^(\-)?(?:90(?:(?:\.0{1,7})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,7})?))$"
    if not re.match(regex, str(value)):
        raise ValidationError("Invalid latitude of geo position")


def validate_longitude(value):
    # value is float
    regex = "^(\-)?(?:180(?:(?:\.0{1,7})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,7})?))$"
    if not re.match(regex, str(value)):
        raise ValidationError("Invalid longitude of geo position")