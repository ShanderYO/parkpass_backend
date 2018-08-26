# -*- coding: utf-8 -*-

import base64
import datetime
from os.path import isfile

import pytz
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from dss.Serializer import serializer

from accounts.models import Account, EmailConfirmation, AccountSession
from accounts.sms_gateway import SMSGateway
from accounts.tasks import generate_current_debt_order, force_pay
from accounts.validators import LoginParamValidator, ConfirmLoginParamValidator, AccountParamValidator, IdValidator, \
    StartAccountParkingSessionValidator, CompleteAccountParkingSessionValidator, EmailValidator, \
    EmailAndPasswordValidator, LoginAndPasswordValidator
from base.enums import AccountTypes
from base.exceptions import AuthException, ValidationException, PermissionException, PaymentException
from base.utils import get_logger, parse_int, datetime_from_unix_timestamp_tz
from base.views import APIView, LoginRequiredAPIView
from parkings.models import ParkingSession, Parking
from parkpass.settings import DEFAULT_AVATAR_URL
from payments.models import CreditCard, Order
from payments.utils import TinkoffExceptionAdapter


def only_for(account, account_type):
    if account.account_type == account_type:
        raise PermissionException(PermissionException.NOT_PRIVELEGIED,
                                  "You aren't privelegied to use this method")


class LoginView(APIView):
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


class CreateUserView():
    pass


class PasswordRestoreView(APIView):
    """
    API View for url /login/restore
    In: POST with json { email: "my@mail.ru" (String) }
    Out:
      200 {}, sending an email with new pw
      400 { AuthException User with such email not found }
    """
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


class PasswordChangeView(LoginRequiredAPIView):
    """
    API View for url /login/changepw
    In: POST with json { old: "old_password", new: "new_password" }
    Out:
    200 {}

    """

    def post(self, request):
        old_password = request.data["old"]
        new_password = request.data["new"]

        account = request.account

        if not account.check_password(old_password):
            e = AuthException(
                AuthException.INVALID_PASSWORD,
                "Invalid old password"
            )
            return JsonResponse(e.to_dict(), status=400)
        account.set_password(new_password)
        return JsonResponse({}, status=200)


class DeactivateAccountView(LoginRequiredAPIView):
    """
    API View for url /account/deactivate
    Clear card list and stop parking session
    Out: {} 200
    """
    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        account = request.account
        CreditCard.objects.filter(account=account).delete()

        parking_session = ParkingSession.get_active_session(account)
        if parking_session is None or not parking_session.is_suspended:
            parking_session.is_suspended = True
            parking_session.suspended_at = datetime.datetime.now()
            parking_session.save()
            # Create payment order and pay
            generate_current_debt_order(parking_session.id)
        return JsonResponse({}, status=200)


# TODO: Отрефакторить методы так, чтобы не было больших блоков кода в if-else конструкциях ( повышение читаемости кода )
"""
class VendorNameLoginView(APIView):
    validator_class = LoginAndPasswordValidator

    def post(self, request):
        login = request.data["login"]
        password = request.data["password"]

        try:
            account = Account.objects.get(name=login)
            if account.account_type != AccountTypes.VENDOR:  # If not casting to `str` cond is True always
                e = PermissionException(  # IDK why...
                    PermissionException.VENDOR_NOT_FOUND,
                    "This account has no vendor privelegies"
                )
                return JsonResponse(e.to_dict(), status=400)
            if account.check_password(raw_password=password):
                if AccountSession.objects.filter(account=account).exists():
                    session = AccountSession.objects.filter(account=account).order_by('-created_at')[0]
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
                "User with such login not found")
            return JsonResponse(e.to_dict(), status=400)
"""

class LoginWithEmailView(APIView):
    validator_class = EmailAndPasswordValidator

    def post(self, request):
        raw_email = request.data["email"]
        password = request.data["password"]
        email = raw_email.lower()

        try:
            account = Account.objects.get(email=email)
            if account.check_password(raw_password=password):
                if AccountSession.objects.filter(account=account).exists():
                    session = AccountSession.objects.filter(account=account).order_by('-created_at')[0]
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
                "User with such login not found")
            return JsonResponse(e.to_dict(), status=400)


class LogoutView(LoginRequiredAPIView):
    def post(self, request):
        request.account.clean_session()
        return JsonResponse({}, status=200)


class SetAvatarView(LoginRequiredAPIView):
    def post(self, request):
        try:
            file = request.data.get("avatar", None)
            if file is None:
                raise ValidationException(
                    ValidationException.RESOURCE_NOT_FOUND,
                    "No file attached"
                )
            request.account.update_avatar(base64.b64decode(file))
        except ValidationException, e:
            return JsonResponse(e.to_dict(), status=400)
        return JsonResponse({}, status=200)


class GetAvatarView(LoginRequiredAPIView):
    def get(self, request):
        path = DEFAULT_AVATAR_URL if not isfile(request.account.get_avatar_path()) else request.account.get_avatar_url()
        body = {
            'url': request.get_host() + path
        }
        return JsonResponse(body, status=200)


class AccountView(LoginRequiredAPIView):
    validator_class = AccountParamValidator

    def get(self, request):
        vendor_tuple = ("name", "secret") if request.account.account_type != AccountTypes.VENDOR else ()
        account_dict = serializer(request.account, exclude_attr=("created_at", "sms_code", "password") + vendor_tuple)
        if request.account.account_type == AccountTypes.USER:
            card_list = CreditCard.get_card_by_account(request.account)
            account_dict["cards"] = serializer(card_list, include_attr=("id", "pan", "exp_date", "is_default"))
        return JsonResponse(account_dict, status=200)

    def post(self, request):
        first_name = request.data.get("first_name")
        if first_name:
            request.account.first_name = first_name
        last_name = request.data.get("last_name")
        if last_name:
            request.account.last_name = last_name
        request.account.save()

        return JsonResponse({}, status=200)


class AccountParkingListView(LoginRequiredAPIView):
    max_paginate_length = 10
    max_select_time_interval = 366 * 24 * 60 * 60 # 1 year

    def get(self, request, *args, **kwargs):
        page = parse_int(request.GET.get("page", None))
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

            if (to_date - from_date) > self.max_select_time_interval:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Max time interval exceeded. Max value %s, accepted %s" % (self.max_select_time_interval,
                                                                               (to_date-from_date))
                )
                return JsonResponse(e.to_dict(), status=400)

        result_query = ParkingSession.objects.filter(
            Q(client_id=request.account.id, state__lte=0) | Q(client_id=request.account.id, is_suspended=True))\
            .select_related("parking")

        if from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)

            result_query = result_query.filter(
                created_at__gt=from_date_datetime, created_at__lt=to_date_datetime).order_by("-id")

        elif page:
            id = int(page)
            result_query = result_query.filter(pk__lt=id).order_by("-id")

        object_list = result_query[:self.max_paginate_length]
        data = serializer(object_list, foreign=False, exclude_attr=("session_id", "client_id",
                                                                    "parking_id", "created_at"))
        for index, obj in enumerate(object_list):
            parking_dict = {
                "id": obj.parking.id,
                "name": obj.parking.name
            }
            data[index]["parking"] = parking_dict

        response = {
            "result":data
        }
        if len(data) == self.max_paginate_length:
            response["next"] = str(data[self.max_paginate_length - 1]["id"])
        return JsonResponse(response)


class DebtParkingSessionView(LoginRequiredAPIView):
    def get(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        current_parking_session = ParkingSession.get_active_session(request.account)
        if current_parking_session:
            debt_dict = serializer(current_parking_session, exclude_attr=("session_id", "client_id", "created_at",))
            orders = Order.objects.filter(session=current_parking_session)
            orders_dict = serializer(orders, foreign=False, include_attr=("id", "sum", "paid"))
            debt_dict["orders"] = orders_dict
            return JsonResponse(debt_dict, status=200)
        else:
            return JsonResponse({}, status=200)


class GetReceiptView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        id = int(request.data["id"])
        try:
            parking_session = ParkingSession.objects.get(id=id)
            orders = Order.objects.filter(session=parking_session, paid=True)

            response = {"result": []}
            for order in orders:
                response["result"].append(order.get_order_with_fiscal_dict())
            return JsonResponse(response, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with id %s does not exist" % id)
            return JsonResponse(e.to_dict(), status=400)


class SendReceiptToEmailView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        id = int(request.data["id"])
        if request.account.email is None:
            e = PermissionException(
                PermissionException.EMAIL_REQUIRED,
                "Your account doesn't have binded email"
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            parking_session = ParkingSession.objects.get(id=id)
            parking_session.send_receipt_to_email()
            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with id %s does not exist" % id)
            return JsonResponse(e.to_dict(), status=400)


class ChangeEmailView(LoginRequiredAPIView):
    validator_class = EmailValidator

    def post(self, request):
        email = str(request.data["email"])
        current_account = request.account
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
            email_confirmation = EmailConfirmation(email=email)

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


class ForcePayView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        id = int(request.data["id"])
        try:
            ParkingSession.objects.get(id=id)
            # Create payment order and pay
            force_pay(id)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with id %s does not exist" % id)
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class AddCardView(LoginRequiredAPIView):
    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        result_dict = CreditCard.bind_request(request.account)

        # If error request
        if not result_dict:
            e = PaymentException(
                PaymentException.BAD_PAYMENT_GATEWAY,
                "Payment gateway temporary not available"
            )
            return JsonResponse(e.to_dict(), status=400)

        # If exception occurs
        if result_dict.get("exception", None):
            exception = result_dict["exception"]
            error_code = int(exception.get("error_code", 0))
            error_message = exception.get("error_message", "")
            error_details = exception.get("error_details", "")

            get_logger().warning("Init exception: " + str(error_code) +
                                 " : " + error_message + " : " + error_details)

            exception_adapter = TinkoffExceptionAdapter(error_code)
            e = exception_adapter.get_api_exeption()
            return JsonResponse(e.to_dict(), status=400)

        # Success result
        return JsonResponse({
            "payment_url": result_dict["payment_url"]
        }, status=200)


class DeleteCardView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        card_id = request.data["id"]
        try:
            card = CreditCard.objects.get(id=card_id, account=request.account)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Your card with such id not found")
            return JsonResponse(e.to_dict(), status=400)

        if CreditCard.objects.filter(account=request.account).count() > 1:
            if not card.is_default:
                card.delete()
            else:
                card.delete()
                another_card = CreditCard.objects.filter(account=request.account)[0]
                another_card.is_default = True
                another_card.save()
        else:
            e = PermissionException(
                PermissionException.ONLY_ONE_CARD,
                "Impossible to delete single card"
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class SetDefaultCardView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        card_id = request.data["id"]
        try:
            card = CreditCard.objects.get(id=card_id, account=request.account)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Your card with such id not found")
            return JsonResponse(e.to_dict(), status=400)

        default_card = CreditCard.objects.get(account=request.account, is_default=True)
        default_card.is_default=False
        default_card.save()

        card.is_default = True
        card.save()
        return JsonResponse({}, status=200)


class StartParkingSession(LoginRequiredAPIView):
    validator_class = StartAccountParkingSessionValidator

    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        session_id = request.data["session_id"]
        parking_id = int(request.data["parking_id"])
        started_at = int(request.data["started_at"])

        # It's needed only for account session creation
        started_at = datetime_from_unix_timestamp_tz(started_at)

        # Check open session
        if ParkingSession.objects.filter(client=request.account, is_suspended=False, state__gt=0).exists():
            e = PermissionException(
                PermissionException.ONLY_ONE_ACTIVE_SESSION_REQUIRED,
                "It's impossible to create second active session")
            return JsonResponse(e.to_dict(), status=400)

        if not CreditCard.objects.filter(account=request.account).exists():
            e = PermissionException(
                PermissionException.CREDIT_CARD_REQUIRED,
                "It's impossible to create session without credit card"
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            parking_session = ParkingSession.objects.get(
                session_id=session_id, parking_id=parking_id
            )
            parking_session.add_client_start_mark()
            parking_session.save()
            return JsonResponse({"id": parking_session.id}, status=200)

        except ObjectDoesNotExist:
            try:
                parking = Parking.objects.get(id=parking_id)
            except ObjectDoesNotExist:
                e = ValidationException(
                    ValidationException.RESOURCE_NOT_FOUND,
                    "Parking with id %s does not exist" % parking_id)
                return JsonResponse(e.to_dict(), status=400)

            parking_session = ParkingSession.objects.create(
                session_id=session_id,
                client=request.account,
                parking=parking,
                state=ParkingSession.STATE_STARTED_BY_CLIENT,
                started_at=started_at
            )
            parking_session.save()
            return JsonResponse({"id": parking_session.id}, status=200)


class ForceStopParkingSession(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        id = int(request.data["id"])

        try:
            parking_session = ParkingSession.objects.get(id=id)
            if not parking_session.is_suspended:
                parking_session.is_suspended = True
                parking_session.suspended_at = pytz.utc.localize(datetime.datetime.now())
                parking_session.save()

                # Create payment order and pay
                generate_current_debt_order(id)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "ParkingSession with id %s not found" % id
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class ResumeParkingSession(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        id = int(request.data["id"])

        try:
            parking_session = ParkingSession.objects.get(id=id)
            if parking_session.is_suspended:
                parking_session.is_suspended = False
                parking_session.suspended_at = None
                parking_session.save()

                if parking_session.is_started_by_vendor():
                    pass
                    # TODO make async payments

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "ParkingSession with id %s not found" % id
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class CompleteParkingSession(LoginRequiredAPIView):
    validator_class = CompleteAccountParkingSessionValidator

    def post(self, request):
        try:
            only_for(request.account, AccountTypes.USER)
        except PermissionException as e:
            return JsonResponse(e.to_dict(), status=400)

        session_id = request.data["id"]
        parking_id = int(request.data["parking_id"])
        completed_at = int(request.data["completed_at"])

        # It's needed only for account session completed
        completed_at = datetime_from_unix_timestamp_tz(completed_at)

        try:
            parking_session = ParkingSession.objects.get(
                session_id=session_id,
                parking_id=parking_id,
                client=request.account
            )

            # If session start is not confirm from vendor
            if not parking_session.is_started_by_vendor():
                parking_session.is_suspended = True
                parking_session.suspended_at = completed_at
                parking_session.save()
                return JsonResponse({}, status=200)

            # Set up completed time if not specified by vendor
            if not parking_session.is_completed_by_vendor():
                parking_session.completed_at = completed_at

            parking_session.add_client_complete_mark()
            parking_session.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session does not exists")
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)