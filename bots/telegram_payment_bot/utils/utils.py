from django.core.exceptions import ObjectDoesNotExist

from rps_vendor.models import ParkingCard, RpsParking


def get_parking_info(card_id, parking_id):

    result = {
        "status": 'success',
        "message": "",
        "data": {}
    }
    try:
        parking_card = ParkingCard.objects.get(
            card_id=card_id
        )

        rps_parking = RpsParking.objects.select_related(
            'parking').get(parking__id=parking_id)

        if not rps_parking.parking.rps_parking_card_available:
            result['status'] = 'error'
            result['message'] = 'Парковка не доступна'

        response_dict = rps_parking.get_parking_card_debt(parking_card)
        if response_dict:
            response_dict["parking_name"] = rps_parking.parking.name
            response_dict["parking_address"] = rps_parking.parking.address
            response_dict["currency"] = rps_parking.parking.currency
            result['data'] = response_dict
        else:
            result['status'] = 'error'
            result['message'] = "Card with number %s does not exist" % card_id

    except ObjectDoesNotExist:
        result['status'] = 'error'
        result['message'] = 'Parking does not found or parking card is unavailable'

    return  result
