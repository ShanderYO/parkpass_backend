from datetime import datetime, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.http.response import JsonResponse
from dss.Serializer import serializer

from accounts.models import Account as UserAccount
from accounts.sms_gateway import SMSGateway
from accounts.validators import *
from base.exceptions import AuthException
from base.utils import datetime_from_unix_timestamp_tz
from base.validators import LoginAndPasswordValidator
from base.views import APIView
from base.views import AdminAPIView as LoginRequiredAPIView
from owners.models import Owner
from parkings.models import Parking, ParkingSession, ComplainSession, UpgradeIssue
from parkings.validators import validate_longitude, validate_latitude
from parkpass.settings import PAGINATION_OBJECTS_PER_PAGE
from validators import create_generic_validator
from vendors.models import Vendor, Issue
from .models import Admin as Account
from .models import AdminSession as AccountSession
from .utils import IntField, ForeignField, FloatField, IntChoicesField, BoolField, DateField, StringField, \
    edit_object_view, PositiveFloatField, PositiveIntField, CustomValidatedField


def generic_pagination_view(obj):
    class GenericPaginationView(LoginRequiredAPIView):
        def post(self, request, page):
            filter = {}
            for key in request.data:
                try:
                    attr, modifier = key.split('__') if not hasattr(obj, key) else (key, 'eq')
                    if modifier not in ('eq', 'gt', 'lt', 'ne', 'ge', 'le', 'in') or not hasattr(obj, attr):
                        raise ValueError()
                    if type(True) == type(request.data[key]):
                        if modifier == 'eq':
                            filter[attr] = request.data[key]
                        elif modifier == 'ne':
                            filter[attr] = not request.data[key]
                        else:
                            raise ValueError()
                    else:
                        if modifier == 'eq':
                            filter[attr] = request.data[key]
                        else:
                            filter[attr + '__' + modifier] = request.data[key]
                except ValueError:
                    e = ValidationException(
                        ValidationException.VALIDATION_ERROR,
                        "Invalid filter format"
                    )
                    return JsonResponse(e.to_dict(), status=400)
            if filter:
                objects = obj.objects.filter(**filter)
            else:
                objects = obj.objects.all()
            page = int(page)
            result = []
            for o in objects:
                result.append(serializer(o))
            length = len(result)
            count = PAGINATION_OBJECTS_PER_PAGE
            if length > count:
                result = result[page * count:(page + 1) * count]
            return JsonResponse({'count': length, 'objects': result}, status=200)

    return GenericPaginationView


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

    validator_class = create_generic_validator(fields)

    def post(self, request, id=-1):
        return edit_object_view(request=request, id=id, object=Vendor, fields=self.fields)


class EditParkingSessionView(LoginRequiredAPIView):
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
    validator_class = create_generic_validator(fields)

    def post(self, request, id=-1):
        return edit_object_view(request=request, id=id, object=ParkingSession, fields=self.fields)


class EditParkingView(LoginRequiredAPIView):
    fields = {
        'name': StringField(),
        'description': StringField(required=True),
        'address': StringField(),
        'latitude': CustomValidatedField(validate_latitude, required=True),
        'longitude': CustomValidatedField(validate_longitude, required=True),
        'enabled': BoolField(),
        'free_places': PositiveIntField(required=True),
        'max_client_debt': PositiveFloatField(),
        'created_at': DateField(),
        'vendor': ForeignField(object=Vendor),
        'owner': ForeignField(object=Owner),
        'approved': BoolField(),
    }
    validator_class = create_generic_validator(fields)  # EditParkingValidator

    def post(self, request, id=-1):
        return edit_object_view(request=request, id=id, object=Parking, fields=self.fields)


class EditComplainView(LoginRequiredAPIView):
    fields = {
        'type': IntChoicesField(choices=None, required=True),
        'message': StringField(required=True, max_length=1023),
        'session': ForeignField(object=ParkingSession, required=True),
        'account': ForeignField(object=UserAccount, required=True),
    }
    validator_class = create_generic_validator(fields)

    def post(self, request, id=-1):
        return edit_object_view(request=request, id=id, object=ComplainSession, fields=self.fields)


class ShowComplainView(generic_pagination_view(ComplainSession)):
    pass


class ShowVendorView(generic_pagination_view(Vendor)):
    pass


class ShowParkingSessionView(generic_pagination_view(ParkingSession)):
    pass


class ShowParkingView(generic_pagination_view(Parking)):
    pass


class AllParkingsStatisticsView(LoginRequiredAPIView):
    def post(self, request):
        try:
            ids = map(int, request.data.get('ids', []).replace(' ', '').split(','))
            start_from = int(request.data.get("start", -1))
            stop_at = int(request.data.get("end", -1))
            page = int(request.data.get("page", 0))
            count = int(request.data.get("count", PAGINATION_OBJECTS_PER_PAGE))
        except ValueError:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "All fields must be int"
            )
            return JsonResponse(e.to_dict(), status=400)
        if stop_at < start_from:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "'stop' should be greater than 'start'"
            )
            return JsonResponse(e.to_dict(), status=400)
        result = []

        if ids:
            pks = Parking.objects.filter(id__in=ids)
        else:
            pks = Parking.objects.all()

        for pk in pks:
            ps = ParkingSession.objects.filter(
                parking=pk,
                started_at__gt=datetime_from_unix_timestamp_tz(start_from) if start_from > -1
                else datetime.now() - timedelta(days=31),
                started_at__lt=datetime_from_unix_timestamp_tz(stop_at) if stop_at > -1 else datetime.now(),
                state__gt=3  # Only completed sessions
            )

            sessions_count = len(ps)
            order_sum = 0
            avg_time = 0
            for session in ps:
                order_sum += session.debt
                avg_time += (session.completed_at - session.started_at).total_seconds()
            try:
                avg_time = avg_time / sessions_count
            except ZeroDivisionError:
                pass

            result.append({
                'parking_id': pk.id,
                'parking_name': pk.name,
                'sessions_count': sessions_count,
                'avg_parking_time': avg_time,
                'order_sum': order_sum,
            })
        length = len(result)
        if len(result) > count:
            result = result[page * count:(page + 1) * count]
        return JsonResponse({'parkings': result, 'count': length}, status=200)


class ShowIssueView(generic_pagination_view(Issue)):
    pass


class EditIssueView(LoginRequiredAPIView):
    fields = {
        'name': StringField(required=True, max_length=255),
        'email': StringField(max_length=255),
        'phone': StringField(required=True, max_length=13),
        'comment': StringField(required=True, max_length=1023),
        'created_at': DateField()
    }
    validator_class = create_generic_validator(fields)

    def post(self, request, id=-1):
        return edit_object_view(request=request, id=id, object=Issue, fields=self.fields)


class ShowUpgradeIssueView(generic_pagination_view(UpgradeIssue)):
    pass


class EditUpgradeIssueView(LoginRequiredAPIView):
    fields = {
        'vendor': ForeignField(object=Vendor),
        'owner': ForeignField(object=Owner),
        'description': StringField(required=True, max_length=1000),
        'type': IntChoicesField(choices=UpgradeIssue.types, required=True),
        'issued_at': DateField(),
        'updated_at': DateField(),
        'completed_at': DateField(),
        'status': IntChoicesField(choices=UpgradeIssue.statuses)
    }
    validator_class = create_generic_validator(fields)

    def post(self, request, id=-1):
        return edit_object_view(request=request, id=id, object=UpgradeIssue, fields=self.fields)
