import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from base.utils import get_logger
from parkpass_backend.celery import app
from parkpass_backend.settings import EMAIL_HOST_USER, BASE_DOMAIN
from payments.payment_api import TinkoffAPI, UzumBankAPI
from payments.models import (
    TinkoffPayment,
    Order,
    PAYMENT_STATUS_AUTHORIZED,
    PAYMENT_STATUS_PREPARED_AUTHORIZED,
    HomeBankPayment,
    PAYMENT_STATUS_CONFIRMED,
    UzumBankPayment,
)
from rps_vendor.models import RpsSubscription


@app.task()
def start_cancel_request(order_id, acquiring="tinkoff"):
    logging.info("start cancel payment for %s" % acquiring)
    if acquiring == "tinkoff":
        payments = TinkoffPayment.objects.filter(order__id=order_id)

        if not payments.exists():
            logging.info("Payments were not found: ")
            return None
        payment = payments[0]

        request_data = payment.build_cancel_request_data()
        result = TinkoffAPI().sync_call(TinkoffAPI.CANCEL, request_data)
        logging.info("Cancel payment response: ")
        logging.info(str(result))

        # Tink-off gateway not responded
        if not result:
            return None
    elif acquiring == "homebank":
        payments = HomeBankPayment.objects.filter(order__id=order_id)

        logging.info("start cancel payment for %s" % acquiring)

        if not payments.exists():
            logging.info("Payments were not found: ")
            return None
        payment = payments[0]
        payment.cancel_payment()


@app.task()
def make_buy_subscription_request(subscription_id, acquiring="tinkoff"):
    get_logger().info("make_buy_subscription_request invoke")
    try:
        subscription = RpsSubscription.objects.get(id=subscription_id)
        order = Order.objects.get(authorized=True, subscription=subscription)

        if acquiring == "tinkoff":
            payments = TinkoffPayment.objects.filter(order=order)

            if subscription.request_buy():
                for payment in payments:
                    if payment.status in [
                        PAYMENT_STATUS_PREPARED_AUTHORIZED,
                        PAYMENT_STATUS_AUTHORIZED,
                    ]:
                        order.confirm_payment(payment)
                        return
            else:
                for payment in payments:
                    if payment.status in [
                        PAYMENT_STATUS_PREPARED_AUTHORIZED,
                        PAYMENT_STATUS_AUTHORIZED,
                    ]:
                        request_data = payment.build_cancel_request_data()
                        result = TinkoffAPI().sync_call(TinkoffAPI.CANCEL, request_data)
                        logging.info("Cancel payment response: ")
                        logging.info(str(result))
                        return
        elif acquiring == "homebank":
            payments = HomeBankPayment.objects.filter(order=order)

            if subscription.request_buy():
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
    msg_html = render_to_string(
        "emails/fiskal_notification.html",
        {
            "link": url,
            "image": "https://%s/api/media/fiskal/%s.png" % (BASE_DOMAIN, name),
        },
    )
    send_mail(
        "Чек об операции. ParkPass",
        "",
        EMAIL_HOST_USER,
        [str(email)],
        html_message=msg_html,
    )


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
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.headless = True

        driver = webdriver.Chrome(DRIVER, options=options)

        driver.get(url)

        S = lambda X: driver.execute_script(
            "return document.body.parentNode.scroll" + X
        )
        driver.set_window_size(S("Width"), S("Height"))
        driver.find_element(
            By.CLASS_NAME, "ticket-wrapper .transaction__ticket"
        ).screenshot(directory + "/" + name + ".png")
        print(directory + "/" + name + ".png")
        driver.quit()
        send_screenshot(url, name, email)

    except Exception as e:
        print("Ошибка сохранения скриншота '%s'" % str(e))
        get_logger().error("Ошибка сохранения скриншота '%s'" % str(e))
        send_screenshot(url, name, email)
        # raise e


@app.task()
def send_uzum_receipts_email(payment_id):
    """
    Отправка чеков Uzum банка клиенту на email
    """
    try:
        payment = UzumBankPayment.objects.select_related("order", "order__account").get(
            id=payment_id
        )
        get_logger().info(
            "Sending Uzum receipts email for payment %s", payment.merchant_order_id
        )

        # Получаем чеки
        receipts = payment.get_receipts()
        if not receipts:
            get_logger().warning(
                "No receipts found for Uzum payment %s", payment.merchant_order_id
            )
            return

        # Получаем email клиента - приоритет у сохраненного email в платеже
        email_to_send = None

        # Сначала проверяем сохраненный email в платеже
        if payment.receipt_email:
            email_to_send = payment.receipt_email
            get_logger().info(
                "Using saved email from payment for Uzum payment %s: %s",
                payment.merchant_order_id,
                email_to_send,
            )
        else:
            # Fallback на логику аккаунта (для обратной совместимости)
            account = payment.order.get_account()
            if (
                account
                and account.email_fiskal_notification_enabled
                and account.email
            ):
                email_to_send = account.email
                get_logger().info(
                    "Using account email for Uzum payment %s: %s",
                    payment.merchant_order_id,
                    email_to_send,
                )

        if not email_to_send:
            get_logger().warning(
                "No email available for Uzum payment %s (no saved email and no account email)",
                payment.merchant_order_id,
            )
            return

        # Подготавливаем данные для email
        receipt_urls = [
            receipt.get("receiptUrl")
            for receipt in receipts
            if receipt.get("receiptUrl")
        ]

        if not receipt_urls:
            get_logger().warning(
                "No receipt URLs found for Uzum payment %s", payment.merchant_order_id
            )
            return

        # Рендерим email шаблон
        msg_html = render_to_string(
            "emails/uzum_receipt_notification.html",
            {
                "receipt_urls": receipt_urls,
                "payment": payment,
                "order": payment.order,
                "email": email_to_send,
                "receipts_count": len(receipt_urls),
            },
        )

        # Отправляем email
        send_mail(
            "Чек об оплате - Uzum Bank",
            "",
            EMAIL_HOST_USER,
            [email_to_send],
            html_message=msg_html,
        )

        get_logger().info(
            "Successfully sent Uzum receipts email to %s for payment %s",
            email_to_send,
            payment.merchant_order_id,
        )

    except UzumBankPayment.DoesNotExist:
        get_logger().error("UzumBankPayment with id %s not found", payment_id)
    except Exception as e:
        get_logger().error(
            "Error sending Uzum receipts email for payment %s: %s", payment_id, str(e)
        )


@app.task(bind=True, max_retries=5, default_retry_delay=60)
def fetch_uzum_receipts(self, payment_id):
    """
    Получение и сохранение чеков Uzum банка с ретраями.
    Гарантирует отправку email только один раз с помощью select_for_update и флага receipt_sent.
    """
    try:
        get_logger().info(
            "Fetching Uzum receipts for payment %s (attempt %d/%d)",
            payment_id,
            self.request.retries + 1,
            5,
        )

        # Сначала проверяем статус и флаг без блокировки
        payment = UzumBankPayment.objects.select_related("order").get(id=payment_id)
        
        # Проверяем, что платеж завершен
        if payment.status != "COMPLETED":
            get_logger().warning(
                "Payment %s is not completed (status: %s), skipping receipts fetch",
                payment.merchant_order_id,
                payment.status,
            )
            return

        # Проверяем, был ли уже отправлен чек
        if payment.receipt_sent:
            get_logger().info(
                "Receipt already sent for payment %s, skipping",
                payment.merchant_order_id,
            )
            return

        # Проверяем, есть ли уже чеки
        existing_receipts = payment.get_receipts()
        if existing_receipts:
            get_logger().info(
                "Receipts already exist for payment %s, sending email",
                payment.merchant_order_id,
            )
            # Отправляем email и помечаем как отправленный в транзакции
            with transaction.atomic():
                payment = (
                    UzumBankPayment.objects.select_related("order")
                    .select_for_update()
                    .get(id=payment_id)
                )
                if not payment.receipt_sent:  # Двойная проверка
                    send_uzum_receipts_email.delay(payment.id)
                    payment.receipt_sent = True
                    payment.save(update_fields=["receipt_sent"])
            return

        # Получаем чеки через API
        receipts_response = UzumBankAPI().get_receipts(payment.uzum_order_id)

        if not receipts_response or "error" in receipts_response:
            get_logger().warning(
                "Failed to get receipts for payment %s (attempt %d): %s",
                payment.merchant_order_id,
                self.request.retries + 1,
                receipts_response,
            )
            # Ретраим задачу
            raise self.retry(
                exc=Exception(f"API error: {receipts_response}"),
                countdown=60 * (self.request.retries + 1),
            )

        receipts = receipts_response.get("result", {}).get("receipts", [])
        receipts_count = len(receipts)

        if receipts_count == 0:
            get_logger().warning(
                "No receipts found for payment %s (attempt %d), retrying...",
                payment.merchant_order_id,
                self.request.retries + 1,
            )
            # Ретраим задачу, если чеков еще нет
            raise self.retry(
                exc=Exception("No receipts available yet"),
                countdown=60 * (self.request.retries + 1),
            )

        # Сохраняем чеки и отправляем email в транзакции
        with transaction.atomic():
            payment = (
                UzumBankPayment.objects.select_related("order")
                .select_for_update()
                .get(id=payment_id)
            )

            # Двойная проверка флага
            if payment.receipt_sent:
                get_logger().info(
                    "Receipt already sent for payment %s (race condition), skipping",
                    payment.merchant_order_id,
                )
                return

            # Сохраняем чеки в отдельное поле
            payment.receipts = receipts
            payment.raw_response = {
                **(payment.raw_response or {}),
                "receipts_fetched_at": timezone.now().isoformat(),
                "receipts_fetch_attempts": self.request.retries + 1,
            }
            payment.save()

            get_logger().info(
                "Successfully saved %d receipts for payment %s",
                receipts_count,
                payment.merchant_order_id,
            )

            # Отправляем email с чеками и помечаем как отправленный
            send_uzum_receipts_email.delay(payment.id)
            payment.receipt_sent = True
            payment.save(update_fields=["receipt_sent"])

    except UzumBankPayment.DoesNotExist:
        get_logger().error("UzumBankPayment with id %s not found", payment_id)
    except Exception as exc:
        get_logger().error(
            "Error fetching Uzum receipts for payment %s (attempt %d): %s",
            payment_id,
            self.request.retries + 1,
            str(exc),
        )
        # Ретраим задачу
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
