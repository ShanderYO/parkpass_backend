# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from django.core.mail import send_mail
from django.db.models import Sum
from django.template.loader import render_to_string
from django.views import View

from accounts.sms_gateway import SMSGateway
from accounts.validators import *
from base.exceptions import AuthException
from base.models import EmailConfirmation
from base.utils import *
from base.validators import *
from base.views import APIView
from base.views import OwnerAPIView as LoginRequiredAPIView
from parkings.models import Parking, ParkingSession
from parkpass.settings import EMAIL_HOST_USER
from vendors.models import Vendor
from .models import Issue, ConnectIssue
from .models import Owner as Account
from .models import OwnerSession as AccountSession
from .models import UpgradeIssue, Company
from .validators import IssueValidator, ConnectIssueValidator
from .validators import validate_inn, validate_kpp


class AccountInfoView(LoginRequiredAPIView):
    def get(self, request):
        account_dict = serializer(request.owner, exclude_attr=("created_at", "sms_code", "password"))
        parkings = Parking.objects.filter(company__owner=request.owner)
        en_parkings = parkings.filter(parkpass_enabled=True)
        account_dict['parkings_total'] = len(parkings)
        account_dict['parkings_enabled'] = len(en_parkings)
        return JsonResponse(account_dict, status=200)


class SummaryStatisticsView(LoginRequiredAPIView):
    def post(self, request):
        period = request.data.get('period', 'day')
        if period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)
        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        else:
            td = timedelta(days=30)
        t = datetime.date.today() - td
        sessions = ParkingSession.objects.filter(parking__company__owner=request.owner,
                                                 completed_at__gt=t)
        count = sessions.count()
        debt = sessions.aggregate(Sum('debt'))['debt__sum']
        seen = set()
        users = 0
        for s in sessions:
            if s.client not in seen:
                seen.add(s.client)
                users += 1
        return JsonResponse({
            'count': count,
            'debt': debt,
            'users': users
        }, status=200)


class ParkingStatisticsView(LoginRequiredAPIView):
    def post(self, request):
        def get_ids_from_list(s):
            if str(s).isdigit():
                return [int(s)]
            s = s.replace(' ', '').strip(',').split(',')
            l = []
            for i in s:
                if i.isdigit():
                    l.append(i)
            return l

        try:
            id = request.data.get("pk", '')
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
                "`start_from` shouldn't be greater than `stop_at`"
            )
            return JsonResponse(e.to_dict(), status=400)
        ids = get_ids_from_list(id)
        try:
            if not ids:
                parkings = Parking.objects.filter(company__owner=request.owner)
            else:
                parkings = Parking.objects.filter(id__in=ids, company__owner=request.owner)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Target parking with such id not found"
            )
            return JsonResponse(e.to_dict(), status=400)
        parkings_list = []
        for parking in parkings:
            stat = ParkingSession.objects.filter(
                parking=parking,
                started_at__gt=datetime_from_unix_timestamp_tz(start_from) if start_from > -1
                else datetime.datetime.now() - timedelta(days=31),
                started_at__lt=datetime_from_unix_timestamp_tz(stop_at) if stop_at > -1 else datetime.datetime.now()
            )
            sessions_list = []
            for ps in stat:
                sessions_list.append(
                    serializer(ps, exclude_attr=['try_refund', 'debt', 'current_refund_sum', 'target_refund_sum'])
                )
            parkings_list.append({
                'parking_id': parking.id,
                'sessions': sessions_list
            })
        return JsonResponse({'count': len(parkings_list),
                             'parkings': parkings_list[page * count:(page + 1) * count]})


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
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        else:
            td = timedelta(days=30)
        t = datetime.date.today() - td
        parkings = Parking.objects.filter(company__owner=request.owner)
        r = []
        for p in parkings:
            r.append({
                'company': p.company.name,
                'address': p.address,
                'debt': ParkingSession.objects.filter(parking=p, completed_at__gt=t).aggregate(Sum('debt'))[
                    'debt__sum'],
            })
        r = sorted(r, key=lambda x: -x['debt'] if x['debt'] else 0)
        return JsonResponse({'top': r[:count + 1]}, status=200)


class IssueUpgradeView(LoginRequiredAPIView):

    def post(self, request):
        account = request.owner
        description = request.data.get('description', None)
        type = request.data.get('issue_type', None)
        if type is None or description is None or not type.isdigit() or 0 > len(description) > 1000:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Both 'issue_type' and 'description' fields are required, 'issue_type' must be int"
            )
            return JsonResponse(e.to_dict(), status=400)
        type = int(type)
        ui = UpgradeIssue(
            owner=account,
            description=description,
            type=type,
        )
        ui.save()
        return JsonResponse({}, status=200)


class IssueView(APIView):
    validator_class = IssueValidator

    def post(self, request):
        name = request.data.get("name", "")
        phone = request.data.get("phone", "")
        email = request.data.get("email", "")
        i = Issue(
            name=name,
            phone=phone,
            email=email
        )
        i.save()
        text = u"Ваша заявка принята в обработку. С Вами свяжутся в ближайшее время."
        if phone:
            sms_gateway = SMSGateway()
            sms_gateway.send_sms(phone, text, message='')
        if email:
            msg_html = render_to_string('emails/issue_accepted.html',
                                        {'name': name})
            send_mail('Ваша заявка в ParkPass принята.', "", EMAIL_HOST_USER,
                      ['%s' % str(email)], html_message=msg_html)
        return JsonResponse({}, status=200)


class EditCompanyView(LoginRequiredAPIView):
    fields = {
        'name': StringField(required=True, max_length=256),
        'inn': CustomValidatedField(callable=validate_inn, required=True),
        'kpp': CustomValidatedField(callable=validate_kpp, required=True),
        'legal_address': StringField(required=True, max_length=512),
        'actual_address': StringField(required=True, max_length=512),
        'email': CustomValidatedField(callable=validate_email, required=True),
        'phone': CustomValidatedField(callable=validate_phone_number, required=True),
        'checking_account': StringField(required=True, max_length=64),
        'checking_kpp': CustomValidatedField(callable=validate_kpp, required=True),
    }

    validator_class = create_generic_validator(fields)

    def post(self, request, id=-1):
        return edit_object_view(request=request, id=id, object=Company, fields=self.fields)


class ConnectIssueView(LoginRequiredAPIView):
    validator_class = ConnectIssueValidator

    def post(self, request):
        parking_id = self.request.data['parking_id']
        vendor_id = self.request.data.get('vendor_id', None)
        org_name = self.request.data.get("org_name", None)
        email = self.request.data.get("email", None)
        phone = self.request.data.get("phone", None)
        website = self.request.data.get("website", None)
        contact_email = self.request.data["contact_email"]

        try:
            parking = Parking.objects.get(id=parking_id, approved=True, enabled=True)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Parking with such ID does not exist or not enabled/approved by administrator'
            )
            return JsonResponse(e.to_dict(), status=400)
        if vendor_id:
            try:
                vendor = Vendor.objects.get(id=vendor_id)
            except ObjectDoesNotExist:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    'Vendor with such ID does not exist'
                )
                return JsonResponse(e.to_dict(), status=400)
            issue = ConnectIssue(
                owner=self.request.owner,
                parking=parking,
                vendor=vendor,
                contact_email=contact_email,
            )
        else:
            issue = ConnectIssue(
                owner=self.request.owner,
                parking=parking,
                organisation_name=org_name,
                phone=phone,
                email=email,
                contact_email=contact_email,
                website=website,
            )
        issue.save()
        return JsonResponse({}, status=200)


class ListCompanyView(generic_pagination_view(Company, LoginRequiredAPIView)):
    pass


class ListUpgradeIssuesView(generic_pagination_view(UpgradeIssue, LoginRequiredAPIView)):
    pass


class ListParkingsView(generic_pagination_view(Parking, LoginRequiredAPIView)):
    pass


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
                "Owner with such login not found")
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
                if AccountSession.objects.filter(owner=account).exists():
                    session = AccountSession.objects.filter(owner=account).order_by('-created_at')[0]
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
