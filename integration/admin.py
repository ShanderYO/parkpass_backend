from django.contrib import admin
from django.utils.html import format_html
from .models import RpsPaymentTask


class RpsParkingFilter(admin.SimpleListFilter):
    title = 'RPS Парковка'
    parameter_name = 'rps_parking'

    def lookups(self, request, model_admin):
        try:
            from rps_vendor.models import RpsParking
            rps_parkings = RpsParking.objects.select_related('parking').all()
            return [
                (rp.id, f"{rp.parking.name} (ID: {rp.id})")
                for rp in rps_parkings
            ]
        except Exception:
            return []

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(rps_parking_id=self.value())
        return queryset


@admin.register(RpsPaymentTask)
class RpsPaymentTaskAdmin(admin.ModelAdmin):
    """
    Админка для управления задачами отправки платежей на RPS.

    RpsPaymentTask - это модель для хранения и отслеживания задач на отправку
    данных об оплате в систему RPS.

    Каждая задача содержит информацию о заказе, парковке, карте и сумме
    платежа, а также отслеживает статус обработки и количество попыток
    отправки.
    """
    list_display = [
        'id',
        'order_id',
        'rps_parking_display',
        'card_id',
        'amount',
        'status_display',
        'attempts_count',
        'created_at',
        'updated_at',
    ]

    list_filter = [
        'status',
        RpsParkingFilter,
        'created_at',
        'updated_at',
    ]

    search_fields = [
        'order_id',
        'card_id',
        'error_message',
        'last_error',
    ]

    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'processed_at',
        'attempts_count',
    ]

    fieldsets = (
        ('Основная информация', {
            'fields': (
                'id',
                'order_id',
                'rps_parking_id',
                'card_id',
                'amount',
            )
        }),
        ('Статус и обработка', {
            'fields': (
                'status',
                'error_message',
                'last_error',
                'attempts_count',
                'max_attempts',
            )
        }),
        ('Временные метки', {
            'fields': (
                'created_at',
                'updated_at',
                'processed_at',
            )
        }),
    )

    ordering = ['-created_at']

    def rps_parking_display(self, obj):
        """Отображает название парковки вместо ID"""
        try:
            from rps_vendor.models import RpsParking
            rps_parking = RpsParking.objects.select_related(
                'parking'
            ).get(id=obj.rps_parking_id)
            return format_html(
                '<a href="/admin/rps_vendor/rpsparking/{}/change/">{}</a>',
                rps_parking.id,
                rps_parking.parking.name
            )
        except Exception:
            return f"ID: {obj.rps_parking_id}"

    rps_parking_display.short_description = 'RPS Парковка'
    rps_parking_display.admin_order_field = 'rps_parking_id'

    def status_display(self, obj):
        """Отображает статус с цветовой индикацией"""
        colors = {
            RpsPaymentTask.STATUS_CREATED: 'orange',
            RpsPaymentTask.STATUS_IN_PROCESS: 'blue',
            RpsPaymentTask.STATUS_SUCCESSFUL: 'green',
            RpsPaymentTask.STATUS_FAILED: 'red',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_display.short_description = 'Статус'
    status_display.admin_order_field = 'status'

    def get_queryset(self, request):
        """Оптимизирует запросы для отображения списка"""
        return super().get_queryset(request).select_related()

    def has_add_permission(self, request):
        """Запрещает создание новых задач через админку"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Запрещает удаление задач через админку"""
        return False
