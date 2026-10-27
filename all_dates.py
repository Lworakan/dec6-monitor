# One-off: availability for every date of the season via the same API the booking page uses.
import datetime, json
from playwright.sync_api import sync_playwright

API = "https://q.wildlifesanctuaryfca16.com/api/v1/bookings/availability?date={}"
start, end = datetime.date(2026, 11, 16), datetime.date(2027, 2, 13)
TH_DAYS = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]

rows = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page()
    page.goto("https://q.wildlifesanctuaryfca16.com/", wait_until="networkidle")
    d = start
    while d <= end:
        try:
            r = page.request.get(API.format(d.isoformat()))
            data = r.json().get("data") or {}
            rows.append((d, data.get("capacity"), data.get("available"), ""))
        except Exception as e:
            rows.append((d, None, None, f"error {e}"[:80]))
        page.wait_for_timeout(300)  # be gentle with the site
        d += datetime.timedelta(days=1)

with open("all_dates.txt", "w", encoding="utf-8") as f:
    for d, cap, avail, err in rows:
        f.write(f"{d} {TH_DAYS[d.weekday()]} capacity={cap} available={avail} {err}\n")
