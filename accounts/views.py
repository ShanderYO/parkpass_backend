import datetime
import pytz

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from dss.Serializer import serializer

from accounts.models import Account, AccountParkingSession
from accounts.sms_gateway import SMSGateway
from accounts.validators import LoginParamValidator, ConfirmLoginParamValidator, AccountParamValidator, IdValidator
from base.exceptions import AuthException, ValidationException, PermissionException, PaymentException
from base.utils import get_logger
from base.views import APIView, LoginRequiredAPIView
from parkings.models import ParkingSession
from payments.models import CreditCard
from payments.utils import TinkoffExceptionAdapter


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


class LogoutView(LoginRequiredAPIView):
    def post(self, request):
        request.account.clean_session()
        return JsonResponse({}, status=200)


class AccountView(LoginRequiredAPIView):
    validator_class = AccountParamValidator

    def get(self, request):
        account_dict = serializer(request.account, exclude_attr=("created_at", "sms_code"))
        card_list = CreditCard.get_card_by_account(request.account)
        account_dict["cards"] = serializer(card_list, include_attr=("id", "pan", "is_default"))
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


class AddCardView(LoginRequiredAPIView):
    def post(self, request):
        """
        Success response
        {
            u'Status': u'NEW',
            u'OrderId': u'2',
            u'Success': True,
            u'PaymentURL': u'https://securepay.tinkoff.ru/5YDUkv',
            u'ErrorCode': u'0',
            u'Amount': 100,
            u'TerminalKey': u'1516954410942DEMO',
            u'PaymentId': u'16630446'
        }
        """
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
            get_logger().warning("Init exception: " + str(error_code) + " : " + error_message + " : " + error_details)

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
        card_id = request.data["id"]
        try:
            card = CreditCard.objects.get(id=card_id, account=request.account)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Your card with such id not found")
            return JsonResponse(e.to_dict(), status=400)

        if CreditCard.objects.filter(account=request.account).count() > 1:
            # TODO make added operation
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
                "Impossible to delete card"
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class SetDefaultCardView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
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

    def post(self, request):
        session_id = request.data["session_id"]
        client_id = int(request.data["client_id"])
        parking_id = int(request.data["parking_id"])
        started_at = int(request.data["started_at"])

        if request.account.pk != client_id:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Invalid client id")
            return JsonResponse(e.to_dict(), status=400)

        started_at_date = datetime.datetime.fromtimestamp(int(started_at))
        started_at_date_tz = pytz.utc.localize(started_at_date)

        account_parking_session = AccountParkingSession(started_at=started_at_date_tz,
                                                        linked_session_id=session_id,
                                                        parking_id=parking_id)
        account_parking_session.save()

        # Set parking session to account
        request.account.parking_session = account_parking_session
        request.account.save()

        return JsonResponse({"id":account_parking_session.pk}, status=200)


class ForceStopParkingSession(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        id = request.data["id"]

        try:
            account_parking_session = AccountParkingSession.objects.get(id=id)
            parking_session = ParkingSession.objects.get(
                session_id=account_parking_session.linked_session_id,
                parking_id=account_parking_session.parking_id)
            parking_session.is_paused = True

            # Remove parking session to account
            request.account.parking_session = None
            request.account.save()

            # TODO Set final debt
            parking_session.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "ParkingSession with such not found")
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class CompleteParkingSession(LoginRequiredAPIView):
    def post (self, request):
        session_id = request.data["session_id"]
        client_id = int(request.data["client_id"])
        parking_id = int(request.data["parking_id"])
        completed_at = int(request.data["completed_at"])

        if request.account.pk != client_id:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Invalid client id")
            return JsonResponse(e.to_dict(), status=400)

        try:
            account_parking_session = AccountParkingSession.objects.get(
                linked_session_id=session_id,
                parking_id = parking_id
            )

            completed_at_date = datetime.datetime.fromtimestamp(int(completed_at))
            completed_at_date_tz = pytz.utc.localize(completed_at_date)

            account_parking_session.completed_at = completed_at_date_tz

            # Remove parking session to account
            request.account.parking_session = None
            request.account.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "ParkingSession with such not found")
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class DebtParkingSessionView(LoginRequiredAPIView):
    def get(self, request):
        account_parking_session = request.account.parking_session

        if account_parking_session:
            try:
                parking_session = ParkingSession.objects.get(
                    session_id=account_parking_session.linked_session_id,
                    parking_id=account_parking_session.parking.id)

                debt_dict = serializer(parking_session, include_attr=("debt", "started_at", "updated_at"))
                debt_dict["paid_debt"] = account_parking_session.paid_debt
                return JsonResponse(debt_dict, status=200)

            except ObjectDoesNotExist:
                e = ValidationException(
                    ValidationException.RESOURCE_NOT_FOUND,
                    "ParkingSession not found")
                return JsonResponse(e.to_dict(), status=400)
        else:
            return JsonResponse({}, status=200)