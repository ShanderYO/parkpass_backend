from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse

# Create your views here.
from dss.Serializer import serializer

from accounts.sms_gateway import SMSGateway
from accounts.validators import LoginParamValidator, ConfirmLoginParamValidator, EmailValidator
from auth.models import User
from base.exceptions import AuthException
from base.utils import clear_phone
from base.views import APIView


class PhoneLoginView(APIView):
    validator_class = LoginParamValidator

    def post(self, request):
        phone = clear_phone(request.data["phone"])

        success_status = 200
        if User.objects.filter(phone=phone).exists():
            user = User.objects.get(phone=phone)
        else:
            user = User(phone=phone)
            success_status = 201

        user.create_sms_code(stub=(phone == "77891234560"))
        user.save()

        sms_gateway = SMSGateway()
        sms_gateway.send_sms(user.phone, user.sms_code)

        if sms_gateway.exception:
            return JsonResponse(sms_gateway.exception.to_dict(), status=400)

        return JsonResponse({}, status=success_status)


class ConfirmPhoneLoginView(APIView):
    validator_class = ConfirmLoginParamValidator

    def post(self, request):
        sms_code = request.data["sms_code"]
        try:
            user = User.objects.get(sms_code=sms_code)
            session = user.mobile_login()
            return JsonResponse(serializer(session,
                                           include_attr=("access_token", "refresh_token", 'expires_at',)))

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "Account with pending sms-code not found")
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
                "User with such email not found")
            return JsonResponse(e.to_dict(), status=400)


class LogoutView(LoginRequiredAPIView):
    def post(self, request):
        request.account.clean_session()
        return JsonResponse({}, status=200)


class PasswordSetLoginView(APIView):
    validator_class = EmailValidator

    def post(self, request):
        pass


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