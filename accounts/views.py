from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from dss.Serializer import serializer

from accounts.models import Account
from accounts.validators import LoginParamValidator, ConfirmLoginParamValidator, AccountParamValidator
from base.exceptions import AuthException
from base.views import APIView, LoginRequiredAPIView


class LoginView(APIView):
    validator_class = LoginParamValidator

    def post(self, request):
        phone = request.data["phone"]
        success_status = 200
        if Account.objects.filter.exists(phone=phone):
            account = Account.objects.get(phone=phone)
        else:
            account = Account(phone=phone)
            success_status = 201

        account.create_sms_code()
        account.save()
        account.send_sms_code()
        return JsonResponse({"sms_code":account.sms_code}, status=success_status)


class ConfirmLoginView(APIView):
    validator_class = ConfirmLoginParamValidator

    def post(self, request):
        sms_code = request.data["sms_code"]
        try:
            account = Account.objects.get(sms_code=sms_code)
            account.login()
            session = account.get_session()
            return JsonResponse(serializer(session))

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

    def post(self, request):
        return JsonResponse({}, status=200)

