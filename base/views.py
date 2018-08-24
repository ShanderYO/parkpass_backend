# Python import
import hashlib
import hmac
import json

# Django import
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

# App import
from base import AccountTypes
from accounts.models import Account
from base.exceptions import ValidationException, AuthException, PermissionException
from base.validators import ValidatePostParametersMixin


class APIView(View, ValidatePostParametersMixin):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):

        # Only application/json Content-type allow
        if not request.META.get('CONTENT_TYPE', "").startswith("application/json") and request.POST:
            return JsonResponse({
                "error":"HTTP Status 415 - Unsupported Media Type"
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

        return super(APIView, self).dispatch(request, *args, **kwargs)


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
            request.vendor = Account.objects.get(
                ven_name=str(request.META["HTTP_X_VENDOR_NAME"]),
                account_type=AccountTypes.VENDOR
            )
            """
            if request.vendor.account_type != AccountTypes.VENDOR:
                e = PermissionException(
                    PermissionException.VENDOR_NOT_FOUND,
                    "This account has no vendor privelegies"
                )
                return JsonResponse(e.to_dict(), status=400)
            """
        except ObjectDoesNotExist:
            e = PermissionException(
                PermissionException.VENDOR_NOT_FOUND,
                "Vendor does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)

        signature = hmac.new(str(request.vendor.ven_secret), request.body, hashlib.sha512)

        if signature.hexdigest() != request.META["HTTP_X_SIGNATURE"].lower():
            e = PermissionException(
                PermissionException.SIGNATURE_INVALID,
                "Invalid signature"
            )
            print signature.hexdigest()
            return JsonResponse(e.to_dict(), status=400)

        return super(SignedRequestAPIView, self).dispatch(request, *args, **kwargs)


class LoginRequiredAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, "account") or not request.account:
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        return super(LoginRequiredAPIView, self).dispatch(request, *args, **kwargs)


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
