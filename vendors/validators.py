import re

from django.core.exceptions import ValidationError

from accounts.validators import validate_password_format
from base.exceptions import ValidationException
from base.validators import BaseValidator


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
