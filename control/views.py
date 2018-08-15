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
    def post(self, request, id=-1):
        r = {'raise_exception': True}
        s = str
        i = lambda x: parse_int(x, **r)
        b = lambda x: parse_bool(x, **r)
        f = lambda x: parse_float(x, **r)
        date = lambda x: datetime_from_unix_timestamp_tz(parse_int(x, **r))

        def vendor(v):
            if not v is None:
                return Vendor.objects.get(id=v)

        def owner(v):
            if not v is None:
                return Owner.objects.get(id=v)
        try:
            if id == -1:
                parking = Parking()
            else:
                parking = Parking.objects.get(id=id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with such ID not found"
            )
            return JsonResponse(e.to_dict(), status=400)
        try:
            delete = parse_bool(request.data.get("delete", None))
            if delete:
                parking.delete()
                return JsonResponse({}, status=200)
            fields = {
                'name': (s,),
                'description': (s, 'required'),
                'address': (s,),
                'latitude': (f, 'required'),
                'longitude': (f, 'required'),
                'enabled': (b,),
                'free_places': (i, 'required'),
                'max_client_debt': (f,),
                'created_at': (date,),
                'vendor': (vendor,),
                'owner': (owner,),
                'approved': (b,),
            }
            for field in fields:
                val = fields[field][0](request.data.get(field, None))
                if not val is None:
                    parking.__setattr__(field, val)
                elif len(fields[field]) > 1 and id == -1:  # If field is required and action == create
                    e = ValidationException(
                        ValidationException.VALIDATION_ERROR,
                        'Field `%s` is required' % field
                    )
                    return JsonResponse(e.to_dict(), status=400)

        except Exception as exc:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                str(exc)
            )
            return JsonResponse(e.to_dict(), status=400)
        parking.save()

        return JsonResponse(serializer(parking), status=200)
