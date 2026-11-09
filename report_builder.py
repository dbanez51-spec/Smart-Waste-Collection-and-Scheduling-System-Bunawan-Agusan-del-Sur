"""
report_builder.py - builds the printable report.

Two outputs are made from the same data:
  1. build_html(data) -> a page the user can print with the Print button
  2. build_pdf(data)  -> a PDF file the user can download and print

The report includes the overall numbers, the barangay table, collector
performance, complaints, the schedule list and the evidence photos.
"""
import base64
import html
from datetime import timedelta
from io import BytesIO

import database as db

MAX_PHOTOS = 12  # how many evidence photos to put in the report


def collect(days):
    """
    Gather all report numbers. days = 7, 30 or None (None means all time).
    Returns one dictionary that both build_html and build_pdf use.
    """
    today = db.today_ph()
    since = (today - timedelta(days=days)).isoformat() if days else None
    period = f"Last {days} days" if days else "All time"

    # Collection log numbers per barangay
    scores = db.health_scores(days or 3650)
    complaints = db.complaints_since(since)

    by_brgy = {}
    for b in db.BARANGAYS:
        s = scores.get(b, {"done": 0, "missed": 0, "rate": None})
        mine = [c for c in complaints if c["barangay"] == b]
        by_brgy[b] = {
            "done": s["done"],
            "missed": s["missed"],
            "rate": s["rate"],
            "complaints": len(mine),
            "open": len([c for c in mine if c["status"] != "Resolved"]),
        }

    total_done = sum(v["done"] for v in by_brgy.values())
    total_missed = sum(v["missed"] for v in by_brgy.values())
    total_stops = total_done + total_missed

    status_counts = {s: len([c for c in complaints if c["status"] == s]) for s in db.STATUSES}
    waste_counts = {w: len([c for c in complaints if c["waste_type"] == w]) for w in db.WASTE_TYPES}

    collectors = []
    for r in db.collector_summary(since):
        total = r["done"] + r["missed"]
        collectors.append({**r, "rate": (r["done"] / total) if total else None})

    photos = []
    for c in complaints:
        path = db.photo_path(c.get("photo"))
        if path:
            photos.append({"tracking": c["tracking"], "barangay": c["barangay"], "area": c["area"],
                           "date": c["date_missed"], "waste": c["waste_type"],
                           "note": c["description"], "path": path})
        if len(photos) >= MAX_PHOTOS:
            break

    return {
        "period": period,
        "generated": db.now_ph().strftime("%B %d, %Y %I:%M %p"),
        "totals": {
            "stops": total_stops,
            "done": total_done,
            "missed": total_missed,
            "rate": (total_done / total_stops) if total_stops else None,
            "complaints": len(complaints),
            "open": len([c for c in complaints if c["status"] != "Resolved"]),
            "resolved": status_counts["Resolved"],
        },
        "by_brgy": by_brgy,
        "status_counts": status_counts,
        "waste_counts": waste_counts,
        "collectors": collectors,
        "complaints": complaints,
        "schedules": db.schedules().to_dict("records"),
        "photos": photos,
    }


def pct(rate):
    return "-" if rate is None else f"{rate * 100:.0f}%"


def esc(value):
    return html.escape(str(value if value is not None else ""))


# ---------------------------------------------------------------------------
# 1) Printable HTML
# ---------------------------------------------------------------------------
def _img_tag(path):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f'<img src="data:image/jpeg;base64,{data}" alt="Evidence photo">'


def build_html(data):
    t = data["totals"]
    rows = ""
    for b, v in data["by_brgy"].items():
        rows += (f"<tr><td>{esc(b)}</td><td>{v['done']}</td><td>{v['missed']}</td>"
                 f"<td>{pct(v['rate'])}</td><td>{v['complaints']}</td><td>{v['open']}</td></tr>")

    col_rows = "".join(
        f"<tr><td>{esc(c['collector'])}</td><td>{c['done']}</td><td>{c['missed']}</td><td>{pct(c['rate'])}</td></tr>"
        for c in data["collectors"]
    ) or '<tr><td colspan="4">No collection records for this period.</td></tr>'

    comp_rows = "".join(
        f"<tr><td>{esc(c['tracking'])}</td><td>{esc(c['date_missed'])}</td><td>{esc(c['barangay'])}</td>"
        f"<td>{esc(c['area'])}</td><td>{esc(c['waste_type'])}</td><td>{esc(c['status'])}</td>"
        f"<td>{'Yes' if c.get('photo') else 'No'}</td></tr>"
        for c in data["complaints"]
    ) or '<tr><td colspan="7">No complaints for this period.</td></tr>'

    sched_rows = "".join(
        f"<tr><td>{esc(s['barangay'])}</td><td>{esc(s['area'])}</td><td>{esc(s['waste_type'])}</td>"
        f"<td>{esc(s['day'])}</td><td>{esc(s['time'])}</td><td>{esc(s['collector'])}</td></tr>"
        for s in data["schedules"]
    )

    photo_html = "".join(
        f'<div class="photo">{_img_tag(p["path"])}<div class="cap"><b>{esc(p["tracking"])}</b> - '
        f'{esc(p["barangay"])}, {esc(p["area"])}<br>{esc(p["waste"])} - {esc(p["date"])}</div></div>'
        for p in data["photos"]
    ) or "<p>No evidence photos for this period.</p>"

    status_txt = " | ".join(f"{k}: {v}" for k, v in data["status_counts"].items())
    waste_txt = " | ".join(f"{k}: {v}" for k, v in data["waste_counts"].items())

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Waste Collection Report</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; color:#111; margin:0; padding:16px; background:#fff; font-size:14px; }}
  h1 {{ color:#0b6b4f; margin:0 0 4px; font-size:22px; }}
  h2 {{ color:#0b6b4f; border-bottom:2px solid #0f9d7a; padding-bottom:4px; margin-top:26px; font-size:17px; }}
  .sub {{ color:#444; margin-bottom:14px; }}
  .cards {{ display:flex; flex-wrap:wrap; gap:10px; }}
  .card {{ flex:1 1 130px; border:1px solid #bfe3d6; background:#eefaf5; border-radius:8px; padding:10px; text-align:center; }}
  .card .n {{ font-size:24px; font-weight:bold; color:#0b6b4f; }}
  table {{ border-collapse:collapse; width:100%; margin-top:8px; }}
  th, td {{ border:1px solid #c9d6d1; padding:6px 8px; text-align:left; font-size:13px; }}
  th {{ background:#0f9d7a; color:#fff; }}
  tr:nth-child(even) td {{ background:#f5faf8; }}
  .photos {{ display:flex; flex-wrap:wrap; gap:12px; }}
  .photo {{ width:210px; border:1px solid #c9d6d1; border-radius:6px; padding:6px; page-break-inside:avoid; }}
  .photo img {{ width:100%; border-radius:4px; }}
  .cap {{ font-size:12px; margin-top:4px; }}
  .btn {{ background:#0f9d7a; color:#fff; border:0; border-radius:8px; padding:12px 22px; font-size:16px; cursor:pointer; margin-bottom:14px; }}
  .sign {{ display:flex; gap:40px; margin-top:50px; }}
  .sign div {{ flex:1; border-top:1px solid #111; padding-top:4px; text-align:center; font-size:12px; }}
  @media print {{ .btn {{ display:none; }} body {{ padding:0; }} h2 {{ page-break-after:avoid; }} }}
</style></head><body>
<button class="btn" onclick="window.print()">Print this report</button>
<h1>Smart Waste Collection and Scheduling System</h1>
<div class="sub">Municipality of Bunawan, Agusan del Sur<br>
Report period: <b>{esc(data['period'])}</b> &nbsp;|&nbsp; Generated: {esc(data['generated'])}</div>

<h2>1. Overall summary</h2>
<div class="cards">
  <div class="card"><div class="n">{t['stops']}</div>Scheduled stops</div>
  <div class="card"><div class="n">{t['done']}</div>Collected</div>
  <div class="card"><div class="n">{t['missed']}</div>Missed</div>
  <div class="card"><div class="n">{pct(t['rate'])}</div>Collection rate</div>
  <div class="card"><div class="n">{t['complaints']}</div>Complaints</div>
  <div class="card"><div class="n">{t['open']}</div>Open complaints</div>
</div>
<p>Complaint status - {esc(status_txt)}<br>Complaints by waste type - {esc(waste_txt)}</p>

<h2>2. Barangay performance</h2>
<table><tr><th>Barangay</th><th>Collected</th><th>Missed</th><th>Rate</th><th>Complaints</th><th>Open</th></tr>{rows}</table>

<h2>3. Collector performance</h2>
<table><tr><th>Collector</th><th>Collected</th><th>Missed</th><th>Rate</th></tr>{col_rows}</table>

<h2>4. Complaints</h2>
<table><tr><th>Tracking</th><th>Date missed</th><th>Barangay</th><th>Area</th><th>Waste</th><th>Status</th><th>Photo</th></tr>{comp_rows}</table>

<h2>5. Collection schedule</h2>
<table><tr><th>Barangay</th><th>Area</th><th>Waste type</th><th>Day</th><th>Time</th><th>Collector</th></tr>{sched_rows}</table>

<h2>6. Evidence photos</h2>
<div class="photos">{photo_html}</div>

<div class="sign"><div>Prepared by</div><div>Checked by</div><div>Approved by</div></div>
</body></html>"""


# ---------------------------------------------------------------------------
# 2) PDF file
# ---------------------------------------------------------------------------
def build_pdf(data):
    """Build the same report as a PDF and return the bytes."""
    from PIL import Image as PILImage
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    GREEN = colors.HexColor("#0f9d7a")
    DARK = colors.HexColor("#0b6b4f")
    LIGHT = colors.HexColor("#eefaf5")

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=DARK, fontSize=18, alignment=0, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=DARK, fontSize=13, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9.5, leading=12)
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8.5, leading=10)

    def P(text, style=cell):
        return Paragraph(esc(text), style)

    def table(header, rows, widths=None):
        head = [Paragraph(f"<b>{esc(h)}</b>", ParagraphStyle("th", parent=cell, textColor=colors.white)) for h in header]
        body_rows = [[c if not isinstance(c, (str, int, float)) else P(c) for c in r] for r in rows]
        t = Table([head] + body_rows, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d6d1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5faf8")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1.6 * cm, 1.0 * cm, "Smart Waste Collection and Scheduling System - Bunawan, Agusan del Sur")
        canvas.drawRightString(A4[0] - 1.6 * cm, 1.0 * cm, f"Page {doc.page}")
        canvas.restoreState()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.7 * cm,
                            title="Waste Collection Report", author="Smart Waste System")
    story = []
    t = data["totals"]

    story.append(Paragraph("Smart Waste Collection and Scheduling System", h1))
    story.append(Paragraph(
        f"Municipality of Bunawan, Agusan del Sur<br/>Report period: <b>{esc(data['period'])}</b> &nbsp;|&nbsp; "
        f"Generated: {esc(data['generated'])}", body))

    # 1. Summary cards (as one table row)
    story.append(Paragraph("1. Overall summary", h2))
    card_style = ParagraphStyle("card", parent=body, alignment=1, fontSize=9)
    def card(num, label):
        return Paragraph(f"<font size=16 color='#0b6b4f'><b>{esc(num)}</b></font><br/>{esc(label)}", card_style)
    cards = Table([[card(t["stops"], "Scheduled stops"), card(t["done"], "Collected"), card(t["missed"], "Missed"),
                    card(pct(t["rate"]), "Collection rate"), card(t["complaints"], "Complaints"),
                    card(t["open"], "Open complaints")]], hAlign="LEFT")
    cards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfe3d6")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfe3d6")),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(cards)
    story.append(Spacer(1, 6))
    story.append(Paragraph("Complaint status - " + esc(" | ".join(f"{k}: {v}" for k, v in data["status_counts"].items())), body))
    story.append(Paragraph("Complaints by waste type - " + esc(" | ".join(f"{k}: {v}" for k, v in data["waste_counts"].items())), body))

    # 2. Barangay table
    story.append(Paragraph("2. Barangay performance", h2))
    story.append(table(
        ["Barangay", "Collected", "Missed", "Rate", "Complaints", "Open"],
        [[b, v["done"], v["missed"], pct(v["rate"]), v["complaints"], v["open"]] for b, v in data["by_brgy"].items()],
    ))

    # 3. Collectors
    story.append(Paragraph("3. Collector performance", h2))
    if data["collectors"]:
        story.append(table(["Collector", "Collected", "Missed", "Rate"],
                           [[c["collector"], c["done"], c["missed"], pct(c["rate"])] for c in data["collectors"]]))
    else:
        story.append(Paragraph("No collection records for this period.", body))

    # 4. Complaints
    story.append(Paragraph("4. Complaints", h2))
    if data["complaints"]:
        story.append(table(
            ["Tracking", "Date missed", "Barangay", "Area", "Waste", "Status", "Photo"],
            [[c["tracking"], c["date_missed"], c["barangay"], c["area"], c["waste_type"], c["status"],
              "Yes" if c.get("photo") else "No"] for c in data["complaints"]],
            widths=[1.9 * cm, 2.1 * cm, 2.7 * cm, 3.4 * cm, 3.2 * cm, 2.0 * cm, 1.3 * cm],
        ))
    else:
        story.append(Paragraph("No complaints for this period.", body))

    # 5. Schedule
    story.append(Paragraph("5. Collection schedule", h2))
    story.append(table(
        ["Barangay", "Area", "Waste type", "Day", "Time", "Collector"],
        [[s["barangay"], s["area"], s["waste_type"], s["day"], s["time"], s["collector"]] for s in data["schedules"]],
    ))

    # 6. Evidence photos (2 per row)
    story.append(Paragraph("6. Evidence photos", h2))
    if data["photos"]:
        cells = []
        for p in data["photos"]:
            with PILImage.open(p["path"]) as im:
                w, h = im.size
            height = min(6.4 * cm * h / w, 5.2 * cm)   # keep photos small so the page is not too long
            img = Image(p["path"], width=height * w / h, height=height)
            caption = Paragraph(
                f"<b>{esc(p['tracking'])}</b> - {esc(p['barangay'])}, {esc(p['area'])}<br/>"
                f"{esc(p['waste'])} - {esc(p['date'])}", cell)
            cells.append([img, caption])
        grid = []
        for i in range(0, len(cells), 2):
            row = cells[i:i + 2]
            if len(row) == 1:
                row.append(["", ""])
            grid.append([Table([[row[0][0]], [row[0][1]]]), Table([[row[1][0]], [row[1][1]]])])
        story.append(Table(grid, colWidths=[8.6 * cm, 8.6 * cm]))
    else:
        story.append(Paragraph("No evidence photos for this period.", body))

    # Signature lines
    story.append(Spacer(1, 24))
    sign = Table([["______________________", "______________________", "______________________"],
                  ["Prepared by", "Checked by", "Approved by"]])
    sign.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(sign)

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
