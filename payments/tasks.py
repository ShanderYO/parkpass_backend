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
    """
        {
            u'Status': u'REFUNDED',
            u'OrderId': u'18',
            u'Success': True,
            u'NewAmount': 0,
            u'ErrorCode': u'0',
            u'TerminalKey': u'1516954410942DEMO',
            u'OriginalAmount': 100,
            u'PaymentId': u'17881695'
        }

        # From callback

        {u'OrderId': u'18', u'Status': u'REFUNDED',
          u'Success': True, u'Token': u'ced65967528612f4aa4a4890d59f44706c788e152c9dc4a4a73db331f2a99055',
           u'ExpDate': u'1122', u'ErrorCode': u'0', u'Amount': 100,
           u'TerminalKey': u'1516954410942DEMO', u'CardId': 3582969,
           u'PaymentId': 17881695, u'Pan': u'430000******0777'}

    """