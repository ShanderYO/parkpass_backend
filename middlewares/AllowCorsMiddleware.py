import time
from hashlib import md5
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from rps_vendor.models import Developer


class AllowCorsMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response


    def process_response(self, req, resp):
        resp["Access-Control-Allow-Origin"] = "*"
        return resp