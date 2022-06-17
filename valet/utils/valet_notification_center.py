import datetime
import logging

import pytz
from django.core.mail import send_mail
from django.utils import timezone

from parkpass_backend.settings import VALETAPP_DOMAIN, BASE_DOMAIN

VALET_NOTIFICATION_REQUEST_FOR_DELIVERY = 1
VALET_NOTIFICATION_REQUEST_CANCEL = 2
VALET_NOTIFICATION_SET_RESPONSIBLE = 3
VALET_NOTIFICATION_REQUEST_ACCEPT = 4
VALET_NOTIFICATION_DELIVERY_TIME_CHANGE = 5
VALET_NOTIFICATION_CAR_IS_ISSUED = 6


class ValetNotificationCenter:

    def __init__(self, type, session, chats=[], valet_user_id=None, send_email_about_booking_notification=True):
        from parkings.models import ParkingValetSessionImages, PHOTOS_FROM_PARKING, PHOTOS_AT_THE_RECEPTION

        self.type = type
        self.session = session
        self.chats = chats
        self.valet_user_id = valet_user_id
        self.send_email_about_booking_notification = send_email_about_booking_notification

        # конвертируем время
        # ..................................................
        tzh = pytz.timezone(session.parking.tz_name)
        self.delivery_time_from_utc = self.session.car_delivery_time
        try:
            self.delivery_time_from_utc = timezone.localtime(session.car_delivery_time, tzh).strftime(
                ("%d.%m.%Y %H:%M"))
        except Exception as e:
            print(e)
        # ..................................................

        # подготавливаем фотки
        # ..................................................
        self.photos = []
        parking_photos = ParkingValetSessionImages.objects.filter(valet_session=session,
                                                                  type=PHOTOS_FROM_PARKING)
        if not parking_photos:
            parking_photos = ParkingValetSessionImages.objects.filter(valet_session=session,
                                                                      type=PHOTOS_AT_THE_RECEPTION)
        if parking_photos:
            for photo in parking_photos:
                self.photos.append(f'https://{BASE_DOMAIN}/api/media{photo.img}')
        # ..................................................

    def run(self):

        if self.type == VALET_NOTIFICATION_REQUEST_FOR_DELIVERY:  # запрос авто
            self._book_notification()
        elif self.type == VALET_NOTIFICATION_REQUEST_CANCEL:  # отмена
            self._cancel_notification()
        elif self.type == VALET_NOTIFICATION_SET_RESPONSIBLE:  # валета назначили ответственным
            self._set_responsible_notification()
        elif self.type == VALET_NOTIFICATION_REQUEST_ACCEPT:  # валет принял заявку
            self._accept_notification()
        elif self.type == VALET_NOTIFICATION_DELIVERY_TIME_CHANGE:  # изменилось время подачи
            self._change_delivery_time_notification()
        elif self.type == VALET_NOTIFICATION_CAR_IS_ISSUED:  # автомобиль выдан
            self._car_is_issued_notification()

    def _book_notification(self):
        from parkings.tasks import send_message_by_valet_bots_task

        # Отправка на почту
        # ..................................................
        if self.send_email_about_booking_notification:
            message = 'VCID: %s \nВремя: %s' % (self.session.valet_card_id, self.delivery_time_from_utc)

            send_mail('Заказ автомобиля: %s, %s' % (self.session.car_number, self.session.car_model),
                      message,
                      "Valet ParkPass <noreply@parkpass.ru>",
                      ['lokkomokko1@gmail.com', 'support@parkpass.ru'])

            if self.session.parking.valet_email:
                send_mail(
                    'Заказ автомобиля: %s, %s' % (self.session.car_number, self.session.car_model),
                    message,
                    "Valet ParkPass <noreply@parkpass.ru>",
                    [self.session.parking.valet_email])
        # ..................................................

        notification_message = """
Пришёл запрос на подачу автомобиля. 
Номер: %s
Марка: %s
VCID: %s
Время подачи: %s

<a href="%s">✅ Принять запрос</a>
                            """ % (
            self.session.car_number, self.session.car_model, self.session.valet_card_id, self.delivery_time_from_utc,
            f'{VALETAPP_DOMAIN}/home/?accept-request={self.session.request.id}')

        # для валетов
        send_message_by_valet_bots_task.delay(notification_message, None, self.session.company_id, self.photos,
                                              True)
        # для общих уведомлений группы
        self.session.parking.send_valet_notification(notification_message, self.photos)

    def _cancel_notification(self):
        from parkings.tasks import send_message_by_valet_bots_task

        notification_message = """
Менеджер отменил подачу автомобиля. 
Номер: %s
Марка: %s
VCID: %s
Время подачи: %s
                                """ % (
            self.session.car_number, self.session.car_model, self.session.valet_card_id, self.delivery_time_from_utc)
        send_message_by_valet_bots_task.delay(notification_message,
                                              self.chats, self.session.company_id, self.photos, True)
        pass

    def _set_responsible_notification(self):
        from parkings.tasks import send_message_by_valet_bots_task

        from owners.models import CompanyUser
        valet = CompanyUser.objects.get(id=self.valet_user_id)

        if valet and valet.telegram_id:
            notification_message = """
Вас назначили ответственным за подачу автомобиля. 
Номер: %s
Марка: %s
VCID: %s
Время подачи: %s

<a href="%s">✅ Принять запрос</a>
                                    """ % (
            self.session.car_number, self.session.car_model, self.session.valet_card_id, self.delivery_time_from_utc,
            f'{VALETAPP_DOMAIN}/home/?accept-request={self.session.request.id}')
            send_message_by_valet_bots_task.delay(notification_message, self.chats, self.session.company_id,
                                                  self.photos, True)

    def _accept_notification(self):

        from owners.models import CompanyUser
        valet = CompanyUser.objects.get(id=self.valet_user_id)

        notification_message = """
Валет принял заявку на подачу. 
Номер: %s
Марка: %s
VCID: %s
Время подачи: %s
Валет: %s
                                            """ % (
            self.session.car_number, self.session.car_model, self.session.valet_card_id, self.delivery_time_from_utc,
            f'{valet.last_name} {valet.first_name}')

        self.session.parking.send_valet_notification(notification_message, self.photos)

    def _change_delivery_time_notification(self):

        if self.session.responsible_for_delivery and self.session.responsible_for_delivery.telegram_id:
            from parkings.tasks import send_message_by_valet_bots_task

            notification_message = """
Изменилось время подачи автомобиля.
Номер: %s
Марка: %s
VCID: %s
Время подачи: %s
                                                                        """ % (
                self.session.car_number, self.session.car_model, self.session.valet_card_id,
                self.delivery_time_from_utc)
            send_message_by_valet_bots_task.delay(notification_message,
                                                  [self.session.responsible_for_delivery.telegram_id],
                                                  self.session.company_id,
                                                  self.photos, True)

    def _car_is_issued_notification(self):
        from owners.models import CompanyUser
        valet = CompanyUser.objects.get(id=self.valet_user_id)

        notification_message = """
Автомобиль выдан клиенту.
Номер: %s
Марка: %s
VCID: %s
Время подачи: %s
Валет: %s
                                                    """ % (
            self.session.car_number, self.session.car_model, self.session.valet_card_id, self.delivery_time_from_utc,
            f'{valet.last_name} {valet.first_name}')
        self.session.parking.send_valet_notification(notification_message, self.photos)
