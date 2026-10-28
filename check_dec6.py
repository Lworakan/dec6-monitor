# Watch 6 Dec 2569 (2026) for free places, using the same API the booking page calls.
# Each GitHub Actions run (started hourly by a push to the tick branch) checks every 5 minutes
# for ~55 minutes and emails only when places are free, plus a heartbeat at 08:xx and 20:xx.
# Needs repo secrets EMAIL and GMAIL_APP_PASSWORD (https://myaccount.google.com/apppasswords).
import os, time, datetime, smtplib, traceback
from email.message import EmailMessage
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("EMAIL", "")
URL = "https://q.wildlifesanctuaryfca16.com/"
API = "https://q.wildlifesanctuaryfca16.com/api/v1/bookings/availability?date=2026-12-06"
PEOPLE = 8                      # group size; we need this many free places
INTERVAL = 5 * 60
RUN_FOR = 55 * 60
TH = datetime.timezone(datetime.timedelta(hours=7))
BOOKING_CLOSES = datetime.datetime(2026, 10, 30, 16, 0, tzinfo=TH)


def now():
    return datetime.datetime.now(TH)


def note(msg):
    print(msg, flush=True)
    with open("status.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def send_email(subject, body):
    msg = EmailMessage()
    msg["From"] = msg["To"] = EMAIL
    msg["Subject"] = subject.splitlines()[0][:150]
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL, os.environ["GMAIL_APP_PASSWORD"])
        s.send_message(msg)


def mail(subject, body):
    try:
        send_email(subject, body)
        note("  email sent: " + subject)
    except Exception:
        note("  email FAILED:\n" + traceback.format_exc())


open("status.txt", "w").close()
if now() > BOOKING_CLOSES:
    note(f"[{now():%Y-%m-%d %H:%M}] booking closed at {BOOKING_CLOSES:%d/%m %H:%M}; not checking")
    raise SystemExit(0)

start = time.monotonic()
last_mailed = None
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")  # Chrome preinstalled on the GitHub runner
    page = browser.new_page()
    try:
        page.goto(URL, wait_until="networkidle")
    except Exception:
        # The API call below works without the page; don't lose the hour over a slow load
        note(f"[{now():%Y-%m-%d %H:%M}] page load failed (continuing):\n" + traceback.format_exc(limit=1))
    first = True
    while True:
        t = now()
        try:
            data = page.request.get(API).json()["data"]
            avail, cap = data["available"], data["capacity"]
            line = f"[{t:%Y-%m-%d %H:%M}] 6 ธ.ค. 69: ว่าง {avail}/{cap}"
            note(line)
            if avail > 0 and avail != last_mailed:
                enough = "พอสำหรับ 8 คน! รีบจอง" if avail >= PEOPLE else f"ยังไม่พอ {PEOPLE} คน"
                mail(f"6 ธ.ค. 69 ว่าง {avail} ที่ ({enough})", line + "\n\nจองที่ " + URL)
                last_mailed = avail
            elif first and t.hour in (8, 20):
                mail(f"6 ธ.ค. 69: ยังเต็ม (บอทยังทำงานอยู่)", line)
        except Exception:
            note(f"[{t:%Y-%m-%d %H:%M}] error:\n" + traceback.format_exc())
        first = False
        if time.monotonic() - start + INTERVAL > RUN_FOR or now() > BOOKING_CLOSES:
            break
        time.sleep(INTERVAL)
