import datetime

import pytz
from autotask.tasks import delayed_task

from parkings.models import ParkingSession

@delayed_task()
def process_updated_sessions(parking, sessions):
    for session in sessions:
        session_id = session["session_id"]
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