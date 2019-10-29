import os
from wsgiref.util import FileWrapper

from django.core.exceptions import ObjectDoesNotExist
from django.http.response import JsonResponse, HttpResponse
from django.utils import timezone
from dss.Serializer import serializer

from accounts.models import Account as UserAccount
from accounts.validators import *
from base.exceptions import AuthException
from base.utils import clear_phone
from base.utils import datetime_from_unix_timestamp_tz
from base.utils import generic_pagination_view as pagination
from base.validators import LoginAndPasswordValidator
from base.views import APIView, ObjectView
from base.views import generic_login_required_view
from owners.models import Owner, Company, OwnerApplication, OwnerIssue
from parkings.models import Parking, ParkingSession, ComplainSession
from parkpass_backend.settings import LOG_DIR
from parkpass_backend.settings import PAGINATION_OBJECTS_PER_PAGE
from payments.models import Order
from vendors.models import Vendor, VendorIssue
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


def generic_object_view(model):
    class GenericObjectView(LoginRequiredAPIView, ObjectView):
        object = admin_objects[model]['object']
        show_fields = admin_objects[model].get('show_fields', None)
        hide_fields = admin_objects[model].get('hide_fields', None)
        readonly_fields = admin_objects[model].get('readonly_fields', None)

    return GenericObjectView


admin_objects = {
    'vendor': {
        'object': Vendor,
        'readonly_fields': ('secret',)
    },
    'vendorissue': {
        'object': VendorIssue,
        'actions': {
            'accept': lambda issue: {'vendor_id': issue.accept().id}
        }
    },
    'order': {
        'object': Order,
    },
    'parkingsession': {
        'object': ParkingSession,
        'readonly_fields': ('id', 'session_id', 'client', 'parking', 'debt', 'state', 'started_at', 'updated_at',
                            'completed_at', 'suspended_at', 'try_refund', 'target_refund_sum',
                            'current_refund_sum', 'created_at',)
    },
    'parking': {
        'object': Parking,
    },
    'complain': {
        'object': ComplainSession,
    },
    'ownerissue': {
        'object': OwnerIssue,
        'actions': {
            'accept': lambda issue: {'owner_id': issue.accept().id}
        }
    },
    'account': {
        'object': UserAccount,
        'actions': {
            'make_hashed_password': lambda a: {'result': 'stub' if a.make_hashed_password() else 'ok'}  # magic! ^.^
        }
    },
    'ownerapplication': {
        'object': OwnerApplication,
    },
    'owner': {
        'object': Owner
    },
    'company': {
        'object': Company
    }
}


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
                else timezone.now() - timezone.timedelta(days=31),
                started_at__lt=datetime_from_unix_timestamp_tz(stop_at) if stop_at > -1 else timezone.now(),
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


class GetLogView(LoginRequiredAPIView):
    def get(self, request, name=None):
        if not name:
            log_list = [i for i in os.walk(LOG_DIR)][0][2]
            return JsonResponse({'logs': log_list})
        else:
            try:
                fname = os.path.join(LOG_DIR, name)
                f = file(fname, 'rb')
            except Exception:
                return JsonResponse({'error': 'Log not found'}, status=404)
            wrapper = FileWrapper(f)
            response = HttpResponse(wrapper)
            response['Content-Length'] = os.path.getsize(fname)
            return response


class ListObjectsView(LoginRequiredAPIView):
    def get(self, request):
        return JsonResponse([i for i in admin_objects], status=200, safe=False)
