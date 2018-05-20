from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from base.utils import get_logger
from base.views import APIView
from payments.models import CreditCard, TinkoffPayment, PAYMENT_STATUS_REJECTED, \
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_CONFIRMED, PAYMENT_STATUS_REVERSED, PAYMENT_STATUS_REFUNDED, \
    PAYMENT_STATUS_PARTIAL_REFUNDED, Order

from payments.payment_api import TinkoffAPI
from payments.tasks import start_cancel_request


class TinkoffCallbackView(APIView):
    #validator_class = TinkoffCallbackValidator

    def post(self, request, *args, **kwargs):
        get_logger().info("Callback payments invoke:")
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

        # Get order and payment
        try:
            # Change order
            order = Order.objects.get(id=order_id)
            order.paid = float(amount)/100
            order.save()

            account = order.account if order.account else order.session.client

            # Change state payment
            payment = TinkoffPayment.objects.get(payment_id=payment_id)

            payment.status = status
            if code > 0:
                payment.error_code = code
            payment.save()

            if code > 0:
                get_logger().info("Callback notification code > 0. Return status 200: OK")
                return HttpResponse("OK", status=200)

            # Change card or rebill_id
            if CreditCard.objects.filter(card_id=card_id, account=account).exists():
                credit_card = CreditCard.objects.get(card_id=card_id, account=account)
                credit_card.rebill_id = rebill_id
                credit_card.save()

            else:
                credit_card = CreditCard(card_id=card_id, pan=pan,
                                         exp_date=exp_date, rebill_id=rebill_id)
                if order.account:
                    credit_card.account = order.account
                    credit_card.is_default = False \
                        if CreditCard.objects.filter(account=order.account).exists() else True
                    credit_card.save()
                    start_cancel_request(payment)
                else:
                    get_logger().warn("Order does not contained account. " +
                                      "Please check payment initialization")
        except ObjectDoesNotExist as e:
            get_logger().warn(e.message)
            return HttpResponse("OK", status=200)

        get_logger().info("status 200: OK")
        return HttpResponse("OK", status=200)

"""
class CancelPayment(APIView):
    def post(self, request):
        payment = 16998111
        new_payment = TinkoffPayment.objects.create()
        new_payment.payment_id = payment
        new_payment.save()

        request_data = new_payment.build_cancel_request_data()
        result = TinkoffAPI().sync_call(
            TinkoffAPI.CANCEL, request_data
        )
        print result
        '
        {
            u'Status': u'REFUNDED',
            u'OrderId': u'8',
            u'Success': True,
            u'NewAmount': 0,
            u'ErrorCode': u'0',
            u'TerminalKey': u'1516954410942DEMO',
            u'OriginalAmount': 100,
            u'PaymentId': u'16998111'
        }
        '

        return HttpResponse("OK", status=200)
"""