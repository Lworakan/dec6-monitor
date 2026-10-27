# One-off: record what data the booking page loads behind the scenes (like DevTools > Network),
# to see how the site decides a day is "เต็ม" and whether it exposes a paid/unpaid split.
# Only structure, numbers and enum-like values are kept; free-text strings (names etc.) are
# redacted, because the output goes to a public branch.
import json, re
from collections import defaultdict
from playwright.sync_api import sync_playwright

# Reuse check() and its helpers without running the hourly email part
exec(open("check_dec6.py", encoding="utf-8").read().split("\nstatus = []")[0])

out = []
js_snippets = []


def shape(v, depth=0):
    """Summarise JSON: keys, numbers, booleans; strings only when enum-like."""
    if depth > 6:
        return "…"
    if isinstance(v, dict):
        return {k: shape(x, depth + 1) for k, x in v.items()}
    if isinstance(v, list):
        if not v:
            return []
        if all(isinstance(x, dict) for x in v):
            fields = defaultdict(set)
            for item in v:
                for k, x in item.items():
                    fields[k].add(json.dumps(x, ensure_ascii=False) if not isinstance(x, (dict, list)) else "<nested>")
            summary = {}
            for k, vals in fields.items():
                sample = next(iter(vals))
                if sample.startswith('"') and len(vals) > 6:
                    summary[k] = f"<{len(vals)} distinct strings, redacted>"
                elif len(vals) <= 6:
                    summary[k] = sorted(vals)
                else:
                    summary[k] = f"<{len(vals)} distinct values, e.g. {sorted(vals)[:3]}>"
            return {"<list of objects>": len(v), "fields": summary, "first": shape(v[0], depth + 1)}
        return {"<list>": len(v), "first": shape(v[0], depth + 1)}
    if isinstance(v, str):
        if re.fullmatch(r"[\d\-:T. +Z/]{6,30}", v) or len(v) <= 15:
            return v
        return f"<str len {len(v)}>"
    return v


def on_response(resp):
    url = resp.url
    ctype = resp.headers.get("content-type", "")
    req = resp.request
    entry = f"{req.method} {resp.status} {url[:200]}  [{ctype[:40]}]"
    if req.post_data:
        try:
            entry += "\n  POST body: " + json.dumps(shape(json.loads(req.post_data)), ensure_ascii=False)[:1500]
        except Exception:
            entry += f"\n  POST body: <{len(req.post_data)} bytes, not JSON>"
    try:
        if "json" in ctype:
            entry += "\n  JSON: " + json.dumps(shape(resp.json()), ensure_ascii=False, indent=1)[:6000]
        elif "javascript" in ctype:
            body = resp.text()
            for m in re.finditer("เต็ม|จองสิทธิ์แล้ว|limit|quota|maxPerson|max_person|paid|payment", body):
                if len(js_snippets) < 15:
                    js_snippets.append(f"{url.rsplit('/', 1)[-1][:60]} @{m.start()}: " + body[max(0, m.start() - 300): m.start() + 300])
    except Exception as e:
        entry += f"\n  (body unreadable: {e})"
    out.append(entry)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page()
    page.set_default_timeout(10000)
    page.on("response", on_response)
    open("status.txt", "w").close()
    try:
        result = check(page)
    except Exception as e:
        result = f"error: {e}"
    page.wait_for_timeout(2000)

with open("inspect.txt", "w", encoding="utf-8") as f:
    f.write(f"check() -> {result}\n\n=== NETWORK ===\n" + "\n\n".join(
        e for e in out if not re.search(r"\.(png|jpe?g|webp|svg|woff2?|ttf|css|ico)(\?|$)", e.split("  [")[0])))
    f.write("\n\n=== JS SNIPPETS ===\n" + "\n\n---\n".join(js_snippets))
