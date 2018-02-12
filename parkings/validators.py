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


class CreateParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        parking_id = self.request.data.get("parking_id", None)
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        if not session_id or not parking_id or not client_id or not started_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Session id is required"
            return False

        # TODO add validation
        return True


class UpdateParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        debt = self.request.data.get("debt", None)
        updated_at = self.request.data.get("updated_at", None)

        if not session_id or not debt or not updated_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Session id is required"
            return False

        # TODO add validation
        return True


class CompleteParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        debt = self.request.data.get("debt", None)
        completed_at = self.request.data.get("updated_at", None)

        if not session_id or not debt or not completed_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Session id is required"
            return False

        # TODO add validation
        return True


class CancelParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        if not session_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Session id is required"
            return False

        # TODO add validation
        return True