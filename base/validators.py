# python import
import re
from abc import ABCMeta, abstractmethod

from django.core.exceptions import ValidationError
# django import
from django.http import JsonResponse

# app import
from base.exceptions import ValidationException


class BaseValidator:
    __metaclass__ = ABCMeta

    def __init__(self, request):
        self.request = request
        self.code = ValidationException.UNKNOWN_VALIDATION_CODE
        self.message = "Stub"

    @abstractmethod
    def is_valid(self):
        return True


def validate_password_format(value):
    # Format more than 5
    if len(str(value)) < 6:
        raise ValidationError("Too short password. Must be 6 or more symbols")


def validate_login_format(value):
    regex = "^[A-Za-z0-9]{6,15}$"
    if not re.match(regex, value):
        raise ValidationError("Login has invalid format")


def validate_boolean(value, allow_none=False):
    if allow_none and value is None:
        return True
    if str(value).lower() not in ('1', '0', 'true', 'false'):
        raise ValidationError("Boolean has invalid format(must be on of [1, 0, true, false])")


def validate_uint(value, key_name='', allow_none=False):
    if allow_none and value is None:
        return True
    try:
        if int(value) >= 0:
            return True
    except (ValueError, TypeError):
        raise ValidationError("Key %s has invalid format. Must be unsigned Int type" % key_name)
    raise ValidationError("Key %s has invalid format. Must be unsigned Int type" % key_name)


def validate_ufloat(value, key_name='', allow_none=False):
    if allow_none and value is None:
        return True
    try:
        float_value = float(value)
        if float_value <= 0:
            raise TypeError()
    except (ValueError, TypeError):
        raise ValidationError("Key %s has invalid format. Must be unsigned float" % key_name)


class LoginAndPasswordValidator(BaseValidator):
    def is_valid(self):
        login = self.request.data.get("login", None)
        password = self.request.data.get("password", None)
        if not login or not password:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Login and password are required"
            return False
        try:
            validate_login_format(login)
            validate_password_format(password)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True


class ValidatePostParametersMixin(object):
    validator_class = None

    def validate_request(self, request):
        if self.validator_class and issubclass(self.validator_class, BaseValidator):
            validator = self.validator_class(request)
            if not validator.is_valid():
                e = ValidationException(
                    validator.code,
                    validator.message
                )
                return JsonResponse(e.to_dict(), status=400)
        return None


an = {'allow_none': True}


class DataGetter:
    def __init__(self, s):
        self.data = s.request.data

    def __getitem__(self, item):
        return self.data.get(item, None)


def create_generic_validator(fields):
    class GenericValidator(BaseValidator):
        def is_valid(self):
            data = self.request.data
            for key in data:
                if key in fields:
                    try:
                        fields[key].parse(data[key])
                    except Exception as e:
                        self.code = 400
                        self.message = '"%s" key parse failed, error is "%s"' % (key, e.message)
                        return False
            return True

    return GenericValidator


def validate_phone_number(value):
    # Format (+code1) code2+number
    regex = r'^\+?\d[\( ]?\d\d\d[\) ]?-? ?\d\d\d[ -]?\d\d[ -]?\d\d$'
    if not re.match(regex, value):
        raise ValidationError("Phone number has invalid format. Please, send like something +7(909)1234332")