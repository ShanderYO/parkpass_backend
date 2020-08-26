# -*- coding: utf-8 -*-

from django.http import JsonResponse
from base.views import APIView, LoginRequiredAPIView

# Create your views here.
from notifications.models import AccountDevice


class RegisterAccountDevice(APIView):
    def post(self, request, *args, **kwargs):
        device_id = request.data["device_id"]
        device_type = request.data["device_type"]
        registration_id = request.data["registration_id"]

        AccountDevice.objects.get_or_create(
            device_id=device_id,
            type=device_type,
            registration_id=registration_id,
        )

        return JsonResponse({}, status=200)


class UnregisterAccountDevice(APIView):
    def post(self, request,  *args, **kwargs):
        device_id = request.data["device_id"]
        AccountDevice.objects.filter(device_id=device_id).delete()
        return JsonResponse({}, status=200)
