from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse

from base.exceptions import ValidationException, PaymentException
from base.utils import get_logger
from base.views import LoginRequiredAPIView, APIView
from payments.models import CreditCard, TinkoffPayment, PAYMENT_STATUS_NEW, PAYMENT_STATUS_REJECTED, \
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_CONFIRMED, PAYMENT_STATUS_REVERSED, PAYMENT_STATUS_REFUNDED, \
    PAYMENT_STATUS_PARTIAL_REFUNDED

from payments.payment_api import TinkoffAPI
from payments.utils import TinkoffExceptionAdapter


class GetInitPaymentUrl(LoginRequiredAPIView):
    def get(self, request):
        """
        Success response
        {
            u'Status': u'NEW',
            u'OrderId': u'2',
            u'Success': True,
            u'PaymentURL': u'https://securepay.tinkoff.ru/5YDUkv',
            u'ErrorCode': u'0',
            u'Amount': 100,
            u'TerminalKey': u'1516954410942DEMO',
            u'PaymentId': u'16630446'
        }
        """
        new_payment = TinkoffPayment.objects.create()
        request_data = new_payment.build_init_request_data()

        result = TinkoffAPI().sync_call(
            TinkoffAPI.INIT, request_data
        )
        # Payment gateway error
        if not request:
            e = PaymentException(
                PaymentException.BAD_PAYMENT_GATEWAY,
                "Payment gateway temporary not available"
            )
            return JsonResponse(e.to_dict(), status=400)

        # Payment success
        if result.get("Success", False):
            order_id = int(result["OrderId"])
            payment_id = int(result["PaymentId"])
            payment_url = result["PaymentURL"]

            raw_status = result["Status"]
            status = PAYMENT_STATUS_NEW if raw_status == u'NEW' \
                else PAYMENT_STATUS_REJECTED

            try:
                payment = TinkoffPayment.objects.get(id=order_id)
                payment.payment_id = payment_id
                payment.status = status
                payment.save()

                return JsonResponse({
                    "payment_url": payment_url
                }, status=200)

            except ObjectDoesNotExist:
                TinkoffPayment.objects.create(payment_id=payment_id, status=status)
                return JsonResponse({
                    "payment_url": payment_url
                }, status=200)

        # Payment exception
        elif int(result.get("ErrorCode", -1)) > 0:
            error_code = int(result["ErrorCode"])
            error_message = result.get("Message", "")
            error_details = request.get("Details", "")
            get_logger().warning("Init exception: "+error_code+" : "+error_message+" : "+error_details)

            exception_adapter = TinkoffExceptionAdapter(error_code)
            e = exception_adapter.get_api_exeption()
            return JsonResponse(e.to_dict(), status=400)

        # Otherwise
        else:
            e = PaymentException(
                PaymentException.EXCEPTION_INTERNAL_ERROR,
                "Payment exception does not contained Success or ErrorCode keys"
            )
            return JsonResponse(e.to_dict(), status=400)


class TinkoffCallbackView(APIView):
    #validator_class = TinkoffCallbackValidator

    def post(self, request, *args, **kwargs):
        get_logger().info("Callback payments invoke")
        get_logger().info(request.data)
        """
        Sample data
        {
            u'OrderId': u'7',
            u'Status': u'CONFIRMED',
            u'Success': True,
            u'RebillId': 1521972571962,
            u'Token': u'6fcb8e5e0980a5810f22845886b7d8cc06130019dbe40b2c8b2c0fd46a9d9dd5',
            u'ExpDate': u'1122',
            u'ErrorCode': u'0',
            u'Amount': 100,
            u'TerminalKey': u'1516954410942DEMO',
            u'CardId': 3582969,
            u'PaymentId': 16993956,
            u'Pan': u'430000******0777'
        }
        """

        # TODO validate token or place to Validator
        token = request.data["Token"]

        order_id = int(request.data["OrderId"])
        payment_id = int(request.data["PaymentId"])
        amount = int(request.data["Amount"])

        raw_status = request.data["Status"]
        status = -1
        if raw_status == "AUTHORIZED":
            status = PAYMENT_STATUS_AUTHORIZED
        elif raw_status == "CONFIRMED":
            status = PAYMENT_STATUS_CONFIRMED
        elif raw_status == "REVERSED":
            status = PAYMENT_STATUS_REVERSED
        elif raw_status == "REFUNDED":
            status = PAYMENT_STATUS_REFUNDED
        elif raw_status == "PARTIAL_REFUNDED":
            status = PAYMENT_STATUS_PARTIAL_REFUNDED
        elif raw_status == "REJECTED":
            status = PAYMENT_STATUS_REJECTED

        if status < 0:
            get_logger().error("status 400: Unknown status -> %s" % raw_status)
            return HttpResponse(status=400)

        card_id = int(request.data["CardId"])
        pan = request.data["Pan"]
        exp_date = request.data["ExpDate"]

        rebill_id = -1
        if request.data.get("Success", False):
            rebill_id = int(request.data.get("RebillId", -1))

        code = -1
        if int(request.data.get("ErrorCode", -1)) > 0:
            code = int(request.data["ErrorCode"])

        try:
            tinkoffPayment = TinkoffPayment.objects.get(payment_id=payment_id)
            tinkoffPayment.card_id = card_id
            tinkoffPayment.pan = pan
            tinkoffPayment.exp_date = exp_date
            if rebill_id > 0:
                tinkoffPayment.rebill_id = rebill_id
            if code > 0:
                tinkoffPayment.error_code = code

            tinkoffPayment.set_new_status(status)
            tinkoffPayment.save()

        except ObjectDoesNotExist:
            get_logger().error("status 400: Don't found payment")
            return HttpResponse(status=400)

        get_logger().info("status 200: OK")
        return HttpResponse("OK", status=200)


class AddCardView(LoginRequiredAPIView):
    def post(self, request):
        number = "00000000"
        if CreditCard.exists(number):
            e = ValidationException(ValidationException.ALREADY_EXISTS, "Card with such number alredy exists")
            return JsonResponse(e.to_dict(), status=400)
        credit_card = CreditCard(account=request.account)
        credit_card.save()
        return JsonResponse({}, status=200)


class DeleteCardView(LoginRequiredAPIView):
    def post(self, request):
        card_id = request.data.get("id", 0)
        try:
            card = CreditCard.objects.get(id=card_id, account=request.account)
            card.delete()
        except ObjectDoesNotExist:
            e = ValidationException(ValidationException.RESOURCE_NOT_FOUND, "Your card with such id is not found")
            return JsonResponse(e.to_dict(), status=400)
        return JsonResponse({}, status=200)


class SetDefaultCardView(LoginRequiredAPIView):
    def post(self, request):
        card_id = request.data.get("id", 0)
        try:
            card = CreditCard.objects.get(id=card_id, account=request.account)
            card.is_default = True
            card.save()
        except ObjectDoesNotExist:
            e = ValidationException(ValidationException.RESOURCE_NOT_FOUND, "Your card with such id is not found")
            return JsonResponse(e.to_dict(), status=400)
        return JsonResponse({}, status=200)


"""
import re
import datetime

from django.core.exceptions import ValidationError

from base.exceptions import ValidationException
from django.core.validators import validate_email, BaseValidator

class CreditCardParamValidator(BaseValidator):
    def is_valid(self):
        card_number = self.request.data.get("card_number", None)
        card_owner = self.request.data.get("card_owner", None)
        expiry_date = self.request.data.get("expiry_date", None)
        card_code = self.request.data.get("card_code", None)

        name_on_card = forms.CharField(max_length=50, required=True)
        card_number = CreditCardField(required=True)
        expiry_date = ExpiryDateField(required=True)
        card_code = VerificationValueField(required=True)


        if not phone:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Phone is required"
            return False
        try:
            validate_phone_number(phone)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e.message)
            return False
        return True
"""
