# -*- coding: utf-8 -*-

from base.exceptions import ValidationException
from base.validators import BaseValidator


class RegisterAccountDeviceValidator(BaseValidator):
    def is_valid(self):
        device_type = self.request.data.get("device_type", None)
        registration_id = self.request.data.get("registration_id", None)

        if not device_type or not registration_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'device_type' and 'registration_id' are required"
            return False

        if device_type not in ["web", "android", "ios"]:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'device_type' should be in web, android or ios"
            return False

        return True


class UnregisterAccountDeviceValidator(BaseValidator):
    def is_valid(self):
        registration_id = self.request.data.get("registration_id", None)

        if not registration_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'registration_id' is required"
            return False

        return True
