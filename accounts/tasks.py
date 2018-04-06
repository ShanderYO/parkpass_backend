from autotask.tasks import periodic_task

from base.utils import get_logger
from parkings.models import ParkingSession
from payments.models import Order


@periodic_task(seconds=30)
def generate_orders_and_pay():

    # TODO check canceled sessions
    active_sessions = ParkingSession.objects.filter(
        state__in=[ParkingSession.STATE_SESSION_STARTED,
                   ParkingSession.STATE_SESSION_UPDATED,
                   ParkingSession.STATE_SESSION_COMPLETED]
    )
    get_logger().info("start generate_dept_orders task: active sessions")

    for session in active_sessions:
        ordered_sum = Order.get_ordered_sum_by_session(session)

        if ordered_sum < session.debt:
            order = None
            if session.state == ParkingSession.STATE_SESSION_COMPLETED:
                current_account_debt = session.debt - ordered_sum
                order = Order(
                    sum=current_account_debt, session=session
                )
                order.save()
            else:
                current_account_debt = session.debt - ordered_sum
                if current_account_debt >= Order.DEFAULT_WITHDRAWAL_AMOUNT:
                    order = Order(
                        sum=Order.DEFAULT_WITHDRAWAL_AMOUNT, session=session
                    )
                    order.save()
            if order:
                order.try_pay()
        else:
            if session.state == ParkingSession.STATE_SESSION_COMPLETED:
                session.state = ParkingSession.STATE_SESSION_CLOSED
                session.save()

    get_logger().info("generate_dept_orders task was executed")