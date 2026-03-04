from sqlalchemy import text
from app.database.db import engine

def insert_event(timestamp, duration, snapshot, summary):

    with engine.connect() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS fatigue_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        duration FLOAT,
        snapshot TEXT,
        summary TEXT)
        """))

        conn.execute(text("""
        INSERT INTO fatigue_events(timestamp,duration,snapshot,summary)
        VALUES(:t,:d,:s,:sum)
        """), {"t":timestamp,"d":duration,"s":snapshot,"sum":summary})

        conn.commit()