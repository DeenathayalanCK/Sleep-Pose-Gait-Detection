import datetime
from app.database.repository import insert_event

def log_event(duration, snapshot, summary):

    timestamp = str(datetime.datetime.now())

    insert_event(timestamp, duration, snapshot, summary)