from django.db import models
from django.utils import timezone


class RpsPaymentTask(models.Model):
    """
    Модель для хранения задач на отправку данных об оплате на RPS.

    RpsPaymentTask используется для отслеживания и управления задачами
    отправки платежных данных в систему RPS. Каждая задача содержит
    информацию о заказе, парковке, карте и сумме платежа.
    """

    STATUS_CREATED = 'created'
    STATUS_IN_PROCESS = 'in_process'
    STATUS_SUCCESSFUL = 'successful'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_CREATED, 'Создана'),
        (STATUS_IN_PROCESS, 'В процессе'),
        (STATUS_SUCCESSFUL, 'Успешно'),
        (STATUS_FAILED, 'Ошибка'),
    ]

    # Основные поля
    order_id = models.IntegerField(help_text="ID заказа")
    rps_parking_id = models.IntegerField(help_text="ID RPS парковки")
    card_id = models.CharField(max_length=100, help_text="ID карты")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Сумма оплаты"
    )

    # Статус и обработка
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        help_text="Статус задачи"
    )
    error_message = models.TextField(
        blank=True, null=True, help_text="Сообщение об ошибке"
    )
    last_error = models.TextField(
        blank=True, null=True, help_text="Последняя ошибка"
    )

    # Временные метки
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Время создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Время обновления"
    )
    processed_at = models.DateTimeField(
        blank=True, null=True, help_text="Время обработки"
    )

    # Счетчики попыток
    attempts_count = models.PositiveIntegerField(
        default=0, help_text="Количество попыток"
    )
    max_attempts = models.PositiveIntegerField(
        default=3, help_text="Максимальное количество попыток"
    )

    class Meta:
        db_table = 'integration_rps_payment_task'
        verbose_name = 'Задача отправки оплаты на RPS'
        verbose_name_plural = 'Задачи отправки оплаты на RPS'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['order_id']),
            models.Index(fields=['rps_parking_id']),
        ]

    def __str__(self):
        return (f"RPS Payment Task {self.id} - Order {self.order_id} - "
                f"{self.status}")

    def can_retry(self):
        """Проверяет, можно ли повторить попытку"""
        return (
            self.status in [self.STATUS_CREATED, self.STATUS_FAILED] and
            self.attempts_count < self.max_attempts
        )

    def mark_as_processing(self):
        """Отмечает задачу как обрабатываемую"""
        self.status = self.STATUS_IN_PROCESS
        self.attempts_count += 1
        self.save(update_fields=['status', 'attempts_count'])

    def mark_as_successful(self):
        """Отмечает задачу как успешно выполненную"""
        self.status = self.STATUS_SUCCESSFUL
        self.processed_at = timezone.now()
        self.error_message = None
        self.last_error = None
        self.save(update_fields=[
            'status', 'processed_at', 'error_message', 'last_error'
        ])

    def mark_as_failed(self, error_message=None):
        """Отмечает задачу как неудачную"""
        self.status = self.STATUS_FAILED
        self.processed_at = timezone.now()
        if error_message:
            self.last_error = error_message
            if not self.error_message:
                self.error_message = error_message
        self.save(update_fields=[
            'status', 'processed_at', 'last_error', 'error_message'
        ])

    @classmethod
    def get_task_for_order(cls, order_id):
        """
        Получает задачу для указанного заказа, если она существует

        Args:
            order_id (int): ID заказа

        Returns:
            RpsPaymentTask or None: Задача для заказа или None, если не найдена
        """
        return cls.objects.filter(order_id=order_id).first()

    @classmethod
    def can_create_task_for_order(cls, order_id):
        """
        Проверяет, можно ли создать задачу для указанного заказа

        Args:
            order_id (int): ID заказа

        Returns:
            bool: True, если можно создать задачу, False - если уже существует
        """
        return not cls.objects.filter(order_id=order_id).exists()
