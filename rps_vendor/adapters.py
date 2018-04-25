import re

from django.core.exceptions import ValidationError

from base.exceptions import ValidationException
from base.validators import BaseValidator
from parkings.validators import validate_id, validate_unix_timestamp


class RpsCreateParkingSessionAdapter(object):

    def __init__(self, request_dict):
        self.request_dict = request_dict

    def adapt(self):
        client_id = self.request_dict.get('client_id', None)
        parking_id = self.request_dict.get('parking_id', None)
        if client_id is None or parking_id is None:
            return None
        self.request_dict["session_id"] = str(parking_id)+"&"+str(client_id)
        return self.request_dict

