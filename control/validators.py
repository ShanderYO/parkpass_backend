from django.core.exceptions import ValidationError

from django.core.exceptions import ValidationError

from base.validators import BaseValidator, validate_boolean, validate_ufloat
from parkings.validators import validate_latitude, validate_longitude, validate_text, validate_uint

an = {'allow_none': True}


class A:
    def __init__(self, s):
        self.data = s.request.data

    def __getitem__(self, item):
        return self.data.get(item, None)


class EditParkingSessionValidator(BaseValidator):
    def is_valid(self):
        a = A(self)
        try:
            validate_text(a['session_id'], 'session_id', **an)
            validate_uint(a['client'], 'client', **an)
            validate_uint(a['parking'], 'parking', **an)
            validate_ufloat(a['debt'], 'debt', **an)
            validate_uint(a['state'], 'state', **an)
            validate_uint(a['started_at'], 'started_at', **an)
            validate_uint(a['updated_at'], 'updated_at', **an)
            validate_uint(a['completed_at'], 'completed_at', **an)
            validate_boolean(a['is_suspended'], **an)
            validate_uint(a['suspended_at'], 'suspended_at', **an)
            validate_boolean(a['try_refund'], **an)
            validate_ufloat(a['target_refund_sum'], 'target_refund_sum', **an)
            validate_ufloat(a['current_refund_sum'], 'current_refund_sum', **an)
            validate_uint(a['created_at'], 'created_at', **an)

        except ValidationError as e:
            self.code = e.code
            self.message = str(e.message)
            return False
        return True


class EditParkingValidator(BaseValidator):
    def is_valid(self):
        a = A(self)
        try:
            validate_boolean(a['delete'], **an)
            validate_latitude(a['latitude'], **an)
            validate_longitude(a['longitude'], **an)
            validate_text(a['name'], 'name', **an)
            validate_boolean(a['enabled'], **an)
            validate_boolean(a['approved'], **an)
            validate_text(a['description'], 'description', **an)
            validate_text(a['address'], 'address', **an)
            validate_uint(a['free_places'], 'free_places', **an)
            validate_uint(a['max_client_debt'], 'max_client_debt', **an)
            validate_uint(a['owner'], 'owner', **an)
            validate_uint(a['vendor'], 'vendor', **an)
            validate_uint(a['created_at'], 'created_at', **an)
        except ValidationError as e:
            self.code = e.code,
            self.message = str(e.message)
            return False
        return True
