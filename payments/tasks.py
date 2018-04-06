from autotask.tasks import delayed_task

from base.utils import get_logger
from payments.payment_api import TinkoffAPI


@delayed_task(delay=0)
def start_cancel_request(payment):
    request_data = payment.build_cancel_request_data()
    result = TinkoffAPI().sync_call(
        TinkoffAPI.CANCEL, request_data
    )
    get_logger().info("Cancel payment response: ")
    get_logger().info(str(result))

    # Tink-off gateway not responded
    if not result:
        return None

    # TODO anything