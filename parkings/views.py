import datetime
import pytz
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from dss.Serializer import serializer

from accounts.models import Account
from base.exceptions import ValidationException
from base.views import LoginRequiredAPIView, APIView
from parkings.models import Parking, ParkingSession
from parkings.validators import validate_longitude, validate_latitude, CreateParkingSessionValidator, \
    CancelParkingSessionValidator, UpdateParkingSessionValidator, UpdateParkingValidator, \
    CompleteParkingSessionValidator


class GetParkingView(LoginRequiredAPIView):
    def get(self, request, *args, **kwargs):
        try:
            parking = Parking.objects.get(id=kwargs["pk"])
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Target parking with such id not found"
            )
            return JsonResponse(e.to_dict())
        result_dict = serializer(parking, exclude_attr=("created_at","enabled",))
        return JsonResponse(result_dict, status=200)


class GetParkingViewList(LoginRequiredAPIView):
    def get(self, request):
        left_top_latitude = request.GET.get("lt_lat", None)
        left_top_longitude = request.GET.get("lt_lon", None)
        right_bottom_latitude = request.GET.get("rb_lat", None)
        right_bottom_longitude = request.GET.get("rb_lon", None)

        if not left_top_latitude or not left_top_longitude or not right_bottom_latitude or not right_bottom_longitude:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Invalid get parameters"
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            validate_latitude(left_top_latitude)
            validate_longitude(left_top_longitude)
            validate_latitude(right_bottom_latitude)
            validate_longitude(right_bottom_longitude)

            left_top_latitude = float(left_top_latitude)
            left_top_longitude = float(left_top_longitude)
            right_bottom_latitude = float(right_bottom_latitude)
            right_bottom_longitude = float(right_bottom_longitude)

        except ValidationError as e:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                e.message
            )
            return JsonResponse(e.to_dict(), status=400)

        lt_point = (left_top_latitude, left_top_longitude)
        rb_point = (right_bottom_latitude, right_bottom_longitude)

        parking_list = Parking.find_between_point(lt_point, rb_point)

        response_dict = dict()
        response_dict["result"] = serializer(
            parking_list, include_attr=("id","name","latitude","longitude","free_places")
        )
        return JsonResponse(response_dict, status=200)


class UpdateParkingView(APIView):
    validator_class = UpdateParkingValidator

    def post(self, request):
        parking_id = int(request.data["parking_id"])
        free_places = int(request.data["free_places"])
        # TODO check signature or hmac
        try:
            parking = Parking.objects.get(id=parking_id)
            parking.free_places = free_places
            parking.save()
            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with such id not found"
            )
            return JsonResponse(e.to_dict(), status=400)


class CreateParkingSessionView(APIView):
    validator_class = CreateParkingSessionValidator

    def post(self, request):
        session_id = request.data["session_id"]
        parking_id = int(request.data["parking_id"])
        client_id = int(request.data["client_id"])
        started_at = int(request.data["started_at"])

        try:
            parking = Parking.objects.get(id=parking_id)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with such id not found"
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            account = Account.objects.get(id=client_id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Account with such id not found"
            )
            return JsonResponse(e.to_dict(), status=400)

        started_at_date = datetime.datetime.fromtimestamp(int(started_at))
        started_at_date_tz = pytz.utc.localize(started_at_date)

        session = ParkingSession(session_id=session_id, client=account,
                                 parking=parking, started_at=started_at_date_tz)
        try:
            session.save()
        except Exception as e:
            e = ValidationException(
                ValidationException.ALREADY_EXISTS,
                "Parking Session with such id for this parking is found"
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class UpdateParkingSessionView(APIView):
    validator_class = UpdateParkingSessionValidator

    def post(self, request):
        session_id = request.data["session_id"]
        debt = float(request.data["debt"])
        updated_at = int(request.data["updated_at"])

        updated_at_date = datetime.datetime.fromtimestamp(int(updated_at))
        updated_at_date_tz = pytz.utc.localize(updated_at_date)

        try:
            session = ParkingSession.objects.get(session_id=session_id)
            session.debt = debt
            session.updated_at = updated_at_date_tz
            session.state = ParkingSession.STATE_SESSION_UPDATED
            session.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Session does not exists"
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class CompleteParkingSessionView(APIView):
    validator_class = CompleteParkingSessionValidator

    def post(self, request):
        session_id = request.data["session_id"]
        debt = int(request.data["debt"])
        completed_at = int(request.data["completed_at"])

        completed_at_date = datetime.datetime.fromtimestamp(int(completed_at))
        completed_at_date_tz = pytz.utc.localize(completed_at_date)

        try:
            session = ParkingSession.objects.get(session_id=session_id)
            session.debt = debt
            session.completed_at = completed_at_date_tz
            session.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Session does not exists"
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class ParkingSessionCancelView(APIView):
    validator_class = CancelParkingSessionValidator

    def post(self, request):
        session_id = request.data["session_id"]
        try:
            session = ParkingSession.objects.get(id=session_id)
            session.delete()
            return JsonResponse({}, 200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Session does not exists"
            )
            return JsonResponse(e.serialize(), 400)

        return JsonResponse({}, 200)


class ParkingSessionListUpdateView(APIView):
    def post(self, request):
        sessions = request.data["sessions"]
        return JsonResponse({}, 200)