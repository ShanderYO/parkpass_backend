import time
from hashlib import md5
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from rps_vendor.models import Developer


class ApiTokenMiddleware(MiddlewareMixin):
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


    def process_request(self, request):

        unix_timestamp = request.request.data.get("time", False)
        developer_id = request.request.data.get("developer_id", False)
        hash = request.request.data.get("hash", False)

        if not unix_timestamp or not developer_id or not hash:
            return JsonResponse({"status": "error", "message": "Required params empty"}, status=400)

        if int(time.time()) - int(unix_timestamp) > 30:
            return JsonResponse({"status": "error", "message": "Time for query expired"}, status=400)

        try:
            developer = Developer.objects.get(developer_id=developer_id)
        except Developer.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Developer not found"}, status=400)

        if not developer.api_key:
            return JsonResponse({"status": "error", "message": "Developer dont have access to API"}, status=400)

        if developer.is_blocked:
            return JsonResponse({"status": "error", "message": "Developer KEY blocked"}, status=400)

        hash_to_compare = md5((str(unix_timestamp) + str(developer.developer_id) + developer.api_key).encode("utf-8")).hexdigest()

        if hash_to_compare != hash:
            return JsonResponse({"status": "error", "message": "Wrong access token"}, status=400)

