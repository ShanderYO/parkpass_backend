# -*- coding: utf-8 -*-
import json
import os
import uuid
from io import BytesIO
from itertools import chain

import xlwt
from PIL import Image
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum, Q, Prefetch
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.timezone import timedelta
from django.views import View

from accounts.validators import *
from base.exceptions import AuthException, PermissionException
from base.models import EmailConfirmation
from base.utils import *
from base.validators import *
from base.views import APIView, ObjectView
from base.views import generic_login_required_view
from jwtauth.models import Session, TokenTypes, Groups
from parkings.models import Parking, ParkingSession, ParkingValetSession, ParkingValetSessionSerializer, \
    ParkingValetSessionRequest, ParkingValetSessionImages, \
    PHOTOS_AT_THE_RECEPTION, PHOTOS_FROM_PARKING, ParkingValetRequestIncludeSessionSerializer, VALET_REQUEST_ACCEPTED, \
    VALET_SESSION_THE_CAR_IS_ISSUED
from payments.models import Order, TinkoffPayment, HomeBankPayment
from rps_vendor.models import RpsSubscription, STATE_CONFIRMED, RpsParkingCardSession, CARD_SESSION_STATES, ParkingCard
from vendors.models import Vendor
from .models import OwnerApplication, Owner, CompanyUser, CompanyUsersRole, CompanyUsersRolePermission, \
    CompanyUsersPermission, CompanyUsersPermissionCategory, CompanyUserSerializer, CompanyUsersRoleSerializer, \
    CompanyUsersRolePermissionSerializer, CompanyUsersRolePermissionWithSlugSerializer
from .models import Owner as Account
from .models import Company
from .validators import ConnectIssueValidator, TariffValidator, ValetSessionsCreateFromLKValidator, \
    ValetSessionsUpdateFromLKValidator

LoginRequiredAPIView = generic_login_required_view(Owner)


def get_owner(request):
    return request.owner if request.owner else request.companyuser.company.owner


class AccountInfoView(LoginRequiredAPIView):
    def get(self, request):
        user = request.owner or request.companyuser
        account_dict = serializer(user, exclude_attr=("name", "created_at", "sms_code", "password"))
        owner = request.owner
        if not owner:
            account_dict['companyuser'] = True
            account_dict['permissions'] = CompanyUsersRolePermissionWithSlugSerializer(
                user.role.companyusersrolepermission_set, many=True).data
            owner = user.company.owner

        parkings = Parking.objects.filter(company__owner=owner, approved=True)
        en_parkings = parkings.filter(parkpass_status=Parking.CONNECTED)
        account_dict['parkings_total'] = len(parkings)
        account_dict['parkings_enabled'] = len(en_parkings)
        return JsonResponse(account_dict, status=200)

    def put(self, request):
        fname = request.data.get('first_name', None)
        lname = request.data.get('last_name', None)
        if fname is not None:
            request.owner.first_name = fname
        if lname is not None:
            request.owner.last_name = lname
        try:
            request.owner.full_clean()
        except ValidationError as e:
            raise ValidationException(ValidationException.VALIDATION_ERROR, e.message_dict)
        request.owner.save()
        return JsonResponse({}, status=200)


class ParkingStatisticsView(LoginRequiredAPIView):
    def get(self, request):
        period = request.GET.get('period', None)
        parking_id = request.GET.get('parking_id', "0").encode('utf-8')

        from_date = parse_timestamp_utc(request.GET.get("from_date", None))
        to_date = parse_timestamp_utc(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None
        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        qs = ParkingSession.objects.filter(
            parking__owner=get_owner(request)
        )

        if td:
            t = timezone.now() - td
            qs = qs.filter(
                started_at__gt=t,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            q1 = Q(
                completed_at__gte=from_date_datetime,
                completed_at__lte=to_date_datetime,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )
            now = timezone.now()
            if from_date_datetime < now < to_date_datetime:
                q2 = Q(
                    completed_at__isnull=True,
                    started_at__gt=from_date_datetime
                )
                qs = qs.filter(q1 | q2)
            else:
                qs = qs.filter(q1)
        else:
            pass

        if parking_id:
            id = parse_int(parking_id)
            if id:
                qs = qs.filter(parking__id=id)

        count = qs.count()
        debt = qs.aggregate(Sum('debt'))['debt__sum']
        seen = set()
        users = 0
        for s in qs:
            if s.client not in seen:
                seen.add(s.client)
                users += 1

        return JsonResponse({
            'sessions': count,
            'income': debt if debt else 0,
            'users': users
        }, status=200)


class SessionsView(LoginRequiredAPIView):
    def get(self, request, **kwargs):
        page = parse_int(request.GET.get('page', 0))
        period = request.GET.get('period', None)

        from_date = parse_timestamp_utc(request.GET.get("from_date", None))
        to_date = parse_timestamp_utc(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        qs = ParkingSession.objects.filter(
            parking__owner=get_owner(request)
        )

        if td:
            to_date_datetime = get_today_end_datetime()
            from_date_datetime = to_date_datetime - td
            qs = qs.filter(
                completed_at__gte=from_date_datetime,
                completed_at__lte=to_date_datetime,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            q1 = Q(
                completed_at__gte=from_date_datetime,
                completed_at__lte=to_date_datetime,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )

            now = timezone.now()
            if from_date_datetime < now < to_date_datetime:
                q2 = Q(
                    completed_at__isnull=True,
                    started_at__gt=from_date_datetime
                )
                qs = qs.filter(q1 | q2)
            else:
                qs = qs.filter(q1)

        else:
            pass

        result_list = []
        if page != 0:
            qs = qs.filter(id__lt=page).order_by('-id')[:10]
        else:
            qs = qs.filter().order_by('-id')[:10]

        for session in qs:
            parking_dict = serializer(session.parking, include_attr=('id', 'name',))
            session_dict = serializer(session, datetime_format='timestamp_notimezone',
                                      exclude_attr=('parking_id', 'try_refund',
                                                    'current_refund_sum', 'target_refund_sum'))
            session_dict["parking"] = parking_dict
            result_list.append(session_dict)

        response_dict = {
            "result": result_list,
            "next": result_list[len(result_list) - 1]["id"] if len(result_list) > 0 else None
        }

        return JsonResponse(response_dict)


class SubscriptionsView(LoginRequiredAPIView):
    def get(self, request, **kwargs):

        page = parse_int(request.GET.get('page', 0))
        period = request.GET.get('period', None)

        from_date = parse_timestamp_utc(request.GET.get("from_date", None))
        to_date = parse_timestamp_utc(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        parkings = Parking.objects.filter(owner=get_owner(request), approved=True)

        qs = RpsSubscription.objects.filter(
            parking__in=parkings,
            state=STATE_CONFIRMED,
            data__isnull=False
        ).select_related('account')

        if td:
            to_date_datetime = get_today_end_datetime()
            from_date_datetime = to_date_datetime - td
            qs = qs.filter(
                started_at__gte=from_date_datetime,
                started_at__lte=to_date_datetime,
            )

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            q1 = Q(
                started_at__gte=from_date_datetime,
                started_at__lte=to_date_datetime
            )

            now = timezone.now()
            if from_date_datetime < now < to_date_datetime:
                q2 = Q(
                    started_at__gt=from_date_datetime
                )
                qs = qs.filter(q1 | q2)
            else:
                qs = qs.filter(q1)

        else:
            pass

        result_list = []
        if page != 0:
            qs = qs.filter(id__lt=page).order_by('-id')[:10]
        else:
            qs = qs.filter().order_by('-id')[:10]

        for subscriptions in qs:
            session_dict = serializer(subscriptions, datetime_format='timestamp_notimezone',
                                      include_attr=('id', 'name', 'account_id', 'unlimited', 'started_at',
                                                    'expired_at', 'sum', 'active', 'prolongation'))
            result_list.append(session_dict)

        response_dict = {
            "result": result_list,
            "next": result_list[len(result_list) - 1]["id"] if len(result_list) > 0 else None
        }

        return JsonResponse(response_dict)


class SubscriptionsViewForExcel(LoginRequiredAPIView):
    def get(self, request, **kwargs):

        period = request.GET.get('period', None)

        from_date = parse_timestamp_utc(request.GET.get("from_date", None))
        to_date = parse_timestamp_utc(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        parkings = Parking.objects.filter(owner=request.owner, approved=True)

        qs = RpsSubscription.objects.filter(
            parking__in=parkings,
            state=STATE_CONFIRMED,
            data__isnull=False
        ).select_related('account')

        if td:
            to_date_datetime = get_today_end_datetime()
            from_date_datetime = to_date_datetime - td
            qs = qs.filter(
                started_at__gte=from_date_datetime,
                started_at__lte=to_date_datetime,
            )

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            q1 = Q(
                started_at__gte=from_date_datetime,
                started_at__lte=to_date_datetime
            )

            now = timezone.now()
            if from_date_datetime < now < to_date_datetime:
                q2 = Q(
                    started_at__gt=from_date_datetime
                )
                qs = qs.filter(q1 | q2)
            else:
                qs = qs.filter(q1)

        else:
            pass

        result_list = []

        qs = qs.filter().order_by('-id')

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="file.xls"'

        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Абонементы')

        # Sheet header, first row
        row_num = 0

        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        columns = ['ID', 'Название', 'CardId', 'Тип клиента', 'Дата покупки', 'Дата окончания', 'Сумма', 'Статус',
                   'Автопродление']

        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        # Sheet body, remaining rows
        font_style = xlwt.XFStyle()
        rows = qs.values_list('id', 'name', 'account_id', 'unlimited', 'started_at', 'expired_at', 'sum', 'active',
                              'prolongation')
        if rows:
            for row in rows:
                row_num += 1
                for col_num in range(len(row)):
                    format = font_style
                    date_format = xlwt.XFStyle()
                    value = str(row[col_num])
                    if col_num == 3:
                        if row[col_num]:
                            value = 'Постоянный'
                        else:
                            value = 'Разовый'
                    if col_num == 4 or col_num == 5:
                        date_format.num_format_str = 'dd-mm-yyyy h:mm'
                        value = row[col_num].strftime("%d-%m-%Y %H:%M")
                        value = datetime.datetime.strptime(value, "%d-%m-%Y %H:%M")
                        format = date_format
                    if col_num == 6:
                        value = value + ' руб.'
                    if col_num == 7:
                        if row[col_num]:
                            value = 'Активен'
                        else:
                            value = 'Не активен'
                    if col_num == 8:
                        if row[col_num]:
                            value = 'Да'
                        else:
                            value = 'Нет'
                    ws.write(row_num, col_num, value, format)

        wb.save(response)

        return response


class CardSessionsView(LoginRequiredAPIView):
    def get(self, request, **kwargs):

        page = parse_int(request.GET.get('page', 0))
        period = request.GET.get('period', None)

        from_date = parse_timestamp_utc(request.GET.get("from_date", None))
        to_date = parse_timestamp_utc(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        # parkings = Parking.objects.filter(owner_id=2)
        parkings = Parking.objects.filter(owner_id=get_owner(request), approved=True)

        qs = RpsParkingCardSession.objects.filter(
            parking_id__in=parkings,
            state=STATE_CONFIRMED,
        ).select_related('account').select_related('parking_card')

        orders = Order.objects.filter(parking_card_session_id__in=qs).values_list('id', 'parking_card_session_id',
                                                                                  'created_at')
        orders_ids = []

        if orders:
            for order in orders:
                orders_ids.append(order[0])

        payments = list(TinkoffPayment.objects.filter(order_id__in=orders_ids).values_list('id', 'order_id')) + list(
            HomeBankPayment.objects.filter(order_id__in=orders_ids).values_list('id', 'order_id'))

        if td:
            to_date_datetime = get_today_end_datetime()
            from_date_datetime = to_date_datetime - td
            qs = qs.filter(
                created_at__gte=from_date_datetime,
                created_at__lte=to_date_datetime,
            )

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            q1 = Q(
                created_at__gte=from_date_datetime,
                created_at__lte=to_date_datetime
            )

            now = timezone.now()
            if from_date_datetime < now < to_date_datetime:
                q2 = Q(
                    created_at__gt=from_date_datetime
                )
                qs = qs.filter(q1 | q2)
            else:
                qs = qs.filter(q1)

        else:
            pass

        result_list = []
        if page != 0:
            qs = qs.filter(id__lt=page).order_by('-id')[:10]
        else:
            qs = qs.filter().order_by('-id')[:10]

        for card_session in qs:
            card_session_dict = serializer(card_session, datetime_format='timestamp_notimezone',
                                           include_attr=('id', 'parking_card_id', 'account_id', 'duration', 'debt'))

            secs = card_session.duration % 60
            mins = (card_session.duration % 3600) // 60
            hours = (card_session.duration % 86400) // 3600
            days = (card_session.duration % 2592000) // 86400
            months = card_session.duration // 2592000
            duration = "%sм. %sд. %sч. %sм." % (months, days, hours, mins)

            card_session_dict['duration'] = duration
            if card_session.account_id:
                card_session_dict['account_id'] = str(card_session.account_id)

            card_session_dict['paid_date'] = ''
            for order in orders:
                if order[1] == card_session_dict['id']:
                    card_session_dict['paid_date'] = order[2]
                    card_session_dict['payment_id'] = next((x for x in payments if x[1] == order[0]), None)

            card_session_dict['parking_name'] = ''
            for parking in parkings:
                if parking.id == card_session.parking_id:
                    card_session_dict['parking'] = {'name': parking.name, 'id': parking.id}

            result_list.append(card_session_dict)

        response_dict = {
            "result": result_list,
            "next": result_list[len(result_list) - 1]["id"] if len(result_list) > 0 else None
        }

        return JsonResponse(response_dict)


class CardSessionsViewForExcel(LoginRequiredAPIView):
    def get(self, request, **kwargs):

        period = request.GET.get('period', None)

        from_date = parse_timestamp_utc(request.GET.get("from_date", None))
        to_date = parse_timestamp_utc(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        parkings = Parking.objects.filter(owner=get_owner(request), approved=True)
        # parkings = Parking.objects.filter(owner=2)

        qs = RpsParkingCardSession.objects.filter(
            parking_id__in=parkings,
            state=STATE_CONFIRMED,
        ).select_related('account').select_related('parking_card')

        orders = Order.objects.filter(parking_card_session_id__in=qs).values_list('id', 'parking_card_session_id',
                                                                                  'created_at')

        if td:
            to_date_datetime = get_today_end_datetime()
            from_date_datetime = to_date_datetime - td
            qs = qs.filter(
                created_at__gte=from_date_datetime,
                created_at__lte=to_date_datetime,
            )

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            q1 = Q(
                created_at__gte=from_date_datetime,
                created_at__lte=to_date_datetime
            )

            now = timezone.now()
            if from_date_datetime < now < to_date_datetime:
                q2 = Q(
                    created_at__gt=from_date_datetime
                )
                qs = qs.filter(q1 | q2)
            else:
                qs = qs.filter(q1)

        else:
            pass

        qs = qs.filter().order_by('-id')

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="file.xls"'

        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Сессии парковочных карт')

        # Sheet header, first row
        row_num = 0

        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        columns = ['ID', 'ID карты', 'ID клиента', 'Продолжительность', 'Сумма оплаты', 'Дата и время оплаты',
                   'Название парковки']

        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        # Sheet body, remaining rows
        font_style = xlwt.XFStyle()
        rows = qs.values_list('id', 'parking_card_id', 'account_id', 'duration', 'debt', 'leave_at', 'parking_id')
        if rows:
            for row in rows:
                row_num += 1
                for col_num in range(len(row)):
                    format = font_style
                    date_format = xlwt.XFStyle()
                    value = str(row[col_num])
                    # if col_num == 3:
                    #     value = "%d:%02d" % (int(row[3]) // 60, int(row[3]) % 60)
                    #     format = date_format

                    if col_num == 3:
                        if row[3] <= 0:
                            value = 0
                        else:
                            secs = row[3] % 60
                            mins = (row[3] % 3600) // 60
                            hours = (row[3] % 86400) // 3600
                            days = (row[3] % 2592000) // 86400
                            months = row[3] // 2592000
                            value = "%sм. %sд. %sч. %sм." % (months, days, hours, mins)

                    if col_num == 5:
                        value = ''
                        for order in orders:
                            if order[1] == row[0]:
                                value = order[2]
                                date_format.num_format_str = 'dd-mm-yyyy h:mm'
                                value = value.strftime("%d-%m-%Y %H:%M")
                                value = datetime.datetime.strptime(value, "%d-%m-%Y %H:%M")
                                format = date_format

                    if col_num == 6:
                        value = ''
                        for parking in parkings:
                            if parking.id == row[col_num]:
                                value = parking.name

                    ws.write(row_num, col_num, value, format)

        wb.save(response)

        return response


class ParkingSessionsView(LoginRequiredAPIView):
    def get(self, request, **kwargs):
        parking_id = kwargs.get('id', "0").encode('utf-8')
        page = parse_int(request.GET.get('page', 0))
        period = request.GET.get('period', None)

        from_date = parse_timestamp_utc(request.GET.get("from_date", None))
        to_date = parse_timestamp_utc(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        qs = ParkingSession.objects.filter(
            parking__id=parking_id,
            parking__owner=get_owner(request)
        )

        if td:
            t = timezone.now() - td
            qs = qs.filter(
                started_at__gt=t,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            q1 = Q(
                completed_at__gte=from_date_datetime,
                completed_at__lte=to_date_datetime,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )

            now = timezone.now()
            if from_date_datetime < now < to_date_datetime:
                q2 = Q(
                    completed_at__isnull=True,
                    started_at__gt=from_date_datetime
                )
                qs = qs.filter(q1 | q2)
            else:
                qs = qs.filter(q1)
        else:
            pass

        result_list = []
        if page != 0:
            qs = qs.filter(id__lt=page).order_by('-id')[:10]
        else:
            qs = qs.filter().order_by('-id')[:10]

        for session in qs:
            parking_dict = serializer(session.parking, include_attr=('id', 'name',))
            session_dict = serializer(session, datetime_format='timestamp_notimezone', exclude_attr=(
                'parking_id', 'try_refund', 'current_refund_sum', 'target_refund_sum'))
            session_dict["parking"] = parking_dict
            result_list.append(session_dict)

        response_dict = {
            "result": result_list,
            "next": result_list[len(result_list) - 1]["id"] if len(result_list) > 0 else None
        }

        return JsonResponse(response_dict)


class ParkingSessionsViewForExcel(LoginRequiredAPIView):
    def get(self, request, **kwargs):
        period = request.GET.get('period', None)

        from_date = parse_timestamp_utc(request.GET.get("from_date", None))
        to_date = parse_timestamp_utc(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        qs = ParkingSession.objects.filter(
            parking__owner=get_owner(request)
        )

        if td:
            to_date_datetime = get_today_end_datetime()
            from_date_datetime = to_date_datetime - td
            qs = qs.filter(
                completed_at__gte=from_date_datetime,
                completed_at__lte=to_date_datetime,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            q1 = Q(
                completed_at__gte=from_date_datetime,
                completed_at__lte=to_date_datetime,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )

            now = timezone.now()
            if from_date_datetime < now < to_date_datetime:
                q2 = Q(
                    completed_at__isnull=True,
                    started_at__gt=from_date_datetime
                )
                qs = qs.filter(q1 | q2)
            else:
                qs = qs.filter(q1)

        else:
            pass

        result_list = []
        qs = qs.filter().order_by('-id')

        for session in qs:
            parking_dict = serializer(session.parking, include_attr=('id', 'name',))
            session_dict = serializer(session, datetime_format='timestamp_notimezone',
                                      exclude_attr=('parking_id', 'try_refund',
                                                    'current_refund_sum', 'target_refund_sum'))
            session_dict["parking"] = parking_dict
            result_list.append(session_dict)

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="file.xls"'

        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Сессии')

        # Sheet header, first row
        row_num = 0

        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        columns = ['ID', 'Местоположение', 'Дата парковки', 'Заезд', 'Выезд', 'Длительность', 'Сумма', 'Статус']

        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        # Sheet body, remaining rows
        font_style = xlwt.XFStyle()

        if len(result_list) > 0:
            for row in result_list:
                row_num += 1
                for col_num in range(len(columns)):
                    format = font_style
                    date_format = xlwt.XFStyle()
                    value = '...'
                    if col_num == 0:
                        value = row['id']
                    elif col_num == 1:
                        value = row['parking']['name']
                    elif col_num == 2:
                        date_format.num_format_str = 'dd-mm-yyyy'
                        value = datetime.datetime.utcfromtimestamp(row['started_at']).strftime("%d-%m-%Y")
                        value = datetime.datetime.strptime(value, "%d-%m-%Y")
                        format = date_format
                    elif col_num == 3:
                        date_format.num_format_str = 'h:mm'
                        value = datetime.datetime.utcfromtimestamp(row['started_at']).strftime("%H:%M")
                        value = datetime.datetime.strptime(value, "%H:%M")
                        format = date_format
                    elif col_num == 4:
                        date_format.num_format_str = 'h:mm'
                        value = datetime.datetime.utcfromtimestamp(row['completed_at']).strftime("%H:%M")
                        value = datetime.datetime.strptime(value, "%H:%M")
                        format = date_format
                    elif col_num == 5:
                        value = "%d:%02d" % (int(row['duration']) // 60, int(row['duration']) % 60)
                        format = date_format
                    elif col_num == 6:
                        value = str(row['debt']) + ' руб.'
                    elif col_num == 7:
                        status = int(row['client_state'])
                        if status == -1:
                            value = 'Отменена'
                        elif status == 0:
                            value = 'Завершена'
                        elif status == 1:
                            value = 'Активна'
                        elif status == 2:
                            value = 'Приостановлена'
                        elif status == 3:
                            value = 'Ожидает оплаты'

                    ws.write(row_num, col_num, value, format)

        wb.save(response)

        return response


class ParkingsTopView(LoginRequiredAPIView):
    def get(self, request):
        count = parse_int(request.GET.get('count', [3])[0])
        period = request.GET.get('period', None)

        from_date = parse_timestamp_utc(request.GET.get("from_date", None))
        to_date = parse_timestamp_utc(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

        page = parse_int(request.GET.get('page', None))
        if period and period not in ('day', 'week', 'month'):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "`period` must be in (`day`, `week`, `month`)"
            )
            return JsonResponse(e.to_dict(), status=400)

        td = None

        if period == 'day':
            td = timedelta(days=1)
        elif period == 'week':
            td = timedelta(days=7)
        elif period == "month":
            td = timedelta(days=30)
        else:
            pass

        qs = ParkingSession.objects.filter(
            parking__owner=get_owner(request)
        )

        if td:
            t = timezone.now() - td
            qs = qs.filter(
                started_at__gt=t,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )

        elif from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)
            q1 = Q(
                completed_at__gte=from_date_datetime,
                completed_at__lte=to_date_datetime,
                client_state=ParkingSession.CLIENT_STATE_CLOSED
            )

            now = timezone.now()
            if from_date_datetime < now < to_date_datetime:
                q2 = Q(
                    completed_at__isnull=True,
                    started_at__gt=from_date_datetime
                )
                qs = qs.filter(q1 | q2)
            else:
                qs = qs.filter(q1)
        else:
            pass

        parkings = Parking.objects.filter(owner=get_owner(request), approved=True)

        r = []

        for p in parkings:
            r.append({
                'id': p.id,
                'name': p.name,
                'address': p.address,
                'city': p.city,
                'income': qs.filter(parking=p).aggregate(Sum('debt'))[
                    'debt__sum'],
            })
        r = sorted(r, key=lambda x: -x['income'] if x['income'] else 0)
        if page is None:
            page = 0

        response_dict = {
            "result": r[page * count:(page + 1) * count],
        }

        if not len(r) <= (page + 1) * count:
            response_dict["next"] = page + 1
        else:
            response_dict["next"] = None

        return JsonResponse(response_dict, status=200, safe=False)


class ApplicationsView(LoginRequiredAPIView, ObjectView):
    object = OwnerApplication
    author_field = 'owner'
    show_fields = ('description', 'type')
    account_filter = 'owner'


class CompanyView(LoginRequiredAPIView, ObjectView):
    object = Company
    show_fields = ('id', 'name', 'inn', 'kpp', 'bic', 'legal_address',
                   'actual_address', 'email', 'phone', 'account',
                   'use_profile_contacts', 'bank')

    account_filter = 'owner'

    def set_owner_and_validate(self, request, obj):
        obj.owner = get_owner(request)
        if not obj.use_profile_contacts:
            if not all((obj.email, obj.phone)):
                raise ValidationException(ValidationException.VALIDATION_ERROR,
                                          {'use_profile_contacts': ['If this field is False, '
                                                                    'email and phone'
                                                                    ' is required.']})

    def serialize_list(self, qs):
        result, page = super(CompanyView, self).serialize_list(qs)
        # TODO improve it
        for obj_dict in result:
            parkings = Parking.objects.filter(company__id=obj_dict['id'])
            serialized = serializer(parkings, include_attr=('id', 'name', 'address', 'city', 'parkpass_status'))
            obj_dict["parkings"] = serialized
        return result, page

    def serialize_obj(self, obj):
        result_dict = super(CompanyView, self).serialize_obj(obj)
        parkings = Parking.objects.filter(company__id=result_dict['id'])
        serialized = serializer(parkings, include_attr=('id', 'name', 'address', 'city', 'parkpass_status'))
        result_dict["parkings"] = serialized
        return result_dict

    def on_create(self, request, obj):
        self.set_owner_and_validate(request, obj)

    def on_post_create(self, request, obj):
        return {'id': obj.id}

    def on_edit(self, request, obj):
        self.set_owner_and_validate(request, obj)

        if obj.get_parking_queryset():
            raise PermissionException(
                PermissionException.FORBIDDEN_CHANGING,
                "Company should have no parking for changing"
            )


class EventsView(LoginRequiredAPIView, ObjectView):
    object = OwnerApplication
    show_fields = (
        'owner_id', 'type', 'owner_id', 'parking_id', 'vendor_id', 'company_id', 'status', 'description', 'created_at',)
    account_filter = 'owner'


class TariffView(LoginRequiredAPIView):
    validator_class = TariffValidator

    def get(self, request, id):
        try:
            parking = Parking.objects.get(id=id)
        except ObjectDoesNotExist:
            e = ValidationException.RESOURCE_NOT_FOUND
            return JsonResponse(e.to_dict(), status=400)

        response = {
            "file_name": parking.tariff_file_name,
            "file_content": parking.tariff_file_content
        }
        return JsonResponse(response, status=200)

    def post(self, request, id):
        try:
            parking = Parking.objects.get(id=id)
        except ObjectDoesNotExist:
            e = ValidationException.RESOURCE_NOT_FOUND
            return JsonResponse(e.to_dict(), status=400)

        parking.tariff_file_name = request.data["file_name"]
        parking.tariff_file_content = request.data["file_content"]
        parking.save()
        return JsonResponse({}, status=200)


class ConnectParkingView(LoginRequiredAPIView):
    validator_class = ConnectIssueValidator

    def post(self, request):
        parking_id = self.request.data['parking_id']
        vendor_id = self.request.data['vendor_id']
        company_id = self.request.data['company_id']
        contact_email = self.request.data.get("contact_email")
        contact_phone = self.request.data.get("contact_phone")

        try:
            parking = Parking.objects.get(id=parking_id, parkpass_status=Parking.DISCONNECTED)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Parking with such ID has already connecting or processing state'
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Vendor with such ID does not exist'
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            company = Company.objects.get(id=company_id, owner=get_owner(request))

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Your company does not found'
            )
            return JsonResponse(e.to_dict(), status=400)

        OwnerApplication.objects.create(
            type=OwnerApplication.TYPE_CONNECT_PARKING,
            owner=get_owner(self.request),
            parking=parking,
            vendor=vendor,
            company=company,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )

        parking.vendor = vendor
        parking.company = company
        parking.parkpass_status = Parking.PENDING
        parking.save()

        return JsonResponse({}, status=200)


class ParkingsView(LoginRequiredAPIView, ObjectView):
    object = Parking
    account_filter = 'owner'
    foreign_field = [('company', ('id', 'name',)), ('vendor', ('id', 'name',))]
    hide_fields = ('picture',)
    readonly_fields = ()

    def on_create(self, request, obj):
        obj.owner = get_owner(request)  # add owner
        if not obj.latitude or not obj.longitude:
            raise ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Longitude and latitude are required"
            )

    def on_edit(self, request, obj):
        if obj.parkpass_status != Parking.DISCONNECTED:
            raise PermissionException(
                PermissionException.FORBIDDEN_CHANGING,
                "Parking should have DISCONNECTED state for changing"
            )

    def on_post_create(self, request, obj):
        return {'id': obj.id}


class VendorsView(LoginRequiredAPIView, ObjectView):
    object = Vendor
    methods = ('GET',)
    show_fields = ('id', 'name',)


class PasswordChangeView(LoginRequiredAPIView):

    def post(self, request):
        old_password = request.data["old"]
        new_password = request.data["new"]

        account = request.owner

        if not account.check_password(old_password):
            e = AuthException(
                AuthException.INVALID_PASSWORD,
                "Invalid old password"
            )
            return JsonResponse(e.to_dict(), status=400)
        account.set_password(new_password)
        return JsonResponse({}, status=200)


class PasswordRestoreView(APIView):
    validator_class = EmailValidator

    def post(self, request):
        email = request.data["email"].lower()

        try:
            owner = Owner.objects.get(email=email)
            owner.create_password_and_send_mail()
            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "User with such email not found"
            )
            return JsonResponse(e.to_dict(), status=400)


class LoginWithEmailView(APIView):
    validator_class = EmailAndPasswordValidator

    def post(self, request):
        raw_email = request.data["email"]
        password = request.data["password"]
        email = raw_email.lower()

        try:

            try:
                user = Owner.objects.get(email=email)
                group = Groups.OWNER
            except ObjectDoesNotExist:
                user = CompanyUser.objects.get(email=email)
                group = Groups.COMPANY_USER

            if user.check_password(raw_password=password):
                session = Session.objects.create(
                    # user=account,
                    type=TokenTypes.WEB,
                    temp_user_id=user.id
                )
                access_token = session.update_access_token(group=group)
                response_dict = serializer(session, include_attr=("refresh_token", 'expires_at',))
                response_dict["access_token"] = access_token
                return JsonResponse(response_dict)

            else:
                e = AuthException(
                    AuthException.INVALID_PASSWORD,
                    "Invalid password"
                )
                return JsonResponse(e.to_dict(), status=400)

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "User with such email not found")
            return JsonResponse(e.to_dict(), status=400)


class LogoutView(LoginRequiredAPIView):
    def post(self, request):
        Session.objects.filter(
            temp_user_id=get_owner(request).id
        ).delete()
        return JsonResponse({}, status=200)


class ChangeEmailView(LoginRequiredAPIView):
    validator_class = EmailValidator

    def post(self, request):
        email = str(request.data["email"])
        current_account = request.owner
        email_confirmation = None

        # check already added email
        if current_account.email == email:
            e = ValidationException(
                ValidationException.ALREADY_EXISTS,
                "Such email is already binded to account"
            )
            return JsonResponse(e.to_dict(), status=400)

        # get if already exists
        email_confirmation_list = EmailConfirmation.objects.filter(email=email)
        if email_confirmation_list.exists():
            email_confirmation = email_confirmation_list[0]

        # create new confirmation
        if email_confirmation is None:
            email_confirmation = EmailConfirmation(email=email, account_type="owner")

        email_confirmation.create_code()
        email_confirmation.save()

        current_account.email_confirmation = email_confirmation
        current_account.save()

        email_confirmation.send_confirm_mail()
        return JsonResponse({}, status=200)


class EmailConfirmationView(View):
    def get(self, request, *args, **kwargs):
        confirmations = EmailConfirmation.objects.filter(code=kwargs["code"])
        if confirmations.exists():
            confirmation = confirmations[0]
            if confirmation.is_expired():
                return JsonResponse({"error": "Link is expired"}, status=200)
            else:
                try:
                    account = Account.objects.get(email_confirmation=confirmation)
                    account.email = confirmation.email
                    account.email_confirmation = None
                    account.save()
                    confirmation.delete()
                    account.create_password_and_send()
                    return JsonResponse({"message": "Email is activated successfully"})

                except ObjectDoesNotExist:
                    return JsonResponse({"error": "Invalid link. Account does not found"}, status=200)

        else:
            return JsonResponse({"error": "Invalid link"}, status=200)


class ZendeskJWTWidgetView(LoginRequiredAPIView):
    def get(self, request, *args, **kwargs):
        jwt_token = request.owner.get_or_create_jwt_for_zendesk_widget()
        return HttpResponse(jwt_token)


# Для valet функциональности views

class CompanyUsersView(LoginRequiredAPIView):
    def get(self, request):
        owner = get_owner(request)
        company = Company.objects.get(owner=owner)
        users = CompanyUser.objects.filter(company=company)
        serializer = CompanyUserSerializer(users, many=True)
        return JsonResponse(serializer.data, status=200, safe=False)

    # создание нового пользователя
    def post(self, request):
        # TODO добавить вывод ошибок
        owner = get_owner(request)
        company = Company.objects.get(owner=owner)
        email = request.POST.get('email', None)
        phone = request.POST.get('phone', None)
        first_name = request.POST.get('first_name', None)
        last_name = request.POST.get('last_name', None)
        avatar = request.FILES.get('avatar', None)
        password = request.POST.get('password', None)
        available_parking = request.POST.get('available_parking', None)
        role_id = request.POST.get('role_id', None)

        if email is None or password is None or available_parking is None or role_id is None:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "missing required params"
            )
            return JsonResponse(e.to_dict(), status=400)

        user = CompanyUser.create_user(
            self=None,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            password=password,
            available_parking=available_parking.split(','),
            role_id=role_id,
            avatar=avatar,
            company=company
        )

        return JsonResponse(user, status=200, safe=False)

    def delete(self, request):
        request.data = json.loads(request.body)
        id = request.data.get('id', None)
        if id is None:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "missing required params"
            )
            return JsonResponse(e.to_dict(), status=400)

        CompanyUser.objects.get(id=id).delete()

        return JsonResponse({'message': 'success'}, status=200)


class CompanyUsersUpdateView(LoginRequiredAPIView):

    def post(self, request):
        # TODO добавить вывод ошибок
        owner = get_owner(request)
        company = Company.objects.get(owner=owner)
        id = request.POST.get('id', None)
        email = request.POST.get('email', None)
        first_name = request.POST.get('first_name', None)
        last_name = request.POST.get('last_name', None)
        phone = request.POST.get('phone', None)
        password = request.POST.get('password', None)
        available_parking = request.POST.get('available_parking', None)
        role_id = request.POST.get('role_id', None)
        avatar = request.FILES.get('avatar', None)

        if id is None or email is None or available_parking is None or role_id is None:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "missing required params"
            )
            return JsonResponse(e.to_dict(), status=400)

        user = CompanyUser.update_user(
            self=None,
            id=id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            password=password,
            available_parking=available_parking.split(','),
            role_id=role_id,
            company=company,
            avatar=avatar
        )

        if (not user):  # проверка на ошибки
            return JsonResponse({'status': 'error'}, status=400)

        return JsonResponse(user, status=200, safe=False)


class CompanyUsersAvatarUpdateView(LoginRequiredAPIView):

    def post(self, request):

        avatar = request.FILES.get('avatar', None)

        valet_user = request.companyuser if request.companyuser else None

        if not valet_user:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Only valet user allow"
            )
            return JsonResponse(e.to_dict(), status=400)

        if avatar is None:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "missing required params"
            )
            return JsonResponse(e.to_dict(), status=400)


        fs = FileSystemStorage()
        extension = os.path.splitext(avatar.name)[1]
        filename = fs.save(f'valet_users_avatars/{str(uuid.uuid4())}{extension}', avatar)
        uploaded_file_url = fs.url(filename)
        valet_user.avatar = uploaded_file_url
        valet_user.save()


        return JsonResponse({"status": "success"}, status=200, safe=False)


class CompanyUsersRoleView(LoginRequiredAPIView):
    def get(self, request):
        owner = get_owner(request)
        company = Company.objects.get(owner=owner)

        # забираем роли стандартные и индивидуальные для компании
        standard_roles = CompanyUsersRole.objects.filter(company__isnull=True)
        company_roles = CompanyUsersRole.objects.filter(company=company)
        roles = list(chain(standard_roles, company_roles))

        serializer = CompanyUsersRoleSerializer(roles, many=True)
        return JsonResponse(serializer.data, status=200, safe=False)

    # создание роли
    def post(self, request):
        owner = get_owner(request)
        company = Company.objects.get(owner=owner)
        name = request.data.get('name', None)

        if not name:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "missing required params"
            )
            return JsonResponse(e.to_dict(), status=400)

        role = CompanyUsersRole.objects.create(
            name=name,
            company=company
        )

        serializer = CompanyUsersRoleSerializer([role], many=True)

        return JsonResponse(serializer.data[0], status=200, safe=False)

    def put(self, request):
        request.data = json.loads(request.body)
        owner = get_owner(request)
        company = Company.objects.get(owner=owner)
        name = request.data.get('name', None)
        id = request.data.get('id', None)
        permissions = request.data.get('permissions', None)

        if name is None or id is None or permissions is None:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "missing required params"
            )
            return JsonResponse(e.to_dict(), status=400)

        role = CompanyUsersRole.objects.get(id=id)

        if (role.company_id != company.id):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "its not allow to edit user from another company"
            )
            return JsonResponse(e.to_dict(), status=400)

        role.name = name

        for permission in permissions:
            p = CompanyUsersRolePermission.objects.get(id=permission['id'])
            p.active = permission['active']
            p.save()

        role.save()

        serializer = CompanyUsersRoleSerializer([role], many=True)

        return JsonResponse(serializer.data[0], status=200, safe=False)

    def delete(self, request):
        request.data = json.loads(request.body)
        id = request.data.get('id', None)
        if id is None:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "missing required params"
            )
            return JsonResponse(e.to_dict(), status=400)

        CompanyUsersRole.objects.get(id=id).delete()

        return JsonResponse({'message': 'success'}, status=200)


class CompanyUsersPermissionView(APIView):
    def get(self, request):
        permissions = CompanyUsersPermission.objects.all()
        categories = CompanyUsersPermissionCategory.objects.all()

        return JsonResponse(
            {
                "permissions": serializer(permissions),
                "categories": serializer(categories)
            },
            status=200
        )


class ValetSessionsView(LoginRequiredAPIView):
    validator_class = ValetSessionsCreateFromLKValidator

    #
    def get(self, request):
        owner = get_owner(request)
        company = Company.objects.get(owner=owner)
        id = request.GET.get('id', None)
        result = None

        if (id):
            single_session = ParkingValetSession.objects.filter(id=id, parking__company_id=company.id).last()
            serializer = ParkingValetSessionSerializer([single_session], many=True)
            result = serializer.data[0]
        else:
            sessions = ParkingValetSession.objects.filter(company_id=company.id,
                                                          parking__company_id=company.id).order_by('-id')
            serializer = ParkingValetSessionSerializer(sessions, many=True)
            result = serializer.data

        return JsonResponse(
            result,
            status=200,
            safe=False
        )

    def post(self, request):

        owner = get_owner(request)
        company = Company.objects.get(owner=owner)
        # sessions = ParkingValetSession.objects.filter(company_id=company.id)

        car_model = self.request.POST.get("car_model")
        car_number = self.request.POST.get("car_number")
        car_color = self.request.POST.get("car_color", None)
        valet_card_id = self.request.POST.get("valet_card_id")
        parking_card = self.request.POST.get("parking_card")
        responsible_id = self.request.POST.get("responsible_id")
        started_at = self.request.POST.get("started_at")
        parking_space_number = self.request.POST.get("parking_space_number")
        parking_id = self.request.POST.get("parking_id")
        photo_accept_array = request.FILES.getlist('photo_accept', [])
        photo_parking_array = request.FILES.getlist('photo_parking', [])

        created_by_user = request.companyuser if request.companyuser else None
        parking_card_model = None

        if parking_card:
            parking_card_model = ParkingCard.objects.get(card_id=parking_card)

        session = ParkingValetSession.objects.create(
            car_model=car_model,
            car_number=car_number,
            valet_card_id=valet_card_id,
            parking_card=parking_card_model,
            responsible_for_reception_id=responsible_id,
            started_at=parse_datetime(started_at),
            parking_space_number=parking_space_number,
            parking_id=parking_id,
            company_id=company.id,
            created_by_user=created_by_user,
            car_color=car_color
        )

        for file in photo_accept_array:
            fs = FileSystemStorage()
            extension = os.path.splitext(file.name)[1]
            filename = fs.save(f'valet_car_photo/{str(uuid.uuid4())}{extension}', file)
            uploaded_file_url = fs.url(filename)
            #
            # img = Image.open(self.profile)
            # resize = img.resize((240, 240), Image.ANTIALIAS)
            # new_image = BytesIO()
            # resize.save(new_image, format=img.format, quality=75)

            ParkingValetSessionImages.objects.create(
                valet_session_id=session.id,
                type=PHOTOS_AT_THE_RECEPTION,
                img=uploaded_file_url.replace('/api/media', '', 1)
            )

        for file in photo_parking_array:
            fs = FileSystemStorage()
            extension = os.path.splitext(file.name)[1]
            filename = fs.save(f'valet_car_photo/{str(uuid.uuid4())}{extension}', file)
            uploaded_file_url = fs.url(filename)
            ParkingValetSessionImages.objects.create(
                valet_session_id=session.id,
                type=PHOTOS_FROM_PARKING,
                img=uploaded_file_url.replace('/api/media', '', 1)
            )

        serializer = ParkingValetSessionSerializer([session], many=True)

        return JsonResponse(
            serializer.data[0],
            status=200,
            safe=False
        )

    def delete(self, request):
        request.data = json.loads(request.body)
        id = self.request.data.get("id")
        ParkingValetSession.objects.filter(id=id).last().delete()
        return JsonResponse(
            {'message': 'success'},
            status=200,
            safe=False
        )


class ValetSessionsUpdateView(LoginRequiredAPIView):
    validator_class = ValetSessionsUpdateFromLKValidator

    def post(self, request):

        owner = get_owner(request)
        state = self.request.POST.get("state")
        id = self.request.POST.get("id")
        car_model = self.request.POST.get("car_model")
        car_color = self.request.POST.get("car_color")
        car_number = self.request.POST.get("car_number")
        valet_card_id = self.request.POST.get("valet_card_id")
        parking_card = self.request.POST.get("parking_card")
        responsible_for_reception_id = self.request.POST.get("responsible_for_reception_id")
        responsible_for_delivery_id = self.request.POST.get("responsible_for_delivery_id")
        started_at = self.request.POST.get("started_at")
        parking_space_number = self.request.POST.get("parking_space_number")
        parking_floor = self.request.POST.get("parking_floor")
        car_delivery_time = self.request.POST.get("car_delivery_time")
        car_delivered_at = self.request.POST.get("car_delivered_at")
        photo_accept_array = request.FILES.getlist('photo_accept', [])
        photo_parking_array = request.FILES.getlist('photo_parking', [])

        parking_card_model = None

        if parking_card:
            parking_card_model = ParkingCard.objects.get(card_id=parking_card)

        session = ParkingValetSession.objects.filter(id=id).last()

        if state: session.state = state
        if car_model: session.car_model = car_model
        if car_number: session.car_number = car_number
        if car_color: session.car_color = car_color
        if valet_card_id: session.valet_card_id = valet_card_id
        if parking_card: session.parking_card = parking_card_model
        if responsible_for_reception_id: session.responsible_for_reception_id = responsible_for_reception_id

        if responsible_for_delivery_id:
            if responsible_for_delivery_id != session.responsible_for_delivery_id:
                session.responsible_for_delivery_id = responsible_for_delivery_id
                if session.request:
                    session.request.accept(responsible_for_delivery_id)

        if started_at: session.started_at = started_at
        if parking_space_number: session.parking_space_number = parking_space_number
        if parking_floor: session.parking_floor = parking_floor
        if car_delivery_time: session.car_delivery_time = car_delivery_time
        if car_delivered_at: session.car_delivered_at = car_delivered_at

        session.get_debt_from_remote()
        session.save()

        if photo_accept_array and len(photo_accept_array) > 0:
            # удаляем старые фотки
            ParkingValetSessionImages.objects.filter(valet_session=session, type=PHOTOS_AT_THE_RECEPTION).delete()
            for file in photo_accept_array:
                fs = FileSystemStorage()
                extension = os.path.splitext(file.name)[1]
                filename = fs.save(f'valet_car_photo/{str(uuid.uuid4())}{extension}', file)
                uploaded_file_url = fs.url(filename)
                ParkingValetSessionImages.objects.create(
                    valet_session_id=session.id,
                    type=PHOTOS_AT_THE_RECEPTION,
                    img=uploaded_file_url.replace('/api/media', '', 1)
                )

        if photo_parking_array and len(photo_parking_array) > 0:
            # удаляем старые фотки
            ParkingValetSessionImages.objects.filter(valet_session=session, type=PHOTOS_FROM_PARKING).delete()

            for file in photo_parking_array:
                fs = FileSystemStorage()
                extension = os.path.splitext(file.name)[1]
                filename = fs.save(f'valet_car_photo/{str(uuid.uuid4())}{extension}', file)
                uploaded_file_url = fs.url(filename)
                ParkingValetSessionImages.objects.create(
                    valet_session_id=session.id,
                    type=PHOTOS_FROM_PARKING,
                    img=uploaded_file_url.replace('/api/media', '', 1)
                )

        serializer = ParkingValetSessionSerializer([session], many=True)

        return JsonResponse(
            serializer.data[0],
            status=200,
            safe=False
        )


class ValetRequestsView(LoginRequiredAPIView):
    def get(self, request):
        owner = get_owner(request)
        company = Company.objects.get(owner=owner)

        requests = ParkingValetSessionRequest.objects.filter(company_id=company.id, finish_time__isnull=True).order_by(
            '-id')

        s = ParkingValetRequestIncludeSessionSerializer(requests, many=True)

        result = s.data

        return JsonResponse(
            result,
            status=200,
            safe=False
        )

    def delete(self, request):
        request.data = json.loads(request.body)
        id = self.request.data.get("id")
        ParkingValetSessionRequest.objects.get(id=id).delete()
        return JsonResponse(
            {'message': 'success'},
            status=200,
            safe=False
        )


class ValetRequestsAcceptView(LoginRequiredAPIView):
    def post(self, request):
        request_id = request.data.get('id')

        valet_user = request.companyuser if request.companyuser else None

        if not request_id:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Missing required value"
            )
            return JsonResponse(e.to_dict(), status=400)

        if not valet_user:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Only valet user allow"
            )
            return JsonResponse(e.to_dict(), status=400)

        request = ParkingValetSessionRequest.objects.get(id=request_id)
        request.accept(valet_user.id)

        return JsonResponse(
            {'message': 'success'},
            status=200,
            safe=False
        )


class ValetRequestsFinishView(LoginRequiredAPIView):
    def post(self, request):
        request_id = request.data.get('id')

        if not request_id:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Missing required value"
            )
            return JsonResponse(e.to_dict(), status=400)

        instance = ParkingValetSessionRequest.objects.get(id=request_id)
        instance.finish_time = datetime.datetime.now(timezone.utc)
        instance.save()

        return JsonResponse(
            {'message': 'success'},
            status=200,
            safe=False
        )


class ValetRequestsHistoryView(LoginRequiredAPIView):
    def get(self, request):
        valet_user = request.companyuser if request.companyuser else None

        if not valet_user:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Only valet user allow"
            )

        requests = ParkingValetSessionRequest.objects.filter(accepted_by=valet_user,
                                                             finish_time__isnull=False).order_by('-id')

        serializer = ParkingValetRequestIncludeSessionSerializer(requests, many=True)

        return JsonResponse(
            serializer.data,
            status=200,
            safe=False
        )


class ValetUserParkingView(LoginRequiredAPIView):
    def get(self, request):
        parking_list = []
        valet_user = request.companyuser if request.companyuser else None
        if valet_user:
            parking_list = valet_user.available_parking
        else:
            parking_list = Parking.objects.filter(approved=True, company__owner=get_owner(request))

        return JsonResponse(
            serializer(parking_list, exclude_attr=("vendor_id", "company_id", "max_client_debt",
                                                   "tariff", "tariff_file_name", "tariff_file_content",
                                                   'hide_parking_coordinates', 'free_places', 'max_places', 'picture')),
            status=200,
            safe=False
        )
