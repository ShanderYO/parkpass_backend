from django.core.exceptions import ObjectDoesNotExist
from django.http.response import JsonResponse
from dss.Serializer import serializer

from accounts.models import Account as UserAccount
from accounts.sms_gateway import SMSGateway
from accounts.validators import *
from base.exceptions import AuthException
from base.validators import LoginAndPasswordValidator
from base.views import APIView
from base.views import AdminAPIView as LoginRequiredAPIView
from owners.models import Owner
from parkings.models import Parking, ParkingSession
from validators import EditParkingValidator, EditParkingSessionValidator
from vendors.models import Vendor
from .models import Admin as Account
from .models import AdminSession as AccountSession
from .utils import IntField, ForeignField, FloatField, IntChoicesField, BoolField, DateField, StringField, \
    edit_object_view


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


class EditVendorView(LoginRequiredAPIView):
    def post(self, request, id=-1):
        fields = {
            'first_name': StringField(),
            'last_name': StringField(),
            'phone': StringField(required=True),
            'sms_code': StringField(),
            'email': StringField(),
            'password': StringField(),
            'email_confirmation': StringField(),
            'created_at': DateField(),
            'display_id': IntField(),
            'account_state': IntChoicesField(choices=Vendor.account_states),
            'name': StringField(required=True),
            'comission': FloatField(),
            'secret': StringField(),
            'test_parking': ForeignField(object=Parking),
            'test_user': ForeignField(object=UserAccount)
        }
        return edit_object_view(request=request, id=id, object=Vendor, fields=fields)


class EditParkingSessionView(LoginRequiredAPIView):
    validator_class = EditParkingSessionValidator

    def post(self, request, id=-1):
        fields = {
            'session_id': StringField(required=True),
            'client': ForeignField(object=UserAccount, required=True),
            'parking': ForeignField(object=Parking, required=True),
            'debt': FloatField(),
            'state': IntChoicesField(required=True, choices=ParkingSession.STATE_CHOICES),
            'started_at': DateField(required=True),
            'updated_at': DateField(),
            'completed_at': DateField(),
            'is_suspended': BoolField(),
            'suspended_at': DateField(),
            'try_refund': BoolField(),
            'target_refund_sum': FloatField(),
            'current_refund_sum': FloatField(),
            'created_at': DateField()
        }
        return edit_object_view(request=request, id=id, object=ParkingSession, fields=fields)


class EditParkingView(LoginRequiredAPIView):
    validator_class = EditParkingValidator

    def post(self, request, id=-1):
            fields = {
                'name': StringField(),
                'description': StringField(required=True),
                'address': StringField(),
                'latitude': FloatField(required=True),
                'longitude': FloatField(required=True),
                'enabled': BoolField(),
                'free_places': IntField(required=True),
                'max_client_debt': FloatField(),
                'created_at': DateField(),
                'vendor': ForeignField(object=Vendor),
                'owner': ForeignField(object=Owner),
                'approved': BoolField(),
            }
            return edit_object_view(request=request, id=id, object=Parking, fields=fields)
