import datetime

import pytz
from autotask.tasks import periodic_task, delayed_task

from parkings.models import ParkingSession
from rps_vendor.models import RpsParking


@delayed_task()
def rps_process_updated_sessions(parking, sessions):
    for session in sessions:
        client_id = session["client_id"]
        started_at = session["stated_at"]
        session_id = str(client_id) + "&" + str(started_at)

        debt = int(session["debt"])
        updated_at = int(session["updated_at"])
        parking_sessions = ParkingSession.objects.filter(session_id=session_id, parking=parking)

        if parking_sessions.count() > 0:
            parking_session = parking_sessions[0]
            parking_session.parking_session = debt

            completed_at_date = datetime.datetime.fromtimestamp(int(updated_at))
            completed_at_date_tz = pytz.utc.localize(completed_at_date)
            parking_session.updated_at = completed_at_date_tz

            parking_session.save()


@periodic_task(seconds=30)
def request_rps_session_update():
    # TODO check canceled sessions

    for rps_parking in RpsParking.objects.all():

        # Return if request_update_url is not specified
        if not rps_parking.request_update_url:
            return

        active_sessions = ParkingSession.objects.filter(
            state__in=[ParkingSession.STATE_SESSION_STARTED,
                   ParkingSession.STATE_SESSION_UPDATED,
                   ParkingSession.STATE_SESSION_COMPLETED]
        )
        # TODO make request for current sessions