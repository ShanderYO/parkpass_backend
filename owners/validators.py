# -*- coding: utf-8 -*-
import json
import re

from django.core.exceptions import ValidationError, ObjectDoesNotExist

from accounts.validators import validate_email_format, validate_id
from base.exceptions import ValidationException
from base.validators import BaseValidator, validate_phone_number
from parkings.validators import validate_tariff
from rps_vendor.models import ParkingCard


def validate_inn(value):
    if not len(value) in (10, 12) or not value.isdigit():
        raise ValidationError("INN must be 12 or 10 digits long and contain only digits")


def validate_kpp(value):
    if not len(value) == 9 or not value.isdigit():
        raise ValidationError("KPP must be 9 digits long")


def validate_name(value):
    regex = r'^[A-Za-zА-Яа-яЁё ]{2,255}$'
    if not re.match(regex, value):
        raise ValidationError("Name has invalid format. Please use only letters. Also, length must be <= 255 letters.")


class IssueValidator(BaseValidator):
    def is_valid(self):
        name = self.request.data.get("name", None)
        phone = self.request.data.get("phone", None)
        email = self.request.data.get("email", None)
        if not name or not phone:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Phone and name is required"
            return False
        try:
            validate_name(name)
            if email:
                validate_email_format(email)
            if phone:
                validate_phone_number(phone)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False
        return True


class TariffValidator(BaseValidator):
    def is_valid(self):
        file_name = self.request.data.get("file_name")
        file_content = self.request.data.get("file_content")
        if not file_name or not file_content:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys file_name and file_content are required"
            return False
        return True


class ConnectIssueValidator(BaseValidator):
    def is_valid(self):
        parking_id = self.request.data.get("parking_id", None)
        vendor_id = self.request.data.get("vendor_id", None)
        company_id = self.request.data.get("company_id", None)
        email = self.request.data.get("contact_email", None)
        phone = self.request.data.get("contact_phone", None)

        if not all([parking_id, vendor_id, company_id]):
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys parking_id, vendor_id, company_id are required"
            return False

        try:
            validate_id(parking_id, 'parking_id')
            validate_id(vendor_id, 'validate_id')
            validate_id(company_id, 'company_id')
            if phone:
                validate_phone_number(phone)
            if email:
                validate_email_format(email)

        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False
        return True


class ValetSessionsCreateFromLKValidator(BaseValidator):
    def is_valid(self):

        car_model = self.request.POST.get("car_model", None)
        car_number = self.request.POST.get("car_number", None)
        valet_card_id = self.request.POST.get("valet_card_id", None)
        responsible_id = self.request.POST.get("responsible_id", None)
        parking_id = self.request.POST.get("parking_id", None)
        started_at = self.request.POST.get("started_at", None)

        parking_card = self.request.POST.get("parking_card", None)

        if not parking_id or not car_model or not car_number or not valet_card_id or not responsible_id or not started_at :
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Required params are missing"
            return False

        # try:
        #     if parking_card:
        #         ParkingCard.objects.get(card_id=parking_card)
        # except ObjectDoesNotExist:
        #     self.code = ValidationException.VALIDATION_ERROR
        #     self.message = "Parking card does not exist"
        #     return False

        return True


class ValetSessionsUpdateFromLKValidator(BaseValidator):
    def is_valid(self):
        id = self.request.POST.get("id", None)
        car_model = self.request.POST.get("car_model", None)
        car_number = self.request.POST.get("car_number", None)
        valet_card_id = self.request.POST.get("valet_card_id", None)
        # responsible_for_reception_id = self.request.POST.get("responsible_for_reception_id", None)
        started_at = self.request.POST.get("started_at", None)

        parking_card = self.request.POST.get("parking_card", None)

        if  not id  :
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Required params are missing"
            return False

        # try:
        #     if parking_card:
        #         ParkingCard.objects.get(card_id=parking_card)
        # except ObjectDoesNotExist:
        #     self.code = ValidationException.VALIDATION_ERROR
        #     self.message = "Parking card does not exist"
        #     return False

        return True