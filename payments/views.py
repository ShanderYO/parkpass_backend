import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from base.utils import get_logger
from base.views import APIView
from parkings.models import ParkingSession
from payments.models import CreditCard, TinkoffPayment, PAYMENT_STATUS_REJECTED, \
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_CONFIRMED, PAYMENT_STATUS_REVERSED, PAYMENT_STATUS_REFUNDED, \
    PAYMENT_STATUS_PARTIAL_REFUNDED, Order, PAYMENT_STATUS_RECEIPT, FiskalNotification, PAYMENT_STATUS_UNKNOWN

from payments.payment_api import TinkoffAPI
from payments.tasks import start_cancel_request


class TinkoffCallbackView(APIView):
    # TODO validate token or place to Validator
    #validator_class = TinkoffCallbackValidator

    is_successful = False
    error_code = -1
    status = PAYMENT_STATUS_UNKNOWN

    def post(self, request, *args, **kwargs):
        self.log_data(request.data)

        self.is_successful = request.data.get("Success", False)
        self.status = self.parse_status(request.data["Status"])

        if not self.is_successful:
            self.error_code = int(request.data["ErrorCode"])

        if self.status == PAYMENT_STATUS_UNKNOWN:
            get_logger().error("status 400: Unknown status: -> %s" % request.data["Status"])
            return HttpResponse(status=400)

        # Check if RECEIPT
        # TODO check if is_successful == False
        if self.status == PAYMENT_STATUS_RECEIPT:
            return self.create_fiskal_and_return_response(request.data)

        # Read general params
        order_id = int(request.data["OrderId"])
        payment_id = int(request.data["PaymentId"])
        pan = request.data.get("Pan", "-")
        rebill_id = int(request.data["RebillId"])

        # Check if PAYMENT REFUNDED
        if self.status == PAYMENT_STATUS_REFUNDED or self.status == PAYMENT_STATUS_PARTIAL_REFUNDED:
            amount = int(request.data["Amount"])
            self.refunded_order(order_id, amount, self.status==PAYMENT_STATUS_PARTIAL_REFUNDED)
            return HttpResponse("OK", status=200)

        # Get order and payment
        order = self.retrieve_order(order_id)
        if order:
            # Check if REJECTED
            if self.status == PAYMENT_STATUS_REJECTED:
                self.update_payment_info(payment_id)
                return HttpResponse("OK", status=200)

            # Check if AUTHORIZE and CONFIRMED

            if self.is_regular_pay(order):
                amount = int(request.data["Amount"])
                # TODO delete
                not_paid_orders = Order.objects.filter(session=order.session, paid=False)
                if not not_paid_orders.exists():
                    parking_session = order.session
                    get_logger().info("not_paid_orders more")
                    if parking_session.is_completed_by_vendor():
                        get_logger().info("order.session.is_completed_by_vendor()")
                        parking_session.state = ParkingSession.STATE_CLOSED
                        parking_session.save()

            if self.is_card_binding(order):
                card_id = int(request.data["CardId"])
                exp_date = request.data["ExpDate"]

                # Change card or rebill_id
                if self.is_card_exists(card_id, order.account):
                    self.update_rebill_id_if_needed(card_id, order.account, rebill_id)

                # Create card or rebill_id
                else:
                    credit_card = CreditCard(
                        card_id=card_id,
                        account=order.account,
                        pan=pan,
                        exp_date=exp_date,
                        rebill_id=rebill_id
                    )
                    credit_card.is_default = False \
                            if CreditCard.objects.filter(account=order.account).exists() else True
                    credit_card.save()
                    start_cancel_request(order)

            else:
                get_logger().warn("Unknown successefull operation")

            order.paid_card_pan = pan
            order.save()

        get_logger().info("status 200: OK")
        return HttpResponse("OK", status=200)


    def log_data(self, data):
        get_logger().info("Callback payments invoke:")
        get_logger().info(data)
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


    def parse_status(self, raw_status):
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
        return status


    def create_fiskal_and_return_response(self, data):
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
        receipt_datetime_str = data["ReceiptDatetime"]
        # TODO add timezone
        datetime_object = datetime.datetime.strptime(
            receipt_datetime_str.split("+")[0], "%Y-%m-%dT%H:%M:%S")
        order_id = long(data.get("OrderId", -1))

        try:
            order = Order.objects.get(id=order_id)
        except ObjectDoesNotExist as e:
            get_logger().warn(e.message)
            return HttpResponse("OK", status=200)

        fiskal = FiskalNotification.objects.create(
            fiscal_number=data.get("FiscalNumber", -1),
            type=data.get("Type", "Unknown"),
            shift_number=data.get("ShiftNumber", -1),
            receipt_datetime=datetime_object,
            fn_number=data.get("FnNumber", "?"),
            ecr_reg_number=data.get("EcrRegNumber", "?"),
            fiscal_document_number=data.get("FiscalDocumentNumber", -1),
            fiscal_document_attribute=data.get("FiscalDocumentAttribute", -1),
            card_pan=order.paid_card_pan,
            receipt=str(data.get("Receipt", "[]"))
        )
        order.fiscal_notification = fiskal
        order.save()
        return HttpResponse("OK", status=200)


    def refunded_order(self, order_id, refunded_amount, is_partial):
        """
            {
                u'OrderId': u'18',
                u'Status': u'REFUNDED',
                u'Success': True,
                u'Token': u'ced65967528612f4aa4a4890d59f44706c788e152c9dc4a4a73db331f2a99055',
                u'ExpDate': u'1122',
                u'ErrorCode': u'0',
                u'Amount': 100,
                u'TerminalKey': u'1516954410942DEMO',
                u'CardId': 3582969,
                u'PaymentId': 17881695,
                u'Pan': u'430000******0777'
            }
        """

        order = self.retrieve_order(order_id)
        if order:
            order.refund_request = False
            # TODO add refunded sum
            order.save()
        else:
            return HttpResponse("OK", status=200)


    def retrieve_order(self, order_id):
        try:
            order = Order.objects.get(id=order_id)
            return order
        except ObjectDoesNotExist as e:
            get_logger().warn(e.message)
            return None


    def update_payment_info(self, payment_id):
        try:
            payment = TinkoffPayment.objects.get(payment_id=payment_id)
            payment.status = self.status
            if self.error_code > 0:
                payment.error_code = self.error_code
            payment.save()
        except ObjectDoesNotExist as e:
            get_logger().warn("TinkoffPayment does not exist id=%s" % payment_id)


    def is_regular_pay(self, order):
        return order.account is None


    def is_card_binding(self, order):
        return order.account != None


    def is_card_exists(self, card_id, account):
        return CreditCard.objects.filter(
            card_id=card_id, account=account).exists()


    def update_rebill_id_if_needed(self, card_id, account, rebill_id):
        credit_card = CreditCard.objects.get(card_id=card_id, account=account)
        if rebill_id != -1:
            if credit_card.rebill_id != rebill_id:
                credit_card.rebill_id = rebill_id
                credit_card.save()