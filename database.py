"""
database.py - all the SQLite (database) work lives here.

The app (app.py) never writes SQL by itself for saving data. It calls the
small functions in this file instead. This keeps app.py easy to read.
"""
import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pandas as pd

# ---------------------------------------------------------------------------
# Folders and files
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "waste.db")

# Philippine time (UTC+8). We use a fixed offset so it works on any server.
PH_TZ = timezone(timedelta(hours=8))

# ---------------------------------------------------------------------------
# Fixed lists used by the whole app
# ---------------------------------------------------------------------------
# The 10 barangays of Bunawan, Agusan del Sur. Each one is a collection zone.
BARANGAYS = [
    "Bunawan Brook", "Consuelo", "Imelda", "Libertad", "Mambalili",
    "Nueva Era", "Poblacion", "San Andres", "San Marcos", "San Teodoro",
]

# These are PLACEHOLDERS. Replace them with real street names using the
# Admin > Areas page after you check with each barangay hall.
HIGHWAY = "Davao-Agusan National Highway"
HIGHWAY_BARANGAYS = ["San Teodoro", "Libertad", "Bunawan Brook", "Consuelo"]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WASTE_TYPES = ["Biodegradable", "Non-biodegradable", "Recyclable", "Special"]
STATUSES = ["Pending", "In Progress", "Resolved"]
ALL_AREAS = "All areas"          # used in schedules: the whole barangay
WHOLE_BARANGAY = "Whole barangay"  # used in complaints when no area applies


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
def now_ph():
    """Current date and time in the Philippines."""
    return datetime.now(PH_TZ)


def today_ph():
    """Today's date in the Philippines."""
    return now_ph().date()


def stamp():
    """Text timestamp used when saving records."""
    return now_ph().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# Basic database helpers
# ---------------------------------------------------------------------------
def connect():
    """Open the database (and create the folders if they do not exist)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql, params=()):
    """Run a SELECT and return a list of dictionaries."""
    conn = connect()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def df(sql, params=()):
    """Run a SELECT and return a pandas DataFrame (keeps column names)."""
    conn = connect()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def execute(sql, params=()):
    """Run INSERT / UPDATE / DELETE and return the new row id."""
    conn = connect()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Create tables and sample data
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barangay TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (barangay, name)
);
CREATE TABLE IF NOT EXISTS collectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    pin TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barangay TEXT NOT NULL,
    area TEXT NOT NULL,
    waste_type TEXT NOT NULL,
    day TEXT NOT NULL,
    time TEXT NOT NULL,
    collector_id INTEGER
);
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking TEXT,
    name TEXT,
    barangay TEXT,
    area TEXT,
    date_missed TEXT,
    waste_type TEXT,
    description TEXT,
    photo TEXT,
    status TEXT DEFAULT 'Pending',
    source TEXT DEFAULT 'resident',
    created TEXT
);
CREATE TABLE IF NOT EXISTS complaint_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER,
    status TEXT,
    note TEXT,
    created TEXT
);
CREATE TABLE IF NOT EXISTS collection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER,
    log_date TEXT,
    status TEXT,
    reason TEXT,
    collector_id INTEGER,
    UNIQUE (schedule_id, log_date)
);
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    body TEXT,
    kind TEXT DEFAULT 'info',
    created TEXT
);
"""

TABLES = ["areas", "collectors", "schedules", "complaints",
          "complaint_updates", "collection_log", "announcements"]


def init_db():
    """Create tables. Add sample data the first time the app runs."""
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        first_run = conn.execute("SELECT COUNT(*) FROM areas").fetchone()[0] == 0
    finally:
        conn.close()
    if first_run:
        seed_sample_data()


def reset_db():
    """Delete everything and put the sample data back."""
    conn = connect()
    try:
        for table in TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
    finally:
        conn.close()
    init_db()


def seed_sample_data():
    """Fill the database with sample (pretend) data so the app looks alive."""
    conn = connect()
    try:
        # 1) Areas: Purok 1-5 for every barangay (+ highway for some)
        for b in BARANGAYS:
            for n in range(1, 6):
                conn.execute("INSERT INTO areas (barangay, name) VALUES (?, ?)", (b, f"Purok {n}"))
            if b in HIGHWAY_BARANGAYS:
                conn.execute("INSERT INTO areas (barangay, name) VALUES (?, ?)", (b, HIGHWAY))

        # 2) Collectors (sample names, sample PIN 1234)
        for name in ["Juan Dela Cruz", "Maria Santos", "Pedro Reyes", "Ana Lopez"]:
            conn.execute("INSERT INTO collectors (name, pin) VALUES (?, ?)", (name, "1234"))

        # 3) Schedules: (barangay, area, waste type, day, time, collector id)
        schedules = [
            ("Poblacion", ALL_AREAS, "Biodegradable", "Monday", "07:00", 1),
            ("Poblacion", ALL_AREAS, "Non-biodegradable", "Thursday", "07:00", 1),
            ("Libertad", ALL_AREAS, "Biodegradable", "Monday", "07:30", 1),
            ("San Teodoro", ALL_AREAS, "Biodegradable", "Tuesday", "06:30", 2),
            ("San Teodoro", HIGHWAY, "Recyclable", "Friday", "08:00", 2),
            ("Consuelo", ALL_AREAS, "Biodegradable", "Wednesday", "07:00", 2),
            ("Bunawan Brook", ALL_AREAS, "Non-biodegradable", "Tuesday", "08:00", 3),
            ("Imelda", ALL_AREAS, "Biodegradable", "Thursday", "07:00", 3),
            ("Mambalili", ALL_AREAS, "Recyclable", "Wednesday", "09:00", 3),
            ("Nueva Era", ALL_AREAS, "Biodegradable", "Friday", "07:00", 4),
            ("San Andres", ALL_AREAS, "Non-biodegradable", "Saturday", "07:00", 4),
            ("San Marcos", ALL_AREAS, "Special", "Saturday", "09:00", 4),
        ]
        conn.executemany(
            "INSERT INTO schedules (barangay, area, waste_type, day, time, collector_id) VALUES (?,?,?,?,?,?)",
            schedules,
        )

        # 4) Sample complaints
        today = today_ph()
        complaints = [
            ("Rosa M.", "Poblacion", "Purok 2", 2, "Biodegradable", "Garbage was not collected on Monday.", "Pending"),
            ("Ben T.", "San Teodoro", HIGHWAY, 3, "Recyclable", "Bottles and cans are still on the roadside.", "In Progress"),
            ("Liza A.", "Consuelo", "Purok 4", 5, "Biodegradable", "The truck did not come to our purok.", "Resolved"),
            ("Mark D.", "Libertad", "Purok 1", 1, "Non-biodegradable", "Trash bags were left at the corner.", "Pending"),
            ("Joy P.", "Imelda", "Purok 3", 4, "Biodegradable", "Our purok was skipped.", "In Progress"),
            ("Carlo S.", "San Marcos", "Purok 2", 6, "Special", "A broken appliance was not picked up.", "Resolved"),
            ("Nena R.", "Bunawan Brook", "Purok 5", 2, "Non-biodegradable", "The truck passed but did not stop.", "Pending"),
            ("Tony V.", "Poblacion", "Purok 1", 7, "Recyclable", "No pickup this week.", "Resolved"),
        ]
        for i, (name, brgy, area, ago, waste, desc, status) in enumerate(complaints, start=1):
            missed = (today - timedelta(days=ago)).isoformat()
            created = (now_ph() - timedelta(days=ago - 1 if ago > 1 else 0)).strftime("%Y-%m-%d %H:%M")
            cur = conn.execute(
                "INSERT INTO complaints (tracking, name, barangay, area, date_missed, waste_type, description, status, source, created) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (f"BUN-{i:04d}", name, brgy, area, missed, waste, desc, status, "resident", created),
            )
            cid = cur.lastrowid
            steps = [("Pending", "Complaint received.")]
            if status in ("In Progress", "Resolved"):
                steps.append(("In Progress", "The collector has been informed."))
            if status == "Resolved":
                steps.append(("Resolved", "Garbage was collected. Thank you!"))
            for st_name, note in steps:
                conn.execute(
                    "INSERT INTO complaint_updates (complaint_id, status, note, created) VALUES (?,?,?,?)",
                    (cid, st_name, note, created),
                )

        # 5) Collection history for the last 28 days (so health scores work)
        rng = random.Random(7)  # same random numbers every time
        miss_chance = {"Imelda": 0.30, "San Marcos": 0.35, "Poblacion": 0.10}
        sched_rows = conn.execute("SELECT * FROM schedules").fetchall()
        for back in range(1, 29):
            d = today - timedelta(days=back)
            for s in sched_rows:
                if DAYS[d.weekday()] != s["day"]:
                    continue
                missed = rng.random() < miss_chance.get(s["barangay"], 0.05)
                conn.execute(
                    "INSERT OR IGNORE INTO collection_log (schedule_id, log_date, status, reason, collector_id) VALUES (?,?,?,?,?)",
                    (s["id"], d.isoformat(), "Missed" if missed else "Collected",
                     "Truck breakdown" if missed else "", s["collector_id"]),
                )

        # 6) Announcements
        conn.execute(
            "INSERT INTO announcements (title, body, kind, created) VALUES (?,?,?,?)",
            ("Welcome!", "Check your barangay schedule and report missed collections here.", "info", stamp()),
        )
        conn.execute(
            "INSERT INTO announcements (title, body, kind, created) VALUES (?,?,?,?)",
            ("Weather notice", "Collections may be delayed during heavy rain. Thank you for your patience.", "warning", stamp()),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Areas (streets / puroks)
# ---------------------------------------------------------------------------
def areas_for(barangay):
    rows = query("SELECT name FROM areas WHERE barangay=? ORDER BY name", (barangay,))
    return [r["name"] for r in rows]


def add_area(barangay, name):
    """Returns True if added, False if the name already exists."""
    try:
        execute("INSERT INTO areas (barangay, name) VALUES (?, ?)", (barangay, name.strip()))
        return True
    except sqlite3.IntegrityError:
        return False


def rename_area(barangay, old, new):
    """Rename an area and keep schedules/complaints in sync."""
    try:
        execute("UPDATE areas SET name=? WHERE barangay=? AND name=?", (new.strip(), barangay, old))
    except sqlite3.IntegrityError:
        return False
    execute("UPDATE schedules SET area=? WHERE barangay=? AND area=?", (new.strip(), barangay, old))
    execute("UPDATE complaints SET area=? WHERE barangay=? AND area=?", (new.strip(), barangay, old))
    return True


def delete_area(barangay, name):
    execute("DELETE FROM areas WHERE barangay=? AND name=?", (barangay, name))
    # Schedules that used this area now cover the whole barangay.
    execute("UPDATE schedules SET area=? WHERE barangay=? AND area=?", (ALL_AREAS, barangay, name))


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------
def collectors():
    return query("SELECT id, name, pin FROM collectors ORDER BY name")


def add_collector(name, pin):
    execute("INSERT INTO collectors (name, pin) VALUES (?, ?)", (name.strip(), pin.strip()))


def delete_collector(cid):
    execute("UPDATE schedules SET collector_id=NULL WHERE collector_id=?", (cid,))
    execute("DELETE FROM collectors WHERE id=?", (cid,))


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------
def schedules(barangay=None, area=None, waste=None, day=None):
    """Return schedules as a DataFrame. Every filter is optional."""
    sql = (
        "SELECT s.id, s.barangay, s.area, s.waste_type, s.day, s.time, s.collector_id, "
        "COALESCE(c.name, 'Not assigned') AS collector "
        "FROM schedules s LEFT JOIN collectors c ON c.id = s.collector_id WHERE 1=1"
    )
    params = []
    if barangay:
        sql += " AND s.barangay = ?"
        params.append(barangay)
    if area and area != ALL_AREAS:
        # A street sees its own schedules plus the "whole barangay" ones.
        sql += " AND (s.area = ? OR s.area = ?)"
        params += [area, ALL_AREAS]
    if waste:
        sql += " AND s.waste_type = ?"
        params.append(waste)
    if day:
        sql += " AND s.day = ?"
        params.append(day)
    return df(sql, tuple(params))


def add_schedule(barangay, area, waste, day, time_text, collector_id):
    execute(
        "INSERT INTO schedules (barangay, area, waste_type, day, time, collector_id) VALUES (?,?,?,?,?,?)",
        (barangay, area, waste, day, time_text, collector_id),
    )


def update_schedule(sid, area, waste, day, time_text, collector_id):
    execute(
        "UPDATE schedules SET area=?, waste_type=?, day=?, time=?, collector_id=? WHERE id=?",
        (area, waste, day, time_text, collector_id, sid),
    )


def delete_schedule(sid):
    execute("DELETE FROM collection_log WHERE schedule_id=?", (sid,))
    execute("DELETE FROM schedules WHERE id=?", (sid,))


def next_pickup(barangay):
    """Find the next pickup for a barangay. Returns (schedule dict, datetime) or None."""
    rows = query("SELECT * FROM schedules WHERE barangay=?", (barangay,))
    now = now_ph()
    best = None
    for r in rows:
        hour, minute = (int(x) for x in r["time"].split(":"))
        weekday = DAYS.index(r["day"])
        for add in range(0, 8):
            d = now.date() + timedelta(days=add)
            if d.weekday() != weekday:
                continue
            when = datetime(d.year, d.month, d.day, hour, minute, tzinfo=PH_TZ)
            if when > now:
                if best is None or when < best[1]:
                    best = (r, when)
                break
    return best


# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------
def save_photo(photo_bytes, tracking):
    """
    Save an evidence photo (from the camera or an upload).
    The picture is made smaller (max 1280 px) so the app stays fast.
    Returns the file name, or None if the file is not a real picture.
    """
    try:
        from PIL import Image, ImageOps
        img = Image.open(BytesIO(photo_bytes))
        img = ImageOps.exif_transpose(img)  # fix phone photos that are rotated
        img = img.convert("RGB")
        img.thumbnail((1280, 1280))
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        name = f"{tracking}.jpg"
        img.save(os.path.join(UPLOAD_DIR, name), "JPEG", quality=80)
        return name
    except Exception:
        return None


def photo_path(photo_name):
    """Full path of a saved photo, or None if the file is missing."""
    if not photo_name:
        return None
    path = os.path.join(UPLOAD_DIR, photo_name)
    return path if os.path.exists(path) else None


def add_complaint(name, barangay, area, date_missed, waste_type, description,
                  photo_bytes=None, source="resident"):
    """Save a complaint and return its tracking number (like BUN-0009)."""
    created = stamp()
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO complaints (name, barangay, area, date_missed, waste_type, description, status, source, created) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (name, barangay, area, str(date_missed), waste_type, description, "Pending", source, created),
        )
        cid = cur.lastrowid
        tracking = f"BUN-{cid:04d}"
        photo_name = save_photo(photo_bytes, tracking) if photo_bytes else None
        conn.execute("UPDATE complaints SET tracking=?, photo=? WHERE id=?", (tracking, photo_name, cid))
        conn.execute(
            "INSERT INTO complaint_updates (complaint_id, status, note, created) VALUES (?,?,?,?)",
            (cid, "Pending", "Complaint received.", created),
        )
        conn.commit()
    finally:
        conn.close()
    return tracking


def get_complaint(tracking):
    rows = query("SELECT * FROM complaints WHERE tracking=?", (tracking.strip().upper(),))
    return rows[0] if rows else None


def timeline(complaint_id):
    return query(
        "SELECT status, note, created FROM complaint_updates WHERE complaint_id=? ORDER BY id",
        (complaint_id,),
    )


def update_complaint(complaint_id, status, note):
    execute("UPDATE complaints SET status=? WHERE id=?", (status, complaint_id))
    execute(
        "INSERT INTO complaint_updates (complaint_id, status, note, created) VALUES (?,?,?,?)",
        (complaint_id, status, note.strip() or f"Status changed to {status}.", stamp()),
    )


def complaints_since(since=None):
    """Complaints (as dictionaries, with photo name) missed on or after a date."""
    if since:
        return query("SELECT * FROM complaints WHERE date_missed >= ? ORDER BY id DESC", (since,))
    return query("SELECT * FROM complaints ORDER BY id DESC")


def collector_summary(since=None):
    """Collected / missed totals for each collector."""
    sql = ("SELECT COALESCE(c.name, 'Not assigned') AS collector, "
           "SUM(CASE WHEN l.status='Collected' THEN 1 ELSE 0 END) AS done, "
           "SUM(CASE WHEN l.status='Missed' THEN 1 ELSE 0 END) AS missed "
           "FROM collection_log l LEFT JOIN collectors c ON c.id = l.collector_id")
    params = ()
    if since:
        sql += " WHERE l.log_date >= ?"
        params = (since,)
    sql += " GROUP BY collector ORDER BY collector"
    return query(sql, params)


def complaints_df(status=None):
    sql = ("SELECT tracking, name, barangay, area, date_missed, waste_type, description, status, source, created "
           "FROM complaints")
    params = ()
    if status and status != "All":
        sql += " WHERE status = ?"
        params = (status,)
    sql += " ORDER BY id DESC"
    return df(sql, params)


# ---------------------------------------------------------------------------
# Collector work: stops and the collection log
# ---------------------------------------------------------------------------
def stops_for(collector_id, the_date):
    """Stops that a collector must visit on a date, with today's status."""
    day_name = DAYS[the_date.weekday()]
    return query(
        "SELECT s.id, s.barangay, s.area, s.waste_type, s.time, l.status AS log_status, l.reason AS log_reason "
        "FROM schedules s LEFT JOIN collection_log l ON l.schedule_id = s.id AND l.log_date = ? "
        "WHERE s.collector_id = ? AND s.day = ? ORDER BY s.time",
        (the_date.isoformat(), collector_id, day_name),
    )


def mark_collected(schedule_id, log_date, collector_id):
    execute(
        "INSERT OR REPLACE INTO collection_log (schedule_id, log_date, status, reason, collector_id) VALUES (?,?,?,?,?)",
        (schedule_id, log_date, "Collected", "", collector_id),
    )


def mark_missed(schedule_id, log_date, collector_id, reason):
    """Mark a stop as missed AND auto-create a complaint (the auto-flag feature)."""
    execute(
        "INSERT OR REPLACE INTO collection_log (schedule_id, log_date, status, reason, collector_id) VALUES (?,?,?,?,?)",
        (schedule_id, log_date, "Missed", reason, collector_id),
    )
    rows = query("SELECT * FROM schedules WHERE id=?", (schedule_id,))
    if not rows:
        return
    s = rows[0]
    area = WHOLE_BARANGAY if s["area"] == ALL_AREAS else s["area"]
    already = query(
        "SELECT id FROM complaints WHERE source='auto' AND barangay=? AND area=? AND date_missed=? AND waste_type=?",
        (s["barangay"], area, log_date, s["waste_type"]),
    )
    if not already:
        add_complaint(
            "Auto-report (collector)", s["barangay"], area, log_date, s["waste_type"],
            f"The collector marked this stop as missed. Reason: {reason}", source="auto",
        )


def undo_log(schedule_id, log_date):
    execute("DELETE FROM collection_log WHERE schedule_id=? AND log_date=?", (schedule_id, log_date))


def log_df(days=None):
    sql = ("SELECT l.log_date AS date, s.barangay, s.area, s.waste_type, s.time, l.status, l.reason, "
           "COALESCE(c.name, '') AS collector "
           "FROM collection_log l JOIN schedules s ON s.id = l.schedule_id "
           "LEFT JOIN collectors c ON c.id = l.collector_id")
    params = ()
    if days:
        sql += " WHERE l.log_date >= ?"
        params = ((today_ph() - timedelta(days=days)).isoformat(),)
    sql += " ORDER BY l.log_date DESC, s.time"
    return df(sql, params)


# ---------------------------------------------------------------------------
# Numbers for dashboards
# ---------------------------------------------------------------------------
def health_scores(days=30):
    """On-time collection rate per barangay for the last N days."""
    since = (today_ph() - timedelta(days=days)).isoformat()
    rows = query(
        "SELECT s.barangay AS barangay, "
        "SUM(CASE WHEN l.status='Collected' THEN 1 ELSE 0 END) AS done, "
        "SUM(CASE WHEN l.status='Missed' THEN 1 ELSE 0 END) AS missed "
        "FROM collection_log l JOIN schedules s ON s.id = l.schedule_id "
        "WHERE l.log_date >= ? GROUP BY s.barangay",
        (since,),
    )
    result = {}
    for r in rows:
        total = r["done"] + r["missed"]
        result[r["barangay"]] = {
            "done": r["done"], "missed": r["missed"],
            "rate": (r["done"] / total) if total else None,
        }
    return result


def complaint_counts():
    """Number of complaints per barangay."""
    rows = query("SELECT barangay, COUNT(*) AS n FROM complaints GROUP BY barangay")
    return {r["barangay"]: r["n"] for r in rows}


def flagged_today():
    """Barangays that had a Missed stop today (shown in red)."""
    rows = query(
        "SELECT DISTINCT s.barangay AS barangay FROM collection_log l "
        "JOIN schedules s ON s.id = l.schedule_id "
        "WHERE l.log_date = ? AND l.status = 'Missed'",
        (today_ph().isoformat(),),
    )
    return {r["barangay"] for r in rows}


def today_stats():
    today = today_ph().isoformat()
    done = query("SELECT COUNT(*) AS n FROM collection_log WHERE log_date=? AND status='Collected'", (today,))[0]["n"]
    missed = query("SELECT COUNT(*) AS n FROM collection_log WHERE log_date=? AND status='Missed'", (today,))[0]["n"]
    open_c = query("SELECT COUNT(*) AS n FROM complaints WHERE status != 'Resolved'")[0]["n"]
    total_c = query("SELECT COUNT(*) AS n FROM complaints")[0]["n"]
    return {"done": done, "missed": missed, "open": open_c, "total": total_c}


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------
def announcements(limit=None):
    sql = "SELECT id, title, body, kind, created FROM announcements ORDER BY id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return query(sql)


def add_announcement(title, body, kind):
    execute(
        "INSERT INTO announcements (title, body, kind, created) VALUES (?,?,?,?)",
        (title.strip(), body.strip(), kind, stamp()),
    )


def delete_announcement(aid):
    execute("DELETE FROM announcements WHERE id=?", (aid,))
