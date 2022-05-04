# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse
from base.exceptions import ValidationException
from base.views import APIView
from parkings.models import ParkingValetSession, ParkingValetSessionSerializer
from valet.validators import ValetSessionGetValidator


class ValetSessionView(APIView):
    validator_class = ValetSessionGetValidator

    def get(self, request):
        id = request.GET.get('id')

        try:
            session = ParkingValetSession.objects.get(valet_card_id=id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Session not found'
            )
            return JsonResponse(e.to_dict(), status=400)

        session.get_debt_from_remote()

        serializer = ParkingValetSessionSerializer([session], many=True)

        return JsonResponse(serializer.data[0], status=200, safe=False)

    @transaction.atomic
    def post(self, request):  # заказ авто клиентом
        id = request.data.get('id')
        delivery_date = request.data.get('date')

        try:
            session = ParkingValetSession.objects.get(valet_card_id=id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                'Session not found'
            )
            return JsonResponse(e.to_dict(), status=400)

        session.get_debt_from_remote()

        session.book(delivery_date)

        serializer = ParkingValetSessionSerializer([session], many=True)

        return JsonResponse(serializer.data[0], status=200, safe=False)


def get_valet_session_status(request):

    id = request.GET.get('id')
    try:
        session = ParkingValetSession.objects.get(valet_card_id=id)
    except ObjectDoesNotExist:
        e = ValidationException(
            ValidationException.VALIDATION_ERROR,
            'Session not found'
        )
        return JsonResponse(e.to_dict(), status=400)

    return JsonResponse({'session_status': session.state}, status=200)