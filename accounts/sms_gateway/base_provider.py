import abc
import requests

from base.exceptions import NetworkException


class SMSBaseProvider:
    SEND_SMS_URL = "stub"

    def __init__(self):
        self.exception = None
        self.phone = None
        self.message = ""

    @abc.abstractmethod
    def build_request(self):
        pass

    def send_by_request(self):
        try:
            return self.build_request()

        except requests.exceptions.ConnectTimeout as e:
            self.exception = NetworkException(
                NetworkException.SMS_GATEWAY_NOT_AVAILABLE,
                "Sms gateway not found"
            )

        except requests.exceptions.ReadTimeout:
            self.exception = NetworkException(
                NetworkException.SMS_GATEWAY_NOT_AVAILABLE,
                "Timeout error"
            )

        except requests.exceptions.HTTPError as e:
            self.exception = NetworkException(
                NetworkException.SMS_GATEWAY_NOT_AVAILABLE,
                "Sms gateway server error"
            )

        except requests.exceptions.RequestException:
            self.exception = NetworkException(
                NetworkException.SMS_GATEWAY_NOT_AVAILABLE,
                "Unknown exception"
            )