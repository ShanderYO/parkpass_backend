# -*- coding: utf-8 -*-

from base.exceptions import ValidationException
from base.validators import BaseValidator


class ValetSessionGetValidator(BaseValidator):
    def is_valid(self):
        id = self.request.data.get("id", None)
        date = self.request.data.get("date", None)
        if not id or not date:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "required params are missing"
            return False

        return True