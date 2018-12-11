from decimal import Decimal

import datetime
from autotask.tasks import periodic_task, delayed_task
from django.core.exceptions import ObjectDoesNotExist

from base.utils import get_logger
from parkings.models import ParkingSession
from payments.models import Order, TinkoffPayment
from payments.payment_api import TinkoffAPI


@delayed_task()
def generate_current_debt_order(parking_session_id):
    get_logger().info("generate_current_debt_order begin")
    try:
        active_session = ParkingSession.objects.get(id=parking_session_id)

        # check completed and zero debt
        if active_session.state in ParkingSession.ACTUAL_COMPLETED_STATES:
            if active_session.debt < 0.01: # < that 1 penny
                active_session.state = ParkingSession.STATE_CLOSED
                active_session.save()
                get_logger().info("Close session %s with <0.01 debt" % parking_session_id)
                return

        ordered_sum = Order.get_ordered_sum_by_session(active_session)
        new_order_sum = active_session.debt - ordered_sum

        get_logger().info(" %s : %s" % (ordered_sum, new_order_sum))

        # if needs to create new order
        if new_order_sum > 0:
            new_order = Order.objects.create(
                session=active_session,
                sum=new_order_sum)
            new_order.try_pay()

        # if start confirm only
        if new_order_sum == 0:
            confirm_all_orders_if_needed(active_session)

        # if over-price authorized
        if new_order_sum < 0:
            last_order = Order.objects.filter(session=active_session)[0]
            get_logger().info("Try reverse order #%s", last_order.id)
            payment = TinkoffPayment.objects.get(order=last_order)
            request_data = payment.build_cancel_request_data(int(last_order.sum * 100))
            result = TinkoffAPI().sync_call(
                TinkoffAPI.CANCEL, request_data
            )
            get_logger().info(result)
            last_order.delete()
            return generate_current_debt_order(parking_session_id)

        # if needs to check closing session
        else:
            orders = Order.objects.filter(session=active_session)
            for order in orders:
                if not order.paid:
                    return

            # Close session if all of orders have paid
            active_session.state = ParkingSession.STATE_CLOSED
            active_session.save()

    except ObjectDoesNotExist:
        pass


def confirm_all_orders_if_needed(parking_session):
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
                    payment = TinkoffPayment.objects.get(order=session_order, error_code=-1)
                    session_order.confirm_payment(payment)
                except ObjectDoesNotExist as e:
                    get_logger().log(e.message)
    else:
        get_logger().info("Wait closing session")


@delayed_task()
def force_pay(parking_session_id):
    try:
        active_session = ParkingSession.objects.get(id=parking_session_id)
        not_authorized_orders = Order.objects.filter(session=active_session, authorized=False)
        if not_authorized_orders.exists():
            for order in not_authorized_orders:
                order.try_pay()
        else:
            not_paid_orders = Order.objects.filter(session=active_session, authorized=True, paid=False)
            for order in not_paid_orders:
                try:
                    payment = TinkoffPayment.objects.get(order=order)
                    order.confirm_payment(payment)
                except ObjectDoesNotExist as e:
                    pass

    except ObjectDoesNotExist:
        pass


@periodic_task(seconds=30)
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
    get_logger().info("start generate_dept_orders task: active sessions %s " % len(active_sessions))

    for session in active_sessions:
        # TODO add checker
        #if session.is_completed_by_vendor() and session.is_completed_by_client() and session.debt == 0:
        #    session.state = ParkingSession.

        ordered_sum = Order.get_ordered_sum_by_session(session)

        if ordered_sum < session.debt:
            order = None
            if session.state == ParkingSession.STATE_COMPLETED \
                    or session.state == ParkingSession.STATE_COMPLETED_BY_VENDOR\
                    or session.state == ParkingSession.STATE_COMPLETED_BY_VENDOR_FULLY:

                current_account_debt = session.debt - ordered_sum
                order = Order(
                    sum=current_account_debt, session=session
                )
                order.save()
            else:
                current_account_debt = session.debt - ordered_sum
                if current_account_debt >= session.parking.max_client_debt:
                    order = Order(
                        sum=session.parking.max_client_debt, session=session
                    )
                    order.save()
            if order:
                order.try_pay()

    get_logger().info("generate_dept_orders task was executed")


def _init_refund(parking_session):
    if parking_session.target_refund_sum <= parking_session.current_refund_sum:
        return

    # Save for stop update again
    parking_session.try_refund=False
    parking_session.save()

    remaining_sum = parking_session.target_refund_sum - parking_session.current_refund_sum

    orders = Order.objects.filter(session=parking_session, paid=True, refund_request=False)
    for order in orders:
        if order.is_refunded():
            continue
        refund = min(remaining_sum, order.sum)
        remaining_sum = remaining_sum - refund
        payment = TinkoffPayment.objects.get(order=order)
        request_data = payment.build_cancel_request_data(int(refund*100))
        result = TinkoffAPI().sync_call(
            TinkoffAPI.CANCEL, request_data
        )
        get_logger().info(result)

        if result.get("Status") == u'REFUNDED':
            order.refunded_sum = float(result.get("OriginalAmount",0))/100
            get_logger().info('REFUNDED: %s' % order.refunded_sum)
            order.save()
        elif result.get("Status") == u'PARTIAL_REFUNDED':
            order.refunded_sum = float(result.get("OriginalAmount", 0)) / 100 - float(result.get("NewAmount", 0)) / 100
            get_logger().info('PARTIAL_REFUNDED: %s' % order.refunded_sum)
            order.save()
        else:
            get_logger().warn('Refund undefined status')

    current_refunded_sum = Decimal(0)
    for order in orders:
        current_refunded_sum = current_refunded_sum + order.refunded_sum

    parking_session.current_refund_sum = current_refunded_sum
    parking_session.try_refund = False
    parking_session.save()


# for 3 day authorized sum
@periodic_task(seconds=3*24*60*60)
def confirm_once_per_3_day():
    _3_days_before = datetime.datetime.now() - datetime.timedelta(days=3)
    authorized_more_that_3_days_orders = Order.objects.filter(authorized=True, created_at__lte=_3_days_before)
    if authorized_more_that_3_days_orders.exists():
        for order in authorized_more_that_3_days_orders:
            try:
                payment = TinkoffPayment.objects.get(order=order)
                order.confirm_payment(payment)
            except ObjectDoesNotExist:
                continue