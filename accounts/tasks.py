from autotask.tasks import periodic_task, delayed_task
from django.core.exceptions import ObjectDoesNotExist

from base.utils import get_logger
from parkings.models import ParkingSession
from payments.models import Order, TinkoffPayment
from payments.payment_api import TinkoffAPI


@delayed_task()
def generate_current_debt_order(parking_session_id):
    try:
        active_session = ParkingSession.objects.get(id=parking_session_id)
        not_paid_orders = Order.objects.filter(session=active_session, paid=False)
        if not_paid_orders.exists():
            for order in not_paid_orders:
                order.try_pay()

        ordered_sum = Order.get_ordered_sum_by_session(active_session)
        new_order_sum = active_session.debt - ordered_sum
        if new_order_sum > 0:
            new_order = Order.objects.create(
                session=active_session,
                account=active_session.client,
                sum=new_order_sum)
            new_order.try_pay()

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
                   ParkingSession.STATE_COMPLETED]
    )
    get_logger().info("start generate_dept_orders task: active sessions")

    for session in active_sessions:
        ordered_sum = Order.get_ordered_sum_by_session(session)

        if ordered_sum < session.debt:
            order = None
            if session.state == ParkingSession.STATE_COMPLETED or session.state == ParkingSession.STATE_COMPLETED_BY_VENDOR:
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
        else:
            if session.state >= ParkingSession.STATE_COMPLETED_BY_VENDOR:
                session.state = ParkingSession.STATE_CLOSED
                session.save()

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

    current_refunded_sum = 0
    for order in orders:
        current_refunded_sum = current_refunded_sum + order.refunded_sum

    parking_session.current_refund_sum = current_refunded_sum
    parking_session.try_refund = False
    parking_session.save()