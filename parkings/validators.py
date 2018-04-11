import re

from django.core.exceptions import ValidationError

from base.exceptions import ValidationException
from base.validators import BaseValidator


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


def validate_id(value, key_name):
    try:
        int_value = int(value)
        if int_value < 1:
            raise ValidationError("Key '%s' requires positive value" % key_name)

        float_value = float(value)
        if int_value != float_value:
            raise ValidationError("Key '%s' has invalid format. Must be unsigned Int64 type" % key_name)

    except (ValueError, TypeError):
        raise ValidationError("Key '%s' has invalid format. Must be unsigned Int64 type" % key_name)


def validate_unix_timestamp(value, key_name):
    try:
        if int(value) >= 0:
            return True
    except (ValueError, TypeError):
        raise ValidationError("Key '%s' has invalid format. Must be unsigned Int type" % key_name)
    raise ValidationError("Key '%s' has invalid format. Must be unsigned Int type" % key_name)


class UpdateParkingValidator(BaseValidator):
    def is_valid(self):
        parking_id = self.request.data.get("parking_id")
        free_places = self.request.data.get("free_places")

        if not parking_id or not free_places:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'parking_id' and 'free_places' are required"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        try:
            validate_id(free_places, "free_places")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        return True


class CreateParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        parking_id = self.request.data.get("parking_id", None)
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        if not session_id or not parking_id or not client_id or not started_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'session_id', 'parking_id', 'client_id' and 'started_at' are required"
            return False

        if len(str(session_id)) > 128:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key length 'session_id' must not be more 128 ASCII symbols"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        try:
            validate_id(client_id, "client_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        try:
            validate_unix_timestamp(started_at, "started_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        return True


class UpdateParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        parking_id = self.request.data.get("parking_id", None)
        debt = self.request.data.get("debt", None)
        updated_at = self.request.data.get("updated_at", None)

        if not session_id or not parking_id or not debt or not updated_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'session_id', 'parking_id', 'debt' and 'updated_at' are required"
            return False

        if len(str(session_id)) > 128:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key length 'session_id' must not be more 128 ASCII symbols"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        try:
            float_debt = float(debt)
            if float_debt <= 0:
                raise TypeError()
        except (ValueError, TypeError):
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'debt' has invalid format. Must be positive decimal value"
            return False

        try:
            validate_unix_timestamp(updated_at, "updated_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        return True


class CompleteParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        parking_id = self.request.data.get("parking_id", None)
        debt = self.request.data.get("debt", None)
        completed_at = self.request.data.get("completed_at", None)

        if not session_id or not parking_id or not debt or not completed_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'session_id', 'parking_id', 'debt' and 'completed_at' are required"
            return False

        if len(str(session_id)) > 128:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key length 'session_id' must not be more 128 ASCII symbols"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        try:
            float_debt = float(debt)
            if float_debt <= 0:
                raise TypeError()
        except (ValueError, TypeError):
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'debt' has invalid format. Must be positive decimal value"
            return False

        try:
            validate_unix_timestamp(completed_at, "completed_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        return True


class CancelParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        if not session_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "session_id is required"
            return False
        return True


class UpdateListParkingSessionValidator(BaseValidator):
    def is_valid(self):
        parking_id = self.request.data.get("parking_id", None)
        sessions = self.request.data.get("sessions", None)

        if not parking_id or not sessions:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'parking_id' and 'sessions' are required"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        if type(sessions) != type([]):
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Session value must be list type"
            return False

        for index, session_dict in enumerate(sessions):
            session_id = session_dict.get("session_id", None)
            debt = session_dict.get("debt", None)
            updated_at = session_dict.get("updated_at", None)

            if not session_id or not debt or not updated_at:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = "Items of session element %s must have 'session_id', 'debt' and 'updated_at' keys" % index
                return False

            try:
                float_debt = float(debt)
                if float_debt <= 0:
                    raise TypeError()
            except (ValueError, TypeError):
                self.code = ValidationException.VALIDATION_ERROR
                self.message = "Key 'debt' in session item %s has invalid format. Must be positive decimal value" % index
                return False

            try:
                validate_unix_timestamp(updated_at, "updated_at")
            except ValidationError as e:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = str(e.message)+"Item %s" % index
                return False
        return True