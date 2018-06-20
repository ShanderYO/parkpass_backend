import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from base.utils import get_logger
from base.views import APIView
from parkings.models import ParkingSession
from payments.models import CreditCard, TinkoffPayment, PAYMENT_STATUS_REJECTED, \
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_CONFIRMED, PAYMENT_STATUS_REVERSED, PAYMENT_STATUS_REFUNDED, \
    PAYMENT_STATUS_PARTIAL_REFUNDED, Order, PAYMENT_STATUS_RECEIPT, FiskalNotification

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

        {u'OrderId': u'580', u'Status': u'CONFIRMED', u'Success': True, u'RebillId': 1527066699680,
         u'Token': u'cd137597450591d46f7e5e0089b40cb69b9659a14be2b8dd90fdd60249d2db52', u'ExpDate': u'1122',
         u'ErrorCode': u'0', u'Amount': 10000, u'TerminalKey': u'1516954410942DEMO', u'CardId': 3592968,
         u'PaymentId': 22017647, u'Pan': u'400000******0333'}

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
        elif raw_status == "RECEIPT":
            status = PAYMENT_STATUS_RECEIPT

        if status < 0:
            get_logger().error("status 400: Unknown status -> %s" % raw_status)
            return HttpResponse(status=400)

        # Check RECEIPT
        if status == PAYMENT_STATUS_RECEIPT and int(request.data.get("ErrorCode", -1)) < 1:
            """{u'OrderId': u'636', u'Status': u'RECEIPT',
            u'Type': u'IncomeReturn', u'FiscalDocumentAttribute': 173423614,
            u'Success': True, u'ReceiptDatetime': u'2018-06-18T12:27:00+03:00',
            u'FiscalNumber': 2, u'Receipt': {
                u'Items': [{u'Tax': u'vat10', u'Price': 4000,
                u'Amount': 4000, u'Name': u'Payment for parking session # 45', u'Quantity': 1
                }],
                u'Taxation': u'osn',
                u'Email': u'strevg@yandex.ru',
                u'Phone': u'(+7)9852413193'
            }, u'Token': u'853b3d4808f0fad89759e9d80f16210f4499216787dd71453c8d594c7e74659e',
            u'FiscalDocumentNumber': 118, u'FnNumber': u'8710000101855975',
            u'ErrorCode': u'0', u'Amount': 4000, u'TerminalKey': u'1516954410942',
            u'PaymentId': 23735099, u'EcrRegNumber': u'0001785103056432', u'ShiftNumber': 56}
            """
            if request.data.get("Success", False):
                receipt_datetime_str = request.data["ReceiptDatetime"]
                # TODO add timezone
                datetime_object = datetime.datetime.strptime(
                    receipt_datetime_str.split("+")[0], "%Y-%m-%dT%H:%M:%S")
                try:
                    order = Order.objects.get(id=long(request.data.get("OrderId", -1)))
                except ObjectDoesNotExist as e:
                    get_logger().warn(e.message)
                    return HttpResponse("OK", status=200)

                fiskal = FiskalNotification.objects.create(
                    fiscal_number=request.data.get("FiscalNumber", -1),
                    type=request.data.get("Type", "Unknown"),
                    shift_number=request.data.get("ShiftNumber", -1),
                    receipt_datetime=datetime_object,
                    fn_number=request.data.get("FnNumber", "?"),
                    ecr_reg_number=request.data.get("EcrRegNumber", "?"),
                    fiscal_document_number=request.data.get("FiscalDocumentNumber", -1),
                    fiscal_document_attribute=request.data.get("FiscalDocumentAttribute", -1),
                    card_pan=order.paid_card_pan,
                    receipt=str(request.data.get("Receipt", "[]"))
                )
                order.fiscal_notification = fiskal
                order.save()
                return HttpResponse("OK", status=200)

        card_id = int(request.data["CardId"])
        pan = request.data["Pan"]
        exp_date = request.data["ExpDate"]

        rebill_id = -1
        #
        if request.data.get("Success", False):
            rebill_id = int(request.data.get("RebillId", -1))

        code = -1
        if int(request.data.get("ErrorCode", -1)) > 0:
            code = int(request.data["ErrorCode"])

        if status == PAYMENT_STATUS_REFUNDED or status == PAYMENT_STATUS_PARTIAL_REFUNDED:
            try:
                order = Order.objects.get(id=order_id)
                order.refund_request = False
                # TODO add refunded sum
                order.save()

            except ObjectDoesNotExist as e:
                get_logger().warn(e.message)
                return HttpResponse("OK", status=200)

        # Get order and payment
        try:
            # Change order
            order = Order.objects.get(id=order_id)
            order.paid = True
            order.paid_card_pan = request.data.get("Pan", "-")
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

            if order.account is None:
                not_paid_orders = Order.objects.filter(session=order.session, paid=False)
                if not not_paid_orders.exists():
                    parking_session = order.session
                    get_logger().info("not_paid_orders more")
                    if parking_session.is_completed_by_vendor():
                        get_logger().info("order.session.is_completed_by_vendor()")
                        parking_session.state = ParkingSession.STATE_CLOSED
                        parking_session.save()


            # Change card or rebill_id
            if CreditCard.objects.filter(card_id=card_id, account=account).exists():
                credit_card = CreditCard.objects.get(card_id=card_id, account=account)
                if rebill_id != -1:
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