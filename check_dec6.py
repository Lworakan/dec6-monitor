# Check how many places are left for 6 Dec 2569 (2026) every hour.
# Runs once per call; GitHub Actions calls it every hour (.github/workflows/check.yml).
# Needs repo secrets EMAIL and GMAIL_APP_PASSWORD (https://myaccount.google.com/apppasswords).
import os, re, datetime, smtplib, traceback
from email.message import EmailMessage
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("EMAIL", "")

URL = "https://q.wildlifesanctuaryfca16.com/"
TARGET_MONTH = "ธันวาคม 2569"
TARGET_DAY = "6"
CAPACITY = 100          # the bar shows "100 / เต็ม" when full, so 100 is assumed to be the max


def note(msg):
    with open("status.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def check(page):
    page.goto(URL, wait_until="networkidle")
    # Wizard: ข้อตกลง -> วิธีการลงทะเบียน -> เลือกวัน
    # Each step: tick checkboxes, scroll down, close any "ตกลง" popup, press "ถัดไป"
    page.get_by_text("ถัดไป", exact=True).first.wait_for(timeout=20000)
    for step in range(8):
        note(f"wizard step {step}: " + page.locator("body").inner_text()[-300:].replace("\n", " | "))
        nav = page.get_by_role("button", name="›")
        if nav.count() and nav.first.is_visible():
            break
        boxes = page.locator("input[type=checkbox]")
        for box in boxes.all():
            if not box.is_checked():
                box.check(force=True)
        if not boxes.count() and page.get_by_text("ฉันยอมรับข้อตกลง").count():
            page.get_by_text("ฉันยอมรับข้อตกลง").first.click()
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(500)
        for name in ("ตกลง", "ยอมรับ", "OK"):
            btn = page.get_by_role("button", name=name, exact=True)
            if btn.count() and btn.first.is_visible():
                btn.first.click()
                page.wait_for_timeout(800)
        nxt = page.get_by_text("ถัดไป", exact=True).last
        note(f"  checkboxes={boxes.count()} next_enabled={nxt.is_enabled()}")
        nxt.click()
        page.wait_for_timeout(1500)

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
    msg["Subject"] = subject.splitlines()[0][:150]
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL, os.environ["GMAIL_APP_PASSWORD"])
        s.send_message(msg)


status = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")  # Chrome preinstalled on the GitHub runner
    page = browser.new_page()
    page.set_default_timeout(10000)
    open("status.txt", "w").close()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")
    try:
        result = check(page)
    except Exception as e:
        result = f"error: {e}"
        status.append(traceback.format_exc())
    line = f"[{now}] 6 ธ.ค. 69 -> {result}"
    print(line, flush=True)
    status.insert(0, line)
    try:
        status.append("URL now: " + page.url)
        status.append("PAGE TEXT:\n" + page.locator("body").inner_text()[:3000])
    except Exception:
        status.append("page text unavailable:\n" + traceback.format_exc())

try:
    send_email(f"6 ธ.ค. 69: {result}", line + "\n\n" + URL)
    status.insert(1, "email: sent")
except Exception:
    status.insert(1, "email: FAILED\n" + traceback.format_exc())

# Written for debugging; the workflow pushes it to the "status" branch
with open("status.txt", "a", encoding="utf-8") as f:
    f.write("\n\n".join(status) + "\n")
