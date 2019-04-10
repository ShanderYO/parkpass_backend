# -*- coding: utf-8 -*-
import json

from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.timezone import timedelta
from django.views import View

from accounts.validators import *
from base.exceptions import AuthException, PermissionException
from base.models import EmailConfirmation
from base.utils import *
from base.validators import *
from base.views import APIView, ObjectView
from base.views import generic_login_required_view
from parkings.models import Parking, ParkingSession
from vendors.models import Vendor
from .models import OwnerApplication
from .models import Owner as Account
from .models import OwnerSession as AccountSession
from .models import Company
from .validators import ConnectIssueValidator, TariffValidator


LoginRequiredAPIView = generic_login_required_view(Account)


class AccountInfoView(LoginRequiredAPIView):
    def get(self, request):
        account_dict = serializer(request.owner, exclude_attr=("name", "created_at", "sms_code", "password"))
        parkings = Parking.objects.filter(company__owner=request.owner)
        en_parkings = parkings.filter(parkpass_status=Parking.CONNECTED)
        account_dict['parkings_total'] = len(parkings)
        account_dict['parkings_enabled'] = len(en_parkings)
        return JsonResponse(account_dict, status=200)

    def put(self, request):
        fname = request.data.get('first_name', None)
        lname = request.data.get('last_name', None)
        if fname is not None:
            request.owner.first_name = fname
        if lname is not None:
            request.owner.last_name = lname
        try:
            request.owner.full_clean()
        except ValidationError as e:
            raise ValidationException(ValidationException.VALIDATION_ERROR, e.message_dict)
        request.owner.save()
        return JsonResponse({}, status=200)


class ParkingStatisticsView(LoginRequiredAPIView):
    def get(self, request):
        period = request.GET.get('period', None)
        parking_id = request.GET.get('parking_id',"0").encode('utf-8')

        from_date = parse_int(request.GET.get("from_date", None))
        to_date = parse_int(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None
        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        sessions = ParkingSession.objects.filter(
            parking__owner=request.owner
        )

        if td:
            t = timezone.now() - td
            sessions = sessions.filter(started_at__gt=t)

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            sessions = sessions.filter(
                started_at__gt=from_date_datetime,
                started_at__lt=to_date_datetime
            )
        else:
            pass

        if parking_id:
            id = parse_int(parking_id)
            if id:
                sessions = sessions.filter(parking__id=id)

        count = sessions.count()
        debt = sessions.aggregate(Sum('debt'))['debt__sum']
        seen = set()
        users = 0
        for s in sessions:
            if s.client not in seen:
                seen.add(s.client)
                users += 1

        return JsonResponse({
            'sessions': count,
            'income': debt if debt else 0,
            'users': users
        }, status=200)


class SessionsView(LoginRequiredAPIView): #, ObjectView):
    """
    object = ParkingSession
    account_filter = 'parking__owner'
    hide_fields = ('try_refund', 'current_refund_sum', 'target_refund_sum')
    foreign_field = [('parking', ('id', 'name',))]

    methods = ('GET',)
    """

    def get(self, request, **kwargs):
        page = parse_int(request.GET.get('page', 0))
        period = request.GET.get('period', None)

        from_date = parse_int(request.GET.get("from_date", None))
        to_date = parse_int(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        qs = ParkingSession.objects.filter(
            parking__owner=request.owner
        )

        if td:
            t = timezone.now() - td
            qs = qs.filter(created_at__gt=t)

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            qs = qs.filter(
                created_at__gt=from_date_datetime,
                created_at__lt=to_date_datetime
            )
        else:
            pass

        result_list = []
        if page != 0:
            qs = qs.filter(id__lt=page).order_by('-id')[:10]
        else:
            qs = qs.filter().order_by('-id')[:10]

        for session in qs:
            parking_dict = serializer(session.parking, include_attr=('id', 'name',))
            session_dict = serializer(session,
                                      exclude_attr=('parking_id', 'try_refund',
                                                    'current_refund_sum', 'target_refund_sum'))
            session_dict["parking"] = parking_dict
            result_list.append(session_dict)

        response_dict = {
            "result": result_list,
            "next": result_list[len(result_list) - 1]["id"] if len(result_list) > 0 else None
        }

        return JsonResponse(response_dict)


class ParkingSessionsView(LoginRequiredAPIView):
    def get(self, request, **kwargs):
        parking_id = kwargs.get('id', "0").encode('utf-8')
        page = parse_int(request.GET.get('page', 0))
        period = request.GET.get('period', None)

        from_date = parse_int(request.GET.get("from_date", None))
        to_date = parse_int(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        qs = ParkingSession.objects.filter(
            parking__id=parking_id,
            parking__owner=request.owner
        )

        if td:
            t = timezone.now() - td
            qs = qs.filter(created_at__gt=t)

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            qs = qs.filter(
                created_at__gt=from_date_datetime,
                created_at__lt=to_date_datetime
            )
        else:
            pass

        result_list = []
        if page != 0:
            qs = qs.filter(id__lt=page).order_by('-id')[:10]
        else:
            qs = qs.filter().order_by('-id')[:10]

        for session in qs:
            parking_dict = serializer(session.parking, include_attr=('id', 'name',))
            session_dict = serializer(session, exclude_attr=('parking_id', 'try_refund', 'current_refund_sum', 'target_refund_sum'))
            session_dict["parking"] = parking_dict
            result_list.append(session_dict)

        response_dict = {
            "result":result_list,
            "next":result_list[len(result_list) - 1]["id"] if len(result_list) > 0 else None
        }

        return JsonResponse(response_dict)


class ParkingsTopView(LoginRequiredAPIView):
    def get(self, request):
        count = parse_int(request.GET.get('count', [3])[0])
        period = request.GET.get('period', None)

        from_date = parse_int(request.GET.get("from_date", None))
        to_date = parse_int(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        page = parse_int(request.GET.get('page', None))
        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        sessions = ParkingSession.objects.filter(
            parking__owner=request.owner
        )

        if td:
            t = timezone.now() - td
            sessions = sessions.filter(started_at__gt=t)

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            sessions = sessions.filter(
                started_at__gt=from_date_datetime,
                started_at__lt=to_date_datetime
            )
        else:
            pass

        parkings = Parking.objects.filter(owner=request.owner)

        r = []

        for p in parkings:
            r.append({
                'id': p.id,
                'name': p.name,
                'address': p.address,
                'city': p.city,
                'income': sessions.filter(parking=p).aggregate(Sum('debt'))[
                    'debt__sum'],
            })
        r = sorted(r, key=lambda x: -x['income'] if x['income'] else 0)
        if page is None:
            page=0

        response_dict = {
            "result": r[page*count:(page+1)*count],
        }

        if not len(r) <= (page + 1) * count:
            response_dict["next"] = page + 1
        else:
            response_dict["next"] = None

        return JsonResponse(response_dict, status=200, safe=False)


class ApplicationsView(LoginRequiredAPIView, ObjectView):
    object = OwnerApplication
    author_field = 'owner'
    show_fields = ('description', 'type')
    account_filter = 'owner'


class CompanyView(LoginRequiredAPIView, ObjectView):
    object = Company
    show_fields = ('id', 'name', 'inn', 'kpp', 'bic', 'legal_address',
                   'actual_address', 'email', 'phone', 'account',
                   'use_profile_contacts', 'bank')

    account_filter = 'owner'

    def set_owner_and_validate(self, request, obj):
        obj.owner = request.owner
        if not obj.use_profile_contacts:
            if not all((obj.email, obj.phone)):
                raise ValidationException(ValidationException.VALIDATION_ERROR,
                                          {'use_profile_contacts': ['If this field is False, '
                                                                    'email and phone'
                                                                    ' is required.']})

    def serialize_list(self, qs):
        result, page = super(CompanyView, self).serialize_list(qs)
        # TODO improve it
        for obj_dict in result:
            parkings = Parking.objects.filter(company__id=obj_dict['id'])
            serialized = serializer(parkings, include_attr=('id', 'name', 'address', 'city', 'parkpass_status'))
            obj_dict["parkings"] = serialized
        return result, page

    def serialize_obj(self, obj):
        result_dict = super(CompanyView, self).serialize_obj(obj)
        parkings = Parking.objects.filter(company__id=result_dict['id'])
        serialized = serializer(parkings, include_attr=('id', 'name', 'address', 'city', 'parkpass_status'))
        result_dict["parkings"] = serialized
        return result_dict

    def on_create(self, request, obj):
        self.set_owner_and_validate(request, obj)

    def on_post_create(self, request, obj):
        return {'id': obj.id}

    def on_edit(self, request, obj):
        self.set_owner_and_validate(request, obj)

        if obj.get_parking_queryset():
            raise PermissionException(
                PermissionException.FORBIDDEN_CHANGING,
                "Company should have no parking for changing"
            )


class EventsView(LoginRequiredAPIView, ObjectView):
    object = OwnerApplication
    show_fields = ('owner_id', 'type', 'owner_id', 'parking_id', 'vendor_id', 'company_id', 'status', 'description', 'created_at', )
    account_filter = 'owner'


class TariffView(LoginRequiredAPIView):
    validator_class = TariffValidator

    def get(self, request, id):
        try:
            parking = Parking.objects.get(id=id)
        except ObjectDoesNotExist:
            e = ValidationException.RESOURCE_NOT_FOUND
            return JsonResponse(e.to_dict(), status=400)

        response = {
            "file_name":parking.tariff_file_name,
            "file_content":parking.tariff_file_content
        }
        return JsonResponse(response, status=200)

    def post(self, request, id):
        try:
            parking = Parking.objects.get(id=id)
        except ObjectDoesNotExist:
            e = ValidationException.RESOURCE_NOT_FOUND
            return JsonResponse(e.to_dict(), status=400)

        parking.tariff_file_name = request.data["file_name"]
        parking.tariff_file_content = request.data["file_content"]
        parking.save()
        return JsonResponse({}, status=200)


class ConnectParkingView(LoginRequiredAPIView):
    validator_class = ConnectIssueValidator

    def post(self, request):
        parking_id = self.request.data['parking_id']
        vendor_id = self.request.data['vendor_id']
        company_id = self.request.data['company_id']
        contact_email = self.request.data.get("contact_email")
        contact_phone = self.request.data.get("contact_phone")

        try:
            parking = Parking.objects.get(id=parking_id, parkpass_status=Parking.DISCONNECTED)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Parking with such ID has already connecting or processing state'
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Vendor with such ID does not exist'
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            company = Company.objects.get(id=company_id, owner=request.owner)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Your company does not found'
            )
            return JsonResponse(e.to_dict(), status=400)

        OwnerApplication.objects.create(
            type=OwnerApplication.TYPE_CONNECT_PARKING,
            owner=self.request.owner,
            parking=parking,
            vendor=vendor,
            company=company,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )

        parking.vendor = vendor
        parking.company = company
        parking.parkpass_status = Parking.PENDING
        parking.save()

        return JsonResponse({}, status=200)


class ParkingsView(LoginRequiredAPIView, ObjectView):
    object = Parking
    account_filter = 'owner'
    foreign_field = [('company', ('id', 'name',)), ('vendor', ('id', 'name',))]
    readonly_fields = ()

    def on_create(self, request, obj):
        obj.owner = request.owner # add owner
        if not obj.latitude or not obj.longitude:
            raise ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Longitude and latitude are required"
            )

    def on_edit(self, request, obj):
        if obj.parkpass_status != Parking.DISCONNECTED:
            raise PermissionException(
                PermissionException.FORBIDDEN_CHANGING,
                "Parking should have DISCONNECTED state for changing"
            )

    def on_post_create(self, request, obj):
        return {'id': obj.id}


class VendorsView(LoginRequiredAPIView, ObjectView):
    object = Vendor
    methods = ('GET',)
    show_fields = ('id','name',)


class PasswordChangeView(LoginRequiredAPIView):

    def post(self, request):
        old_password = request.data["old"]
        new_password = request.data["new"]

        account = request.owner

        if not account.check_password(old_password):
            e = AuthException(
                AuthException.INVALID_PASSWORD,
                "Invalid old password"
            )
            return JsonResponse(e.to_dict(), status=400)
        account.set_password(new_password)
        return JsonResponse({}, status=200)


class LoginView(APIView):
    validator_class = LoginAndPasswordValidator

    def post(self, request):
        name = request.data["login"]
        password = request.data["password"]

        try:
            account = Account.objects.get(name=name)
            if account.check_password(raw_password=password):
                if AccountSession.objects.filter(owner=account).exists():
                    session = AccountSession.objects.filter(owner=account).order_by('-created_at')[0]
                    response_dict = serializer(session)
                    return JsonResponse(response_dict)
                else:
                    account.login()
                    session = account.get_session()
                    response_dict = serializer(session)
                    return JsonResponse(response_dict)
            else:
                e = AuthException(
                    AuthException.INVALID_PASSWORD,
                    "Invalid password"
                )
                return JsonResponse(e.to_dict(), status=400)

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "Owner with such login not found")
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


class PasswordRestoreView(APIView):
    validator_class = EmailValidator

    def post(self, request):
        email = request.data["email"].lower()

        try:
            account = Account.objects.get(email=email)
            account.create_password_and_send(is_recovery=True)
            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "User with such email not found"
            )
            return JsonResponse(e.to_dict(), status=400)


class LoginWithEmailView(APIView):
    validator_class = EmailAndPasswordValidator

    def post(self, request):
        raw_email = request.data["email"]
        password = request.data["password"]
        email = raw_email.lower()

        try:
            account = Account.objects.get(email=email)
            if account.check_password(raw_password=password):
                if AccountSession.objects.filter(owner=account).exists():
                    session = AccountSession.objects.filter(owner=account).order_by('-created_at')[0]
                    response_dict = serializer(session, exclude_attr=("created_at",))
                    return JsonResponse(response_dict)
                else:
                    account.login()
                    session = account.get_session()
                    return JsonResponse(serializer(session, exclude_attr=("created_at",)))
            else:
                e = AuthException(
                    AuthException.INVALID_PASSWORD,
                    "Invalid password"
                )
                return JsonResponse(e.to_dict(), status=400)

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "User with such email not found")
            return JsonResponse(e.to_dict(), status=400)


class LogoutView(LoginRequiredAPIView):
    def post(self, request):
        request.account.clean_session()
        return JsonResponse({}, status=200)


class ChangeEmailView(LoginRequiredAPIView):
    validator_class = EmailValidator

    def post(self, request):
        email = str(request.data["email"])
        current_account = request.owner
        email_confirmation = None

        # check already added email
        if current_account.email == email:
            e = ValidationException(
                ValidationException.ALREADY_EXISTS,
                "Such email is already binded to account"
            )
            return JsonResponse(e.to_dict(), status=400)

        # get if already exists
        email_confirmation_list = EmailConfirmation.objects.filter(email=email)
        if email_confirmation_list.exists():
            email_confirmation = email_confirmation_list[0]

        # create new confirmation
        if email_confirmation is None:
            email_confirmation = EmailConfirmation(email=email, account_type="owner")

        email_confirmation.create_code()
        email_confirmation.save()

        current_account.email_confirmation = email_confirmation
        current_account.save()

        email_confirmation.send_confirm_mail()
        return JsonResponse({}, status=200)


class EmailConfirmationView(View):
    def get(self, request, *args, **kwargs):
        confirmations = EmailConfirmation.objects.filter(code=kwargs["code"])
        if confirmations.exists():
            confirmation = confirmations[0]
            if confirmation.is_expired():
                return JsonResponse({"error": "Link is expired"}, status=200)
            else:
                try:
                    account = Account.objects.get(email_confirmation=confirmation)
                    account.email = confirmation.email
                    account.email_confirmation = None
                    account.save()
                    confirmation.delete()
                    account.create_password_and_send()
                    return JsonResponse({"message": "Email is activated successfully"})

                except ObjectDoesNotExist:
                    return JsonResponse({"error": "Invalid link. Account does not found"}, status=200)

        else:
            return JsonResponse({"error": "Invalid link"}, status=200)


class ZendeskJWTWidgetView(LoginRequiredAPIView):
    def get(self, request, *args, **kwargs):
        jwt_token = request.owner.get_or_create_jwt_for_zendesk_widget()
        return HttpResponse(jwt_token)