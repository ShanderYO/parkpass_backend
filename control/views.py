from django.core.exceptions import ObjectDoesNotExist
from django.http.response import JsonResponse
from dss.Serializer import serializer

from accounts.sms_gateway import SMSGateway
from accounts.validators import *
from base.exceptions import AuthException
from base.utils import parse_bool, parse_float, parse_int, datetime_from_unix_timestamp_tz
from base.validators import LoginAndPasswordValidator
from base.views import APIView
from base.views import AdminAPIView as LoginRequiredAPIView
from owners.models import Owner
from parkings.models import Parking
from vendors.models import Vendor
from .models import Admin as Account
from .models import AdminSession as AccountSession


class LoginView(APIView):
    validator_class = LoginAndPasswordValidator

    def post(self, request):
        name = request.data["login"]
        password = request.data["password"]

        try:
            account = Account.objects.get(name=name)
            if account.check_password(raw_password=password):
                if AccountSession.objects.filter(admin=account).exists():
                    session = AccountSession.objects.filter(admin=account).order_by('-created_at')[0]
                    response_dict = serializer(session)
                    return JsonResponse(response_dict)
                else:
                    e = AuthException(
                        AuthException.INVALID_SESSION,
                        "Invalid session. Login with phone required"
                    )
                    return JsonResponse(e.to_dict(), status=400)
            else:
                e = AuthException(
                    AuthException.INVALID_PASSWORD,
                    "Invalid password"
                )
                return JsonResponse(e.to_dict(), status=400)

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "Admin with such login not found")
            return JsonResponse(e.to_dict(), status=400)


class LoginWithPhoneView(APIView):
    validator_class = LoginParamValidator

    def post(self, request):
        phone = request.data["phone"]
        success_status = 200
        if Account.objects.filter(phone=phone).exists():
            account = Account.objects.get(phone=phone)
        else:
            account = Account(phone=phone)
            success_status = 201

        account.create_sms_code()
        account.save()

        # Send sms
        sms_gateway = SMSGateway()
        sms_gateway.send_sms(account.phone, account.sms_code)
        if sms_gateway.exception:
            return JsonResponse(sms_gateway.exception.to_dict(), status=400)

        return JsonResponse({}, status=success_status)


class ConfirmLoginView(APIView):
    validator_class = ConfirmLoginParamValidator

    def post(self, request):
        sms_code = request.data["sms_code"]
        try:
            account = Account.objects.get(sms_code=sms_code)
            account.login()
            session = account.get_session()
            return JsonResponse(serializer(session, exclude_attr=("created_at",)))

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "Account with pending sms-code not found")
            return JsonResponse(e.to_dict(), status=400)


class LogoutView(LoginRequiredAPIView):
    def post(self, request):
        request.admin.clean_session()
        return JsonResponse({}, status=200)


class EditParkingView(LoginRequiredAPIView):
    def post(self, request, id):
        r = {'raise_exception': True}
        try:
            parking = Parking.objects.get(id=id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with such ID not found"
            )
            return JsonResponse(e.to_dict(), status=400)
        try:
            name = request.data.get("name", None)
            if not name is None:
                parking.name = name
            description = request.data.get("description", None)
            if not description is None:
                parking.description = description
            address = request.data.get("address", None)
            if not address is None:
                parking.address = address
            latitude = parse_float(request.data.get("latitude", None), **r)
            if not latitude is None:
                parking.latitude = latitude
            longitude = parse_float(request.data.get("longitude", None), **r)
            if not longitude is None:
                parking.longitude = longitude
            enabled = parse_bool(request.data.get("enabled", None), **r)
            if not enabled is None:
                parking.enabled = enabled
            free_places = parse_int(request.data.get("free_places", None), **r)
            if not free_places is None:
                parking.free_places = free_places
            max_client_debt = parse_int(request.data.get("max_client_debt", None), **r)
            if not max_client_debt is None:
                parking.max_client_debt = max_client_debt
            vendor = parse_int(request.data.get("vendor", None), **r)
            if not vendor is None:
                try:
                    parking.vendor = Vendor.objects.get(id=vendor)
                except ObjectDoesNotExist:
                    e = ValidationException(
                        ValidationException.RESOURCE_NOT_FOUND,
                        'Vendor with such ID not found')
                    return JsonResponse(e.to_dict(), status=400)
            owner = parse_int(request.data.get("owner", None), **r)
            if not owner is None:
                try:
                    parking.owner = Owner.objects.get(id=owner)
                except ObjectDoesNotExist:
                    e = ValidationException(
                        ValidationException.RESOURCE_NOT_FOUND,
                        'Owner with such ID not found')
                    return JsonResponse(e.to_dict(), status=400)
            created_at = parse_int(request.data.get("created_at", None), **r)
            if not created_at is None:
                parking.created_at = datetime_from_unix_timestamp_tz(created_at)
            approved = parse_bool(request.data.get("approved", None), **r)
            if not approved is None:
                parking.approved = approved
        except ValueError as exc:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                str(exc)
            )
            return JsonResponse(e.to_dict(), status=400)
        parking.save()

        return JsonResponse(serializer(parking), status=200)
