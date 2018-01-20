from django.shortcuts import render

# Create your views here.
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from dss.Serializer import serializer

from accounts.models import Account
from accounts.validators import LoginParamValidator
from base.exceptions import ValidationException
from base.views import APIView, LoginRequiredAPIView
from payments.models import CreditCard
from payments.validators import CreditCardParamValidator


class AddCardView(LoginRequiredAPIView):
    validator_class = CreditCardParamValidator

    def post(self, request):
        number = "00000000"
        if CreditCard.exists(number):
            e = ValidationException(ValidationException.ALREADY_EXISTS, "Card with such number alredy exists")
            return JsonResponse(e.to_dict(), status=400)
        credit_card = CreditCard(account=request.account)
        credit_card.save()
        return JsonResponse({}, status=200)


class DeleteCardView(LoginRequiredAPIView):
    def post(self, request):
        card_id = request.data.get("id", 0)
        try:
            card = CreditCard.objects.get(id=card_id, account=request.account)
            card.delete()
        except ObjectDoesNotExist:
            e = ValidationException(ValidationException.RESOURCE_NOT_FOUND, "Your card with such id is not found")
            return JsonResponse(e.to_dict(), status=400)
        return JsonResponse({}, status=200)


class SetDefaultCardView(LoginRequiredAPIView):
    def post(self, request):
        card_id = request.data.get("id", 0)
        try:
            card = CreditCard.objects.get(id=card_id, account=request.account)
            card.is_default = True
            card.save()
        except ObjectDoesNotExist:
            e = ValidationException(ValidationException.RESOURCE_NOT_FOUND, "Your card with such id is not found")
            return JsonResponse(e.to_dict(), status=400)
        return JsonResponse({}, status=200)


"""
import re
import datetime

from django.core.exceptions import ValidationError

from base.exceptions import ValidationException
from django.core.validators import validate_email, BaseValidator

class CreditCardParamValidator(BaseValidator):
    def is_valid(self):
        card_number = self.request.data.get("card_number", None)
        card_owner = self.request.data.get("card_owner", None)
        expiry_date = self.request.data.get("expiry_date", None)
        card_code = self.request.data.get("card_code", None)

        name_on_card = forms.CharField(max_length=50, required=True)
        card_number = CreditCardField(required=True)
        expiry_date = ExpiryDateField(required=True)
        card_code = VerificationValueField(required=True)


        if not phone:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Phone is required"
            return False
        try:
            validate_phone_number(phone)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True
"""
