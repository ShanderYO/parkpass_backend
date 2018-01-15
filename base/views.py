# Python import
import json

# Django import
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.http import JsonResponse

# App import
from base.exceptions import ValidationException, AuthException
from base.validators import ValidatePostParametersMixin


class APIView(View, ValidatePostParametersMixin):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):

        # Only application/json Content-type allow
        if request.META['CONTENT_TYPE'] != "application/json":
            return JsonResponse({
                "error":"HTTP Status 415 - Unsupported Media Type"
            }, status=415)

        if request.method == 'POST':
            # Parse json-string
            try:
                request.data = json.loads(self.request.POST.get("data", '{}'))
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


class LoginRequiredAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not request.account:
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        return super(LoginRequiredAPIView, self).dispatch(request, *args, **kwargs)


class LoginRequiredFormMultipartView(View, ValidatePostParametersMixin):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):

        # Only multipart/form-data Content-type allow
        if request.META['CONTENT_TYPE'] != "multipart/form-data":
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
