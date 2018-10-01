import json
import re

from django.core.exceptions import ValidationError

from base.exceptions import ValidationException
from base.validators import BaseValidator, validate_uint


def validate_latitude(value, allow_none=False):
    # value is float
    if allow_none and value is None:
        return True
    regex = "^(\-)?(?:90(?:(?:\.0{1,7})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,7})?))$"
    if not re.match(regex, str(value)):
        raise ValidationError("Invalid latitude of geo position")
    return float(value)


def validate_longitude(value, allow_none=False):
    # value is float
    if allow_none and value is None:
        return True
    regex = "^(\-)?(?:180(?:(?:\.0{1,7})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,7})?))$"
    if not re.match(regex, str(value)):
        raise ValidationError("Invalid longitude of geo position")
    return float(value)


def validate_id(value, key_name, allow_none=False):
    if allow_none and value is None:
        return True
    try:
        int_value = int(value)
        if int_value < 0:
            raise ValidationError("Key '%s' requires positive value" % key_name)

        float_value = float(value)
        if int_value != float_value:
            raise ValidationError("Key '%s' has invalid format. Must be unsigned Int64 type" % key_name)

    except (ValueError, TypeError):
        raise ValidationError("Key '%s' has invalid format. Must be unsigned Int64 type" % key_name)


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


def validate_text(value, key, allow_none=False, length=500):
    if allow_none and value is None:
        return True
    try:
        str(value)
    except Exception:
        raise ValidationError("Key %s has invalid format. Must be a string" % key)
    if not length > len(value) > 1:
        raise ValidationError("Key %s has invalid format. Length must be between 1 and %s letters." % (key, length))


class CreateParkingValidator(BaseValidator):
    def is_valid(self):
        a = {
            'name': self.request.data.get("name", None),
            'description': self.request.data.get("description", None),
            'address': self.request.data.get('address', None),
            'max_places': self.request.data.get('max_places', None),
            'latitude': self.request.data.get("latitude", None),
            'longitude': self.request.data.get("longitude", None),
            'max_client_debt': self.request.data.get("max_client_debt", None),
        }
        for i in a:
            if a[i] is None:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = '"%s" is required field' % i
                return False
        try:
            validate_latitude(a['latitude'])
            validate_longitude(a['longitude'])
            validate_text(a['name'], 'name')
            validate_text(a['description'], 'description')
            validate_text(a['address'], 'address')
            validate_uint(a['max_places'], 'max_places')
            validate_uint(a['max_client_debt'], 'max_client_debt')
        except ValidationError as e:
            self.code = e.code,
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
            validate_uint(started_at, "started_at")
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
            validate_uint(updated_at, "updated_at")
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
            validate_uint(completed_at, "completed_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        return True


class CancelParkingSessionValidator(BaseValidator):
    def is_valid(self):
        session_id = self.request.data.get("session_id", None)
        parking_id = self.request.data.get("parking_id", None)
        if not session_id or not parking_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'session_id' and 'parking_id' is required"
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
                validate_uint(updated_at, "updated_at")
            except ValidationError as e:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = str(e.message)+"Item %s" % index
                return False
        return True


class ComplainSessionValidator(BaseValidator):
    def is_valid(self):
        complain_type = self.request.data.get("type", 0)
        message = self.request.data.get("message", None)
        session_id = self.request.data.get("session_id", 0)

        if not complain_type or not message or not session_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'type', 'session_id' and 'message' are required"
            return False

        try:
            validate_id(session_id, "session_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        # TODO add type list validator and message requirements lenght

        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False

        return True


def validate_tariff(tariff):
    days = []
    try:
        j = json.loads(tariff)
    except ValueError:
        raise ValidationError("Not a valid JSON object")
    tariff = j.get('tariff', None)
    if not isinstance(tariff, list):
        raise ValidationError('Field "tariff" should have "list" type, not %s' % str(type(tariff))[6:-1])
    for i in tariff:
        if not isinstance(i, dict):
            raise ValidationError('Elements of field "tariff" should have "dict" type, not %s' % str(type(i))[6:-1])
        dayList = i.get('dayList', None)
        periodList = i.get('periodList', None)
        if not all((isinstance(dayList, list), isinstance(periodList, list))):
            raise ValidationError('Child elements of "tariff" elements should have "list" type')
        for day in dayList:
            if not isinstance(day, int):
                raise ValidationError('Elements of field "dayList" should have "int" type, not %s'
                                      % str(type(day))[6:-1])
            if day in days:
                raise ValidationError('Day numbers should not be repeating in tariff')
            if day not in range(7):
                raise ValidationError('Day numbers should be in 0..6 range')
            days += [day]
        for period in periodList:
            time_start = period.get('time_start', None)
            time_end = period.get('time_end', None)
            description = period.get('description', None)
            if not all((isinstance(time_start, int), isinstance(time_end, int), isinstance(description, unicode))):
                raise ValidationError('"time_start" and "time_end" should have type "int", "description" - "str"')
            if not time_start < time_end:
                raise ValidationError('"time_start" should be less than "time_end"')
            if any((time_start < 0, time_end < 0, time_start > 60 * 60 * 24, time_end > 60 * 60 * 24)):
                raise ValidationError('Time fields should be in range 0..60*60*24')
    if not [i for i in range(7)] == sorted(days):
        raise ValidationError("Tariff should contain description for all days of week([0, 1, 2, 3, 4, 5, 6])")
