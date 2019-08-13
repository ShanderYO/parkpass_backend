# -*- coding: utf-8 -*-
import datetime
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from auth.utils import parse_jwt
from base.exceptions import ValidationException
from base.validators import BaseValidator, validate_phone_number


class IdValidator(BaseValidator):
    def is_valid(self):
        id = self.request.data.get("id", None)
        if not id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Id is required"
            return False
        try:
            self.request.data["id"] = int(id)
        except ValueError:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Id has invalid format"
            return False
        return True


class EmailValidator(BaseValidator):
    def is_valid(self):
        email = self.request.data.get("email", None)
        if not email:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Email is required"
            return False
        try:
            validate_email(email)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
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
            self.message = "Key `sms_code` are required"
            return False
        try:
            validate_sms_code(sms_code)

        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True


class NewConfirmLoginParamValidator(BaseValidator):
    def is_valid(self):
        sms_code = self.request.data.get("sms_code", None)
        phone = self.request.data.get("phone", None)

        if not sms_code or not phone:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys `phone` and `sms_code` are required"
            return False
        try:
            validate_phone_number(phone)
            validate_sms_code(sms_code)

        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True


class UpdateTokensValidator(BaseValidator):
    def is_valid(self):
        access_token = self.request.data.get("access_token", None)
        refresh_token = self.request.data.get("refresh_token", None)

        if not access_token or not refresh_token:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys `access_token` and `refresh_token` are required"
            return False

        return True


class EmailAndPasswordValidator(BaseValidator):
    def is_valid(self):
        email = self.request.data.get("email", None)
        password = self.request.data.get("password", None)
        if not email or not password:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Login and password are required"
            return False
        try:
            validate_email_format(email)
            validate_password_format(password)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True


class LoginAndPasswordValidator(BaseValidator):
    def is_valid(self):
        login = self.request.data.get("login", None)
        password = self.request.data.get("password", None)
        if not login or not password:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Login and password are required"
            return False
        try:
            validate_account_name(login, "Login")
            validate_password_format(password)
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
            if first_name:
                validate_name(first_name)
            if last_name:
                validate_name(last_name)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True


class StartAccountParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        parking_id = self.request.data.get("parking_id", None)
        started_at = self.request.data.get("started_at", None)

        if not session_id or not parking_id or not started_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'session_id', 'parking_id' and 'started_at' is required"
            return False
        try:
            validate_id(parking_id, "parking_id")
            validate_unix_timestamp(started_at, "started_at")
        except Exception as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False
        return True


class CompleteAccountParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("id", None)
        parking_id = self.request.data.get("parking_id", None)
        completed_at = self.request.data.get("completed_at", None)

        if not session_id or not parking_id or not completed_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "id', 'parking_id' and 'completed_at' is required"
            return False
        try:
            validate_id(parking_id, "parking_id")
            validate_unix_timestamp(completed_at, "completed_at")
        except Exception as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False
        return True


class ExternalLoginValidator(BaseValidator):
    def is_valid(self):
        vendor_id = self.request.data.get("vendor_id", None)
        external_user_id = self.request.data.get("external_user_id", None)
        if not vendor_id or not external_user_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'vendor_id' and 'external_user_id' are required"
            return False
        try:
            validate_id(vendor_id, "vendor_id")
        except Exception as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False
        return True


def validate_id(value, key_name):

    try:
        int_value = int(value)
        if int_value < 1:
            raise ValidationError("Key '%s' requires positive value" % key_name)

        # if isinstance(value, str) or isinstance(value, unicode):
        #    raise ValidationError("Key '%s' has invalid format. Must be unsigned Int64 type" % key_name)

    except (ValueError, TypeError):
        raise ValidationError("Key '%s' has invalid format. Must be unsigned Int64 type" % key_name)


def validate_unix_timestamp(value, key_name):
    try:
        if int(value) >= 0:
            return True
    except (ValueError, TypeError):
        raise ValidationError("Key '%s' has invalid format. Must be unsigned Int type" % key_name)
    raise ValidationError("Key '%s' has invalid format. Must be unsigned Int type" % key_name)


def validate_email_format(value):
    validate_email(value)


def validate_name(value):
    regex = u'[A-Za-zА-Яа-яЁё]{2,50}'
    if not re.match(regex, value):
        raise ValidationError("Name has invalid format. Please use only letters. Also, length must be <= 50 letters.")


def validate_account_birthday(value):
    if value > datetime.date.today() or value < datetime.date(1900,1,1):
        raise ValidationError("There can be only since 1990 until today")


def validate_account_name(value, field_name="NonameField"):
    regex = regex = "^[A-Za-z0-9]{6,15}$"
    if not re.match(regex,value):
        raise ValidationError("%s has invalid format" % field_name)


def validate_mail_code(value):
    regex = '^[0-9a-f]{32}$'
    if not re.match(regex, value):
        raise ValidationError("Invalid e-mail confirmation code format")


def validate_sms_code(value):
    regex = '^[0-9]{5}$'
    if not re.match(regex, value):
        raise ValidationError("Phone code has invalidate format")


def validate_password_format(value):
    # Format more than 5
    if len(str(value)) < 6:
        raise ValidationError("Too short password. Must be 6 or more symbols")


def validate_parking_card_id(value):
    if len(str(value)) < 6:
        raise ValidationError("Invalid parking card id. Must be 6 or more symbols")
