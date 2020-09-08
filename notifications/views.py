# -*- coding: utf-8 -*-
import uuid

from django.http import JsonResponse
from base.views import APIView, LoginRequiredAPIView

# Create your views here.
from notifications.models import AccountDevice
from notifications.validators import RegisterAccountDeviceValidator, UnregisterAccountDeviceValidator


class RegisterAccountDevice(LoginRequiredAPIView):
    validator_class = RegisterAccountDeviceValidator

    def post(self, request, *args, **kwargs):
        device_type = request.data["device_type"]
        registration_id = request.data["registration_id"]

        AccountDevice.objects.get_or_create(
            account=request.account,
            device_id=str(uuid.uuid4()),
            type=device_type,
            registration_id=registration_id,
        )

        return JsonResponse({}, status=200)


class UnregisterAccountDevice(LoginRequiredAPIView):
    validator_class = UnregisterAccountDeviceValidator

    def post(self, request,  *args, **kwargs):
        registration_id = request.data["registration_id"]
        AccountDevice.objects.filter(registration_id=registration_id).delete()
        return JsonResponse({}, status=200)

