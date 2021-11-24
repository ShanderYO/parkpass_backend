import logging
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from base.utils import get_logger
from parkings.models import ParkingSession
from parkpass_backend import settings
from parkpass_backend.celery import app
from payments.models import Order, TinkoffPayment, PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_PREPARED_AUTHORIZED, \
    HomeBankPayment
from payments.payment_api import TinkoffAPI
import requests

@app.task()
def generate_current_debt_order(parking_session_id):
    logging.info("generate_current_debt_order begin")
    try:
        active_session = ParkingSession.objects.select_related(
            'parking').get(id=parking_session_id)

        # check completed and zero debt
        if active_session.state in ParkingSession.ACTUAL_COMPLETED_STATES:
            if active_session.get_debt() < 0.01: # < that 1 penny
                active_session.state = ParkingSession.STATE_CLOSED
                active_session.save()
                logging.info("Close session %s with < 0.01 debt" % parking_session_id)
                return

        ordered_sum = Order.get_ordered_sum_by_session(active_session)
        new_order_sum = active_session.get_debt() - ordered_sum

        logging.info(" %s : %s" % (ordered_sum, new_order_sum))

        # Prevent create order with sum less than max_client_debt of parking
        if active_session.state not in ParkingSession.ACTUAL_COMPLETED_STATES \
                and active_session.state != ParkingSession.STATE_CLOSED:
            if new_order_sum >= active_session.parking.max_client_debt:
                new_order_sum = active_session.parking.max_client_debt
            else:
                new_order_sum = 0

        if new_order_sum > 0:
            new_order = Order.objects.create(
                session=active_session,
                sum=new_order_sum,
                acquiring=active_session.parking.acquiring)
            new_order.try_pay()

        # if start confirm only
        if new_order_sum == 0:
            confirm_all_orders_if_needed(active_session)

        # if over-price authorized
        if new_order_sum < 0:
            last_order = Order.objects.filter(session=active_session)[0]
            logging.info("Try reverse order #%s", last_order.id)

            if (last_order.acquiring ==  'homebank'):
                payment = HomeBankPayment.objects.filter(order=last_order)[0]
                payment.cancel_payment()

            else:
                payment = TinkoffPayment.objects.get(order=last_order, status=PAYMENT_STATUS_AUTHORIZED)
                request_data = payment.build_cancel_request_data(int(last_order.sum * 100))
                result = TinkoffAPI().sync_call(
                    TinkoffAPI.CANCEL, request_data
                )
                logging.info(result)

            last_order.delete()
            return generate_current_debt_order(parking_session_id)

        # if needs to check closing session
        else:
            orders = Order.objects.filter(session=active_session)
            for order in orders:
                if not order.paid:
                    return

            # Close session if all of orders have paid and session completed
            if active_session.is_completed_by_vendor():
                active_session.state = ParkingSession.STATE_CLOSED
                active_session.save()

    except ObjectDoesNotExist:
        pass

def count_refund_orders_for_session(parking_session):
    orders = Order.objects.filter(session=parking_session, refund_request=True)
    current_refunded_sum = Decimal(0)

    for order in orders:
        get_logger().info('order id for refund %s sum %s' % (order.id, order.refunded_sum))
        current_refunded_sum = current_refunded_sum + order.refunded_sum

    get_logger().info(current_refunded_sum)

    parking_session.current_refund_sum = current_refunded_sum
    parking_session.try_refund = False
    parking_session.save()

    get_logger().info('current_refunded_sum: %s' % current_refunded_sum )

def confirm_all_orders_if_needed(parking_session):
    logging.info("check begin confirmation..")
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
                    if session_order.acquiring == 'homebank':
                        payment = HomeBankPayment.objects.filter(order=session_order, status=PAYMENT_STATUS_AUTHORIZED)[0]
                        session_order.confirm_payment_homebank(payment)
                    else:
                        payment = TinkoffPayment.objects.get(
                            order=session_order,
                            status__in=[PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED],
                            error_code=-1)
                        session_order.confirm_payment(payment)
                except ObjectDoesNotExist as e:
                    logging.warning(e)
    else:
        logging.info("Wait vendor completing session")


def force_pay(parking_session_id):
    get_logger().info('force_pay_start')
    try:
        active_session = ParkingSession.objects.get(id=parking_session_id)
        not_authorized_orders = Order.objects.filter(session=active_session, authorized=False)
        not_paid_orders = Order.objects.filter(session=active_session, authorized=True, paid=False)

        if not_authorized_orders.exists():
            get_logger().info('not_authorized_orders.exists()')
            for order in not_authorized_orders:
                get_logger().info('order.try_pay()')
                order.try_pay()
        elif not_paid_orders.exists():
            get_logger().info('not_paid_orders')
            get_logger().info(not_paid_orders)

            for order in not_paid_orders:
                if (order.acquiring == 'homebank'):
                    payments = HomeBankPayment.objects.filter(order=order)
                    paid = False
                    get_logger().info(payments)

                    for payment in payments:
                        if payment.status == PAYMENT_STATUS_AUTHORIZED:
                            order.confirm_payment_homebank(payment)
                            paid = True
                            return

                    if not paid:
                        order.try_pay()
                        get_logger().info('not paid')
                        if (order.acquiring == 'homebank'):
                            get_logger().info('force pay 1')
                            payments = HomeBankPayment.objects.filter(order=order)
                            for payment in payments:
                                get_logger().info('force pay 2 - %s %s' % (payment.status, payment.payment_id))
                                get_logger().info(payment.status == PAYMENT_STATUS_AUTHORIZED)
                                get_logger().info(type(payment.status))
                                get_logger().info(type(PAYMENT_STATUS_AUTHORIZED))

                                if payment.status == PAYMENT_STATUS_AUTHORIZED:
                                    get_logger().info('force pay 3')
                                    order.confirm_payment_homebank(payment)
                                    break
                else:
                    payments = TinkoffPayment.objects.filter(order=order)
                    for payment in payments:
                        if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                            order.confirm_payment(payment)
                            return
                    if payments.exists():
                        order.confirm_payment(payments[0])
                    else:
                        order.try_pay()
                        get_logger().info('payments not exists()')
                        if (order.acquiring == 'homebank'):
                            get_logger().info('payments not exists | force pay close 1')
                            payments = HomeBankPayment.objects.filter(order=order)
                            for payment in payments:
                                get_logger().info('payments not exists | force pay close 2 - %s %s' % (payment.status, payment.payment_id))
                                get_logger().info(payment.status == PAYMENT_STATUS_AUTHORIZED)
                                get_logger().info(type(payment.status))
                                get_logger().info(type(PAYMENT_STATUS_AUTHORIZED))

                                if payment.status == PAYMENT_STATUS_AUTHORIZED:
                                    get_logger().info('payments not exists | force pay close 3')
                                    order.confirm_payment_homebank(payment)
                                    break
                        else:
                            payments = TinkoffPayment.objects.filter(order=order)
                            for payment in payments:
                                if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                                    order.confirm_payment(payment)
                                    break


        else:
            sum_to_pay = active_session.get_debt()
            new_order = Order.objects.create(
                session=active_session,
                sum=sum_to_pay,
                acquiring=active_session.parking.acquiring)
            new_order.try_pay()
            get_logger().info('force pay close 0')

            if (new_order.acquiring == 'homebank'):
                get_logger().info('force pay close 1')
                payments = HomeBankPayment.objects.filter(order=new_order)
                for payment in payments:
                    get_logger().info('force pay close 2 - %s %s' % (payment.status, payment.payment_id))
                    get_logger().info(payment.status == PAYMENT_STATUS_AUTHORIZED)
                    get_logger().info(type(payment.status))
                    get_logger().info(type(PAYMENT_STATUS_AUTHORIZED))

                    if payment.status == PAYMENT_STATUS_AUTHORIZED:
                        get_logger().info('force pay close 3')
                        new_order.confirm_payment_homebank(payment)
                        break
            else:
                payments = TinkoffPayment.objects.filter(order=new_order)
                for payment in payments:
                    if payment.status in [PAYMENT_STATUS_PREPARED_AUTHORIZED, PAYMENT_STATUS_AUTHORIZED]:
                        new_order.confirm_payment(payment)
                        break
                print(sum_to_pay)

    except ObjectDoesNotExist:
        pass


@app.task()
def generate_orders_and_pay():

    # Check refund request
    refund_required_sessions = ParkingSession.objects.filter(try_refund=True)
    if refund_required_sessions.exists():
        for session in refund_required_sessions:
            _init_refund(session)

    # TODO check canceled sessions
    active_sessions = ParkingSession.objects.filter(
        state__in=[ParkingSession.STATE_STARTED,
                   ParkingSession.STATE_STARTED_BY_VENDOR,
                   ParkingSession.STATE_COMPLETED_BY_VENDOR,
                   ParkingSession.STATE_COMPLETED_BY_VENDOR_FULLY,
                   ParkingSession.STATE_COMPLETED_BY_CLIENT_FULLY,
                   ParkingSession.STATE_COMPLETED],
        is_suspended=False,
    )
    logging.info("start generate_dept_orders task: active sessions %s " % len(active_sessions))

    for session in active_sessions:
        ordered_sum = Order.get_ordered_sum_by_session(session)

        if ordered_sum < session.get_debt():
            order = None
            if session.state == ParkingSession.STATE_COMPLETED \
                    or session.state == ParkingSession.STATE_COMPLETED_BY_VENDOR\
                    or session.state == ParkingSession.STATE_COMPLETED_BY_VENDOR_FULLY:

                current_account_debt = session.get_debt() - ordered_sum
                order = Order(
                    sum=current_account_debt, session=session,
                    acquiring=session.parking.acquiring
                )
                order.save()
            else:
                current_account_debt = session.get_debt() - ordered_sum
                if current_account_debt >= session.parking.max_client_debt:
                    order = Order(
                        sum=session.parking.max_client_debt, session=session,
                        acquiring=session.parking.acquiring
                    )
                    order.save()
            if order:
                order.try_pay()

    logging.info("generate_dept_orders task was executed")


def _init_refund(parking_session):
    if parking_session.target_refund_sum <= parking_session.current_refund_sum:
        return

    # Save for stop update again
    parking_session.try_refund=False
    parking_session.save()

    remaining_sum = parking_session.target_refund_sum - parking_session.current_refund_sum

    orders = Order.objects.filter(session=parking_session, authorized=True, canceled=True, refund_request=False)

    get_logger().info("_init_refund %s " % remaining_sum)

    for order in orders:
        if order.is_refunded():
            get_logger().info("if order.is_refunded continue")
            continue
        refund = min(remaining_sum, order.sum)
        remaining_sum = remaining_sum - refund

        get_logger().info("refund %s " % refund)

        if (order.acquiring == 'homebank'):
            get_logger().info("cancel homebank payment")
            if refund:
                payment = HomeBankPayment.objects.filter(order=order)[0]
                payment.cancel_payment()
        else:
            get_logger().info("cancel tinkoff payment")
            payment = TinkoffPayment.objects.get(order=order, status=PAYMENT_STATUS_AUTHORIZED)
            request_data = payment.build_cancel_request_data(int(refund*100))
            result = TinkoffAPI().sync_call(
                TinkoffAPI.CANCEL, request_data
            )
            get_logger().info(result)

            if result.get("Status") == u'REFUNDED' or result.get("Status") == u'REVERSED':
                order.refund_request = True
                order.refunded_sum = float(result.get("OriginalAmount",0))/100
                get_logger().info('REFUNDED: %s' % order.refunded_sum)
                order.save()
            elif result.get("Status") == u'PARTIAL_REFUNDED':
                order.refund_request = True
                order.refunded_sum = float(result.get("OriginalAmount", 0)) / 100 - float(result.get("NewAmount", 0)) / 100
                get_logger().info('PARTIAL_REFUNDED: %s' % order.refunded_sum)
                order.save()
            else:
                get_logger().warning('Refund undefined status')

    get_logger().info("remaining_sum %s " % remaining_sum)

    count_refund_orders_for_session(parking_session)


@app.task()
def confirm_once_per_3_day():
    _3_days_before = timezone.now() - timezone.timedelta(days=3)
    authorized_more_that_3_days_orders = Order.objects.filter(
        authorized=True, created_at__lte=_3_days_before)

    if authorized_more_that_3_days_orders.exists():
        for order in authorized_more_that_3_days_orders:
            if order.acquiring == 'homebank':
                payments = HomeBankPayment.objects.filter(order=order)
            else:
                payments = TinkoffPayment.objects.filter(order=order)
            if payments.exists():
                order.confirm_payment(payments[0])
