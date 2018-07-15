from autotask.tasks import delayed_task

from base.utils import get_logger
from payments.payment_api import TinkoffAPI
from payments.models import TinkoffPayment


@delayed_task(delay=0)
def start_cancel_request(order):
    payments = TinkoffPayment.order.filter(order=order)
    if not payments.exists():
        get_logger().info("Payments were not found: ")
        return None
    payment = payments[0]

    request_data = payment.build_cancel_request_data()
    result = TinkoffAPI().sync_call(
        TinkoffAPI.CANCEL, request_data
    )
    get_logger().info("Cancel payment response: ")
    get_logger().info(str(result))

    # Tink-off gateway not responded
    if not result:
        return None