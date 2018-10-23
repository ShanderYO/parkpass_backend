# Python import
import hashlib
import hmac
import json

# Django import
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from accounts.validators import validate_phone_number
# App import
from base.exceptions import ValidationException, AuthException, PermissionException
from base.utils import get_logger
from base.validators import ValidatePostParametersMixin
from parkpass.settings import REQUESTS_LOGGER_NAME
from vendors.models import Vendor
from .models import NotifyIssue


class APIView(View, ValidatePostParametersMixin):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        logger = get_logger(REQUESTS_LOGGER_NAME)
        logger.info("Accessing URL '%s'" % request.path)
        if request.method == 'GET':
            logger.info("It's a GET request")
        elif request.method == 'POST':
            logger.info("POST request content: '%s'" % request.body)
        else:
            logger.info("Unrecognized request method")
        # Only application/json Content-type allow
        if not request.META.get('CONTENT_TYPE', "").startswith("application/json") and request.POST:
            return JsonResponse({
                "error": "HTTP Status 415 - Unsupported Media Type"
            }, status=415)

        if request.method == 'POST':
            # Parse json-string
            try:
                request.data = json.loads(request.body)
            except Exception as e:
                e = ValidationException(
                    ValidationException.INVALID_JSON_FORMAT,
                    e.message
                )
                return JsonResponse(e.to_dict(), status=400)
            # Validate json-parameters
            if self.validator_class:
                exception_response = self.validate_request(request)
                if exception_response:
                    return exception_response
        response = super(APIView, self).dispatch(request, *args, **kwargs)
        logger.info("Sending response '%s' with code '%i'" % (response.content, response.status_code))
        return response


class SignedRequestAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not request.META.get('HTTP_X_SIGNATURE', None):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Signature is empty. [x-signature] header required"
            )
            return JsonResponse(e.to_dict(), status=400)

        if not request.META.get('HTTP_X_VENDOR_NAME', None):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "The vendor name is empty. [x-vendor-name] header required"
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            request.vendor = Vendor.objects.get(
                name=str(request.META["HTTP_X_VENDOR_NAME"]),
            )
        except ObjectDoesNotExist:
            e = PermissionException(
                PermissionException.VENDOR_NOT_FOUND,
                "Vendor does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)

        signature = hmac.new(str(request.vendor.secret), request.body, hashlib.sha512)

        if request.vendor.account_state == request.vendor.ACCOUNT_STATE.DISABLED:
            e = PermissionException(
                PermissionException.NO_PERMISSION,
                "Account is disabled"
            )
            return JsonResponse(e.to_dict(), status=400)

        if signature.hexdigest() != request.META["HTTP_X_SIGNATURE"].lower():
            e = PermissionException(
                PermissionException.SIGNATURE_INVALID,
                "Invalid signature"
            )
            return JsonResponse(e.to_dict(), status=400)

        return super(SignedRequestAPIView, self).dispatch(request, *args, **kwargs)


class LoginRequiredAPIView(APIView):
    account_type = 'account'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, self.account_type) or not getattr(request, self.account_type, None):
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        return super(LoginRequiredAPIView, self).dispatch(request, *args, **kwargs)


def generic_login_required_view(account_model):
    class GenericLoginRequiredAPIView(LoginRequiredAPIView):
        account_type = account_model.__name__.lower()

    print("DEPRECATED: Will be removed due to optimizing accounting architecture")
    return GenericLoginRequiredAPIView


def type_variative_view(view, type):
    """
    Fabric of account views for specific account type
    :param view: APIView with TypeVariativeViewMixin to specify type of it
    :param type: Type of account
    :return: Generic view for specified account type
    """

    class GenericTypeVariativeView(view):
        __doc__ = view.__doc__
        account_class = type

    return GenericTypeVariativeView


class LoginRequiredFormMultipartView(View, ValidatePostParametersMixin):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):

        # Only multipart/form-data Content-type allow
        if not request.META['CONTENT_TYPE'].startswith("multipart/form-data"):
            return JsonResponse({
                "error": "HTTP Status 415 - Unsupported Media Type"
            }, status=415)

        if request.method == 'POST':
            # Parse json-string
            try:
                request.data = json.loads(request.body)
            except Exception as e:
                e = ValidationException(
                    ValidationException.INVALID_JSON_FORMAT,
                    e.message
                )
                return JsonResponse(e.to_dict(), status=400)

            # Validate json-parameters
            if self.validator_class:
                exception_response = self.validate_request(request)
                if exception_response:
                    return exception_response

        if not request.account:
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        return super(LoginRequiredFormMultipartView, self).dispatch(request, *args, **kwargs)


class NotifyIssueView(APIView):
    def post(self, request):
        phone = request.data.get('phone', None)
        try:
            validate_phone_number(phone)
        except ValidationError:
            e = ValidationException(ValidationException.VALIDATION_ERROR,
                                    'Invalid phone')
            return JsonResponse(e.to_dict(), status=400)
        NotifyIssue.objects.create(phone=phone)
        return JsonResponse({}, status=200)