# -*- coding: utf-8 -*-
import base64
import traceback
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.views import View
from dss.Serializer import serializer

from accounts.models import Account
from accounts.tasks import generate_current_debt_order
from base.exceptions import PermissionException
from base.exceptions import ValidationException
from base.utils import datetime_from_unix_timestamp_tz, parse_int, get_logger
from base.views import generic_login_required_view, SignedRequestAPIView, APIView
from owners.models import Owner, OwnerApplication
from parkings.models import Parking, ParkingSession, ComplainSession, Wish
from parkings.tasks import process_updated_sessions
from parkings.validators import validate_longitude, validate_latitude, CreateParkingSessionValidator, \
    UpdateParkingSessionValidator, UpdateParkingValidator, CompleteParkingSessionValidator, \
    UpdateListParkingSessionValidator, ComplainSessionValidator, SubscriptionsPayValidator
from payments.models import Order, TinkoffPayment, PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED, \
    HomeBankPayment
from rps_vendor.models import RpsSubscription, RpsParking
from vendors.models import Vendor, VendorNotification, VENDOR_NOTIFICATION_TYPE_SESSION_CREATED, \
    VENDOR_NOTIFICATION_TYPE_SESSION_COMPLETED

LoginRequiredAPIView = generic_login_required_view(Account)
VendorAPIView = generic_login_required_view(Vendor)
OwnerAPIView = generic_login_required_view(Owner)


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
            parking = Parking.objects.get(id=int(kwargs['parking']), approved=False)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Target parking with such id and not approved is not found"
            )
            return JsonResponse(e.to_dict(), status=400)
        """
        if parking.enabled:
            e = ValidationException(
                ValidationException.ALREADY_EXISTS,
                "This parking is already able to use"
            )
            return JsonResponse(e.to_dict(), status=400)
        """

        user = request.account
        wish = Wish.objects.create(parking=parking, user=user)
        wish.add_account(user)
        return JsonResponse({}, status=200)


class CountWishView(OwnerAPIView):
    def get(self, request, parking):
        try:
            w = Wish.objects.get(parking__id=parking)
        except ObjectDoesNotExist:
            return JsonResponse({'count': 0}, status=200)
        return JsonResponse({'count': len(w)}, status=200)


class ParkingStatisticsView(LoginRequiredAPIView):
    def post(self, request):
        try:
            id = int(request.data.get("pk", -1))
            start_from = int(request.data.get("start", -1))
            stop_at = int(request.data.get("end", -1))
            page = int(request.data.get("page", 0))
            count = int(request.data.get("count", 10))
        except ValueError:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "All fields must be int"
            )
            return JsonResponse(e.to_dict(), status=400)
        if id < 0 or stop_at < start_from:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "One or more required parameters isn't specified correctly"
            )
            return JsonResponse(e.to_dict(), status=400)
        try:
            parking = Parking.objects.get(id=id, vendor=request.vendor)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Target parking with such id not found"
            )
            return JsonResponse(e.to_dict(), status=400)
        stat = ParkingSession.objects.filter(
            parking=parking,
            started_at__gt=datetime_from_unix_timestamp_tz(start_from) if start_from > -1
            else timezone.now() - timezone.timedelta(days=31),
            started_at__lt=datetime_from_unix_timestamp_tz(stop_at) if stop_at > -1 else timezone.now()
        )
        lst = []
        length = len(stat)
        if len(stat) > count:
            stat = stat[page * count:(page + 1) * count]
        for ps in stat:
            lst.append(
                serializer(ps)
            )
        return JsonResponse({'sessions': lst, 'count': length})


class AllParkingsStatisticsView(LoginRequiredAPIView):
    def post(self, request):
        try:
            ids = map(int, request.data.get('ids', []).replace(' ', '').split(','))
            start_from = int(request.data.get("start", -1))
            stop_at = int(request.data.get("end", -1))
            page = int(request.data.get("page", 0))
            count = int(request.data.get("count", 10))
        except ValueError:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "All fields must be int"
            )
            return JsonResponse(e.to_dict(), status=400)
        if stop_at < start_from:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "'stop' should be greater than 'start'"
            )
            return JsonResponse(e.to_dict(), status=400)
        result = []

        if ids:
            pks = Parking.objects.filter(id__in=ids)
        else:
            pks = Parking.objects.all()

        for pk in pks:
            ps = ParkingSession.objects.filter(
                parking=pk,
                started_at__gt=datetime_from_unix_timestamp_tz(start_from) if start_from > -1
                else timezone.now() - timedelta(days=31),
                started_at__lt=datetime_from_unix_timestamp_tz(stop_at) if stop_at > -1 else timezone.now(),
                state__gt=3  # Only completed sessions
            )

            sessions_count = len(ps)
            order_sum = 0
            avg_time = 0
            for session in ps:
                order_sum += session.debt
                avg_time += (
                            session.completed_at - session.started_at).total_seconds()  # При переезде на новую версию Django: реализовать с помощью https://stackoverflow.com/questions/3131107/annotate-a-queryset-with-the-average-date-difference-django
            try:
                avg_time = avg_time / sessions_count
            except ZeroDivisionError:
                pass

            result.append({
                'parking_id': pk.id,
                'parking_name': pk.name,
                'sessions_count': sessions_count,
                'avg_parking_time': avg_time,
                'order_sum': order_sum,
            })
        length = len(result)
        if len(result) > count:
            result = result[page * count:(page + 1) * count]
        return JsonResponse({'parkings': result, 'count': length}, status=200)


class GetParkingViewMixin:
    def get(self, request, *args, **kwargs):
        try:
            parking = Parking.objects.get(id=kwargs["pk"])
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Target parking with such id not found"
            )
            return JsonResponse(e.to_dict(), status=400)
        result_dict = serializer(parking, exclude_attr=("vendor_id", "company_id", "max_client_debt",
                                                        "tariff", "tariff_file_name", "tariff_file_content"))
        return JsonResponse(result_dict, status=200)


class GetParkingView(GetParkingViewMixin, LoginRequiredAPIView):
    pass


class GetTariffParkingView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden("Operation isn't permitted!")

        try:
            parking = Parking.objects.get(id=int(kwargs["pk"]))
            if parking.tariff_file_content:
                file_data = base64.b64decode(parking.tariff_file_content)
                bytes_out = BytesIO()
                bytes_out.write(file_data)
                response = HttpResponse(
                    bytes_out.getvalue(),
                    content_type="application/pdf"
                )
                name = "parking_%d_tariff.pdf" % parking.id
                response["Content-Disposition"] = "attachment; filename={}".format(name)
                return response
            return HttpResponse("Empty file content. Decoding error")

        except ObjectDoesNotExist:
            return HttpResponse("Parking doesn't exist. Please check link again")
        except TypeError:
            return HttpResponse("Invalid file content. Decoding error")


class GetParkingViewListMixin:
    def get(self, request, *args, **kwargs):
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
                str(e)
            )
            return JsonResponse(e.to_dict(), status=400)

        lt_point = (left_top_latitude, left_top_longitude)
        rb_point = (right_bottom_latitude, right_bottom_longitude)

        parking_list = Parking.parking_manager.find_between_point(lt_point, rb_point)

        response_dict = dict()
        response_dict["result"] = serializer(
            parking_list, include_attr=("id", "name", "latitude",
                                        "longitude", "free_places", "approved",)
        )
        return JsonResponse(response_dict, status=200)


class GetParkingViewList(GetParkingViewListMixin, LoginRequiredAPIView):
    pass


class GetAvailableParkingsView(APIView):
    def get(self, request):
        last_parking_id = parse_int(request.GET.get('last_parking_id', 0))
        if last_parking_id is None:
            last_parking_id = 0
        parkings = Parking.objects.filter(approved=True, id__gt=last_parking_id)
        if parkings.count() == 0:
            return JsonResponse({}, status=304)
        else:
            parkings_list = serializer(Parking.objects.filter(approved=True),
                                       include_attr=('id', 'name', 'description', 'address',
                                                     'latitude', 'longitude', 'free_places','max_permitted_time', 'currency', 'acquiring'))
            return JsonResponse({"result":parkings_list}, status=200)


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
        vendor_id = request.data.get("vendor_id", None)

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

        utc_started_at = parking.get_utc_parking_datetime(started_at)

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
            session.started_at = utc_started_at
            session.vendor_id = int(vendor_id) if vendor_id else 0

        except ObjectDoesNotExist:
            # check active session
            last_active_session = ParkingSession.get_active_session(account)
            if last_active_session:
                last_active_session.state = ParkingSession.STATE_VERIFICATION_REQUIRED
                last_active_session.suspended_at = utc_started_at
                last_active_session.save()

            session = ParkingSession(
                session_id=session_id,
                client=account,
                parking=parking,
                state=ParkingSession.STATE_STARTED_BY_VENDOR,
                started_at=utc_started_at
            )
            session.vendor_id = int(vendor_id) if vendor_id else 0
        try:
            session.save()

        except IntegrityError as e:
            e = ValidationException(
                ValidationException.ALREADY_EXISTS,
                "'session_id' value %s for 'parking_id' %s is already exist" % (session_id, parking_id)
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            VendorNotification.objects.create(
                parking_session=session,
                type=VENDOR_NOTIFICATION_TYPE_SESSION_CREATED)
        except Exception as e:
            get_logger().info(str(e))

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
                    "Parking session cancelling error. Current state: %s" % session.state
                )
                return JsonResponse(e.to_dict(), status=400)

            # Anyway reset mask
            session.reset_client_completed_state()

            # Reset completed time
            if session.completed_at:
                session.completed_at = None

            # If user didn't get in
            if not session.is_started_by_vendor():
                session.state = ParkingSession.STATE_CANCELED
            session.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with session_id %s for parking %s does not exist" % (session_id, parking_id)
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            VendorNotification.objects.filter(
                parking_session=session,
                type=VENDOR_NOTIFICATION_TYPE_SESSION_CREATED
            ).delete()

        except Exception as e:
            get_logger().info(str(e))

        return JsonResponse({}, status=200)


class UpdateParkingSessionView(SignedRequestAPIView):
    validator_class = UpdateParkingSessionValidator

    def post(self, request):
        session_id = str(request.data["session_id"])
        parking_id = int(request.data["parking_id"])
        debt = float(request.data["debt"])
        updated_at = int(request.data["updated_at"])

        try:
            session = ParkingSession.objects.select_related('parking').get(
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

            utc_updated_at = session.parking.get_utc_parking_datetime(updated_at)

            session.debt = debt
            session.updated_at = utc_updated_at
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

        try:
            session = ParkingSession.objects.select_related('parking').get(
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

            utc_completed_at = session.parking.get_utc_parking_datetime(completed_at)

            # payment
            session_orders = session.get_session_orders()

            for order in session_orders:
                if (order.acquiring == 'homebank'):
                    payments = HomeBankPayment.objects.filter(order=order)
                    for payment in payments:
                        if payment.status == PAYMENT_STATUS_AUTHORIZED:
                            order.confirm_payment_homebank(payment)
                            break
                else:
                    payments = TinkoffPayment.objects.filter(order=order)
                    for payment in payments:
                        if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                            order.confirm_payment(payment)
                            break
            # end payment

            session.debt = debt
            session.completed_at = utc_completed_at
            session.add_vendor_complete_mark()
            session.save()
            generate_current_debt_order.delay(session.id)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with session_id %s for parking %s does not exist" % (session_id, parking_id)
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            VendorNotification.objects.create(
                parking_session=session,
                type=VENDOR_NOTIFICATION_TYPE_SESSION_COMPLETED)
        except Exception as e:
            get_logger().info(str(e))

        return JsonResponse({}, status=200)


class ParkingSessionListUpdateView(SignedRequestAPIView):
    validator_class = UpdateListParkingSessionValidator

    def post(self, request):
        parking_id = int(request.data["parking_id"])
        sessions = request.data["sessions"]
        try:
            Parking.objects.get(id=parking_id,
                                vendor=request.vendor,
                                approved=True)

            process_updated_sessions.delay(parking_id, sessions)
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
            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with id %s does not exist" % session_id
            )
            return JsonResponse(e.to_dict(), status=400)


class GetAvailableSubscriptionsView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            rps_parking = RpsParking.objects.select_related('parking').get(parking__id=int(kwargs["pk"]))
            if rps_parking.parking.rps_subscriptions_available:
                url = rps_parking.request_get_subscriptions_list_url
                result_dict = RpsSubscription.get_subscription(url)
                if result_dict:
                    return JsonResponse(result_dict, status=200)
                else:
                    return JsonResponse({}, status=400)
            else:
                raise ObjectDoesNotExist()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.ACTION_UNAVAILABLE,
                "This parking don't support subscriptions"
            )
            return JsonResponse(e.to_dict(), status=400)


class SubscriptionsPayView(LoginRequiredAPIView):
    validator_class = SubscriptionsPayValidator

    def post(self, request, *args, **kwargs):
        name = request.data["name"]
        sum = int(request.data["sum"])
        duration = int(request.data["duration"])

        idts = request.data["idts"]
        id_transition = request.data["id_transition"]

        parking_id = int(request.data["parking_id"])
        prolongation = bool(request.data.get("prolong", False))

        # TODO get description
        description = request.data.get("description", "")
        data = request.data.get("data", None)

        try:
            parking = Parking.objects.get(id=parking_id)
            if not parking.rps_subscriptions_available:
                e = ValidationException(
                    ValidationException.ACTION_UNAVAILABLE,
                    "This parking don't support subscriptions"
                )
                return JsonResponse(e.to_dict(), status=400)

            subscription = RpsSubscription.objects.create(
                name=name, description=description,
                sum=sum, started_at=timezone.now(),
                duration=duration,
                prolongation=prolongation,
                expired_at=timezone.now() + timedelta(seconds=duration),
                parking=parking,
                data=data,
                account=request.account,
                idts=idts, id_transition=id_transition
            )
            subscription.create_order_and_pay()
            return JsonResponse({"subscription_id": subscription.id}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with id %s does not exist" % parking_id
            )
            return JsonResponse(e.to_dict(), status=400)


class SubscriptionsPayStatusView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            subs = RpsSubscription.objects.get(id=kwargs["pk"])
            result_dict = serializer(subs, include_attr=("id", "name", "description", "data",
                                                         "started_at", "idts", "id_transition", "unlimited",
                                                         "state", "error_message"))
            return JsonResponse(result_dict, status=200)

        except ObjectDoesNotExist:
            pass

        e = ValidationException(
            ValidationException.RESOURCE_NOT_FOUND,
            "Target subscription with order such id not found"
        )
        return JsonResponse(e.to_dict(), status=400)


class CloseSessionRequest(APIView):
    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            try:
                active_session = ParkingSession.objects.get(id=request.GET['session_id'])
                session_orders = active_session.get_session_orders()
                debt_sum = Decimal(request.GET['sum'])
                sum_to_pay = debt_sum
                target_refund_sum = 0

                for order in session_orders:
                    if sum_to_pay >= order.sum:
                        # pay
                        if (order.acquiring == 'homebank'):
                            payments = HomeBankPayment.objects.filter(order=order)
                            for payment in payments:
                                if payment.status == PAYMENT_STATUS_AUTHORIZED:
                                    order.confirm_payment_homebank(payment)
                                    break

                            sum_to_pay = sum_to_pay - order.sum
                        else:
                            payments = TinkoffPayment.objects.filter(order=order)
                            for payment in payments:
                                if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                                    order.confirm_payment(payment)
                                    break
                            sum_to_pay = sum_to_pay - order.sum
                    else:
                        # refund
                        target_refund_sum = target_refund_sum + order.sum

                        order.need_refund = True
                        order.save()
                        print(sum_to_pay)
                        # sum_to_pay = 0
                        get_logger().info('refund sum 1 %s' % target_refund_sum)

                if target_refund_sum:
                    active_session.try_refund = True
                    active_session.target_refund_sum = target_refund_sum
                    get_logger().info('refund sum 2 %s' % target_refund_sum)

                if sum_to_pay:
                    new_order = Order.objects.create(
                        session=active_session,
                        sum=sum_to_pay,
                        acquiring=active_session.parking.acquiring)
                    new_order.try_pay()
                    get_logger().info('manual close 0')

                    if (new_order.acquiring == 'homebank'):
                        get_logger().info('manual close 1')
                        payments = HomeBankPayment.objects.filter(order=new_order)
                        for payment in payments:
                            get_logger().info('manual close 2 - %s %s' % (payment.status, payment.payment_id))
                            get_logger().info(payment.status == PAYMENT_STATUS_AUTHORIZED)
                            get_logger().info(type(payment.status))
                            get_logger().info(type(PAYMENT_STATUS_AUTHORIZED))

                            if payment.status == PAYMENT_STATUS_AUTHORIZED:
                                get_logger().info('manual close 3')
                                new_order.confirm_payment_homebank(payment)
                                break
                    else:
                        payments = TinkoffPayment.objects.filter(order=new_order)
                        for payment in payments:
                            if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                                new_order.confirm_payment(payment)
                                break
                        print(sum_to_pay)

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    'Сессия успешно закрыта'
                )

                old_debt = active_session.debt
                canceled_sum = old_debt - debt_sum
                if canceled_sum >= 0:
                    active_session.canceled_sum = canceled_sum

                active_session.state = ParkingSession.STATE_CLOSED
                active_session.manual_close = True
                active_session.debt = debt_sum
                active_session.save()

            except Exception as e:
                trace_back = traceback.format_exc()
                message = str(e) + " " + str(trace_back)
                messages.add_message(
                    request,
                    messages.ERROR,
                    message
                )

            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

