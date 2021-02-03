# -*- coding: utf-8 -*-
from base.exceptions import PaymentException
from payments.payment_api import TinkoffApiException


class TinkoffExceptionAdapter(object):
    def __init__(self, code):
        self.code = code

    def get_api_exeption(self):
        if self.code in TinkoffApiException.TINKOFF_EXCEPTION_3DS_NOT_AUTH:
            return PaymentException(
                PaymentException.EXCEPTION_3DS_NOT_AUTH,
                "Не пройдена идентификация 3DS"
            )
        if self.code in TinkoffApiException.TINKOFF_EXCEPTION_DENIED_FROD_MONITOR:
            return PaymentException(
                PaymentException.TINKOFF_EXCEPTION_DENIED_FROD_MONITOR,
                "Операция отклонена фрод-мониторингом"
            )
        if self.code in TinkoffApiException.TINKOFF_EXCEPTION_INVALID_CARD:
            return PaymentException(
                PaymentException.EXCEPTION_DENIED_INVALID_CARD,
                "Проверьте реквизиты или воспользуйтесь другой картой"
            )
        if self.code in TinkoffApiException.TINKOFF_EXCEPTION_INVALID_REPEAT_LATER:
            return PaymentException(
                PaymentException.EXCEPTION_INVALID_REPEAT_LATER,
                "Воспользуйтесь другой картой, банк, выпустивший карту, отклонил операцию"
            )
        if self.code in TinkoffApiException.TINKOFF_EXCEPTION_BANK_OPERATION_DENIED:
            return PaymentException(
                PaymentException.TINKOFF_EXCEPTION_BANK_OPERATION_DENIED,
                "Повторите попытку позже"
            )
        if self.code in TinkoffApiException.TINKOFF_EXCEPTION_MANY_MONEY:
            return PaymentException(
                PaymentException.EXCEPTION_INVALID_REPEAT_LATER,
                "Недостаточно средств на карте"
            )
        # default
        return PaymentException(
            PaymentException.EXCEPTION_INTERNAL_ERROR,
            "Внутренняя ошибка системы"
        )
