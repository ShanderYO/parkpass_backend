import logging

from django.core.exceptions import ObjectDoesNotExist

from base.utils import get_logger
from parkpass_backend.celery import app
from payments.payment_api import TinkoffAPI, HomeBankAPI
from payments.models import TinkoffPayment, Order, PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_PREPARED_AUTHORIZED, \
    HomeBankPayment
from rps_vendor.models import RpsSubscription


@app.task()
def start_cancel_request(order_id, acquiring='tinkoff'):
    logging.info("start cancel payment for %s" % acquiring)
    if acquiring == 'tinkoff':
        payments = TinkoffPayment.objects.filter(order__id=order_id)

        if not payments.exists():
            logging.info("Payments were not found: ")
            return None
        payment = payments[0]

        request_data = payment.build_cancel_request_data()
        result = TinkoffAPI().sync_call(
            TinkoffAPI.CANCEL, request_data
        )
        logging.info("Cancel payment response: ")
        logging.info(str(result))

        # Tink-off gateway not responded
        if not result:
            return None
    elif acquiring == 'homebank':
        payments = HomeBankPayment.objects.filter(order__id=order_id)

        logging.info("start cancel payment for %s" % acquiring)
        get_logger().info("home bank log 8")

        if not payments.exists():
            logging.info("Payments were not found: ")
            return None
        payment = payments[0]
        payment.cancel_payment()
        get_logger().info("home bank log 9")


@app.task()
def make_buy_subscription_request(subscription_id, acquiring='tinkoff'):
    get_logger().info("make_buy_subscription_request invoke")
    try:
        subscription = RpsSubscription.objects.get(
            id=subscription_id
        )
        order = Order.objects.get(
            authorized = True,
            subscription = subscription)

        if acquiring == 'tinkoff':
            payments = TinkoffPayment.objects.filter(order=order)

            if subscription.request_buy():
                for payment in payments:
                    if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                        order.confirm_payment(payment)
                        return
            else:
                for payment in payments:
                    if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                        request_data = payment.build_cancel_request_data()
                        result = TinkoffAPI().sync_call(
                            TinkoffAPI.CANCEL, request_data
                        )
                        logging.info("Cancel payment response: ")
                        logging.info(str(result))
                        return
        elif acquiring == 'homebank':
            payments = HomeBankPayment.objects.filter(order=order)

            if subscription.request_buy():
                pass
                for payment in payments:
                    if payment.status == 'init':
                        order.try_pay(payment)
                        return
            else:
                for payment in payments:
                    if payment.status == 'paid':
                        logging.info("Cancel payment response: ")
                        payment.cancel_payment()
                        return

    except ObjectDoesNotExist:
        get_logger().warn("Subscription does not found")