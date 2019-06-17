import uuid
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse

from base.exceptions import ValidationException
from base.utils import get_logger
from base.views import SignedRequestAPIView, APIView, LoginRequiredAPIView
from parkings.models import Parking
from parkings.views import CreateParkingSessionView, UpdateParkingSessionView, CancelParkingSessionView, \
    CompleteParkingSessionView
from payments.models import Order, TinkoffPayment
from rps_vendor.models import ParkingCard, RpsParking, RpsParkingCardSession, STATE_CREATED, STATE_INITED, STATE_ERROR
from rps_vendor.tasks import rps_process_updated_sessions
from rps_vendor.validators import RpsCreateParkingSessionValidator, RpsUpdateParkingSessionValidator, \
    RpsCancelParkingSessionValidator, RpsCompleteParkingSessionValidator, RpsUpdateListParkingSessionValidator, \
    ParkingCardRequestBodyValidator, ParkingCardSessionBodyValidator


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


class GetParkingCardDebt(APIView):
    validator_class = ParkingCardRequestBodyValidator

    def post(self, request, *args, **kwargs):
        card_id = request.data["card_id"]
        phone = request.data["phone"]
        parking_id = request.data["parking_id"]

        parking_card, _ = ParkingCard.objects.get_or_create(
            card_id=card_id,
            defaults={'phone': phone}
        )
        try:
            rps_parking = RpsParking.objects.select_related(
                'parking').get(parking__id=parking_id)

            if not rps_parking.parking.rps_parking_card_available:
                raise ObjectDoesNotExist()

            response_dict = rps_parking.get_parking_card_debt(parking_card)
            if response_dict:
                response_dict["parking_name"] = rps_parking.parking.name
                return JsonResponse(response_dict, status=200)
            else:
                e = ValidationException(
                    ValidationException.RESOURCE_NOT_FOUND,
                    "Card with number %s does not exist" % card_id)
                return JsonResponse(e.to_dict(), status=400)

        except ObjectDoesNotExist:
            e = ValidationException(
                code=ValidationException.ACTION_UNAVAILABLE,
                message="Parking does not found or parking card is unavailable"
            )
            return JsonResponse(e.to_dict(), status=400)


class AccountInitPayment(LoginRequiredAPIView):
    validator_class = ParkingCardSessionBodyValidator

    def post(self, request, *args, **kwargs):
        card_session = int(request.data["card_session"])
        try:
            card_session = RpsParkingCardSession.objects.get(
                id=card_session
            )
            if card_session.state != STATE_CREATED:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Parking card session is already paid"
                )
                return JsonResponse(e.to_dict(), status=400)

            if card_session.debt == 0:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Debt is 0. Nothing to pay"
                )
                return JsonResponse(e.to_dict(), status=400)

            # Add user to session
            card_session.account = request.account
            order = Order.objects.create(
                sum=Decimal(card_session.debt),
                parking_card_session=card_session,
            )
            card_session.state = STATE_INITED
            card_session.save()

            order.try_pay()
            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                message="Parking card session does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)


class InitPayDebt(APIView):
    validator_class = ParkingCardSessionBodyValidator

    def post(self, request, *args, **kwargs):
        card_session = int(request.data["card_session"])
        try:
            card_session = RpsParkingCardSession.objects.get(
                id=card_session
            )
            if card_session.state not in [STATE_CREATED, STATE_ERROR]:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Parking card session is already paid"
                )
                return JsonResponse(e.to_dict(), status=400)

            if card_session.debt == 0:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Debt is 0. Nothing to pay"
                )
                return JsonResponse(e.to_dict(), status=400)

            new_client_uuid = uuid.uuid4()
            card_session.client_uuid = new_client_uuid
            card_session.save()

            order = Order.objects.create(
                sum=Decimal(card_session.debt),
                parking_card_session=card_session,
            )
            result = order.create_non_recurrent_payment()
            response_dict = dict(
                client_uuid=str(new_client_uuid)
            )
            if result:
                card_session.state = STATE_INITED
                card_session.save()
                response_dict["payment_url"] = result["payment_url"]

            return JsonResponse(response_dict, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                message="Parking card session does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)


class GetCardSessionStatus(APIView):
    validator_class = ParkingCardSessionBodyValidator

    def post(self, request, *args, **kwargs):
        card_session = int(request.data["card_session"])

        try:
            card_session = RpsParkingCardSession.objects.get(
                id=card_session
            )

            orders = Order.objects.filter(parking_card_session=card_session).order_by('-created_at')
            if not orders.exists() or card_session.state == STATE_CREATED:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Payment is not yet inited. Please, call /payment/init/ method"
                )
                return JsonResponse(e.to_dict(), status=400)

            last_order = orders[0]
            response_dict = {
                "order_id": last_order.id,
                "sum": last_order.sum,
                "refunded_sum":last_order.refunded_sum,
                "authorized": last_order.authorized,
                "paid": last_order.paid,
                "error": None,
            }

            payments = TinkoffPayment.objects.filter(order=last_order)
            current_payment = payments[0] if payments.exists() else None
            if current_payment and current_payment.error_code > 0:
                if current_payment.error_message or current_payment.error_description:
                    response_dict["error"] = "Error occurs at payments"
                    card_session.state = STATE_ERROR
                    card_session.save()

            return JsonResponse(response_dict, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                message="Parking card session does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)


class MockingGetParkingCardDebt(SignedRequestAPIView):
    def post(self, request, *args, **kwargs):
        card_id = request.data["card_id"]
        parking_id = request.data["parking_id"]
        phone = request.data["phone"]
        get_logger().info((card_id, phone,))

        response_dict = dict(
            card_id=card_id,
            parking_id=parking_id,
            duration=200,
            debt=10
        )
        return JsonResponse(response_dict, status=200)


class MockingOrderAuthorized(SignedRequestAPIView):
    def post(self, request, *args, **kwargs):
        card_id = request.data["card_id"]
        order_id = request.data["order_id"]
        sum = request.data["sum"]

        get_logger().info((card_id, order_id, sum,))

        return JsonResponse({}, status=200)


class MockingOrderConfirm(SignedRequestAPIView):
    def post(self, request, *args, **kwargs):
        card_id = request.data["card_id"]
        order_id = request.data["order_id"]

        get_logger().info((card_id, order_id,))
        return JsonResponse({}, status=200)


class MockingOrderRefund(SignedRequestAPIView):
    def post(self, request, *args, **kwargs):
        card_id = request.data["card_id"]
        order_id = request.data["order_id"]
        refund_sum = request.data["refund_sum"]
        reason = request.data["refund_reason"]

        get_logger().info((card_id, order_id, refund_sum, reason,))
        return JsonResponse({}, status=200)


class SubscriptionCallbackView(SignedRequestAPIView):
    def post(self, request, *args, **kwargs):
        get_logger().info(request.data)
        return JsonResponse({"status":"OK"}, status=200)