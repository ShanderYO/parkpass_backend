from celery import shared_task
from django.db import transaction, models
from base.utils import get_logger
from integration.models import RpsPaymentTask
from integration.services import RpsIntegrationService
from rps_vendor.models import RpsParking
import time
import random


def exponential_backoff(attempt, base_delay=1, max_delay=60, jitter=True):
    """Экспоненциальная задержка с jitter"""
    delay = min(base_delay * (2 ** attempt), max_delay)
    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    return delay


@shared_task(bind=True, max_retries=3)
def send_rps_payment_task(self, task_id):
    """
    Celery task для отправки данных об оплате на RPS с exponential backoff
    """
    logger = get_logger()
    start_time = time.time()

    try:
        # Получаем задачу с блокировкой в транзакции
        with transaction.atomic():
            try:
                task = RpsPaymentTask.objects.select_for_update().get(
                    id=task_id
                )
            except RpsPaymentTask.DoesNotExist:
                error_msg = f"RpsPaymentTask with id {task_id} not found"
                logger.error(error_msg)
                return error_msg

            # Проверяем, можно ли обрабатывать задачу
            if not task.can_retry():
                logger.warning(
                    f"Task {task_id} cannot be retried. "
                    f"Status: {task.status}, attempts: {task.attempts_count}"
                )
                return f"Task {task_id} cannot be retried"

            # Отмечаем задачу как обрабатываемую
            task.mark_as_processing()

        # Получаем RPS парковку вне транзакции
        try:
            rps_parking = RpsParking.objects.get(id=task.rps_parking_id)
        except RpsParking.DoesNotExist:
            error_msg = f"RPS Parking with id {task.rps_parking_id} not found"
            logger.error(error_msg)
            with transaction.atomic():
                task = RpsPaymentTask.objects.select_for_update().get(
                    id=task_id
                )
                task.mark_as_failed(error_msg)
            return error_msg

        # Применяем exponential backoff
        attempt = task.attempts_count - 1  # Уже увеличили в mark_as_processing
        if attempt > 0:
            delay = exponential_backoff(attempt)
            logger.info(
                f"Applying backoff delay {delay}s for task {task_id}"
            )
            time.sleep(delay)

        # Выполняем отправку данных на RPS
        try:
            service = RpsIntegrationService()
            result = service.send_rps_confirm_payment(
                rps_parking=rps_parking,
                card_id=task.card_id,
                amount=int(task.amount)
            )

            if result is not None:
                # Успешная отправка
                with transaction.atomic():
                    task = RpsPaymentTask.objects.select_for_update().get(
                        id=task_id
                    )
                    task.mark_as_successful()

                duration = time.time() - start_time
                logger.info(
                    f"Successfully sent payment to RPS for task {task_id} "
                    f"in {duration:.2f}s"
                )
                return (
                    f"Payment sent successfully for task {task_id} "
                    f"in {duration:.2f}s"
                )
            else:
                # Ошибка отправки
                error_msg = f"RPS service returned None for task {task_id}"
                logger.error(error_msg)
                with transaction.atomic():
                    task = RpsPaymentTask.objects.select_for_update().get(
                        id=task_id
                    )
                    task.mark_as_failed(error_msg)
                return error_msg

        except Exception as e:
            error_msg = (
                f"Exception during RPS payment send for task {task_id}: "
                f"{str(e)}"
            )
            logger.error(error_msg)

            with transaction.atomic():
                task = RpsPaymentTask.objects.select_for_update().get(
                    id=task_id
                )
                task.mark_as_failed(error_msg)

            return error_msg

    except Exception as e:
        error_msg = (
            f"Unexpected error in send_rps_payment_task {task_id}: {str(e)}"
        )
        logger.error(error_msg)
        return error_msg


@shared_task
def retry_failed_rps_payment_tasks():
    """
    Celery task для поиска и повторной отправки неудачных задач
    """
    logger = get_logger()

    # Находим задачи со статусами created и failed, которые можно повторить
    # Ограничиваем количество для предотвращения перегрузки
    failed_tasks = RpsPaymentTask.objects.filter(
        status__in=[
            RpsPaymentTask.STATUS_CREATED, RpsPaymentTask.STATUS_FAILED
        ],
        attempts_count__lt=models.F('max_attempts')
    ).order_by('created_at')[:50]  # Максимум 50 задач за раз

    processed_count = 0

    for task in failed_tasks:
        try:
            # Запускаем задачу на отправку
            send_rps_payment_task.apply_async(
                args=[task.id],
                priority=9  # Максимальный приоритет
            )
            processed_count += 1
            logger.info(f"Queued retry for task {task.id}")
        except Exception as e:
            logger.error(f"Failed to queue retry for task {task.id}: {str(e)}")

    logger.info(f"Queued {processed_count} tasks for retry")
    return f"Queued {processed_count} tasks for retry"
