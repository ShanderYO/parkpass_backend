import requests
from typing import TYPE_CHECKING
from datetime import datetime as dt
from base.utils import get_logger

if TYPE_CHECKING:
    from rps_vendor.models import RpsParking


class RpsIntegrationService:

    connect_timeout = 5.0

    @staticmethod
    def get_token(rps_parking: "RpsParking"):
        url = f"https://{rps_parking.domain}/api2/integration/token"
        payload = {
            "id": rps_parking.integrator_id,
            "pwd": rps_parking.integrator_password,
        }

        try:
            response = requests.post(url, json=payload, timeout=3.0)
            if response.status_code == 200:
                result = response.json()
                token = result.get("token")

                expired_date = dt.strptime(
                    result.get("tokenValidTo"), "%Y-%m-%d %H:%M:%S"
                )
                return token, expired_date
            else:
                # Handle non-200 response
                return None, None
        except requests.exceptions.RequestException:
            # Handle request exception
            return None, None

    def make_rps_request(self, rps_parking, url, payload=None, max_retries=1):
        """
        Выполняет запрос к RPS с retry логикой для увеличения надежности

        Args:
            rps_parking: Объект RpsParking
            url (str): URL для запроса
            payload (dict, optional): Данные для отправки
            max_retries (int): Максимальное количество повторных попыток
                              (по умолчанию 1)

        Returns:
            dict or None: Ответ от RPS или None в случае ошибки
        """
        headers = {
            "RPSIntegrator": f"{rps_parking.integrator_id}",
            "Authorization": f"Bearer {rps_parking.token}",
            "Content-Type": "application/json",
        }

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                logger = get_logger()

                # Логируем попытку запроса
                if attempt > 0:
                    logger.info(
                        f"RPS request retry attempt {attempt} for URL: {url}"
                    )
                else:
                    logger.info(
                        f"RPS request attempt {attempt + 1} for URL: {url}"
                    )

                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=(self.connect_timeout, 10.0)
                )

                # Проверяем статус ответа
                if response.status_code == 200:
                    try:
                        result = response.json()
                        logger.info(f"RPS request successful for URL: {url}")
                        return result
                    except ValueError as e:
                        logger.error(f"Invalid JSON response from RPS: {e}")
                        return None
                elif response.status_code == 401:
                    logger.error(
                        f"RPS authentication failed (401) for URL: {url}"
                    )
                    return None
                elif response.status_code == 500:
                    logger.error(f"RPS server error (500) for URL: {url}")
                    if attempt < max_retries:
                        logger.info("Retrying RPS request due to server error")
                        continue
                    return None
                else:
                    logger.error(
                        f"RPS request failed with status "
                        f"{response.status_code} for URL: {url}"
                    )
                    if attempt < max_retries:
                        logger.info(
                            f"Retrying RPS request due to status "
                            f"{response.status_code}"
                        )
                        continue
                    return None

            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(
                    f"RPS request timeout (attempt {attempt + 1}): {e}"
                )
                if attempt < max_retries:
                    logger.info("Retrying RPS request due to timeout")
                    continue

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(
                    f"RPS connection error (attempt {attempt + 1}): {e}"
                )
                if attempt < max_retries:
                    logger.info(
                        "Retrying RPS request due to connection error"
                    )
                    continue

            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.error(
                    f"RPS request exception (attempt {attempt + 1}): {e}"
                )
                if attempt < max_retries:
                    logger.info(
                        "Retrying RPS request due to request exception"
                    )
                    continue

        # Если все попытки исчерпаны
        logger.error(
            f"RPS request failed after {max_retries + 1} attempts "
            f"for URL: {url}"
        )
        if last_exception:
            logger.error(f"Last exception: {last_exception}")
        return None

    def send_rps_confirm_payment(self, rps_parking, card_id, amount):
        """
        Отправляет подтверждение оплаты на RPS с улучшенной надежностью

        Args:
            rps_parking: Объект RpsParking
            card_id (str): ID карты
            amount (int): Сумма оплаты

        Returns:
            dict or None: Ответ от RPS или None в случае ошибки
        """
        url = f"https://{rps_parking.domain}/api2/integration/payment"
        payload = {"regularCustomerId": card_id, "amount": amount}

        logger = get_logger()
        logger.info(
            f"Sending RPS payment confirmation: card_id={card_id}, "
            f"amount={amount}"
        )

        return self.make_rps_request(rps_parking, url, payload, max_retries=1)


class RpsPaymentTaskService:
    """
    Сервис для создания и управления задачами отправки данных об оплате на RPS
    """

    @staticmethod
    def create_payment_task(order_id, rps_parking_id, card_id, amount):
        """
        Создает задачу на отправку данных об оплате на RPS и запускает celery task

        Args:
            order_id (int): ID заказа
            rps_parking_id (int): ID RPS парковки
            card_id (str): ID карты
            amount (Decimal): Сумма оплаты

        Returns:
            RpsPaymentTask: Созданная задача
        """
        from integration.models import RpsPaymentTask
        from integration.tasks import send_rps_payment_task

        logger = get_logger()

        try:
            # Создаем задачу
            task = RpsPaymentTask.objects.create(
                order_id=order_id,
                rps_parking_id=rps_parking_id,
                card_id=card_id,
                amount=amount
            )

            # Запускаем celery task
            send_rps_payment_task.delay(task.id)

            logger.info(
                f"Created RPS payment task {task.id} for order {order_id}"
            )
            return task

        except Exception as e:
            logger.error(
                f"Failed to create RPS payment task for order {order_id}: {str(e)}"
            )
            raise

    @staticmethod
    def send_rps_confirm_payment_async(rps_parking, card_id, amount, order_id=None):
        """
        Асинхронная отправка данных об оплате на RPS

        Args:
            rps_parking: Объект RpsParking
            card_id (str): ID карты
            amount (Decimal): Сумма оплаты
            order_id (int, optional): ID заказа

        Returns:
            RpsPaymentTask: Созданная задача
        """
        if order_id is None:
            # Если order_id не передан, создаем временный ID
            order_id = 0

        return RpsPaymentTaskService.create_payment_task(
            order_id=order_id,
            rps_parking_id=rps_parking.id,
            card_id=card_id,
            amount=amount
        )


class RPSService:
    def __init__(self, rps_parking_instance, base_url: str):
        self.rps_parking = rps_parking_instance
        self.connect_timeout = 5.0
        self.base_url = base_url

    def get_subscriptions(self):
        url = f"{self.base_url}/subscriptions"
        headers = {
            "RPSIntegrator": f"Id {self.rps_parking.integrator_id}",
            "Authorization": f"Bearer {self.rps_parking.token}",
        }

        try:
            response = requests.get(
                url, headers=headers, timeout=(self.connect_timeout, 5.0)
            )
            response.raise_for_status()
            return response.json() if response.status_code == 200 else None
        except requests.exceptions.RequestException as e:
            print(f"Request to RPS failed: {e}")
            return None

    def purchase_subscription(
        self, user_id, subscription_id, amount, ts_id, transaction_id
    ):
        url = f"{self.base_url}/subscriptions/pay"
        headers = {
            "RPSIntegrator": f"Id {self.rps_parking.integrator_id}",
            "Authorization": f"Bearer {self.rps_parking.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "user_id": user_id,
            "subscription_id": subscription_id,
            "sum": amount,
            "ts_id": ts_id,
            "transaction_id": transaction_id,
        }

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=(self.connect_timeout, 5.0)
            )
            return response.status_code  # Возвращаем статус кода ответа
        except requests.exceptions.RequestException as e:
            print(f"Request to RPS failed: {e}")
            return None

    def subscription_callback(self, subscription_id, expired_at):
        url = "https://parkpass.ru/api/v1/parking/rps/subscription/callback/"
        payload = {"subscription_id": subscription_id, "expired_at": expired_at}

        try:
            response = requests.post(
                url, json=payload, timeout=(self.connect_timeout, 5.0)
            )
            return response.status_code  # Возвращаем статус кода ответа
        except requests.exceptions.RequestException as e:
            print(f"Callback to ParkPass failed: {e}")
            return None

    def entrance_permission(self, eTicket, regularCustomerId):
        url = f"{self.base_url}/api2/integration/qr/entrance/permission"
        headers = {
            "RPSIntegrator": f"Id {self.rps_parking.integrator_id}",
            "Authorization": f"Bearer {self.rps_parking.token}",
            "Content-Type": "application/json",
        }
        payload = {"eTicket": eTicket, "regularCustomerId": regularCustomerId}

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=(self.connect_timeout, 5.0)
            )
            return response.json() if response.status_code == 200 else None
        except requests.exceptions.RequestException as e:
            print(f"Request to RPS failed: {e}")
            return None

    def entrance_confirmation(self, eTicket, regularCustomerId):
        url = f"{self.base_url}/api2/integration/qr/entrance/confirmation"
        headers = {
            "RPSIntegrator": f"Id {self.rps_parking.integrator_id}",
            "Authorization": f"Bearer {self.rps_parking.token}",
            "Content-Type": "application/json",
        }
        payload = {"eTicket": eTicket, "regularCustomerId": regularCustomerId}

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=(self.connect_timeout, 5.0)
            )
            return response.status_code  # Возвращаем статус кода ответа
        except requests.exceptions.RequestException as e:
            print(f"Request to RPS failed: {e}")
            return None

    def get_sessions_status(self, sessions):
        url = f"{self.base_url}/api2/integration/qr/sessions"
        headers = {
            "RPSIntegrator": f"Id {self.rps_parking.integrator_id}",
            "Authorization": f"Bearer {self.rps_parking.token}",
            "Content-Type": "application/json",
        }
        payload = {"sessions": sessions}

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=(self.connect_timeout, 5.0)
            )
            return response.json() if response.status_code == 200 else None
        except requests.exceptions.RequestException as e:
            print(f"Request to RPS failed: {e}")
            return None

    def notify_payment(self, eTicket, regularCustomerId, amount):
        url = f"{self.base_url}/api2/integration/payment"
        headers = {
            "RPSIntegrator": f"Id {self.rps_parking.integrator_id}",
            "Authorization": f"Bearer {self.rps_parking.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "eTicket": eTicket,
            "regularCustomerId": regularCustomerId,
            "amount": amount,
        }

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=(self.connect_timeout, 5.0)
            )
            return response.status_code  # Возвращаем статус кода ответа
        except requests.exceptions.RequestException as e:
            print(f"Request to RPS failed: {e}")
            return None

    def exit_permission(self, deviceId, qrNumber, eTicket, regularCustomerId):
        url = f"{self.base_url}/api2/integration/qr/exit/permission"
        headers = {
            "RPSIntegrator": f"Id {self.rps_parking.integrator_id}",
            "Authorization": f"Bearer {self.rps_parking.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "deviceId": deviceId,
            "qrNumber": qrNumber,
            "eTicket": eTicket,
            "regularCustomerId": regularCustomerId,
        }

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=(self.connect_timeout, 5.0)
            )
            return response.json() if response.status_code == 200 else None
        except requests.exceptions.RequestException as e:
            print(f"Request to RPS failed: {e}")
            return None

    def exit_confirmation(self, deviceId, qrNumber, eTicket, regularCustomerId):
        url = f"{self.base_url}/api2/integration/qr/exit/confirmation"
        headers = {
            "RPSIntegrator": f"Id {self.rps_parking.integrator_id}",
            "Authorization": f"Bearer {self.rps_parking.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "deviceId": deviceId,
            "qrNumber": qrNumber,
            "eTicket": eTicket,
            "regularCustomerId": regularCustomerId,
        }

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=(self.connect_timeout, 5.0)
            )
            return response.status_code  # Возвращаем статус кода ответа
        except requests.exceptions.RequestException as e:
            print(f"Request to RPS failed: {e}")
            return None
