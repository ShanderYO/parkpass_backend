# -*- coding: utf-8 -*-
from parkpass import settings
from sms_gateway import providers


def get_default_sms_provider():
    conf = getattr(settings, "SMS_GATEWAYS", {})
    for provider in conf:
        if provider.get("is_default", False):
            return providers.SMSProviderBeeline()
            #return _load_provider(provider)

"""
def my_import(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def _load_provider(conf):
    class_name = conf["provider"]
    cls = my_import(class_name)
    return cls(conf)
"""

class SMSGateway(object):
    def __init__(self):
        self.provider = get_default_sms_provider()
        self.exception = False

    def send_formatted_message(self, phone, template, params):
        message = template % params
        self.send_message(phone, message)

    def send_message(self, phone, message):
        # phone has format +7(XXX)XXXXXXX
        if not settings.SMS_GATEWAY_ENABLED:
            return
        # Notmalize format +7 XXX XXXXXXX
        formatted_phone = self._get_phone_format(phone)

        try:
            self.provider.send_sms(formatted_phone, message)
        except Exception as e:
            self.exception = e

    def _get_phone_format(self, phone):
        return phone.replace('+', '').replace('(', '').replace(')', '').replace(' ', '')
