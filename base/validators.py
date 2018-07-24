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