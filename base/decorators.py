#import from python
import json
from functools import wraps

from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

def rest_methods(methods=[]):
    def decorator(view_func):
        @csrf_exempt
        def handler(request, *args, **kwargs):
            if request.method not in methods:
                return HttpResponseNotAllowed(
                    permitted_methods=methods,
                    content_type="application/json")

            if request.META['CONTENT_TYPE'] != "application/json":
                return JsonResponse(status = 415)
            if request.body:
                try:
                    request.data = json.loads(request.body)
                except Exception as e:
                    return JsonResponse({"error":e.message})
            else:
                request.data = {}
            return view_func(request, *args, **kwargs)
        return wraps(view_func)(handler)
    return decorator