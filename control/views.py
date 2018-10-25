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
from base.views import generic_login_required_view
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

LoginRequiredAPIView = generic_login_required_view(Account)

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
        phone = clear_phone(request.data.get("phone", None))
        password = request.data.get('password', None)
        if not all((phone, password)):
            e = ValidationException(ValidationException.VALIDATION_ERROR,
                                    'phone and password are required')
            return JsonResponse(e.to_dict(), status=400)
        if Account.objects.filter(phone=phone).exists():
            account = Account.objects.get(phone=phone)
            if account.check_password(password):
                account.login()
                session = account.get_session()
            else:
                e = AuthException(
                    AuthException.INVALID_PASSWORD,
                    "Invalid password"
                )
                return JsonResponse(e.to_dict(), status=400)
        else:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Account with such phone number doesn't exist"
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse(serializer(session, exclude_attr=("created_at",)))


class LogoutView(LoginRequiredAPIView):
    def post(self, request):
        request.admin.clean_session()
        return JsonResponse({}, status=200)


admin_objects = {
    'vendor': {
        'fields': {
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
        },
        'object': Vendor
    },
    'order': {
        'fields': {
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
        },
        'object': Order
    },
    'parkingsession': {
        'fields': {
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
        },
        'object': ParkingSession
    },
    'parking': {
        'object': Parking,
        'fields': {
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
    },
    'complain': {
        'object': ComplainSession,
        'fields': {
            'type': IntChoicesField(choices=ComplainSession.COMPLAIN_TYPE_CHOICES, required=True),
            'message': StringField(required=True, max_length=1023),
            'session': ForeignField(object=ParkingSession, required=True),
            'account': ForeignField(object=UserAccount, required=True),
        }
    },
    'issue': {
        'object': Issue,
        'fields': {
            'name': StringField(required=True, max_length=255),
            'email': StringField(max_length=255),
            'phone': StringField(required=True, max_length=13),
            'comment': StringField(required=True, max_length=1023),
            'created_at': DateField()
        },
        'actions': {
            'accept': lambda issue: {'owner_id': issue.accept().id}
        }
    }
}


class ObjectView(LoginRequiredAPIView):

    def put(self, request, name, id=None):
        try:
            if id is None:
                e = ValidationException(ValidationException.VALIDATION_ERROR, 'Specify ID to PUT object')
                return JsonResponse(e.to_dict(), 405)
            self.validator_class = create_generic_validator(admin_objects[name]['fields'])
            self.validate_request(request)
            return edit_object_view(request=request, id=id,
                                    object=admin_objects[name]['object'],
                                    fields=admin_objects[name]['fields'],
                                    create=False, edit=True)
        except LookupError:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                'Admin object `%s` was not found' % name)
            return JsonResponse(e.to_dict(), 404)

    def post(self, request, name, id=None):
        try:
            self.validator_class = create_generic_validator(admin_objects[name]['fields'])
            self.validate_request(request)
            return edit_object_view(request=request, id=id if id else -1,
                                    object=admin_objects[name]['object'],
                                    fields=admin_objects[name]['fields'],
                                    create=True, edit=False)
        except LookupError:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                'Admin object `%s` was not found' % name)
            return JsonResponse(e.to_dict(), 404)

    def get(self, request, name, id=None):
        try:
            if id is None:
                pager = generic_pagination_view(admin_objects[name]['object'])
                return pager().get(request)
            else:
                try:
                    obj = admin_objects[name]['object'].objects.get(id=id)
                    return JsonResponse(serializer(obj))
                except ObjectDoesNotExist:
                    e = ValidationException(ValidationException.RESOURCE_NOT_FOUND, 'Object wasn\'t found')
                    return JsonResponse(e.to_dict(), status=404)

        except LookupError:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                'Admin object `%s` was not found' % name)
            return JsonResponse(e.to_dict(), 404)

    def delete(self, request, name, id=None):
        try:
            if id is None:
                e = ValidationException(ValidationException.VALIDATION_ERROR, 'Specify ID to DELETE object')
                return JsonResponse(e.to_dict(), 405)
            try:
                obj = admin_objects[name]['object'].objects.get(id=id)
            except ObjectDoesNotExist:
                e = ValidationException(ValidationException.RESOURCE_NOT_FOUND, 'Object with that ID wasn\'t found')
                return JsonResponse(e.to_dict(), status=404)
            obj.delete()
            return JsonResponse({}, status=200)
        except LookupError:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                'Admin object `%s` was not found' % name)
            return JsonResponse(e.to_dict(), 404)


class ObjectActionView(LoginRequiredAPIView):
    def post(self, request, name, id, action):
        try:
            obj = admin_objects[name]['object']
            action = admin_objects[name]['actions'][action]
        except LookupError:
            e = ValidationException(ValidationException.RESOURCE_NOT_FOUND,
                                    'Such object(%s) or action for this object(%s) was not found'
                                    % (name, action))
            return JsonResponse(e.to_dict(), 400)
        try:
            try:
                result = action(obj.objects.get(id=id))
            except ValidationException as e:
                return JsonResponse(e.to_dict(), status=400)
            return JsonResponse({'result': result}, status=200)
        except ObjectDoesNotExist:
            e = ValidationException(ValidationException.RESOURCE_NOT_FOUND,
                                    'Object with such ID was not found')
            return JsonResponse(e.to_dict(), status=404)


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
