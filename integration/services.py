import requests
import logging

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
        url = f"https://{rps_parking.domain}/api2/integration/token/"
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
                url, json=payload, headers=headers, timeout=(self.connect_timeout, 3.0)
            )
            response.raise_for_status()
            return response.json() if response.status_code == 200 else {"error": response.json().get("reason", "Unknown Error")}
        except requests.exceptions.RequestException as e:
            # Возвращаем ошибку в случае исключения
            logging.error(f"Request to RPS failed: {e}")
            return {"error": str(e)}


    def send_rps_confirm_payment(self, rps_parking, card_id: str, amount: float):
        url = f"https://{rps_parking.domain}/api2/integration/payment"
        payload = {"regularCustomerId": card_id, "amount": amount}

        return self.make_rps_request(rps_parking, url, payload)
    
    def check_entrance_permission(self, rps_parking, e_ticket: str, card_id: str, parking_session):
        """
        Проверяет разрешение на въезд через сервер РПС.
        """
        url = f"https://{rps_parking.domain}/api2/integration/qr/entrance/permission"
        payload = {
            "eTicket": e_ticket,
            "regularCustomerId": card_id,
        }

        try:
            response = self.make_rps_request(rps_parking, url, payload)

            if "error" in response:
                # Если ошибка, записываем ее в сессию
                parking_session.error = response["error"]
            else:
                # Если ошибки нет, обновляем состояние и сохраняем eTicket
                parking_session.state = parking_session.ENTER_ALLOWED
                parking_session.e_ticket = e_ticket
                parking_session.error = ""
            parking_session.save()

        except Exception as e:
            # Обработка неожиданных исключений
            parking_session.error = f"Exception occurred: {str(e)}"
            parking_session.save()
            
    def confirm_entrance(self, rps_parking, e_ticket, regular_customer_id, parking_session):
        """
        Подтверждает въезд на парковку через сервер РПС.
        """
        url = f"https://{rps_parking.domain}/api2/integration/qr/entrance/confirmation"
        payload = {
            "eTicket": e_ticket,
            "regularCustomerId": regular_customer_id
        }

        try:
            response = self.make_rps_request(rps_parking, url, payload)

            if response is None:
                # Если нет ответа, записываем ошибку
                parking_session.error = "No response from RPS server"
            elif response.get("reason") is None:
                # Успешный ответ, обновляем статус сессии
                parking_session.state = parking_session.STATE_STARTED
                parking_session.error = ""
            else:
                # В ответе есть причина ошибки
                parking_session.error = response.get("reason")

            # Сохраняем изменения в сессии
            parking_session.save()

        except Exception as e:
            parking_session.error = f"Exception occurred: {str(e)}"
            parking_session.save()
            
    def get_sessions_status(self, rps_parking, sessions_payload):
        """
        Получает статус сессий из РПС.
        :param rps_parking: объект RpsParking для авторизации
        :param sessions_payload: список словарей с eTicket и regularCustomerId
        :return: JSON-ответ от сервера или None в случае ошибки
        """
        url = f"https://{rps_parking.domain}/api2/integration/qr/sessions"
        payload = {"sessions": sessions_payload}

        try:
            # Выполняем запрос через make_rps_request
            response = self.make_rps_request(rps_parking, url, payload)
            if response is not None and response.get("reason") == "Ok":
                return response
            else:
                # Логируем, если сервер вернул неуспешный ответ
                logging.error(f"Failed to fetch session statuses: {response}")
                return None
        except Exception as e:
            # Логируем исключение в случае ошибки
            logging.error(f"Exception occurred while fetching session statuses: {str(e)}")
            return None


class RPSService:
    def __init__(self, rps_parking_instance, base_url: str):
        self.rps_parking = rps_parking_instance
        self.connect_timeout = 5.0
        self.base_url = base_url

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
