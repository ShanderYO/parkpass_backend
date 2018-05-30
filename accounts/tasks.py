from autotask.tasks import periodic_task, delayed_task
from django.core.exceptions import ObjectDoesNotExist

from base.utils import get_logger
from parkings.models import ParkingSession
from payments.models import Order


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

    # TODO check canceled sessions
    active_sessions = ParkingSession.objects.filter(
        state__in=[ParkingSession.STATE_STARTED,
                   ParkingSession.STATE_STARTED_BY_VENDOR,
                   ParkingSession.STATE_COMPLETED_BY_VENDOR,
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
            if session.state == ParkingSession.STATE_COMPLETED:
                session.state = ParkingSession.STATE_CLOSED
                session.save()

    get_logger().info("generate_dept_orders task was executed")