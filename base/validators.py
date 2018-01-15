# python import
from abc import ABCMeta, abstractmethod

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