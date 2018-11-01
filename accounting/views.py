from django.http import JsonResponse
from base.exceptions import AuthException, ValidationException, PermissionException
import base64
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from base.views import APIView
from os.path import isfile
from .models import BaseAccount
from parkpass.settings import DEFAULT_AVATAR_URL


class LoginRequiredAPIView(APIView):
    """
    "Only for authorized users" view
    Change account_type to specify account type(vendor etc.)
    Raises 401 Unauthorized if no or invalid token
    Raises 403 Forbidden if wrong account type
    """
    account_type = BaseAccount
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, 'account') or not request.account:
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        if not isinstance(request.account, self.account_type):
            perm_exception = PermissionException(PermissionException.NO_PERMISSION,
                                                 "Wrong account type")
            return JsonResponse(perm_exception.to_dict(), status=403)
        return super(LoginRequiredAPIView, self).dispatch(request, *args, **kwargs)


class AvatarView(LoginRequiredAPIView):
    """
    POST avatar to JSON Field 'avatar' in base64
    GET JSON with field 'url' pointing to file
    """
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

    def get(self, request):
        path = DEFAULT_AVATAR_URL if not isfile(request.account.get_avatar_path()) else request.account.get_avatar_url()
        body = {
            'url': request.get_host() + path
        }
        return JsonResponse(body, status=200)


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
            account = User.objects.get(email=email)
            account.create_password_and_send()
            return JsonResponse({}, status=200)
        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "User with such email not found"
            )
            return JsonResponse(e.to_dict(), status=400)