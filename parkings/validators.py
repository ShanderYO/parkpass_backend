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


class UpdateParkingValidator(BaseValidator):
    def is_valid(self):
        parking_id = self.request.data.get("parking_id")
        free_places = self.request.data.get("free_places")

        if not parking_id or not free_places:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Parking id and free places are required"
            return False

        try:
            int(parking_id)
            int(free_places)

        except Exception:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Invalid format free_places. Int required"
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
            self.message = "Session id, parking id, client id and started at are required"
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
            self.message = "Session id, debt and updated at are required"
            return False
        try:
            float(debt)
            int(updated_at)

        except Exception:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Invalid format debt or updated_at. Debt float required, Updated at int required"
            return False

        # TODO add validation
        return True


class CompleteParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        debt = self.request.data.get("debt", None)
        completed_at = self.request.data.get("completed_at", None)

        if not session_id or not debt or not completed_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Session id, debt and completed at are required"
            return False
        try:
            float(debt)
            int(completed_at)

        except Exception:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Invalid format debt or completed_at. Debt float required, Completed at int required"
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


class UpdateListParkingSessionValidator(BaseValidator):
    def is_valid(self):
        sessions = self.request.data.get("sessions", None)
        if not sessions:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Sessions is required"
            return False
        # TODO check format bulk update
        return True