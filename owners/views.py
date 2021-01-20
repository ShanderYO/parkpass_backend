# -*- coding: utf-8 -*-
import json

import xlwt
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.utils import timezone
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
from parkings.models import Parking, ParkingSession
from rps_vendor.models import RpsSubscription, STATE_CONFIRMED
from vendors.models import Vendor
from .models import OwnerApplication, Owner
from .models import Owner as Account
from .models import Company
from .validators import ConnectIssueValidator, TariffValidator


LoginRequiredAPIView = generic_login_required_view(Owner)


class AccountInfoView(LoginRequiredAPIView):
    def get(self, request):
        account_dict = serializer(request.owner, exclude_attr=("name", "created_at", "sms_code", "password"))
        parkings = Parking.objects.filter(company__owner=request.owner)
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
        parking_id = request.GET.get('parking_id',"0").encode('utf-8')

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
            parking__owner=request.owner
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
            parking__owner=request.owner
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

        parkings = Parking.objects.filter(owner=request.owner)

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

        parkings = Parking.objects.filter(owner=request.owner)

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

        columns = ['ID', 'Название', 'CardId', 'Тип клиента', 'Дата покупки', 'Дата окончания', 'Сумма', 'Статус', 'Автопродление']

        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        # Sheet body, remaining rows
        font_style = xlwt.XFStyle()
        rows = qs.values_list('id', 'name', 'account_id','unlimited', 'started_at', 'expired_at', 'sum', 'active',
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
            parking__owner=request.owner
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
            session_dict = serializer(session, datetime_format='timestamp_notimezone', exclude_attr=('parking_id', 'try_refund', 'current_refund_sum', 'target_refund_sum'))
            session_dict["parking"] = parking_dict
            result_list.append(session_dict)

        response_dict = {
            "result":result_list,
            "next":result_list[len(result_list) - 1]["id"] if len(result_list) > 0 else None
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
            parking__owner=request.owner
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
            parking__owner=request.owner
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

        parkings = Parking.objects.filter(owner=request.owner)

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
            page=0

        response_dict = {
            "result": r[page*count:(page+1)*count],
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
        obj.owner = request.owner
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
    show_fields = ('owner_id', 'type', 'owner_id', 'parking_id', 'vendor_id', 'company_id', 'status', 'description', 'created_at', )
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
            "file_name":parking.tariff_file_name,
            "file_content":parking.tariff_file_content
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
            company = Company.objects.get(id=company_id, owner=request.owner)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Your company does not found'
            )
            return JsonResponse(e.to_dict(), status=400)

        OwnerApplication.objects.create(
            type=OwnerApplication.TYPE_CONNECT_PARKING,
            owner=self.request.owner,
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
    readonly_fields = ()

    def on_create(self, request, obj):
        obj.owner = request.owner # add owner
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
    show_fields = ('id','name',)


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
            owner = Owner.objects.get(email=email)
            if owner.check_password(raw_password=password):
                session = Session.objects.create(
                    #user=account,
                    type=TokenTypes.WEB,
                    temp_user_id=owner.id
                )
                access_token = session.update_access_token(group=Groups.OWNER)
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
            temp_user_id=request.owner.id
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

