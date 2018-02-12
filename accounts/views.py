from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from dss.Serializer import serializer

from accounts.models import Account
from accounts.sms_gateway import SMSGateway
from accounts.validators import LoginParamValidator, ConfirmLoginParamValidator, AccountParamValidator, IdValidator, \
    CardParamValidator
from base.exceptions import AuthException, ValidationException, PermissionException
from base.views import APIView, LoginRequiredAPIView
from parkings.models import ParkingSession
from payments.models import CreditCard


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
        #sms_gateway = SMSGateway()
        #sms_gateway.send_sms(account.phone, account.code)
        #if sms_gateway.exception:
        #    return JsonResponse(sms_gateway.exception.to_dict, status=400)

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
        account_dict["cards"] = serializer(card_list, include_attr=("id", "number", "is_default"))
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


class CreateCardView(LoginRequiredAPIView):
    validator_class = CardParamValidator

    def post(self, request):
        number = self.request.data["number"]
        owner = self.request.data["owner"]
        expiration_date_month = self.request.data["expiration_date_month"]
        expiration_date_year = self.request.data["expiration_date_year"]
        #TODO check card in bank
        # TODO check exist

        card_by_default = False
        if not CreditCard.objects.filter(account=request.account).exists():
            card_by_default = True

        card = CreditCard(number=number, account=request.account, is_default=card_by_default)
        card.save()

        return JsonResponse({}, status=200)


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
    validator_class = IdValidator

    def post(self, request):
        client_id = request.data["client_id"]
        parking_id = request.data["parking_id"]
        start_at = request.data["client_id"]
        # TODO create session
        return JsonResponse({}, status=200)


class ForceStopParkingSession(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        account_session_id = request.data["session_id"]
        # TODO set up pause on session
        return JsonResponse({}, status=200)


class FinishParkingSession(LoginRequiredAPIView):
    validator_class = IdValidator

    def post (self, request):
        account_session_id = request.data["session_id"]
        completed_at = request.data["completed_at"]
        # TODO set up stop session
        return JsonResponse({}, status=200)


class DebtParkingSession(LoginRequiredAPIView):
    def get(self, request):
        try:
            # TODO get current debt debt - paid_debt
            parking_session = ParkingSession.objects.get(client=request.account)
            debt_dict = serializer(parking_session, include_attr=("debt", "start_at", "update_at"))
            return JsonResponse(debt_dict, status=200)
        except ObjectDoesNotExist:
            return JsonResponse({}, status=200)