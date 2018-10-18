import os
from datetime import datetime, timedelta
from wsgiref.util import FileWrapper

from django.core.exceptions import ObjectDoesNotExist
from django.http.response import JsonResponse, HttpResponse
from dss.Serializer import serializer

from accounts.models import Account as UserAccount
from accounts.validators import *
from base.exceptions import AuthException
from base.utils import IntField, ForeignField, FloatField, IntChoicesField, BoolField, DateField, StringField, \
    edit_object_view, PositiveFloatField, PositiveIntField, CustomValidatedField
from base.utils import clear_phone
from base.utils import datetime_from_unix_timestamp_tz
from base.utils import generic_pagination_view as pagination
from base.validators import LoginAndPasswordValidator
from base.validators import create_generic_validator
from base.views import APIView
from base.views import AdminAPIView as LoginRequiredAPIView
from owners.admin import accept_issue
from owners.models import Company
from owners.models import Issue
from owners.models import Owner
from parkings.models import Parking, ParkingSession, ComplainSession, UpgradeIssue
from parkings.validators import validate_longitude, validate_latitude
from parkpass.settings import PAGINATION_OBJECTS_PER_PAGE
from parkpass.settings import REQUESTS_LOG_FILE as LOG_FILE
from payments.models import Order, FiskalNotification
from vendors.models import Vendor
from .models import Admin as Account
from .models import AdminSession as AccountSession


def generic_pagination_view(x):
    return pagination(x, LoginRequiredAPIView)


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
                    account.login()
                    session = account.get_session()
                    return JsonResponse(serializer(session))
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
        phone = clear_phone(request.data["phone"])
        if Account.objects.filter(phone=phone).exists():
            account = Account.objects.get(phone=phone)
        else:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Administrator with that phone number was not found"
            )
            return JsonResponse(e.to_dict(), status=400)

        account.login()
        session = account.get_session()

        return JsonResponse(serializer(session, exclude_attr=("created_at",)), status=200)


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


class EditOrderView(LoginRequiredAPIView):
    fields = {
        'sum': PositiveFloatField(required=True),
        'payment_attempts': PositiveIntField(),
        'authorized': BoolField(),
        'paid': BoolField(),
        'paid_card_pan': StringField(),
        'session': ForeignField(object=ParkingSession),
        'refund_request': BoolField(),
        'refunded_sum': PositiveFloatField(),
        'fiskal_notification': ForeignField(object=FiskalNotification),
        'created_at': DateField(),
    }

    validator_class = create_generic_validator(fields)

    def post(self, request, id=-1):
        return edit_object_view(request=request, id=id, object=Order, fields=self.fields)


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
        'parkpass_enabled': BoolField(),
        'max_places': PositiveIntField(required=True),
        'free_places': PositiveIntField(),
        'max_client_debt': PositiveFloatField(),
        'created_at': DateField(),
        'vendor': ForeignField(object=Vendor),
        'company': ForeignField(object=Company),
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


class AcceptIssueView(LoginRequiredAPIView):
    def post(self, request, id):
        try:
            issue = Issue.objects.get(id=id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Issue with such id was not found"
            )
            return JsonResponse(e.to_dict(), status=400)
        try:
            owner = accept_issue(issue)
        except ValidationError:
            return JsonResponse({'error': 'Can\'t accept issue: ValidationError'}, status=400)
        return JsonResponse({'owner_id': owner.id})


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


class ShowOrderView(generic_pagination_view(Order)):
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


class GetLogView(LoginRequiredAPIView):
    def post(self, request):
        try:
            f = file(LOG_FILE, 'rb')
        except Exception, e:
            return JsonResponse({'error': 'Log not found'}, status=400)
        wrapper = FileWrapper(f)
        response = HttpResponse(wrapper)
        response['Content-Length'] = os.path.getsize(LOG_FILE)
        return response
