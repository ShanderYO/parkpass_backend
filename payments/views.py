import datetime
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils import timezone

from base.utils import get_logger
from base.views import APIView
from parkings.models import ParkingSession
from payments.models import CreditCard, TinkoffPayment, PAYMENT_STATUS_REJECTED, \
    PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_CONFIRMED, PAYMENT_STATUS_REVERSED, PAYMENT_STATUS_REFUNDED, \
    PAYMENT_STATUS_PARTIAL_REFUNDED, Order, PAYMENT_STATUS_RECEIPT, FiskalNotification, PAYMENT_STATUS_UNKNOWN, \
    PAYMENT_STATUS_PREPARED_AUTHORIZED
from payments.payment_api import TinkoffAPI

from payments.tasks import start_cancel_request, make_buy_subscription_request


class TinkoffCallbackView(APIView):
    # TODO validate token or place to Validator
    #validator_class = TinkoffCallbackValidator
    current_terminal = None

    is_successful = False
    error_code = -1
    status = PAYMENT_STATUS_UNKNOWN

    def post(self, request, *args, **kwargs):
        self.log_data(request.data)

        self.is_successful = request.data.get("Success", False)
        self.status = self.parse_status(request.data["Status"])
        self.current_terminal = request.data.get("TerminalKey")

        if self.status == PAYMENT_STATUS_UNKNOWN:
            get_logger().error("status 400: Unknown status: -> %s" % request.data["Status"])
            return HttpResponse(status=400)

        if not self.is_successful:
            self.error_code = int(request.data["ErrorCode"])
            # TODO add custom execution in the future

        if self.status == PAYMENT_STATUS_RECEIPT:
            self.create_fiskal(request.data)
            return HttpResponse("OK", status=200)

        # Read general params
        order_id = int(request.data["OrderId"])
        payment_id = int(request.data["PaymentId"])
        pan = request.data.get("Pan", "-")
        amount = int(request.data.get("Amount", 0))

        # Check if PAYMENT REFUNDED
        if self.status == PAYMENT_STATUS_REFUNDED or self.status == PAYMENT_STATUS_PARTIAL_REFUNDED:
            self.refunded_order(
                order_id, amount,
                self.status==PAYMENT_STATUS_PARTIAL_REFUNDED)
            return HttpResponse("OK", status=200)

        if self.status == PAYMENT_STATUS_REVERSED:
            self.reverse_order(order_id, amount)
            return HttpResponse("OK", status=200)

        # Check if REJECTED
        if self.status == PAYMENT_STATUS_REJECTED:
            order = self.retrieve_order(order_id)
            if order:
                order.paid_card_pan = pan
            self.update_payment_info(payment_id)
            return HttpResponse("OK", status=200)

        # Get order with dependencies
        order = Order.retrieve_order_with_fk(order_id, fk=["account", "session",
                                                          "parking_card_session", "subscription"])
        if not order:
            get_logger().warn("Order with id %s does not exist" % order_id)
            return HttpResponse("OK", status=200)

        order.paid_card_pan = pan

        # AUTHORIZE or CONFIRMED
        if self.is_session_pay(order):
            if self.status == PAYMENT_STATUS_AUTHORIZED:
                order.authorized = True
                order.save()
                self.confirm_all_orders_if_needed(order) # Optimize it

            elif self.status == PAYMENT_STATUS_CONFIRMED:
                order.paid = True
                order.save()
                self.close_parking_session_if_needed(order)

        elif self.is_account_credit_card_payment(order):
            rebill_id = int(request.data["RebillId"])
            card_id = int(request.data["CardId"])
            exp_date = request.data["ExpDate"]

            stored_card = CreditCard.objects.filter(
                card_id=card_id, account=order.account).first()

            # Change rebill_id
            if stored_card:
                if rebill_id != -1 and stored_card.rebill_id != rebill_id:
                    stored_card.rebill_id = rebill_id
                    stored_card.save()

            # Create new card and return first pay
            else:
                credit_card = CreditCard(
                    card_id=card_id,
                    account=order.account,
                    pan=pan,
                    exp_date=exp_date,
                    rebill_id=rebill_id
                )

                if not CreditCard.objects.filter(account=order.account).exists():
                    credit_card.is_default = True
                    credit_card.save()

                if self.status == PAYMENT_STATUS_AUTHORIZED:
                    order.authorized = True
                    order.save()
                    start_cancel_request.delay(order.id)

        elif self.is_non_account_pay(order):
            if self.status == PAYMENT_STATUS_AUTHORIZED:
                order.authorized = True
                order.save()
                self.confirm_order(order)

            elif self.status == PAYMENT_STATUS_CONFIRMED:
                order.paid = True
                order.save()

        elif self.is_parking_card_pay(order):
            if self.status == PAYMENT_STATUS_AUTHORIZED:
                order.authorized = True
                order.save()
                self.notify_authorize_rps(order) # TODO make async

            elif self.status == PAYMENT_STATUS_CONFIRMED:
                order.paid = True
                order.save()
                self.notify_confirm_rps(order)  # TODO make async

            else:
                order.paid = False
                order.authorized = False
                self.notify_refund_rps(order)  # TODO make async

        elif self.is_subscription_pay(order):
            if self.status == PAYMENT_STATUS_AUTHORIZED:
                order.authorized = True
                order.save()

                subs = order.subscription
                subs.authorize()
                make_buy_subscription_request.delay(order.subscription.id)

            elif self.status == PAYMENT_STATUS_CONFIRMED:
                order.paid = True
                order.save()
                subs = order.subscription
                subs.activate()
                subs.save()

            else:
                subs = order.subscription
                subs.reset(error_message="Payment error")

        else:
            get_logger().warn("Unknown successefull operation")
            order.save()

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


    def create_fiskal(self, data):
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

        datetime_object = datetime.datetime.strptime(
            receipt_datetime_str.split("+")[0], "%Y-%m-%dT%H:%M:%S")
        order_id = int(data.get("OrderId", -1))

        try:
            order = Order.objects.get(id=order_id)
        except ObjectDoesNotExist as e:
            get_logger().warn(e)
            return

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
            order.refunded_sum = order.refunded_sum + Decimal(float(refunded_amount)/100)
            order.save()

    def reverse_order(self, order_id, amount):
        """
            {
                u'OrderId': u'743',
                u'Status': u'REVERSED',
                u'Success': True,
                u'Token': u'f6f9f767f1b5e2e947fab9021b97aedd92894f0417517ae1e516423c47e08897',
                u'ExpDate': u'0819',
                u'ErrorCode': u'0',
                u'Amount': 100,
                u'TerminalKey': u'1516954410942',
                u'CardId': 5546930,
                u'PaymentId': 27254547,
                u'Pan': u'510092******6768'
            }
        """

        order = self.retrieve_order(order_id)
        if order:
            order.refunded_sum = order.refunded_sum + Decimal(float(amount) / 100)
            order.save()

    def retrieve_order(self, order_id):
        try:
            order = Order.objects.get(id=order_id)
            return order
        except ObjectDoesNotExist as e:
            get_logger().warn(e)
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


    def is_session_pay(self, order):
        return order.session != None

    def is_parking_card_pay(self, order):
        return order.parking_card_session != None

    def is_subscription_pay(self, order):
        return order.subscription != None

    def is_non_account_pay(self, order):
        return order.client_uuid != None

    def is_account_credit_card_payment(self, order):
        return order.account != None

    def update_rebill_id_if_needed(self, card_id, account, rebill_id):
        credit_card = CreditCard.objects.get(card_id=card_id, account=account)
        if rebill_id != -1:
            if credit_card.rebill_id != rebill_id:
                credit_card.rebill_id = rebill_id
                credit_card.save()

    # TODO optimize this method
    def confirm_all_orders_if_needed(self, order):
        parking_session = order.session
        get_logger().info("check begin confirmation..")
        non_authorized_orders = Order.objects.filter(
            session=parking_session,
            authorized=False
        )

        if not non_authorized_orders.exists() and parking_session.is_completed_by_vendor():
            # Start confirmation
            session_orders = Order.objects.filter(
                session=parking_session,
            )
            for session_order in session_orders:
                if session_order.authorized and not session_order.paid:
                    try:
                        get_logger().info(str(session_order))
                        get_logger().info(str(PAYMENT_STATUS_AUTHORIZED))
                        payment = TinkoffPayment.objects.get(order=session_order,
                                                             status__in=[PAYMENT_STATUS_PREPARED_AUTHORIZED,
                                                                         PAYMENT_STATUS_AUTHORIZED],
                                                             error_code=-1)
                        session_order.confirm_payment(payment)
                    except ObjectDoesNotExist as e:
                        get_logger().info(e)
        else:
            get_logger().info("Wait closing session")


    def close_parking_session_if_needed(self, order):
        non_paid_orders = Order.objects.filter(
            session=order.session,
            paid=False
        )
        if not non_paid_orders.exists():
            parking_session = order.session
            if parking_session.is_completed_by_vendor():
                get_logger().info("Close session... id=%s" % parking_session.id)
                parking_session.state = ParkingSession.STATE_CLOSED
                parking_session.save()

    def confirm_order(self, order):
        payments = TinkoffPayment.objects.filter(order=order, error_code=-1)
        if payments.exists():
            order.confirm_payment(payments[0])
        else:
            get_logger().info("No one payment for order")

    def notify_authorize_rps(self, order):
        if order.parking_card_session.notify_authorize(order):
            self.confirm_order(order)
        else:
            self.refund(order)

    def notify_confirm_rps(self, order):
        if order.parking_card_session.notify_confirm(order):
            order.paid_notified_at = timezone.now()
            order.save()

    def notify_refund_rps(self, order, sum):
        order.parking_card_session.notify_refund(sum, order)

    def refund(self, order):
        payments = TinkoffPayment.objects.filter(order=order, error_code=-1)
        if payments.exists():
            payment = payments[0]
            request_data = payment.build_cancel_request_data(int(order.sum * 100))
            result = TinkoffAPI().sync_call(
                TinkoffAPI.CANCEL, request_data
            )
            get_logger().info(result)
            if result.get("Status") == u'REVERSED':
                order.refunded_sum = float(result.get("OriginalAmount", 0)) / 100
                get_logger().info('REVERSED: %s' % order.refunded_sum)
                order.save()
            else:
                get_logger().warning('Refund undefined status')