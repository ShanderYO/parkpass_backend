"""
Сервисы для обработки платежей
"""
from django.http import HttpResponse
from base.utils import get_logger
from rps_vendor.models import RpsParking
from integration.services import RpsPaymentTaskService


class UzumPaymentService:
    """
    Сервис для обработки платежей Uzum банка
    """
    
    @staticmethod
    def process_completed_payment(order):
        """
        Обрабатывает завершенный платеж Uzum банка
        
        Args:
            order: Объект Order
            
        Returns:
            HttpResponse or None: HTTP ответ в случае ошибки, None при успехе
        """
        logger = get_logger()
        
        if not order.payload:
            logger.warning(
                "UzumPaymentService: No payload in order %s", order.id
            )
            return None
            
        parking_id = order.parking_card_session.parking_id
        card_id = order.payload.get("card_id")
        
        # Валидация данных
        if not card_id:
            logger.error(
                "UzumPaymentService: Missing card_id in order payload "
                "for order %s",
                order.id
            )
            return HttpResponse("Missing card_id", status=400)
        
        try:
            rps_parking = RpsParking.objects.get(parking_id=parking_id)
        except RpsParking.DoesNotExist:
            logger.error(
                "UzumPaymentService: RPS parking not found for parking_id %s",
                parking_id
            )
            return HttpResponse("RPS parking not found", status=404)

        # Создаем задачу отправки данных на RPS
        try:
            RpsPaymentTaskService.send_rps_confirm_payment_async(
                rps_parking=rps_parking,
                card_id=card_id,
                amount=order.sum,
                order_id=order.id
            )
            logger.info(
                "UzumPaymentService: Created RPS payment task for order %s",
                order.id
            )
        except (ValueError, TypeError, AttributeError) as e:
            # Ловим только бизнес-логические ошибки
            logger.error(
                "UzumPaymentService: Failed to create RPS payment task "
                "for order %s: %s",
                order.id, str(e)
            )
            return HttpResponse("Failed to create RPS task", status=500)
        except Exception as e:
            # Системные ошибки логируем, но не возвращаем HTTP ошибку
            logger.critical(
                "UzumPaymentService: Unexpected error creating RPS task "
                "for order %s: %s",
                order.id, str(e)
            )
            # Не возвращаем ошибку, чтобы не блокировать callback
            
        return None
