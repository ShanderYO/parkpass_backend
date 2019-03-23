import datetime

import pytz
from autotask.tasks import delayed_task

from base.utils import datetime_from_unix_timestamp_tz
from parkings.models import ParkingSession

@delayed_task()
def process_updated_sessions(parking, sessions):
    for session in sessions:
        session_id = session["session_id"]
        debt = int(session["debt"])
        updated_at = int(session["updated_at"])

        utc_updated_at = parking.get_utc_parking_datetime(updated_at)

        parking_sessions = ParkingSession.objects.filter(
            session_id=session_id, parking=parking)

        if parking_sessions.count() > 0:
            parking_session = parking_sessions[0]
            if not parking_sessions.is_available_for_vendor_update():
                continue

            parking_session.debt = debt
            parking_session.updated_at = utc_updated_at
            parking_session.save()