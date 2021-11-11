import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.template.loader import render_to_string

from base.utils import get_logger
from parkpass_backend.celery import app
from parkpass_backend.settings import BASE_DIR, EMAIL_HOST_USER, BASE_DOMAIN
from payments.payment_api import TinkoffAPI, HomeBankAPI
from payments.models import TinkoffPayment, Order, PAYMENT_STATUS_AUTHORIZED, PAYMENT_STATUS_PREPARED_AUTHORIZED, \
    HomeBankPayment, PAYMENT_STATUS_CONFIRMED
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

        if not payments.exists():
            logging.info("Payments were not found: ")
            return None
        payment = payments[0]
        payment.cancel_payment()


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
                    if payment.status == PAYMENT_STATUS_AUTHORIZED:
                        order.confirm_payment_homebank(payment)
                        return
            else:
                for payment in payments:
                    if payment.status == PAYMENT_STATUS_CONFIRMED:
                        logging.info("Cancel payment response: ")
                        payment.cancel_payment()
                        return

    except ObjectDoesNotExist:
        get_logger().warn("Subscription does not found")


def send_screenshot(url, name, email):
    msg_html = render_to_string('emails/fiskal_notification.html', {'link': url,
                                                                    'image': 'https://%s/api/media/fiskal/%s.png' % (
                                                                    BASE_DOMAIN, name)})
    send_mail('Чек об операции. ParkPass', "", EMAIL_HOST_USER,
              [str(email)], html_message=msg_html)

@app.task()
def create_screenshot(url, name, email):
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager
        import os

        DRIVER = ChromeDriverManager().install()

        directory = "/app/media/fiskal"

        if not os.path.exists(directory):
            os.makedirs(directory)

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.headless = True

        driver = webdriver.Chrome(DRIVER, options=options)

        driver.get(url)

        S = lambda X: driver.execute_script('return document.body.parentNode.scroll' + X)
        driver.set_window_size(S('Width'), S('Height'))
        driver.find_element(By.CLASS_NAME, 'ticket-wrapper .transaction__ticket').screenshot(
            directory + '/' + name + '.png')
        print(directory + '/' + name + '.png')
        driver.quit()
        send_screenshot(url, name, email)

    except Exception as e:
        print("Ошибка сохранения скриншота '%s'" % str(e))
        get_logger().error("Ошибка сохранения скриншота '%s'" % str(e))
        send_screenshot(url, name, email)
        # raise e