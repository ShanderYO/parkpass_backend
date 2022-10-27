import datetime
import secrets
import time
import uuid
from decimal import Decimal

import requests
from dateutil import parser
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.utils.decorators import decorator_from_middleware

from accounts.models import Account
from base.exceptions import ValidationException
from base.models import Terminal
from base.utils import get_logger, clear_phone, datetime_from_unix_timestamp_tz, elastic_log
from base.views import SignedRequestAPIView, APIView, LoginRequiredAPIView
from dss.Serializer import serializer
from jwtauth.utils import datetime_to_timestamp
from middlewares.ApiTokenMiddleware import ApiTokenMiddleware
from notifications.models import AccountDevice, Mailing
from parkings.models import Parking, ParkingSession
from parkings.views import CreateParkingSessionView, UpdateParkingSessionView, CancelParkingSessionView, \
    CompleteParkingSessionView
from parkpass_backend.settings import ES_APP_CARD_PAY_LOGS_INDEX_NAME
from payments.models import Order, TinkoffPayment, PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_PREPARED_AUTHORIZED, \
    HomeBankPayment, PAYMENT_STATUS_CONFIRMED
from payments.payment_api import TinkoffAPI
from rps_vendor.models import ParkingCard, RpsParking, RpsParkingCardSession, STATE_CREATED, STATE_INITED, STATE_ERROR, \
    RpsSubscription, STATE_CONFIRMED, Developer, DevelopersLog, DEVELOPER_LOG_GET_DEBT, DEVELOPER_STATUS_SUCCESS, \
    DEVELOPER_LOG_CONFIRM, CARD_SESSION_STATE_DICT
from rps_vendor.tasks import rps_process_updated_sessions
from rps_vendor.validators import RpsCreateParkingSessionValidator, RpsUpdateParkingSessionValidator, \
    RpsCancelParkingSessionValidator, RpsCompleteParkingSessionValidator, RpsUpdateListParkingSessionValidator, \
    ParkingCardRequestBodyValidator, ParkingCardSessionBodyValidator, CreateOrGetAccountBodyValidator, \
    SubscriptionUpdateBodyValidator, DeveloperCardSessionBodyValidator


class RpsCreateParkingSessionView(SignedRequestAPIView):
    validator_class = RpsCreateParkingSessionValidator

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            request.data["session_id"] = str(request.data["client_id"]) + "&" + str(request.data["started_at"])
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


class GetParkingCardDebtMixin:
    validator_class = ParkingCardRequestBodyValidator

    # @decorator_from_middleware(AllowCorsMiddleware)
    def post(self, request, *args, **kwargs):
        card_id = request.data["card_id"]
        parking_id = request.data["parking_id"]

        parking_card, _ = ParkingCard.objects.get_or_create(
            card_id=card_id
        )
        try:
            rps_parking = RpsParking.objects.select_related(
                'parking').get(parking__id=parking_id)

            if not rps_parking.parking.rps_parking_card_available:
                raise ObjectDoesNotExist()

            response_dict = rps_parking.get_parking_card_debt(parking_card)
            if response_dict:
                response_dict["parking_name"] = rps_parking.parking.name
                response_dict["parking_address"] = rps_parking.parking.address
                response_dict["currency"] = rps_parking.parking.currency

                elastic_log(ES_APP_CARD_PAY_LOGS_INDEX_NAME, "Get parking card debt", {
                    'response_dict': response_dict,
                    'card_id': card_id,
                    'parking_id': parking_id,
                })

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


class GetParkingCardDebt(GetParkingCardDebtMixin, APIView):
    pass


class GetDeveloperParkingCardDebtMixin:
    validator_class = ParkingCardRequestBodyValidator

    #@decorator_from_middleware(ApiTokenMiddleware)
    def post(self, request, *args, **kwargs):

        card_id = request.data["card_id"]
        parking_id = request.data["parking_id"]
        developer_id = request.data.get("developer_id")

        parking_card, _ = ParkingCard.objects.get_or_create(
            card_id=card_id
        )

        get_logger().info("GetDeveloperParkingCardDebtMixin card_id %s" % card_id)

        developer_log = DevelopersLog.objects.create(
            parking_card_id=card_id,
            developer=Developer.objects.get(developer_id=developer_id),
            type = DEVELOPER_LOG_GET_DEBT,
        )

        try:
            rps_parking = RpsParking.objects.select_related(
                'parking').get(parking__id=parking_id)

            if not rps_parking.parking.rps_parking_card_available:
                raise ObjectDoesNotExist()

            response_dict = rps_parking.get_parking_card_debt_for_developers(parking_card, developer_id)

            if response_dict:
                developer_log.parking = rps_parking
                developer_log.debt = response_dict["debt"]
                developer_log.status = DEVELOPER_STATUS_SUCCESS
                developer_log.save()
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


class GetDeveloperParkingCardDebt(GetDeveloperParkingCardDebtMixin, APIView):
    pass


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

            if card_session.get_debt() == 0:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Debt is 0. Nothing to pay"
                )
                return JsonResponse(e.to_dict(), status=400)

            # Add user to session
            card_session.account = request.account
            order = Order.objects.create(
                sum=Decimal(card_session.get_debt()),
                parking_card_session=card_session,
                acquiring=Parking.objects.get(id=card_session.parking_id).acquiring
            )
            card_session.state = STATE_INITED
            card_session.save()

            order.try_pay()

            elastic_log(ES_APP_CARD_PAY_LOGS_INDEX_NAME, "Account pay", {
                'order': serializer(order),
                'card_session': serializer(card_session),
                'account': serializer(request.account, exclude_attr=("created_at", "sms_code", "password"))
            })

            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                message="Parking card session does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)


class InitPayDebtMixin:
    validator_class = ParkingCardSessionBodyValidator

    def post(self, request, *args, **kwargs):
        card_session = int(request.data["card_session"])
        # phone = request.data.get("phone", "-")
        email = request.data.get("email", "")

        try:
            card_session = RpsParkingCardSession.objects.get(
                id=card_session
            )

            # Update client phone
            # card_session.parking_card.phone = str(phone)
            card_session.parking_card.save()

            if card_session.state not in [STATE_CREATED, STATE_ERROR]:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Parking card session is already paid"
                )
                return JsonResponse(e.to_dict(), status=400)

            if card_session.get_debt() == 0:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Debt is 0. Nothing to pay"
                )
                return JsonResponse(e.to_dict(), status=400)

            new_client_uuid = uuid.uuid4()
            card_session.client_uuid = new_client_uuid
            card_session.save()

            order = Order.objects.create(
                sum=Decimal(card_session.get_debt()),
                parking_card_session=card_session,
                terminal=Terminal.objects.get(name="pcard"),
                acquiring=Parking.objects.get(id=card_session.parking_id).acquiring
            )
            result = order.create_non_recurrent_payment(email)
            response_dict = dict(
                client_uuid=str(new_client_uuid),
                order_id=str(order.id)
            )
            if result:
                card_session.state = STATE_INITED
                card_session.save()

                if order.acquiring != 'homebank':
                    qr_result = TinkoffAPI(with_terminal='pcard').sync_call(
                        TinkoffAPI.GET_QR, {
                            "PaymentId": result["payment_id"]
                        }
                    )

                    if qr_result:
                        if qr_result.get("Success", False):
                            response_dict["data"] = qr_result["Data"]

                response_dict["payment_url"] = result["payment_url"]


            elastic_log(ES_APP_CARD_PAY_LOGS_INDEX_NAME, "Guest pay", {
                'order': serializer(order),
                'card_session': serializer(card_session),
                'email': email,
                'result': result
            })

            return JsonResponse(response_dict, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                message="Parking card session does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)

class InitWebPayDebtMixin:
    validator_class = ParkingCardSessionBodyValidator

    def post(self, request, *args, **kwargs):
        card_session = int(request.data["card_session"])
        email = request.data.get("email", "")

        try:
            card_session = RpsParkingCardSession.objects.get(
                id=card_session
            )

            # Update client phone
            # card_session.parking_card.phone = str(phone)
            card_session.parking_card.save()

            if card_session.state not in [STATE_CREATED, STATE_ERROR]:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Parking card session is already paid"
                )
                return JsonResponse(e.to_dict(), status=400)

            if card_session.get_debt() == 0:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Debt is 0. Nothing to pay"
                )
                return JsonResponse(e.to_dict(), status=400)

            new_client_uuid = uuid.uuid4()
            card_session.client_uuid = new_client_uuid
            card_session.save()

            order = Order.objects.create(
                sum=Decimal(card_session.get_debt()),
                parking_card_session=card_session,
                acquiring=Parking.objects.get(id=card_session.parking_id).acquiring
            )
            payment = order.create_non_recurrent_payment(email, True)
            qr_link = ""
            if payment:
                if order.acquiring != 'homebank':
                    qr_result = TinkoffAPI(with_terminal='pcard').sync_call(
                        TinkoffAPI.GET_QR, {
                            "PaymentId": payment["payment_id"]
                        }
                    )
                    if qr_result:
                        if qr_result.get("Success", False):
                            qr_link = qr_result["Data"]

            return JsonResponse({"payment": serializer(payment), "order": serializer(order), "qr_link": qr_link}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                message="Parking card session does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)

class InitPayDebt(InitPayDebtMixin, APIView):
    pass

class InitWebPayDebt(InitWebPayDebtMixin, APIView):
    pass

class ConfirmPayDeveloperDebt(APIView):
    validator_class = DeveloperCardSessionBodyValidator

    @decorator_from_middleware(ApiTokenMiddleware)
    def post(self, request, *args, **kwargs):
        card_session_id = int(request.data["card_session_id"])
        parking_card_id = int(request.data["parking_card_id"])
        parking_id = int(request.data["parking_id"])
        debt = int(request.data["debt"])
        developer_id = request.data.get("developer_id")

        get_logger().info("ConfirmPayDeveloperDebt card_session_id %s" % card_session_id)

        try:
            rps_parking = RpsParking.objects.select_related(
                'parking').get(parking__id=parking_id)

        except ObjectDoesNotExist:
            e = ValidationException(
                code=ValidationException.ACTION_UNAVAILABLE,
                message="Parking does not found"
            )
            return JsonResponse(e.to_dict(), status=400)


        developer_log = DevelopersLog.objects.create(
            parking_card_id=parking_card_id,
            parking=rps_parking,
            developer=Developer.objects.get(developer_id=developer_id),
            type=DEVELOPER_LOG_CONFIRM,
            debt=debt
        )

        try:
            card_session = RpsParkingCardSession.objects.get(
                id=card_session_id,
                parking_card_id=parking_card_id,
                parking_id=parking_id,
                # duration=duration,
                # debt=debt, // TODO убрал по причине калькуляции коммиссии
            )

            if card_session.state not in [STATE_CREATED, STATE_ERROR]:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Parking card session is already paid"
                )
                return JsonResponse(e.to_dict(), status=400)

            if card_session.get_debt() == 0:
                e = ValidationException(
                    code=ValidationException.INVALID_RESOURCE_STATE,
                    message="Debt is 0. Nothing to pay"
                )
                return JsonResponse(e.to_dict(), status=400)

            new_client_uuid = uuid.uuid4()
            card_session.client_uuid = new_client_uuid
            card_session.save()

            order = Order.objects.create(
                sum=Decimal(card_session.get_debt()),
                parking_card_session=card_session,
                acquiring=Parking.objects.get(id=card_session.parking_id).acquiring,
                authorized=True,
                paid=True
            )
            get_logger().info("ConfirmPayDeveloperDebt notify_authorize")

            status = 'error'
            if order.parking_card_session.notify_authorize(order, developer_id, rps_parking):
                status = 'success'
                developer_log.status = DEVELOPER_STATUS_SUCCESS
                developer_log.save()
                order.parking_card_session.notify_confirm(order)

            return JsonResponse({"status": status}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                message="Parking card session does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)


class GetCardSessionStatusMixin:
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
                "payment_state": CARD_SESSION_STATE_DICT[card_session.state],
                "order_id": last_order.id,
                "sum": last_order.sum,
                "refunded_sum": last_order.refunded_sum,
                "authorized": last_order.authorized,
                "paid": last_order.paid,
                "leave_at": datetime_to_timestamp(card_session.leave_at) if card_session.leave_at else None,
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


class GetCardSessionStatus(GetCardSessionStatusMixin, APIView):
    pass


class GetCardSessionStatusForDeveloperMixin:
    validator_class = ParkingCardSessionBodyValidator

    #@decorator_from_middleware(ApiTokenMiddleware)
    def post(self, request, *args, **kwargs):
        card_session = int(request.data["card_session"])

        try:
            card_session = RpsParkingCardSession.objects.get(
                id=card_session
            )
            orders = Order.objects.filter(
                parking_card_session=card_session).order_by('-created_at')
            orders = Order.objects.filter(
                parking_card_session=card_session).order_by('-created_at')

            last_order = orders[0]
            response_dict = {
                "payment_state": CARD_SESSION_STATE_DICT[card_session.state],
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


class GetCardSessionStatusForDeveloper(GetCardSessionStatusForDeveloperMixin, APIView):
    pass


class CheckTimestamp(APIView):
    def get(self, request, *args, **kwargs):
        return HttpResponse(int(time.time()), status=200)

class ResetDeveloperToken(APIView):
    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            try:
                developer = Developer.objects.get(id=request.GET.get('id'))
            except ObjectDoesNotExist:
                return HttpResponse('Разработчик не найден', status=400)
            messages.add_message(
                request,
                messages.SUCCESS,
                'Api key изменен'
            )
            developer.api_key = secrets.token_hex(24)
            developer.save()
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

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

        subscription_id = request.data["subscription_id"]
        rps_subscription = RpsSubscription.objects.filter(id=int(subscription_id)).select_related('parking').first()

        if not rps_subscription:
            get_logger().warning("RpsSubscription with %s does not exists " % subscription_id)
            return JsonResponse({"status": "OK"}, status=200)

        order = Order.objects.filter(authorized=True, subscription=rps_subscription).first()
        if not order:
            rps_subscription.reset(error_message="Authorized order not found")
            return JsonResponse({"status": "OK"}, status=200)

        payments = TinkoffPayment.objects.filter(order=order)

        status = request.data.get("status")
        if status:
            data = str(request.data["data"])
            str_expired_at = str(request.data["expired_at"])

            ISO_KOZULIN_FORMAT = "%d.%m.%Y %H:%M:%S"

            try:
                parsed_datetime = datetime.datetime.strptime(str_expired_at, ISO_KOZULIN_FORMAT)
                parsed_timestamp = datetime_to_timestamp(parsed_datetime)
                tz_datetime = rps_subscription.parking.get_utc_parking_datetime(parsed_timestamp)
                rps_subscription.expired_at = tz_datetime

            except ValueError:
                get_logger().info("Error parsing kozulin date: %s " % str_expired_at)

            rps_subscription.data = data
            rps_subscription.save()

            RpsSubscription.objects.filter(
                parking=rps_subscription.parking,
                account=rps_subscription.account
            ).exclude(id=rps_subscription.id).update(expired_at=timezone.now())

            if (rps_subscription.parking.acquiring == 'homebank'):
                payments = HomeBankPayment.objects.filter(order=order)
                for payment in payments:
                    if payment.status == PAYMENT_STATUS_AUTHORIZED:
                        order.confirm_payment_homebank(payment)
                        break
            else:
                for payment in payments:
                    if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                        order.confirm_payment(payment)
                        break
        else:
            error_message = request.data.get("message", "")
            rps_subscription.reset(error_message=error_message)
            if (rps_subscription.parking.acquiring == 'homebank'):
                payments = HomeBankPayment.objects.filter(order=order)
                for payment in payments:
                    if payment.status == PAYMENT_STATUS_CONFIRMED:
                        payment.cancel_payment()
                        get_logger().info("Cancel subscription payment response: ")
                        break
            else:
                for payment in payments:
                    if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                        request_data = payment.build_cancel_request_data()
                        result = TinkoffAPI().sync_call(
                            TinkoffAPI.CANCEL, request_data
                        )
                        get_logger().info("Cancel subscription payment response: ")
                        get_logger().info(str(result))
                        break

        return JsonResponse({"status": "OK"}, status=200)


class SubscriptionUpdateView(SignedRequestAPIView):
    validator_class = SubscriptionUpdateBodyValidator

    def post(self, request, *args, **kwargs):
        get_logger().info(request.data)

        name = request.data.get("name")
        user_id = int(request.data["user_id"])
        parking_id = int(request.data["parking_id"])
        data = request.data["data"]

        unlimited = bool(request.data.get("unlimited", False))

        if not unlimited:
            description = request.data["description"]
            duration = int(request.data.get("duration", 0))
            id_ts = request.data["id_ts"]
            id_transition = request.data["id_transition"]
            expired_at = int(request.data.get("expired_at", 0))

        account = None
        try:
            account = Account.objects.get(id=user_id)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "User with id %s does not exist" % user_id
            )
            return JsonResponse(e.to_dict(), status=400)

        parking = None
        try:
            parking = Parking.objects.get(id=parking_id)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with id %s is not found" % parking_id
            )
            return JsonResponse(e.to_dict(), status=400)

        subscription_qs = RpsSubscription.objects.filter(
            account=account,
            parking=parking,
            active=True)

        prolongation = False
        subscription = subscription_qs.first()
        if subscription:
            prolongation = subscription.prolongation
            # Disable all subscriptions
            subscription_qs.update(active=False)

        if unlimited:
            default_infinity_duration = 60 * 60 * 24 * 356 * 10
            default_infinity_expiration_datetime = timezone.now() + datetime.timedelta(
                seconds=default_infinity_duration)

            RpsSubscription.objects.create(
                name=name if name else "Постоянный клиент",
                description="-",
                unlimited=True,
                sum=0,
                idts="",
                id_transition="",
                started_at=timezone.now(),
                expired_at=default_infinity_expiration_datetime,
                duration=default_infinity_duration,
                parking=parking,
                account=account,
                prolongation=prolongation,
                data=data,
                active=True,
                state=STATE_CONFIRMED
            )

        else:
            RpsSubscription.objects.create(
                name=name,
                description=description,
                sum=0,
                started_at=timezone.now(),
                expired_at=datetime_from_unix_timestamp_tz(expired_at),
                duration=duration,
                parking=parking,
                account=account,
                prolongation=prolongation,
                idts=id_ts,
                id_transition=id_transition,
                data=data,
                active=True,
                state=STATE_CONFIRMED
            )

        return JsonResponse({}, status=200)


class RpsCreateOrGetAccount(SignedRequestAPIView):
    validator_class = CreateOrGetAccountBodyValidator

    def post(self, request, *args, **kwargs):
        phone = clear_phone(request.data["phone"])
        parking_id = int(request.data["parking_id"])
        is_new_user = True
        subscription_data = None

        account = Account.objects.filter(phone=phone).first()
        if not account:
            account = Account(phone=phone)
            account.save()

        else:
            is_new_user = False
            subscription = RpsSubscription.objects.filter(
                account=account,
                parking_id=parking_id,
                active=True
            ).first()
            if subscription:
                subscription_data = subscription.data

        return JsonResponse({
            "user_id": account.id,
            "is_new_user": is_new_user,
            "data": subscription_data
        })


def send_push_notifications(request):
    if request.user.is_superuser:

        title = request.GET.get('title', None)
        text = request.GET.get('text', None)
        id = request.GET.get('id', None)
        mailing = Mailing.objects.get(id=id)
        user_ids = request.GET.get('user_ids', None)
        parking_id = request.GET.get('parking_id', None)
        parkings_sessions_date = request.GET.get('parkings_sessions_date', None)

        if user_ids:
            user_ids = user_ids.split(',')

        if title and text and mailing:
            if parking_id:
                parking = Parking.objects.get(id=parking_id)
                sessions = ParkingSession.objects.filter(parking=parking, client_id__isnull=False)
                if parkings_sessions_date:
                    sessions = sessions.filter(started_at__gte=mailing.parkings_sessions_date)

                user_ids = []
                for session in sessions:
                    if session.client_id not in user_ids:
                        user_ids.append(session.client_id)

                qs = AccountDevice.objects.filter(active=True, account_id__in=user_ids)
            elif user_ids:
                qs = AccountDevice.objects.filter(active=True, account_id__in=user_ids)
            else:
                qs = AccountDevice.objects.filter(active=True)

            for account_device in qs:
                get_logger().info("send push to %s" % account_device.account_id)
                account_device.send_message(title=title, body=text)

            mailing.sended_at = timezone.now()
            mailing.save()
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


    return HttpResponse("Fail", status=400)

def get_users_for_push_notifications(request):
    if request.user.is_superuser:
        parking_id = request.GET.get('parking_id', None)
        id = request.GET.get('id', None)
        mailing = Mailing.objects.get(id=id)

        if parking_id:
            parking = Parking.objects.get(id=parking_id)
            sessions = ParkingSession.objects.filter(parking=parking, client_id__isnull=False)
            if mailing.parkings_sessions_date:
                sessions = sessions.filter(started_at__gte=mailing.parkings_sessions_date)

            user_ids = []
            for session in sessions:
                if session.client_id not in user_ids:
                    user_ids.append(session.client_id)

            qs = AccountDevice.objects.filter(active=True, account_id__in=user_ids)
            result = []
            if qs:
                for q in qs:
                    if str(q.account_id) not in result:
                        result.append(str(q.account_id))

            return JsonResponse({'result': result}, status=200)

    return HttpResponse("Fail", status=400)

def check_remote_network(request):
    if request.user.is_superuser:

        url = request.GET.get('url', None)

        r = requests.get(url, timeout=(2, 5.0))
        try:
            result = r.json()
            return JsonResponse(result, status=200)

        except Exception as e:
            return HttpResponse(str(e) + url, status=400)


    return HttpResponse("Fail", status=400)
