from celery import shared_task
from parkings.models import ParkingSession
from integration.services import RpsIntegrationService
from base.utils import get_logger

logger = get_logger(__name__)


@shared_task
def check_entrance_permission(parking_session_id):
    """
    Задача Celery для отложенного запуска проверки разрешения на въезд.
    :param parking_session_id: ID парковочной сессии
    """
    try:
        parking_session = ParkingSession.objects.select_related('parking').get(id=parking_session_id)

        if not parking_session.e_ticket or not parking_session.client:
            raise ValueError("eTicket или client отсутствует в сессии")

        rps_parking = parking_session.parking.rpsparking_set.order_by('id').last()
        if not rps_parking:
            raise ValueError("RpsParking отсутствует для парковки")

        rps_service = RpsIntegrationService()

        rps_service.check_entrance_permission(
            rps_parking=rps_parking,
            e_ticket=parking_session.e_ticket,
            card_id=str(parking_session.client.id),
            parking_session=parking_session
        )

    except ParkingSession.DoesNotExist:
        logger.error(f"ParkingSession with ID {parking_session_id} does not exist.")
    except Exception as e:
        logger.error(f"Error in delayed_check_entrance_permission: {str(e)}")
