# Check how many places are left for 6 Dec 2569 (2026) every 15 minutes.
# Runs once per call; GitHub Actions calls it every 15 minutes (.github/workflows/check.yml).
# Needs repo secrets EMAIL and GMAIL_APP_PASSWORD (https://myaccount.google.com/apppasswords).
import os, re, datetime, smtplib
from email.message import EmailMessage
from playwright.sync_api import sync_playwright

EMAIL = os.environ["EMAIL"]

URL = "https://q.wildlifesanctuaryfca16.com/"
TARGET_MONTH = "ธันวาคม 2569"
TARGET_DAY = "6"
CAPACITY = 100          # the bar shows "100 / เต็ม" when full, so 100 is assumed to be the max


def check(page):
    page.goto(URL, wait_until="networkidle")
    page.get_by_text("1. ขอรหัสจองลงทะเบียน").first.click()
    page.wait_for_load_state("networkidle")

    # Click "›" until December 2569 shows
    for _ in range(24):
        if page.get_by_text(TARGET_MONTH).count():
            break
        page.get_by_role("button", name="›").click()
        page.wait_for_timeout(300)

    # Day buttons inside the calendar; use the first "6" (not 6 of next month)
    day = page.locator(".react-calendar__month-view__days button", has_text=re.compile(rf"^{TARGET_DAY}$"))
    if not day.count():
        day = page.get_by_role("button", name=re.compile(rf"^{TARGET_DAY}$"))
    if day.first.is_disabled():
        return "ปิดจอง (กดเลือกวันไม่ได้)"
    day.first.click()
    page.wait_for_timeout(1500)

    # Bar: "จองสิทธิ์แล้ว  <n>  เต็ม/ว่าง"
    text = page.locator("body").inner_text()
    m = re.search(r"จองสิทธิ์แล้ว\s*(\d+)\s*(\S+)", text)
    if not m:
        return "หาแถบจำนวนไม่เจอ: " + text[-300:].replace("\n", " ")
    booked = int(m.group(1))
    return f"จองแล้ว {booked} | ว่าง {CAPACITY - booked} ที่ | สถานะ: {m.group(2)}"


def send_email(subject, body):
    msg = EmailMessage()
    msg["From"] = msg["To"] = EMAIL
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL, os.environ["GMAIL_APP_PASSWORD"])
        s.send_message(msg)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")
    try:
        result = check(page)
    except Exception as e:
        result = f"error: {e}"
    line = f"[{now}] 6 ธ.ค. 69 -> {result}"
    print(line, flush=True)
    send_email(f"6 ธ.ค. 69: {result}", line + "\n\n" + URL)
