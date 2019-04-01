from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse

from base.exceptions import ValidationException
from base.views import SignedRequestAPIView
from parkings.models import Parking
from parkings.views import CreateParkingSessionView, UpdateParkingSessionView, CancelParkingSessionView, \
    CompleteParkingSessionView
from rps_vendor.tasks import rps_process_updated_sessions
from rps_vendor.validators import RpsCreateParkingSessionValidator, RpsUpdateParkingSessionValidator, \
    RpsCancelParkingSessionValidator, RpsCompleteParkingSessionValidator, RpsUpdateListParkingSessionValidator


class RpsCreateParkingSessionView(SignedRequestAPIView):
    validator_class = RpsCreateParkingSessionValidator

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            request.data["session_id"] = str(request.data["client_id"])+"&"+str(request.data["started_at"])
            return CreateParkingSessionView().post(request, *args, **kwargs)


class RpsUpdateParkingSessionView(SignedRequestAPIView):
    validator_class = RpsUpdateParkingSessionValidator

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            request.data["session_id"] = str(request.data["client_id"]) + "&" + str(request.data["started_at"])
            return UpdateParkingSessionView().post(request, *args, **kwargs)


class RpsCancelParkingSessionView(SignedRequestAPIView):
    validator_class = RpsCancelParkingSessionValidator

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            request.data["session_id"] = str(request.data["client_id"]) + "&" + str(request.data["started_at"])
            return CancelParkingSessionView().post(request, *args, **kwargs)


class RpsCompleteParkingSessionView(SignedRequestAPIView):
    validator_class = RpsCompleteParkingSessionValidator

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            request.data["session_id"] = str(request.data["client_id"]) + "&" + str(request.data["started_at"])
            return CompleteParkingSessionView().post(request, *args, **kwargs)


class RpsParkingSessionListUpdateView(SignedRequestAPIView):
    validator_class = RpsUpdateListParkingSessionValidator

    def post(self, request):
        parking_id = int(request.data["parking_id"])
        sessions = request.data["sessions"]
        try:
            parking = Parking.objects.get(id=parking_id, vendor=request.vendor)
            rps_process_updated_sessions.delay(parking_id, sessions)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with id %s for vendor '%s' not found" % (parking_id, request.vendor.name)
            )
            return JsonResponse(e.to_dict(), status=400)
        return JsonResponse({}, status=202)