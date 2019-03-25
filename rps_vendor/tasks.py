import datetime
import json
import traceback

import pytz
from django.utils import timezone
import requests
from autotask.tasks import periodic_task, delayed_task
from dss.TimeFormatFactory import TimeFormatFactory

from base.utils import get_logger
from parkings.models import ParkingSession
from rps_vendor.models import RpsParking


@delayed_task()
def rps_process_updated_sessions(parking, sessions):
    get_logger().info("rps_process_updated_sessions")
    for session in sessions:
        client_id = session["client_id"]
        started_at = session["started_at"]
        session_id = str(client_id) + "&" + str(started_at)

        debt = float(session["debt"])
        updated_at = int(session["updated_at"])
        parking_sessions = ParkingSession.objects.filter(session_id=session_id, parking=parking)

        if parking_sessions.count() > 0:
            parking_session = parking_sessions[0]
            if not parking_session.is_completed_by_vendor():
                parking_session.debt = debt
                utc_updated_at = parking.get_utc_parking_datetime(updated_at)
                parking_session.updated_at = utc_updated_at
                get_logger().info("Update list parking at %s", str(utc_updated_at))
                parking_session.save()


@periodic_task(seconds=30)
def request_rps_session_update():
    for rps_parking in RpsParking.objects.all().select_related("parking"):

        # Return if request_update_url is not specified
        if not rps_parking.request_update_url or not rps_parking.polling_enabled:
            continue

        active_sessions = ParkingSession.objects.filter(
            parking=rps_parking.parking,
            state__in=[ParkingSession.STATE_STARTED, ParkingSession.STATE_STARTED_BY_VENDOR],
            is_suspended=False,
        )
        if active_sessions.count() == 0:
            continue

        payload = _get_payload_from_session_queryset(active_sessions)
        _make_http_request(rps_parking.request_update_url, payload, rps_parking)


def _get_payload_from_session_queryset(active_sessions):
    result_dict = {"sessions":[]}
    for active_session in active_sessions:
        session = {
            "parking_id":active_session.parking.id,
            "client_id":active_session.client.id,
            "started_at":int(TimeFormatFactory.get_time_func('timestamp')(active_session.started_at))
        }
        result_dict["sessions"].append(session)

    return json.dumps(result_dict)


def _make_http_request(url, payload, rps_parking):
    connect_timeout = 2

    headers = {'Content-type': 'application/json'}
    rps_parking.last_request_date = timezone.now()
    rps_parking.last_request_body = payload

    try:
        r = requests.post(url, data=payload, headers=headers,
                          timeout=(connect_timeout, 5.0))
        try:
            result = r.json()
            rps_parking.last_response_code = r.status_code
            rps_parking.last_response_body = result if result else ""
            rps_parking.save()

        except Exception as e:
            traceback_str = traceback.format_exc()
            rps_parking.last_response_code=998
            rps_parking.last_response_body="Parkpass intenal error: "+str(e) + '\n' + traceback_str
            rps_parking.save()

    except Exception as e:
        traceback_str = traceback.format_exc()
        rps_parking.last_response_code=999
        rps_parking.last_response_body="Vendor error: "+str(e) + '\n' + traceback_str
        rps_parking.save()