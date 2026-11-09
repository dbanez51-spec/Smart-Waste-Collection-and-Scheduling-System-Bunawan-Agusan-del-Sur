"""
app.py - Smart Waste Collection and Scheduling System
Municipality of Bunawan, Agusan del Sur

Run it with:   streamlit run app.py

How this file is organized (top to bottom):
  1. Setup and settings
  2. Words for English / Tagalog
  3. Small helper functions
  4. One function per page
  5. The main part: sidebar, login, and showing the chosen page
"""
import os
from datetime import time as dtime
from datetime import timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import database as db
import report_builder as rb

# ---------------------------------------------------------------------------
# 1. Setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Smart Waste Bunawan", page_icon="♻️", layout="wide")
db.init_db()  # makes the tables and sample data the first time


def get_secret(name, default):
    """Read a PIN from Streamlit secrets if set, else use the default."""
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


ADMIN_PIN = get_secret("ADMIN_PIN", "admin123")  # change this before real use!

# Colors used by the tiles
GREEN, YELLOW, RED, GRAY = "#2e9e5b", "#e0a800", "#d64545", "#7b8b86"

# Look and feel: big readable text and big buttons (good for phones)
st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 16px; }
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        width: 100%; min-height: 48px; font-size: 1.05rem; border-radius: 10px;
    }
    .tile { border-radius: 12px; padding: 14px 10px; text-align: center; margin-bottom: 10px; }
    .tile-title { font-weight: 700; font-size: 1.0rem; }
    .tile-big { font-size: 1.9rem; font-weight: 800; line-height: 1.2; }
    .tile-small { font-size: 0.85rem; opacity: 0.95; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 2. Words: English and Tagalog
# ---------------------------------------------------------------------------
T = {
    "en": {
        "title": "Smart Waste Collection and Scheduling System",
        "subtitle": "Municipality of Bunawan, Agusan del Sur",
        "home": "🏠 Home",
        "schedule": "📅 Schedule Board",
        "report": "📸 Report Missed Collection",
        "track": "🔎 Track Complaint",
        "collector": "🚛 Collector Dashboard",
        "admin": "🛠️ Admin Dashboard",
        "reports": "📊 Reports and Print",
        "health": "🗺️ Barangay Health and Heat Grid",
        "barangay": "Barangay",
        "street": "Street / Purok",
        "language": "Language / Wika",
        "role": "I am a...",
        "menu": "Menu",
        "announcements": "📢 Announcements",
        "my_barangay": "📍 My Barangay",
        "choose_brgy": "Choose your barangay",
        "next_pickup": "Next pickup",
        "tips": "♻️ Segregation tips",
        "submit_report": "Submit report",
        "track_btn": "Track",
        "logout": "Log out",
    },
    "tl": {
        "title": "Matalinong Sistema ng Koleksyon at Iskedyul ng Basura",
        "subtitle": "Bayan ng Bunawan, Agusan del Sur",
        "home": "🏠 Tahanan",
        "schedule": "📅 Iskedyul",
        "report": "📸 Mag-ulat ng Hindi Nakolekta",
        "track": "🔎 Subaybayan ang Reklamo",
        "collector": "🚛 Dashboard ng Kolektor",
        "admin": "🛠️ Dashboard ng Admin",
        "reports": "📊 Mga Ulat at Print",
        "health": "🗺️ Kalagayan ng mga Barangay",
        "barangay": "Barangay",
        "street": "Kalye / Purok",
        "language": "Language / Wika",
        "role": "Ako ay...",
        "menu": "Menu",
        "announcements": "📢 Mga Anunsyo",
        "my_barangay": "📍 Aking Barangay",
        "choose_brgy": "Piliin ang iyong barangay",
        "next_pickup": "Susunod na koleksyon",
        "tips": "♻️ Mga tip sa pagsasaayos ng basura",
        "submit_report": "Ipadala ang ulat",
        "track_btn": "Hanapin",
        "logout": "Mag-log out",
    },
}

TIPS = {
    "Biodegradable": ("🍃", "Food scraps, leaves, and peelings. Put them in a green bin or compost pit."),
    "Non-biodegradable": ("🛍️", "Plastic wrappers, styrofoam, and diapers. Tie them in a bag before pickup."),
    "Recyclable": ("♻️", "Clean bottles, cans, paper, and cardboard. Rinse and keep them dry."),
    "Special": ("⚠️", "Batteries, bulbs, old electronics, and sharp items. Wrap them safely and tell the collector."),
}

STATUS_ICON = {"Pending": "🟡", "In Progress": "🔵", "Resolved": "🟢"}


CURRENT = {"lang": "en"}
# Remember the chosen language at the start of every run.
CURRENT["lang"] = st.session_state.get("lang", "en")


def t(key):
    """Get a word in the chosen language (falls back to English)."""
    return T.get(CURRENT["lang"], T["en"]).get(key, T["en"].get(key, key))


# ---------------------------------------------------------------------------
# 3. Small helpers
# ---------------------------------------------------------------------------
def flash(message):
    """Save a message to show after the page reloads."""
    st.session_state["flash"] = message


def show_flash():
    msg = st.session_state.pop("flash", None)
    if msg:
        st.success(msg)


def goto(page):
    """Used by buttons that jump to another page."""
    st.session_state[f"page_{st.session_state.get('role', 'Resident')}"] = page


def tile(title, big, small, color, text="white"):
    return (f'<div class="tile" style="background:{color};color:{text}">'
            f'<div class="tile-title">{title}</div><div class="tile-big">{big}</div>'
            f'<div class="tile-small">{small}</div></div>')


def show_photo(photo_name, caption="Evidence photo"):
    path = db.photo_path(photo_name)
    if path:
        st.image(path, caption=caption, width=320)


def countdown_text(when):
    delta = when - db.now_ph()
    mins = int(delta.total_seconds() // 60)
    days, rest = divmod(mins, 1440)
    hours, minutes = divmod(rest, 60)
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if not days and minutes:
        parts.append(f"{minutes} min")
    return "in " + " ".join(parts) if parts else "very soon"


def rate_color(rate):
    """Green / yellow / red for the Barangay Health Score."""
    if rate is None:
        return GRAY, "white"
    if rate >= 0.90:
        return GREEN, "white"
    if rate >= 0.75:
        return YELLOW, "#222"
    return RED, "white"


# ---------------------------------------------------------------------------
# 4. Pages
# ---------------------------------------------------------------------------
def page_home():
    st.title(t("title"))
    st.caption(t("subtitle"))

    # Red banner if a stop was missed today (auto-flag feature)
    flagged = db.flagged_today()
    if flagged:
        st.error("🚩 Missed collection today in: " + ", ".join(sorted(flagged)) + ". A complaint was created automatically.")

    # Announcements
    st.subheader(t("announcements"))
    notes = db.announcements(limit=5)
    if not notes:
        st.info("No announcements right now.")
    for n in notes:
        text = f"**{n['title']}** - {n['body']}  \n*{n['created']}*"
        (st.warning if n["kind"] == "warning" else st.info)(text)

    # My Barangay card
    st.subheader(t("my_barangay"))
    saved = st.query_params.get("brgy")
    options = db.BARANGAYS
    index = options.index(saved) if saved in options else None

    def save_choice():
        choice = st.session_state.get("my_brgy")
        if choice:
            st.query_params["brgy"] = choice  # remembered in the web address

    mine = st.selectbox(t("choose_brgy"), options, index=index, key="my_brgy",
                        placeholder=t("choose_brgy"), on_change=save_choice)
    if mine:
        found = db.next_pickup(mine)
        if found:
            sched, when = found
            area = "all areas" if sched["area"] == db.ALL_AREAS else sched["area"]
            c1, c2 = st.columns(2)
            c1.metric(t("next_pickup"), when.strftime("%a, %b %d - %I:%M %p"))
            c2.metric("Countdown", countdown_text(when))
            st.write(f"**{sched['waste_type']}** pickup for {area}.")
        else:
            st.info("No pickup is scheduled for this barangay yet.")
    else:
        st.info("Pick your barangay to see your next garbage pickup.")

    # Quick buttons
    st.subheader("Quick actions")
    c1, c2, c3 = st.columns(3)
    c1.button(t("schedule"), key="q_sched", on_click=goto, args=("schedule",))
    c2.button(t("report"), key="q_report", on_click=goto, args=("report",))
    c3.button(t("track"), key="q_track", on_click=goto, args=("track",))

    with st.expander(t("tips")):
        for waste, (icon, text) in TIPS.items():
            st.markdown(f"{icon} **{waste}**: {text}")


def page_schedule():
    st.header(t("schedule"))
    ALL = "All"
    c1, c2 = st.columns(2)
    brgy = c1.selectbox(t("barangay"), [ALL] + db.BARANGAYS, key="sch_brgy")
    area_options = [db.ALL_AREAS] + (db.areas_for(brgy) if brgy != ALL else [])
    area = c2.selectbox(t("street"), area_options, key="sch_area", disabled=(brgy == ALL))
    c3, c4 = st.columns(2)
    waste = c3.selectbox("Waste type", [ALL] + db.WASTE_TYPES, key="sch_waste")
    when = c4.radio("Show", ["This week", "Today"], horizontal=True, key="sch_when")

    today_name = db.DAYS[db.today_ph().weekday()]
    data = db.schedules(
        barangay=None if brgy == ALL else brgy,
        area=None if brgy == ALL else area,
        waste=None if waste == ALL else waste,
        day=today_name if when == "Today" else None,
    )
    if data.empty:
        st.info("No schedules match your choices. Try another barangay or waste type.")
    else:
        today_idx = db.today_ph().weekday()
        data["order"] = data["day"].map(lambda d: (db.DAYS.index(d) - today_idx) % 7)
        data = data.sort_values(["order", "time"])
        show = data[["day", "time", "barangay", "area", "waste_type", "collector"]].rename(columns={
            "day": "Day", "time": "Time", "barangay": "Barangay", "area": "Street / Purok",
            "waste_type": "Waste type", "collector": "Collector"})
        st.caption(f"{len(show)} schedule(s) found. Today is {today_name}.")
        st.dataframe(show, hide_index=True)

    with st.expander(t("tips")):
        for w, (icon, text) in TIPS.items():
            st.markdown(f"{icon} **{w}**: {text}")


def page_report():
    st.header(t("report"))
    n = st.session_state.get("rep_n", 0)  # changes after a report is sent, so the form is empty again

    # Success message from the last report
    last = st.session_state.get("last_tracking")
    if last:
        st.success(f"✅ Report sent! Your tracking number is **{last}**. Please save it.")
        st.code(last, language=None)
        c1, c2 = st.columns(2)
        c1.button("Track this complaint", key="rep_goto_track", on_click=_track_last)
        c2.button("Close this message", key="rep_close", on_click=lambda: st.session_state.pop("last_tracking", None))

    st.write("Tell us where the garbage was not collected. A photo helps the team act faster.")

    # These two are OUTSIDE the form so the street list updates right away
    brgy = st.selectbox(t("barangay"), db.BARANGAYS, index=None, key=f"rep_brgy_{n}",
                        placeholder=t("choose_brgy"))
    areas = db.areas_for(brgy) if brgy else []
    area = st.selectbox(t("street"), areas, index=None, key=f"rep_area_{n}", disabled=not brgy,
                        placeholder="Choose your street or purok")

    with st.form(f"report_form_{n}"):
        name = st.text_input("Your name", key=f"rep_name_{n}")
        missed_date = st.date_input("Date it was missed", value=db.today_ph(), max_value=db.today_ph(),
                                    key=f"rep_date_{n}")
        waste = st.selectbox("Waste type", db.WASTE_TYPES, key=f"rep_waste_{n}")
        desc = st.text_area("What happened?", key=f"rep_desc_{n}",
                            placeholder="Example: The truck did not stop at our purok.")

        st.markdown("**📸 Evidence photo of the garbage** (optional, but it really helps)")
        tab_cam, tab_up = st.tabs(["📷 Take a photo", "🖼️ Upload a photo"])
        with tab_cam:
            shot = st.camera_input("Take a picture of the garbage", key=f"rep_cam_{n}")
        with tab_up:
            upload = st.file_uploader("Choose a picture from your phone or computer",
                                      type=["jpg", "jpeg", "png"], key=f"rep_up_{n}")
        send = st.form_submit_button(t("submit_report"), type="primary")

    if send:
        problems = []
        if not name.strip():
            problems.append("Please enter your name.")
        if not brgy:
            problems.append("Please choose your barangay.")
        elif not area:
            problems.append("Please choose your street or purok.")
        if not desc.strip():
            problems.append("Please tell us what happened.")
        if problems:
            for p in problems:
                st.error(p)
            return

        photo_file = shot or upload  # camera photo first, else the uploaded file
        photo_bytes = photo_file.getvalue() if photo_file else None
        tracking = db.add_complaint(name.strip(), brgy, area, missed_date, waste, desc.strip(),
                                    photo_bytes=photo_bytes)
        if photo_bytes and not db.get_complaint(tracking)["photo"]:
            st.warning("Your report was saved, but the photo could not be read. Please try another picture.")
        st.session_state["last_tracking"] = tracking
        st.session_state["rep_n"] = n + 1
        st.rerun()


def _track_last():
    """Button action: go to the Track page with the last tracking number."""
    st.session_state["tracked_code"] = st.session_state.get("last_tracking", "")
    st.session_state["track_code"] = st.session_state.get("last_tracking", "")
    goto("track")


def page_track():
    st.header(t("track"))
    with st.form("track_form"):
        code = st.text_input("Tracking number", key="track_code", placeholder="Example: BUN-0001")
        go = st.form_submit_button(t("track_btn"), type="primary")
    if go:
        st.session_state["tracked_code"] = code.strip()

    code = st.session_state.get("tracked_code", "")
    if not code:
        st.info("Type your tracking number above. You got it when you sent your report.")
        return
    c = db.get_complaint(code)
    if not c:
        st.error(f"We could not find '{code}'. Please check the number and try again.")
        return

    st.subheader(f"{STATUS_ICON.get(c['status'], '')} {c['tracking']} - {c['status']}")
    st.write(f"**Where:** {c['barangay']}, {c['area']}  \n**Waste type:** {c['waste_type']}  \n"
             f"**Date missed:** {c['date_missed']}  \n**Details:** {c['description']}")
    show_photo(c["photo"])
    st.markdown("#### Timeline")
    for step in db.timeline(c["id"]):
        st.markdown(f"{STATUS_ICON.get(step['status'], '•')} **{step['status']}** - {step['note']}  \n"
                    f"<small>{step['created']}</small>", unsafe_allow_html=True)


def _collect_ok(sid, day, cid):
    db.mark_collected(sid, day, cid)


def _open_miss(sid):
    st.session_state[f"missopen_{sid}"] = True


def _close_miss(sid):
    st.session_state[f"missopen_{sid}"] = False


def _confirm_miss(sid, day, cid):
    reason = st.session_state.get(f"reason_{sid}", "Other")
    note = st.session_state.get(f"note_{sid}", "").strip()
    text = f"{reason}: {note}" if note else reason
    db.mark_missed(sid, day, cid, text)
    st.session_state[f"missopen_{sid}"] = False


def page_collector():
    cid = st.session_state["collector_id"]
    me = next((c for c in db.collectors() if c["id"] == cid), None)
    st.header(t("collector"))
    st.write(f"Hello, **{me['name']}**!")
    the_date = st.date_input("Date", value=db.today_ph(), key="col_date")
    day = the_date.isoformat()
    stops = db.stops_for(cid, the_date)
    st.caption(f"{db.DAYS[the_date.weekday()]} - {len(stops)} stop(s)")

    if not stops:
        st.info("No stops for this date. Enjoy your day off, or pick another date.")
        return

    done = len([s for s in stops if s["log_status"]])
    st.progress(done / len(stops), text=f"{done} of {len(stops)} stops done")

    for s in stops:
        sid = s["id"]
        area = "All areas" if s["area"] == db.ALL_AREAS else s["area"]
        with st.container(border=True):
            st.markdown(f"**{s['time']} - {s['barangay']}** ({area})  \n{s['waste_type']}")
            if s["log_status"] is None:
                b1, b2 = st.columns(2)
                b1.button("✅ Collected", key=f"ok_{sid}", on_click=_collect_ok, args=(sid, day, cid))
                b2.button("❌ Missed", key=f"miss_{sid}", on_click=_open_miss, args=(sid,))
                if st.session_state.get(f"missopen_{sid}"):
                    st.selectbox("Why was it missed?",
                                 ["Truck breakdown", "Road blocked", "Bad weather", "Garbage not out", "Other"],
                                 key=f"reason_{sid}")
                    st.text_input("Extra note (optional)", key=f"note_{sid}")
                    c1, c2 = st.columns(2)
                    c1.button("Confirm missed", key=f"confirm_{sid}", type="primary",
                              on_click=_confirm_miss, args=(sid, day, cid))
                    c2.button("Cancel", key=f"cancel_{sid}", on_click=_close_miss, args=(sid,))
            else:
                icon = "✅" if s["log_status"] == "Collected" else "❌"
                extra = f" - {s['log_reason']}" if s["log_reason"] else ""
                st.markdown(f"{icon} **{s['log_status']}**{extra}")
                if s["log_status"] == "Missed":
                    st.caption("A complaint was created automatically for this stop.")
                st.button("Undo", key=f"undo_{sid}", on_click=db.undo_log, args=(sid, day))


def page_health():
    st.header(t("health"))
    scores = db.health_scores()
    counts = db.complaint_counts()
    flagged = db.flagged_today()

    st.subheader("Barangay Health Score (last 30 days)")
    st.caption("🟢 90% or more on time   🟡 75% to 89%   🔴 below 75%   ⚪ no data")
    cols = st.columns(5)
    for i, b in enumerate(db.BARANGAYS):
        s = scores.get(b)
        rate = s["rate"] if s else None
        color, text = rate_color(rate)
        big = "-" if rate is None else f"{rate * 100:.0f}%"
        small = "No data" if not s else f"{s['done']} collected, {s['missed']} missed"
        with cols[i % 5]:
            st.markdown(tile(b, big, small, color, text), unsafe_allow_html=True)

    st.subheader("Missed-collection Heat Grid")
    st.caption("Darker red means more complaints. 🚩 means a stop was missed today.")
    cols = st.columns(5)
    for i, b in enumerate(db.BARANGAYS):
        n = counts.get(b, 0)
        if b in flagged or n >= 3:
            color, text = RED, "white"
        elif n >= 1:
            color, text = YELLOW, "#222"
        else:
            color, text = GREEN, "white"
        small = "🚩 Missed today" if b in flagged else "complaint(s)"
        with cols[i % 5]:
            st.markdown(tile(b, n, small, color, text), unsafe_allow_html=True)


# ----- Admin pages ---------------------------------------------------------
def collector_label(cid):
    for c in db.collectors():
        if c["id"] == cid:
            return c["name"]
    return "Not assigned"


def admin_schedules():
    data = db.schedules()
    show = data[["barangay", "area", "waste_type", "day", "time", "collector"]].rename(columns={
        "barangay": "Barangay", "area": "Street / Purok", "waste_type": "Waste type", "day": "Day",
        "time": "Time", "collector": "Collector"})
    st.dataframe(show, hide_index=True)

    collector_ids = [None] + [c["id"] for c in db.collectors()]

    st.subheader("Add a schedule")
    b = st.selectbox(t("barangay"), db.BARANGAYS, key="add_s_b")
    a = st.selectbox(t("street"), [db.ALL_AREAS] + db.areas_for(b), key="add_s_a")
    with st.form("add_schedule", clear_on_submit=True):
        w = st.selectbox("Waste type", db.WASTE_TYPES)
        d = st.selectbox("Day", db.DAYS)
        tm = st.time_input("Time", value=dtime(7, 0))
        col = st.selectbox("Collector", collector_ids, format_func=collector_label)
        ok = st.form_submit_button("Add schedule", type="primary")
    if ok:
        db.add_schedule(b, a, w, d, tm.strftime("%H:%M"), col)
        flash("Schedule added.")
        st.rerun()

    st.subheader("Edit or delete a schedule")
    if data.empty:
        st.info("There are no schedules yet.")
        return
    labels = {int(r.id): f"#{r.id} - {r.barangay} | {r.area} | {r.waste_type} | {r.day} {r.time}"
              for r in data.itertuples()}
    sid = st.selectbox("Choose a schedule", list(labels), format_func=labels.get, key="edit_sid")
    row = data[data["id"] == sid].iloc[0]
    st.caption("To move a schedule to another barangay, delete it and add a new one.")
    area_options = [db.ALL_AREAS] + db.areas_for(row["barangay"])
    if row["area"] not in area_options:
        area_options.append(row["area"])
    hh, mm = (int(x) for x in row["time"].split(":"))
    current_col = None if pd.isna(row["collector_id"]) else int(row["collector_id"])
    with st.form(f"edit_form_{sid}"):
        e_area = st.selectbox(t("street"), area_options, index=area_options.index(row["area"]))
        e_waste = st.selectbox("Waste type", db.WASTE_TYPES, index=db.WASTE_TYPES.index(row["waste_type"]))
        e_day = st.selectbox("Day", db.DAYS, index=db.DAYS.index(row["day"]))
        e_time = st.time_input("Time", value=dtime(hh, mm))
        e_col = st.selectbox("Collector", collector_ids, index=collector_ids.index(current_col)
                             if current_col in collector_ids else 0, format_func=collector_label)
        save = st.form_submit_button("Save changes", type="primary")
    if save:
        db.update_schedule(sid, e_area, e_waste, e_day, e_time.strftime("%H:%M"), e_col)
        flash("Schedule updated.")
        st.rerun()

    sure = st.checkbox("Yes, I want to delete this schedule", key=f"del_ok_{sid}")
    if st.button("🗑️ Delete schedule", key=f"del_btn_{sid}", disabled=not sure):
        db.delete_schedule(sid)
        flash("Schedule deleted.")
        st.rerun()


def admin_complaints():
    status = st.radio("Show", ["All"] + db.STATUSES, horizontal=True, key="adm_cstatus")
    data = db.complaints_df(status)
    st.dataframe(data, hide_index=True)
    if data.empty:
        st.info("No complaints with this status.")
        return
    code = st.selectbox("Choose a complaint to update", data["tracking"].tolist(), key="adm_ctrack")
    c = db.get_complaint(code)
    st.markdown(f"**{c['tracking']}** - {c['barangay']}, {c['area']} - {c['waste_type']}  \n"
                f"{c['description']}  \n*Reported by {c['name']} on {c['created']}*")
    show_photo(c["photo"])
    with st.form(f"cupdate_{c['id']}"):
        new_status = st.selectbox("New status", db.STATUSES, index=db.STATUSES.index(c["status"]))
        note = st.text_area("Reply note (the resident will see this)")
        ok = st.form_submit_button("Save update", type="primary")
    if ok:
        db.update_complaint(c["id"], new_status, note)
        flash(f"{c['tracking']} is now {new_status}.")
        st.rerun()


def admin_areas():
    b = st.selectbox(t("barangay"), db.BARANGAYS, key="area_b")
    areas = db.areas_for(b)
    st.write(f"**{len(areas)} areas** in {b}: " + (", ".join(areas) if areas else "none yet"))
    st.caption("Tip: replace the sample Purok names with the real street names from the barangay hall.")

    with st.form("add_area", clear_on_submit=True):
        new = st.text_input("New street / purok name")
        ok = st.form_submit_button("Add area", type="primary")
    if ok:
        if not new.strip():
            st.error("Please type a name first.")
        elif db.add_area(b, new):
            flash(f"Added '{new.strip()}' to {b}.")
            st.rerun()
        else:
            st.error("That name already exists in this barangay.")

    if areas:
        st.markdown("##### Rename")
        old = st.selectbox("Area to rename", areas, key="ren_old")
        with st.form("rename_area", clear_on_submit=True):
            newname = st.text_input("New name")
            ren = st.form_submit_button("Rename")
        if ren:
            if not newname.strip():
                st.error("Please type the new name.")
            elif db.rename_area(b, old, newname):
                flash(f"Renamed '{old}' to '{newname.strip()}'.")
                st.rerun()
            else:
                st.error("That name already exists in this barangay.")

        st.markdown("##### Delete")
        target = st.selectbox("Area to delete", areas, key="del_area")
        sure = st.checkbox("Yes, delete this area", key=f"del_area_ok_{b}_{target}")
        if st.button("🗑️ Delete area", key="del_area_btn", disabled=not sure):
            db.delete_area(b, target)
            flash(f"Deleted '{target}'. Its schedules now cover the whole barangay.")
            st.rerun()


def admin_collectors():
    people = db.collectors()
    if people:
        st.dataframe(pd.DataFrame(people)[["name", "pin"]].rename(columns={"name": "Name", "pin": "PIN"}),
                     hide_index=True)
    with st.form("add_collector", clear_on_submit=True):
        name = st.text_input("Collector name")
        pin = st.text_input("PIN (numbers)", max_chars=8)
        ok = st.form_submit_button("Add collector", type="primary")
    if ok:
        if not name.strip() or not pin.strip():
            st.error("Please enter both a name and a PIN.")
        else:
            db.add_collector(name, pin)
            flash(f"Collector '{name.strip()}' added.")
            st.rerun()
    if people:
        who = st.selectbox("Remove a collector", [p["id"] for p in people],
                           format_func=collector_label, key="del_col")
        sure = st.checkbox("Yes, remove this collector", key=f"del_col_ok_{who}")
        if st.button("🗑️ Remove collector", key="del_col_btn", disabled=not sure):
            db.delete_collector(who)
            flash("Collector removed. Their schedules are now unassigned.")
            st.rerun()


def admin_announcements():
    with st.form("add_note", clear_on_submit=True):
        title = st.text_input("Title")
        body = st.text_area("Message")
        kind = st.radio("Type", ["info", "warning"], horizontal=True,
                        format_func=lambda k: "ℹ️ Notice" if k == "info" else "⚠️ Warning")
        ok = st.form_submit_button("Post announcement", type="primary")
    if ok:
        if not title.strip() or not body.strip():
            st.error("Please fill in the title and the message.")
        else:
            db.add_announcement(title, body, kind)
            flash("Announcement posted.")
            st.rerun()
    for n in db.announcements():
        with st.container(border=True):
            st.markdown(f"**{n['title']}** ({n['kind']})  \n{n['body']}  \n*{n['created']}*")
            if st.button("Delete", key=f"del_note_{n['id']}"):
                db.delete_announcement(n["id"])
                flash("Announcement deleted.")
                st.rerun()


def page_admin():
    st.header(t("admin"))
    show_flash()
    tabs = st.tabs(["Schedules", "Complaints", "Areas", "Collectors", "Announcements"])
    with tabs[0]:
        admin_schedules()
    with tabs[1]:
        admin_complaints()
    with tabs[2]:
        admin_areas()
    with tabs[3]:
        admin_collectors()
    with tabs[4]:
        admin_announcements()

    with st.expander("⚠️ Danger zone"):
        st.write("This deletes all your changes and brings back the sample data.")
        sure = st.checkbox("I understand. Reset everything.", key="reset_ok")
        if st.button("Reset sample data", key="reset_btn", disabled=not sure):
            db.reset_db()
            flash("Sample data restored.")
            st.rerun()


def page_reports():
    st.header(t("reports"))
    stats = db.today_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Collected today", stats["done"])
    c2.metric("Missed today", stats["missed"])
    c3.metric("Open complaints", stats["open"])
    c4.metric("All complaints", stats["total"])

    st.subheader("Collection rate per barangay (last 30 days)")
    scores = db.health_scores()
    rates = {b: round(s["rate"] * 100, 1) for b, s in scores.items() if s["rate"] is not None}
    if rates:
        st.bar_chart(pd.DataFrame({"Collection rate (%)": rates}))
    else:
        st.info("No collection records yet.")

    st.subheader("Complaints by status")
    counts = db.complaints_df()["status"].value_counts() if stats["total"] else pd.Series(dtype=int)
    if not counts.empty:
        st.bar_chart(counts)

    # ----- Printable report -----
    st.subheader("🖨️ Printable report")
    st.write("Choose a period. Then print the report, or download it as a PDF. It includes the overall "
             "numbers, barangay table, collectors, complaints, schedule, and evidence photos.")
    choice = st.radio("Report period", ["Last 7 days", "Last 30 days", "All time"], horizontal=True,
                      index=1, key="rep_period")
    days = {"Last 7 days": 7, "Last 30 days": 30, "All time": None}[choice]
    data = rb.collect(days)

    stamp_name = db.today_ph().strftime("%Y%m%d")
    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇️ Download PDF report", rb.build_pdf(data), file_name=f"waste_report_{stamp_name}.pdf",
                       mime="application/pdf", key="dl_pdf")
    d2.download_button("⬇️ Complaints (CSV)", db.complaints_df().to_csv(index=False).encode("utf-8"),
                       file_name=f"complaints_{stamp_name}.csv", mime="text/csv", key="dl_csv_c")
    d3.download_button("⬇️ Collection log (CSV)", db.log_df(days).to_csv(index=False).encode("utf-8"),
                       file_name=f"collection_log_{stamp_name}.csv", mime="text/csv", key="dl_csv_l")

    with st.expander("👁️ Preview and print this report", expanded=False):
        st.caption("Press the green 'Print this report' button inside the preview.")
        components.html(rb.build_html(data), height=800, scrolling=True)


# ---------------------------------------------------------------------------
# 5. Main part: sidebar, login, and page choice
# ---------------------------------------------------------------------------
PAGES = {
    "Resident": ["home", "schedule", "report", "track", "health"],
    "Collector": ["collector", "schedule", "health"],
    "Admin": ["admin", "reports", "schedule", "health"],
}
RENDER = {
    "home": page_home, "schedule": page_schedule, "report": page_report, "track": page_track,
    "collector": page_collector, "admin": page_admin, "reports": page_reports, "health": page_health,
}


def login_collector():
    st.header("🚛 Collector login")
    people = db.collectors()
    if not people:
        st.warning("There are no collectors yet. Ask the Admin to add one.")
        st.stop()
    with st.form("collector_login"):
        who = st.selectbox("Your name", [p["id"] for p in people], format_func=collector_label)
        pin = st.text_input("PIN", type="password")
        ok = st.form_submit_button("Log in", type="primary")
    if ok:
        row = next(p for p in people if p["id"] == who)
        if row["pin"] == pin.strip():
            st.session_state["collector_id"] = who
            st.rerun()
        else:
            st.error("Wrong PIN. Please try again.")
    st.caption("Sample collectors use the PIN 1234.")
    st.stop()


def login_admin():
    st.header("🛠️ Admin login")
    with st.form("admin_login"):
        pin = st.text_input("Admin PIN", type="password")
        ok = st.form_submit_button("Log in", type="primary")
    if ok:
        if pin.strip() == ADMIN_PIN:
            st.session_state["admin_ok"] = True
            st.rerun()
        else:
            st.error("Wrong PIN. Please try again.")
    st.caption("Sample Admin PIN: admin123")
    st.stop()


def logout():
    st.session_state["collector_id"] = None
    st.session_state["admin_ok"] = False


with st.sidebar:
    st.title("♻️ Bunawan Waste")
    st.radio(t("language"), ["en", "tl"], key="lang", horizontal=True,
             format_func=lambda x: "English" if x == "en" else "Tagalog")
    role = st.selectbox(t("role"), ["Resident", "Collector", "Admin"], key="role")

if role == "Collector":
    if not any(c["id"] == st.session_state.get("collector_id") for c in db.collectors()):
        login_collector()
elif role == "Admin":
    if not st.session_state.get("admin_ok"):
        login_admin()

with st.sidebar:
    page = st.radio(t("menu"), PAGES[role], format_func=t, key=f"page_{role}")
    if role != "Resident":
        st.button(t("logout"), key="logout_btn", on_click=logout)
    st.caption("Barangays: " + ", ".join(db.BARANGAYS))

RENDER[page]()
