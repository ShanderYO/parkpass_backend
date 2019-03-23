# -*- coding: utf-8 -*-
from django.core.mail import send_mail
from django.db.models import Sum
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View

from accounts.sms_gateway import SMSGateway
from accounts.validators import *
from base.exceptions import AuthException
from base.models import EmailConfirmation
from base.utils import *
from base.validators import *
from base.validators import validate_phone_number
from base.views import APIView
from base.views import generic_login_required_view
from owners.validators import IssueValidator
from owners.models import OwnerApplication
from owners.validators import validate_inn, validate_kpp
from parkings.models import ParkingSession, Parking
from parkings.validators import validate_latitude, validate_longitude
from parkpass.settings import EMAIL_HOST_USER
from .models import Vendor
from .models import Vendor as Account
from .models import VendorSession as AccountSession

LoginRequiredAPIView = generic_login_required_view(Vendor)


class EditVendorView(LoginRequiredAPIView):
    fields = {
        'org_name': StringField(max_length=255, required=True),
        'inn': CustomValidatedField(callable=validate_inn, required=True),
        'bik': IntField(required=True),
        'kpp': CustomValidatedField(callable=validate_kpp, required=True),
        'legal_address': StringField(required=True, max_length=512),
        'actual_address': StringField(required=True, max_length=512),
        'email': CustomValidatedField(callable=validate_email, required=True),
        'phone': CustomValidatedField(callable=validate_phone_number, required=True),
        'checking_account': StringField(required=True, max_length=64),
        'checking_kpp': CustomValidatedField(callable=validate_kpp, required=True),
    }

    validator_class = create_generic_validator(fields)

    def post(self, request):
        return edit_object_view(request=request, id=request.vendor.id,
                                object=Vendor, fields=self.fields,
                                incl_attr=list(self.fields))


class ParkingStatisticsView(LoginRequiredAPIView):
    def post(self, request):
        try:
            id = int(request.data.get("pk", -1))
            start_from = int(request.data.get("start", -1))
            stop_at = int(request.data.get("end", -1))
            page = int(request.data.get("page", 0))
            count = int(request.data.get("count", 10))
        except ValueError:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "All fields must be int"
            )
            return JsonResponse(e.to_dict(), status=400)
        if id < 0 or stop_at < start_from:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "One or more required parameters isn't specified correctly"
            )
            return JsonResponse(e.to_dict(), status=400)
        try:
            parking = Parking.objects.get(id=id, vendor=request.vendor)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Target parking with such id not found"
            )
            return JsonResponse(e.to_dict(), status=400)
        stat = ParkingSession.objects.filter(
            parking=parking,
            started_at__gt=datetime_from_unix_timestamp_tz(start_from) if start_from > -1
            else timezone.now() - timezone.timedelta(days=31),
            started_at__lt=datetime_from_unix_timestamp_tz(stop_at) if stop_at > -1 else timezone.now()
        )
        lst = []
        length = len(stat)
        if len(stat) > count:
            stat = stat[page * count:(page + 1) * count]
        for ps in stat:
            lst.append(
                serializer(ps)
            )
        return JsonResponse({'sessions': lst, 'count': length})


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
            pks = Parking.objects.filter(id__in=ids, vendor=request.vendor)
        else:
            pks = Parking.objects.filter(vendor=request.vendor)

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


class IssueUpgradeView(LoginRequiredAPIView):

    def post(self, request):
        account = request.vendor
        description = request.data.get('description', None)
        type = request.data.get('issue_type', None)
        if type is None or description is None or not type.isdigit() or 0 > len(description) > 1000:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Both 'issue_type' and 'description fields are required, 'issue_type' must be int"
            )
            return JsonResponse(e.to_dict(), status=400)
        type = int(type)
        ui = OwnerApplication(
            vendor=account,
            description=description,
            type=type,
        )
        ui.save()
        return JsonResponse({}, status=200)


class ListUpgradeIssuesView(generic_pagination_view(OwnerApplication, LoginRequiredAPIView, filter_by_account=True)):
    pass


class ParkingsTopView(LoginRequiredAPIView):
    def post(self, request):
        count = request.data.get('count', 3)
        period = request.data.get('period', 'day')
        if period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)
        if period == 'day':
            td = timezone.timedelta(days=1)
        elif period == 'week':
            td = timezone.timedelta(days=7)
        else:
            td = timezone.timedelta(days=30)
        t = timezone.now() - td
        parkings = Parking.objects.filter(vendor=request.vendor)
        r = []
        for p in parkings:
            r.append({
                'id': p.id,
                'title': p.name,
                'address': p.address,
                'debt': ParkingSession.objects.filter(parking=p, completed_at__gt=t).aggregate(Sum('debt'))[
                    'debt__sum'],
            })
        r = sorted(r, key=lambda x: -x['debt'] if x['debt'] else 0)
        return JsonResponse({
            'top': r[:count + 1],
            'comission': request.vendor.comission,
            'sessions_count': len(r)
        }, status=200)


class ListParkingsView(generic_pagination_view(Parking, LoginRequiredAPIView, filter_by_account=True)):
    pass


class ParkingView(LoginRequiredAPIView):
    fields = {
        'name': StringField(max_length=63, required=True),
        'address': StringField(max_length=63, required=True),
        'max_places': PositiveIntField(required=True),
        'tz_name': StringField(max_length=63, required=True),
    }
    validator_class = create_generic_validator(fields)

    def post(self, request, id):

        if id < 0:
            e = ValidationException(ValidationException.RESOURCE_NOT_FOUND)
            return JsonResponse(e.to_dict(), status=400)
        return edit_object_view(request, id, Parking, self.fields, req_attr={'vendor': request.vendor},
                                incl_attr=['name', 'address', 'created_at', 'parkpass_enabled', 'tz_name',
                                                                            'max_places', 'company__name',
                                           'software_updated_at', ])


class CreateParkingView(LoginRequiredAPIView):
    fields = {
        'name': StringField(max_length=63, required=True),
        'address': StringField(max_length=63, required=True),
        'description': StringField(max_length=1000),
        'latitude': CustomValidatedField(callable=validate_latitude, required=True),
        'longitude': CustomValidatedField(callable=validate_longitude, required=True),
        'tz_name': StringField(max_length=63, required=True),
        'enabled': BoolField(),
        'max_client_debt': PositiveIntField(),
        'max_places': PositiveIntField(required=True)
    }
    validator_class = create_generic_validator(fields)

    def post(self, request):
        return edit_object_view(request, -1, Parking, self.fields, incl_attr=list(self.fields) + ['id'],
                                req_attr={'vendor': request.vendor, 'approved': False})


class InfoView(LoginRequiredAPIView):

    def get(self, request):
        account = request.vendor

        response = {
            'vendor_name': account.name,
            'display_id': account.display_id,
            'secret_key': account.secret,
            'comission': account.comission
        }

        return JsonResponse(response, status=200)


class PasswordChangeView(LoginRequiredAPIView):

    def post(self, request):
        old_password = request.data["old"]
        new_password = request.data["new"]

        account = request.vendor

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
                if AccountSession.objects.filter(vendor=account).exists():
                    session = AccountSession.objects.filter(vendor=account).order_by('-created_at')[0]
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
                "Vendor with such login not found")
            return JsonResponse(e.to_dict(), status=400)


class IssueView(APIView):
    validator_class = IssueValidator

    def post(self, request):
        name = request.data.get("name", "")
        phone = request.data.get("phone", "")
        email = request.data.get("email", "")
        issue = Issue(
            name=name,
            phone=phone,
            email=email
        )
        issue.save()
        text = u"Ваша заявка принята в обработку. С Вами свяжутся в ближайшее время."
        if phone:
            sms_gateway = SMSGateway()
            sms_gateway.send_sms(phone, text, message='')
        if email:
            msg_html = render_to_string('emails/issue_accepted.html',
                                        {'number': str(issue.id)})
            send_mail('Заявка в систему Parkpass принята', "", EMAIL_HOST_USER,
                      ['%s' % str(email)], html_message=msg_html)
        return JsonResponse({}, status=200)


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
            account.create_password_and_send()
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
                if AccountSession.objects.filter(vendor=account).exists():
                    session = AccountSession.objects.filter(vendor=account).order_by('-created_at')[0]
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
                "User with such email not found")
            return JsonResponse(e.to_dict(), status=400)


class LogoutView(LoginRequiredAPIView):
    def post(self, request):
        request.vendor.clean_session()
        return JsonResponse({}, status=200)


class ChangeEmailView(LoginRequiredAPIView):
    validator_class = EmailValidator

    def post(self, request):
        email = str(request.data["email"])
        current_account = request.vendor
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
            email_confirmation = EmailConfirmation(email=email, account_type="vendor")

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


class TestView(LoginRequiredAPIView):
    def post(self, request):
        account = request.vendor
        parking = account.test_parking
        if parking is None:
            return JsonResponse(
                {
                    'error': 'There is no test parking assigned to your account. Please contact administrator.'
                }, status=400
            )
        try:
            sessions = ParkingSession.objects.filter(parking=parking)
            created_at = sessions.latest('created_at').created_at
            updated_at = sessions.latest('updated_at').updated_at
            updated_debt = sessions.latest('updated_at').debt
            completed_at = sessions.latest('completed_at').completed_at
        except ObjectDoesNotExist:
            return JsonResponse({
                'result': 'There is no parking sessions in test parking.'
            }, status=400)
        return JsonResponse({
            'result': {
                'last_started_at': '%s' % created_at,
                'last_updated_at': '%s' % updated_at,
                'last_completed_at': '%s' % completed_at,
                'last_updated_debt': updated_debt,
                'free_places': parking.free_places,
            }
        })
