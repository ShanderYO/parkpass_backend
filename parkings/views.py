from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from dss.Serializer import serializer

from accounts.models import Account
from accounts.tasks import generate_current_debt_order
from base.exceptions import PermissionException
from base.exceptions import ValidationException
from base.utils import datetime_from_unix_timestamp_tz
from base.views import LoginRequiredAPIView, SignedRequestAPIView
from parkings.models import Parking, ParkingSession, ComplainSession, Wish
from parkings.tasks import process_updated_sessions
from parkings.validators import validate_longitude, validate_latitude, CreateParkingSessionValidator, \
    UpdateParkingSessionValidator, UpdateParkingValidator, CompleteParkingSessionValidator, \
    UpdateListParkingSessionValidator, ComplainSessionValidator, CreateParkingValidator


def check_permission(vendor, parking=None):
    if vendor.account_state == vendor.ACCOUNT_STATE.DISABLED:
        return False
    elif vendor.account_state == vendor.ACCOUNT_STATE.NORMAL:
        return True
    elif vendor.account_state == vendor.ACCOUNT_STATE.TEST:
        return parking is None or vendor.test_parking == parking
    else:
        raise ValueError('Illegal account state encountered')


class WishView(LoginRequiredAPIView):

    def get(self, request, *args, **kwargs):
        try:
            parking = Parking.objects.get(id=int(kwargs['parking']), approved=True)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Target parking with such id not found"
            )
            return JsonResponse(e.to_dict(), status=400)
        if parking.enabled:
            e = ValidationException(
                ValidationException.ALREADY_EXISTS,
                "This parking is already able to use"
            )
            return JsonResponse(e.to_dict(), status=400)
        user = request.account
        wp = Wish(parking=parking, user=user)
        wp.save()
        return JsonResponse({}, status=200)


class IssueParkingView(SignedRequestAPIView):
    validator_class = CreateParkingValidator

    def post(self, request):
        # max_client_debt, enabled, longitude, latitude, address, description, name
        if not check_permission(request.vendor):
            e = PermissionException(
                PermissionException.NO_PERMISSION,
                'Permission denied'
            )
            return JsonResponse(e.to_dict(), status=400)
        parking = Parking(
            name=self.request.data['name'],
            description=self.request.data['description'],
            address=self.request.data['address'],
            latitude=float(self.request.data['latitude']),
            longitude=float(self.request.data['longitude']),
            free_places=int(self.request.data['free_places']),
            approved=False,
            max_client_debt=int(self.request.data['max_client_debt'])
        )
        parking.save()
        return JsonResponse({}, status=200)


class GetParkingView(LoginRequiredAPIView):

    def get(self, request, *args, **kwargs):
        try:
            parking = Parking.objects.get(id=kwargs["pk"], approved=True)
            if not check_permission(request.vendor, parking):
                e = PermissionException(
                    PermissionException.NO_PERMISSION,
                    'Permission denied'
                )
                return JsonResponse(e.to_dict(), status=400)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Target parking with such id not found"
            )
            return JsonResponse(e.to_dict())
        result_dict = serializer(parking, exclude_attr=("created_at","enabled","vendor_id","max_client_debt",))
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

        parking_list = Parking.parking_manager.find_between_point(lt_point, rb_point)

        response_dict = dict()
        response_dict["result"] = serializer(
            parking_list, include_attr=("id","name","latitude","longitude","free_places")
        )
        return JsonResponse(response_dict, status=200)


class TestSignedRequestView(SignedRequestAPIView):

    def post(self, request):
        if not check_permission(request.vendor):
            e = PermissionException(
                PermissionException.NO_PERMISSION,
                'Permission denied'
            )
            return JsonResponse(e.to_dict(), status=400)
        res = {}
        for key in request.data:
            res[key] = request.data[key]
        return JsonResponse(res, status=200)


class UpdateParkingView(SignedRequestAPIView):
    validator_class = UpdateParkingValidator

    def post(self, request):
        parking_id = int(request.data["parking_id"])
        free_places = int(request.data["free_places"])

        try:
            parking = Parking.objects.get(id=parking_id, vendor=request.vendor, approved=True)
            parking.free_places = free_places
            if not check_permission(request.vendor, parking):
                e = PermissionException(
                    PermissionException.NO_PERMISSION,
                    'Permission denied'
                )
                return JsonResponse(e.to_dict(), status=400)
            parking.save()
            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with id %s for vendor '%s' not found" % (parking_id, request.vendor.name)
            )
            return JsonResponse(e.to_dict(), status=400)


class CreateParkingSessionView(SignedRequestAPIView):
    validator_class = CreateParkingSessionValidator

    def post(self, request):
        session_id = str(request.data["session_id"])
        parking_id = int(request.data["parking_id"])
        client_id = int(request.data["client_id"])
        started_at = int(request.data["started_at"])

        try:
            parking = Parking.objects.get(id=parking_id, vendor=request.vendor, approved=True)
            if not check_permission(request.vendor, parking):
                e = PermissionException(
                    PermissionException.NO_PERMISSION,
                    'Permission denied'
                )
                return JsonResponse(e.to_dict(), status=400)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with id %s for vendor '%s' not found" % (parking_id, request.vendor.name)
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            account = Account.objects.get(id=client_id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Client with such id not found"
            )
            return JsonResponse(e.to_dict(), status=400)

        started_at = datetime_from_unix_timestamp_tz(started_at)
        session = None
        try:
            session = ParkingSession.objects.get(session_id=session_id, parking=parking)
            if session.is_started_by_vendor():
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Session has already started by vendor"
                )
                return JsonResponse(e.to_dict(), status=400)
            session.add_vendor_start_mark()

        except ObjectDoesNotExist:
            session = ParkingSession(
                session_id=session_id,
                client=account,
                parking=parking,
                state=ParkingSession.STATE_STARTED_BY_VENDOR,
                started_at=started_at
            )
        try:
            session.save()
        except IntegrityError as e:
            e = ValidationException(
                ValidationException.ALREADY_EXISTS,
                "'session_id' value %s for 'parking_id' %s is already exist" % (session_id, parking_id)
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class CancelParkingSessionView(SignedRequestAPIView):
    validator_class = UpdateParkingSessionValidator

    def post(self, request):
        session_id = str(request.data["session_id"])
        parking_id = int(request.data["parking_id"])

        try:
            session = ParkingSession.objects.get(
                session_id=session_id,
                parking__id=parking_id,
                parking__vendor=request.vendor,
            )
            if not check_permission(request.vendor, Parking.objects.get(id=parking_id)):
                e = PermissionException(
                    PermissionException.NO_PERMISSION,
                    'Permission denied'
                )
                return JsonResponse(e.to_dict(), status=400)
            # Check if session is is_cancelable
            if not session.is_cancelable():
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Parking session cancelling error. Current state: %s" % self.state
                )
                return JsonResponse(e.to_dict(), status=400)

            session.state = ParkingSession.STATE_CANCELED
            session.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with session_id %s for parking %s does not exist" % (session_id, parking_id)
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class UpdateParkingSessionView(SignedRequestAPIView):
    validator_class = UpdateParkingSessionValidator

    def post(self, request):
        session_id = str(request.data["session_id"])
        parking_id = int(request.data["parking_id"])
        debt = float(request.data["debt"])
        updated_at = int(request.data["updated_at"])

        updated_at = datetime_from_unix_timestamp_tz(updated_at)

        try:
            session = ParkingSession.objects.get(
                session_id=session_id, parking__id=parking_id, parking__vendor=request.vendor
            )
            if not check_permission(request.vendor, Parking.objects.get(id=parking_id)):
                e = PermissionException(
                    PermissionException.NO_PERMISSION,
                    'Permission denied'
                )
                return JsonResponse(e.to_dict(), status=400)
            if not session.is_started_by_vendor():
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Parking session is not started by vendor. Please create session"
                )
                return JsonResponse(e.to_dict(), status=400)

            # Check if session is canceled
            if not session.is_available_for_vendor_update():
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Parking session has canceled or completed state"
                )
                return JsonResponse(e.to_dict(), status=400)

            session.debt = debt
            session.updated_at = updated_at
            session.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with session_id %s for parking %s does not exist" % (session_id, parking_id)
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class CompleteParkingSessionView(SignedRequestAPIView):
    validator_class = CompleteParkingSessionValidator

    def post(self, request):
        session_id = str(request.data["session_id"])
        parking_id = int(request.data["parking_id"])
        debt = float(request.data["debt"])
        completed_at = int(request.data["completed_at"])

        completed_at = datetime_from_unix_timestamp_tz(completed_at)

        try:
            session = ParkingSession.objects.get(
                session_id=session_id,
                parking__id=parking_id,
                parking__vendor=request.vendor
            )
            if not check_permission(request.vendor, Parking.objects.get(id=parking_id)):
                e = PermissionException(
                    PermissionException.NO_PERMISSION,
                    'Permission denied'
                )
                return JsonResponse(e.to_dict(), status=400)
            # Check if session was already not active
            if not session.is_active():
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Parking session with session_id %s for parking %s is completed" % (session_id, parking_id)
                )
                return JsonResponse(e.to_dict(), status=400)

            session.debt = debt
            session.completed_at = completed_at
            session.add_vendor_complete_mark()
            session.save()
            generate_current_debt_order(session.id)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with session_id %s for parking %s does not exist" % (session_id, parking_id)
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class ParkingSessionListUpdateView(SignedRequestAPIView):
    validator_class = UpdateListParkingSessionValidator

    def post(self, request):
        parking_id = int(request.data["parking_id"])
        sessions = request.data["sessions"]
        try:
            parking = Parking.objects.get(id=parking_id, vendor=request.vendor, approved=True)
            process_updated_sessions(parking, sessions)
            if not check_permission(request.vendor, parking_id):
                e = PermissionException(
                    PermissionException.NO_PERMISSION,
                    'Permission denied'
                )
                return JsonResponse(e.to_dict(), status=400)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with id %s for vendor '%s' not found" % (parking_id, request.vendor.name)
            )
            return JsonResponse(e.to_dict(), status=400)
        return JsonResponse({}, status=202)


class ComplainSessionView(LoginRequiredAPIView):
    validator_class = ComplainSessionValidator

    def post(self, request, *args, **kwargs):
        complain_type = int(request.data["type"])
        message = request.data["message"]
        session_id = int(request.data["session_id"])

        try:
            parking_session = ParkingSession.objects.get(id=session_id)
            ComplainSession.objects.create(
                type=complain_type,
                message=message,
                account=request.account,
                session=parking_session,
            )
            if not check_permission(request.vendor, parking_session.parking):
                e = PermissionException(
                    PermissionException.NO_PERMISSION,
                    'Permission denied'
                )
                return JsonResponse(e.to_dict(), status=400)
            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with id %s does not exist" % session_id
            )
            return JsonResponse(e.to_dict(), status=400)