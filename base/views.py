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
from base.exceptions import ValidationException, AuthException, PermissionException
from base.validators import ValidatePostParametersMixin
from vendors.models import Vendor


class APIView(View, ValidatePostParametersMixin):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):

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
            request.vendor = Vendor.objects.get(
                name=str(request.META["HTTP_X_VENDOR_NAME"])
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


class VendorAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, "vendor") or not request.vendor:
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        return super(VendorAPIView, self).dispatch(request, *args, **kwargs)


class OwnerAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, "owner") or not request.owner:
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        return super(OwnerAPIView, self).dispatch(request, *args, **kwargs)


class AdminAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, "admin") or not request.admin:
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        return super(AdminAPIView, self).dispatch(request, *args, **kwargs)


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
