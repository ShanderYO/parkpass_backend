# -*- coding: utf-8 -*-
import json

from django.core.mail import send_mail
from django.db.models import Sum
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.timezone import timedelta
from django.views import View

from accounts.sms_gateway import SMSGateway
from accounts.validators import *
from base.exceptions import AuthException
from base.models import EmailConfirmation
from base.utils import *
from base.validators import *
from base.views import APIView, ObjectView
from base.views import generic_login_required_view
from parkings.models import Parking, ParkingSession
from parkpass.settings import EMAIL_HOST_USER
from vendors.models import Vendor
from .models import Issue, ConnectIssue
from .models import Owner as Account
from .models import OwnerSession as AccountSession
from .models import UpgradeIssue, Company
from .validators import ConnectIssueValidator, TariffValidator

LoginRequiredAPIView = generic_login_required_view(Account)

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
        t = timezone.now() - td
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


class ParkingSessionsView(LoginRequiredAPIView, ObjectView):
    object = ParkingSession
    account_filter = 'parking__company__owner'
    hide_fields = ('try_refund', 'debt', 'current_refund_sum', 'target_refund_sum')
    methods = ('GET',)


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
        t = timezone.now() - td
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


class UpgradeIssueView(LoginRequiredAPIView, ObjectView):
    object = UpgradeIssue
    author_field = 'owner'
    show_fields = ('description', 'type')
    account_filter = 'owner'


class IssueView(APIView, ObjectView):
    object = Issue
    methods = ('POST',)
    show_fields = ('name', 'phone', 'email')

    def on_create(self, request, obj):
        name = request.data.get("name", "")
        phone = request.data.get("phone", "")
        email = request.data.get("email", "")
        text = u"Ваша заявка принята в обработку. С Вами свяжутся в ближайшее время."
        if phone:
            sms_gateway = SMSGateway()
            sms_gateway.send_sms(phone, text, message='')
        if email:
            msg_html = render_to_string('emails/issue_accepted.html',
                                        {'name': name})
            send_mail('Ваша заявка в ParkPass принята.', "", EMAIL_HOST_USER,
                      ['%s' % str(email)], html_message=msg_html)


class CompanyView(LoginRequiredAPIView, ObjectView):
    object = Company
    show_fields = ('name', 'inn', 'kpp', 'legal_address',
                   'actual_address', 'email', 'phone', 'checking_account',
                   'checking_kpp')
    account_filter = 'owner'


class TariffView(LoginRequiredAPIView):
    validator_class = TariffValidator

    def get(self, request, id):
        try:
            p = Parking.objects.get(id=id)
        except ObjectDoesNotExist:
            e = ValidationException.RESOURCE_NOT_FOUND
            return JsonResponse(e.to_dict(), status=400)
        return JsonResponse(json.loads(p.tariff), status=200)

    def post(self, request, id):
        try:
            p = Parking.objects.get(id=id)
        except ObjectDoesNotExist:
            e = ValidationException.RESOURCE_NOT_FOUND
            return JsonResponse(e.to_dict(), status=400)
        p.tariff = request.data
        return JsonResponse({}, status=200)


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


class ParkingsView(LoginRequiredAPIView, ObjectView):
    object = Parking
    account_filter = 'company__owner'
    methods = ('GET',)


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
