import re
import datetime

from django.core.exceptions import ValidationError

from base.exceptions import ValidationException
from django.core.validators import validate_email
from base.validators import BaseValidator


class IdValidator(BaseValidator):
    def is_valid(self):
        id = self.request.data.get("id", None)
        if not id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Id is required"
            return False
        try:
            self.request.data["id"] = int(id)
        except Exception:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Id has invalid format"
            return False
        return True


class LoginParamValidator(BaseValidator):
    def is_valid(self):
        phone = self.request.data.get("phone", None)
        if not phone:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Phone is required"
            return False
        try:
            validate_phone_number(phone)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True


class ConfirmLoginParamValidator(BaseValidator):
    def is_valid(self):
        sms_code = self.request.data.get("sms_code", None)
        if not sms_code:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Empty sms-code"
            return False
        try:
            validate_sms_code(sms_code)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True


class AccountParamValidator(BaseValidator):
    def is_valid(self):
        first_name = self.request.data.get("first_name", None)
        last_name = self.request.data.get("last_name", None)
        if not first_name and not last_name:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Nothing change"
            return False
        try:
            validate_name(first_name)
            validate_name(last_name)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True


def validate_email_format(value):
    validate_email(value)

def validate_name(value):
    # TODO implement
    pass
#---------------------------------------------------------------------------------------------------------

def validate_phone_number(value):
    # Format (+code1) code2+number
    regex = '^\(\+[0-9]{1,3}\)\s?[0-9]{9,13}$'
    if not re.match(regex, value):
        raise ValidationError("Phone number has invalid format. Please, send like something (+7)9091234332")


def validate_account_birthday(value):
    if value > datetime.date.today() or value < datetime.date(1900,1,1):
        raise ValidationError("There can be only since 1990 untill today")


def validate_account_name(value, field_name="NonameField"):
    #TODO add accepted regex!
    regex = "^.*$"
    if not re.match(regex,value):
        raise ValidationError("%s has invalid format" % field_name)


def validate_mail_code(value):
    regex = '^[0-9a-f]{32}$'
    if not re.match(regex, value):
        raise ValidationError("Invalid activation email code format")


def validate_sms_code(value):
    regex = '^[0-9]{5}$'
    if not re.match(regex, value):
        raise ValidationError("Phone code has invalidate format")
