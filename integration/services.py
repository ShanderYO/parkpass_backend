import requests
from typing import TYPE_CHECKING
from datetime import timedelta
from django.utils import timezone
from datetime import datetime as dt

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
            response = requests.post(url, json=payload, timeout=5)
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
        except requests.exceptions.RequestException as e:
            # Handle request exception
            return None, None

    def make_rps_request(self, rps_parking, url, payload=None):
        headers = {
            "RPSIntegrator": f"{rps_parking.integrator_id}",
            "Authorization": f"Bearer {rps_parking.token}",
            # "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=(self.connect_timeout, 5.0)
            )
            response.raise_for_status()
            return response.json() if response.status_code == 200 else None
        except requests.exceptions.RequestException as e:
            # Обработка ошибок запроса
            print(f"Request to RPS failed: {e}")
            return None

    def send_rps_confirm_payment(self, rps_parking, card_id, amount):
        url = f"https://{rps_parking.domain}/api2/integration/payment"
        payload = {"regularCustomerId": card_id, "amount": amount}

        return self.make_rps_request(rps_parking, url, payload)


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
