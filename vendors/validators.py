# -*- coding: utf-8 -*-
import re

from django.core.exceptions import ValidationError

from accounts.validators import validate_email_format, validate_phone_number
from base.exceptions import ValidationException
from base.validators import BaseValidator


def validate_name(value):
    regex = r'^[A-Za-zА-Яа-яЁё ]{2,255}$'
    if not re.match(regex, value):
        raise ValidationError("Name has invalid format. Please use only letters. Also, length must be <= 255 letters.")


class IssueValidator(BaseValidator):
    def is_valid(self):
        name = self.request.data.get("name", None)
        phone = self.request.data.get("phone", None)
        email = self.request.data.get("email", None)
        if not name or not phone:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Phone and name is required"
            return False
        try:
            validate_name(name)
            if email:
                validate_email_format(email)
            if phone:
                validate_phone_number(phone)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True
