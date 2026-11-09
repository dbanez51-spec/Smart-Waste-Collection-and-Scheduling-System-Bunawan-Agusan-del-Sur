# Smart Waste Collection and Scheduling System
Municipality of Bunawan, Agusan del Sur - built with Python and Streamlit.

Residents can see garbage collection schedules, report missed collections with a **photo as evidence**,
and track their complaint. Collectors mark their stops. The Admin manages everything and can
**print or download a full report as a PDF**.

## What is inside

| File | What it does |
|---|---|
| `app.py` | The Streamlit app (all pages and buttons) |
| `database.py` | Saves and reads data (SQLite) |
| `report_builder.py` | Makes the printable report (print view + PDF) |
| `requirements.txt` | Python packages to install |
| `.streamlit/config.toml` | Green theme |
| `.gitignore` | Keeps the database, photos and secrets out of GitHub |

## Run it on your computer

1. Install Python 3.10 or newer.
2. Open a terminal in this folder and run:
   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Your browser opens at http://localhost:8501

The database and sample data are created automatically the first time.

## Sample logins

| Role | How to log in |
|---|---|
| Resident | No login needed |
| Collector | Pick a name, PIN `1234` |
| Admin | PIN `admin123` |

**Change the Admin PIN before using it for real.** In Streamlit Cloud, open *App settings > Secrets* and add:
```
ADMIN_PIN = "your-new-pin"
```
For local use, put the same line in `.streamlit/secrets.toml` (this file is ignored by Git).

## Main features

- **Schedule Board** - filter by barangay, street/purok, waste type, Today / This week
- **Report Missed Collection** - choose barangay and street, then **take a photo with the camera or upload one**
- **Track Complaint** - type the tracking number (like BUN-0001) to see the status timeline and the photo
- **Collector Dashboard** - Collected / Missed buttons. Missed (with a reason) **creates a complaint automatically**
- **Admin Dashboard** - schedules, complaints (reply notes), areas (streets/puroks), collectors, announcements
- **Reports and Print** - charts, **Download PDF**, **Print preview**, CSV downloads
- **Barangay Health Score** and **Heat Grid** - green / yellow / red for all 10 barangays
- **My Barangay** card with next pickup and countdown
- English / Tagalog switch

## Streets and puroks

All 10 barangays are included: Bunawan Brook, Consuelo, Imelda, Libertad, Mambalili, Nueva Era,
Poblacion, San Andres, San Marcos, San Teodoro.

The street names are **placeholders** (Purok 1 to 5, plus "Davao-Agusan National Highway" in a few barangays).
Replace them with the real names: log in as Admin > **Areas** tab > add, rename, or delete.
Renaming updates the schedules and complaints automatically.

## Put it on GitHub and Streamlit Cloud

1. Create a new repository on GitHub and upload all files in this folder.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app**, choose your repository, and set the main file to `app.py`.
4. Click **Deploy**.

## Important note about saved data

Streamlit Community Cloud can erase local files when the app restarts or sleeps.
That means complaints and photos saved in `data/` may disappear. This is fine for a class demo.
The Admin page has a **Reset sample data** button to start fresh. For real use, connect an
online database (for example Supabase or Google Sheets) and store photos in cloud storage.

## Beginner tips

- The code has simple comments in English.
- Each page is one function in `app.py` (`page_home`, `page_schedule`, `page_report`, ...).
- All database work is in `database.py`, so you can find it in one place.
