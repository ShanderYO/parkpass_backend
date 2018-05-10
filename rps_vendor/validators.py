from django.core.exceptions import ValidationError

from accounts.validators import validate_id, validate_unix_timestamp
from base.exceptions import ValidationException
from base.validators import BaseValidator


class RpsCreateParkingSessionValidator(BaseValidator):
    def is_valid(self):
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        parking_id = self.request.data.get("parking_id", None)

        if not parking_id or not client_id or not started_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'session_id', 'parking_id', 'client_id' and 'started_at' are required"
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


class RpsUpdateParkingSessionValidator(BaseValidator):
    def is_valid(self):
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        parking_id = self.request.data.get("parking_id", None)
        debt = self.request.data.get("debt", None)
        updated_at = self.request.data.get("updated_at", None)

        if not client_id or not started_at or not parking_id or not debt or not updated_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'client_id', 'started_at', 'parking_id', 'debt' and 'updated_at' are required"
            return False

        try:
            validate_id(client_id, "client_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
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
            validate_unix_timestamp(started_at, "started_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        try:
            validate_unix_timestamp(updated_at, "updated_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        return True


class RpsCancelParkingSessionValidator(BaseValidator):
    def is_valid(self):
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        parking_id = self.request.data.get("parking_id", None)

        if not parking_id or not client_id or not parking_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'parking_id', 'started_at' and 'client_id' are required"
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


class RpsCompleteParkingSessionValidator(BaseValidator):
    def is_valid(self):
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        parking_id = self.request.data.get("parking_id", None)
        debt = self.request.data.get("debt", None)
        completed_at = self.request.data.get("completed_at", None)

        if not client_id or not started_at or not parking_id or not debt or not completed_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'session_id', 'parking_id', 'debt' and 'completed_at' are required"
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
            float_debt = float(debt)
            if float_debt <= 0:
                raise TypeError()
        except (ValueError, TypeError):
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'debt' has invalid format. Must be positive decimal value"
            return False

        try:
            validate_unix_timestamp(started_at, "started_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        try:
            validate_unix_timestamp(completed_at, "completed_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        return True


class RpsUpdateListParkingSessionValidator(BaseValidator):
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
            client_id = session_dict.get("client_id", None)
            started_at = session_dict.get("started_at", None)
            debt = session_dict.get("debt", None)
            updated_at = session_dict.get("updated_at", None)

            if not client_id or not started_at or debt is None or not updated_at:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = "Items of session element %s must have 'client_id', 'started_at', 'debt' and 'updated_at' keys" % index
                return False

            try:
                validate_id(client_id, "client_id")
            except ValidationError as e:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = str(e.message) + "Item %s" % index
                return False

            try:
                float_debt = float(debt)
                if float_debt < 0:
                    raise TypeError()
            except (ValueError, TypeError):
                self.code = ValidationException.VALIDATION_ERROR
                self.message = "Key 'debt' in session item %s has invalid format. Must be positive or zero decimal value" % index
                return False

            try:
                validate_unix_timestamp(started_at, "started_at")
            except ValidationError as e:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = str(e.message) + "Item %s" % index
                return False

            try:
                validate_unix_timestamp(updated_at, "updated_at")
            except ValidationError as e:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = str(e.message)+"Item %s" % index
                return False
        return True