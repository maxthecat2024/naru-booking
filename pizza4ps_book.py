"""
Pizza 4P's Indiranagar — automated booking script  (v2 — rewritten)
Platform : TableCheck (tablecheck.com)
Window   : Daily at 10:00 AM IST — books slots up to 7 days ahead
Target   : Next Fri / Sat / Sun, preferred slots 12 PM → 1 PM → 7 PM → 8 PM
Party    : Config via env vars BOOKING_FIRST_NAME, BOOKING_LAST_NAME, BOOKING_EMAIL, BOOKING_PHONE

Flow documented from live site 2026-03-20:
  /reserve/message   → policy page, click "Confirm and continue"
  /reserve/landing    → guest count + date + time + "Find availability"
  /reserve/availability → seating selection (Indoor / Balcony / Pizza Counter)
  /reserve/review     → first name, last name, email, phone, special requests, "Confirm booking"
"""

import asyncio, os, smtplib, traceback
from datetime    import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from pathlib import Path

from playwright.async_api import async_playwright

# ── config ────────────────────────────────────────────────────────────────────
FIRST_NAME  = os.environ.get("BOOKING_FIRST_NAME", "Your")
LAST_NAME   = os.environ.get("BOOKING_LAST_NAME", "Name")
PHONE       = os.environ.get("BOOKING_PHONE", "0000000000")
EMAIL_ADDR  = os.environ.get("BOOKING_EMAIL", "you@example.com")
PARTY_SIZE  = 2        # all adults

SLOT_PRIO   = ["12:00","12:30","1:00","1:30","7:00","7:30","8:00","8:30"]
PREF_DAYS   = ["Friday","Saturday","Sunday"]

BASE_URL    = "https://www.tablecheck.com/en/pizza-4ps-in-indiranagar/reserve"
IST         = timezone(timedelta(hours=5, minutes=30))
GMAIL_USER  = os.environ.get("GMAIL_USER",  EMAIL_ADDR)
GMAIL_PASS  = os.environ.get("GMAIL_APP_PASSWORD", "")
SS          = Path("booking_result.png")

# ── helpers ───────────────────────────────────────────────────────────────────
def log(m):
    print(f"[{datetime.now(IST).strftime('%H:%M:%S IST')}] {m}")

def send_email(subject, body, attach=None):
    if not GMAIL_PASS:
        log("⚠️  No GMAIL_APP_PASSWORD — skipping email"); return
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER; msg["To"] = EMAIL_ADDR; msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        if attach and attach.exists():
            with open(attach,"rb") as f:
                p = MIMEBase("application","octet-stream"); p.set_payload(f.read())
            encoders.encode_base64(p)
            p.add_header("Content-Disposition", f"attachment; filename={attach.name}")
            msg.attach(p)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.sendmail(GMAIL_USER, EMAIL_ADDR, msg.as_string())
        log(f"📧 Email: {subject}")
    except Exception as e:
        log(f"❌ Email failed: {e}")

async def wait_until_10am():
    now = datetime.now(IST)
    t   = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if now >= t:
        log("Already past 10 AM IST — running immediately"); return
    secs = (t - now).total_seconds() - 0.05
    if secs > 300:
        log(f"⚡ Test/manual run — skipping {secs:.0f}s wait"); return
    log(f"⏳ {secs:.1f}s until 10:00 AM IST…")
    await asyncio.sleep(secs)
    log("🚀 10:00 AM — GO!")

def next_preferred_date():
    """Return the next Fri/Sat/Sun date as a datetime (IST)."""
    now = datetime.now(IST)
    for ahead in range(1, 8):
        d = now + timedelta(days=ahead)
        if d.strftime("%A") in PREF_DAYS:
            return d
    return now + timedelta(days=5)   # fallback

async def safe_click(page, selector, timeout=3000):
    """Click an element with retries, return True if clicked."""
    try:
        el = page.locator(selector).first
        await el.wait_for(state="visible", timeout=timeout)
        await el.click()
        return True
    except Exception:
        return False

async def screenshot(page, label=""):
    """Take a screenshot for debugging."""
    if label:
        log(f"📸 Screenshot: {label}")
    await page.screenshot(path=str(SS), full_page=True)

# ── main automation ───────────────────────────────────────────────────────────
async def book():
    async with async_playwright() as pw:
        br  = await pw.chromium.launch(headless=True, args=["--no-sandbox","--disable-setuid-sandbox"])
        ctx = await br.new_context(
            viewport={"width":1280,"height":900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        )
        page = await ctx.new_page()

        try:
            # ── STEP 1: Policy / intro page ──────────────────────────────
            log(f"🌐 Opening {BASE_URL}/message")
            await page.goto(f"{BASE_URL}/message", wait_until="networkidle", timeout=30_000)
            await asyncio.sleep(2)

            # Click "Confirm and continue"
            clicked = False
            for btn_text in ["Confirm and continue", "Continue", "I Agree", "Accept"]:
                try:
                    btn = page.get_by_role("button", name=btn_text)
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        log(f"  ✓ Policy accepted: '{btn_text}'")
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                # Try any prominent button
                await safe_click(page, "button.css-2rk8jx")
                log("  ✓ Policy accepted via CSS selector")

            await page.wait_for_url("**/landing**", timeout=10_000)
            log("  ✓ On landing page")
            await asyncio.sleep(2)

            # ── STEP 2: Guest count ──────────────────────────────────────
            log(f"👥 Setting party size → {PARTY_SIZE} adults")

            # Click on the guests field to open breakdown modal
            guests_clicked = False
            for sel in ["text=Guests", "text=guests", "[class*='guest']", "text=2 Guests"]:
                if await safe_click(page, sel, 3000):
                    guests_clicked = True
                    log(f"  ✓ Opened guests modal via {sel}")
                    break

            if guests_clicked:
                await asyncio.sleep(1)
                # The modal has Adults, Seniors, Children, Babies with +/- buttons
                # Default is likely 2 adults. Adjust if needed.
                if PARTY_SIZE != 2:
                    # Find the Adults row and click + or - to adjust
                    adults_section = page.locator("text=Adults").locator("..")
                    for i in range(abs(PARTY_SIZE - 2)):
                        if PARTY_SIZE > 2:
                            await adults_section.locator("button:has-text('+')").click()
                        else:
                            await adults_section.locator("button:has-text('-')").click()
                        await asyncio.sleep(0.3)

                # Confirm guest selection
                for btn_text in ["Confirm", "Done", "Apply", "OK", "Save"]:
                    try:
                        btn = page.get_by_role("button", name=btn_text)
                        if await btn.is_visible(timeout=2000):
                            await btn.click()
                            log(f"  ✓ Guests confirmed: '{btn_text}'")
                            break
                    except Exception:
                        continue
                await asyncio.sleep(1)

            # ── STEP 3: Select date ──────────────────────────────────────
            target_date = next_preferred_date()
            log(f"📅 Targeting {target_date.strftime('%A %d %b %Y')}")

            # Click on the date field
            for sel in ["text=Select a date", "text=Date", "[class*='date']"]:
                if await safe_click(page, sel, 3000):
                    log(f"  ✓ Opened date picker via {sel}")
                    break
            await asyncio.sleep(1)

            # Click on the target day number in the calendar
            day_num = str(target_date.day)
            clicked_date = False
            # Try aria-label with date
            for fmt in [
                target_date.strftime("%A, %B %-d, %Y"),  # "Friday, March 21, 2026"
                target_date.strftime("%B %-d"),            # "March 21"
                target_date.strftime("%-d"),               # "21"
            ]:
                try:
                    el = page.locator(f"[aria-label*='{fmt}']").first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        log(f"  ✓ Date selected: {fmt}")
                        clicked_date = True
                        break
                except Exception:
                    continue

            if not clicked_date:
                # Click the number directly in the calendar
                try:
                    # Find day numbers in the calendar, be careful not to click a header
                    calendar_days = page.locator(f"button:has-text('{day_num}')")
                    count = await calendar_days.count()
                    for i in range(count):
                        txt = (await calendar_days.nth(i).inner_text()).strip()
                        if txt == day_num:
                            await calendar_days.nth(i).click()
                            log(f"  ✓ Date clicked: day {day_num}")
                            clicked_date = True
                            break
                except Exception as e:
                    log(f"  ⚠️ Date click failed: {e}")

            await asyncio.sleep(1)

            # ── STEP 4: Select time ──────────────────────────────────────
            log("🕐 Selecting time slot…")

            # Click on the time field
            for sel in ["text=Select a time", "text=Time", "[class*='time']"]:
                if await safe_click(page, sel, 3000):
                    log(f"  ✓ Opened time picker via {sel}")
                    break
            await asyncio.sleep(1)

            # Time picker has sections: Lunch, Tea, Dinner
            # Click each priority slot
            slot_ok = False
            for slot in SLOT_PRIO:
                try:
                    el = page.get_by_text(slot, exact=False).first
                    if await el.is_visible(timeout=1500):
                        await el.click()
                        log(f"  ✓ Slot: {slot}")
                        slot_ok = True
                        break
                except Exception:
                    continue

            if not slot_ok:
                # Click any available time button
                try:
                    time_btns = page.locator("[class*='time'] button:not([disabled])")
                    if await time_btns.count() > 0:
                        txt = await time_btns.first.inner_text()
                        await time_btns.first.click()
                        log(f"  ✓ First available slot: {txt.strip()}")
                        slot_ok = True
                except Exception:
                    pass

            if not slot_ok:
                await screenshot(page, "no-slots")
                await br.close()
                return False, "No time slots available."

            await asyncio.sleep(1)

            # ── STEP 5: Click "Find availability" ────────────────────────
            log("🔍 Finding availability…")
            find_clicked = False
            for btn_text in ["Find availability", "Search", "Check Availability", "Find"]:
                try:
                    btn = page.get_by_role("button", name=btn_text)
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        log(f"  ✓ '{btn_text}'")
                        find_clicked = True
                        break
                except Exception:
                    continue

            if not find_clicked:
                # Try by CSS
                await safe_click(page, "button.css-2rk8jx")
                log("  ✓ Find availability via CSS")

            await asyncio.sleep(3)

            # ── STEP 6: Check for availability / alternatives ────────────
            log("📋 Checking results…")
            html = (await page.content()).lower()

            if "no availability" in html or "fully booked" in html or "no tables" in html:
                # Check for alternative dates/times offered
                alt_slots = page.locator("[class*='alternative'], [class*='suggest']")
                if await alt_slots.count() > 0:
                    await alt_slots.first.click()
                    log("  ✓ Clicked alternative slot")
                    await asyncio.sleep(2)
                else:
                    await screenshot(page, "no-availability")
                    await br.close()
                    return False, "No tables available for the selected date/time."

            # Check if we're on availability page (seating selection)
            current_url = page.url
            if "availability" in current_url:
                log("🪑 Seating selection page")
                # Try clicking first available seating option (Indoor preferred)
                for seat_pref in ["Indoor", "Balcony", "Pizza Counter", "Counter", "Outdoor"]:
                    try:
                        seat_el = page.get_by_text(seat_pref, exact=False).first
                        if await seat_el.is_visible(timeout=2000):
                            await seat_el.click()
                            log(f"  ✓ Seating: {seat_pref}")
                            await asyncio.sleep(2)
                            break
                    except Exception:
                        continue

            # If we landed on a page with alternative times, click the first one
            alt_btns = page.locator("button:has-text('pm'), button:has-text('am')")
            alt_count = await alt_btns.count()
            if alt_count > 0 and "review" not in page.url:
                txt = await alt_btns.first.inner_text()
                await alt_btns.first.click()
                log(f"  ✓ Selected alternative: {txt.strip()}")
                await asyncio.sleep(2)

            # ── STEP 7: Fill contact details on /review page ─────────────
            log("📝 Filling contact details…")
            await asyncio.sleep(2)

            # Wait for review page
            try:
                await page.wait_for_url("**/review**", timeout=10_000)
                log("  ✓ On review page")
            except Exception:
                log(f"  ⚠️ Not on review page, current: {page.url}")
                await screenshot(page, "not-review-page")

            # First Name
            for sel in ["input[name='first_name']", "input[placeholder*='First']",
                        "input[autocomplete='given-name']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.fill(FIRST_NAME)
                        log(f"  ✓ First name: {FIRST_NAME}")
                        break
                except Exception:
                    continue

            # Last Name
            for sel in ["input[name='last_name']", "input[placeholder*='Last']",
                        "input[autocomplete='family-name']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.fill(LAST_NAME)
                        log(f"  ✓ Last name: {LAST_NAME}")
                        break
                except Exception:
                    continue

            # Email
            for sel in ["input[type='email']", "input[name*='email']",
                        "input[placeholder*='email' i]"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.fill(EMAIL_ADDR)
                        log(f"  ✓ Email: {EMAIL_ADDR}")
                        break
                except Exception:
                    continue

            # Phone
            for sel in ["input.iti__tel-input", "input[type='tel']",
                        "input[name*='phone']", "input[placeholder*='phone' i]"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.fill(PHONE)
                        log(f"  ✓ Phone: {PHONE}")
                        break
                except Exception:
                    continue

            # Special Requests (optional)
            try:
                textarea = page.locator("textarea").first
                if await textarea.is_visible(timeout=2000):
                    await textarea.fill("No special requests.")
                    log("  ✓ Special requests filled")
            except Exception:
                pass

            await asyncio.sleep(1)

            # ── STEP 8: Confirm booking ──────────────────────────────────
            log("✅ Confirming booking…")
            for btn_text in ["Confirm booking", "Confirm", "Reserve", "Book",
                             "Submit", "Complete", "Place Reservation"]:
                try:
                    btn = page.get_by_role("button", name=btn_text)
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        log(f"  ✓ '{btn_text}'")
                        break
                except Exception:
                    continue

            await asyncio.sleep(5)
            await screenshot(page, "final-result")

            # ── STEP 9: Detect result ────────────────────────────────────
            html = (await page.content()).lower()
            ok   = any(s in html for s in ["confirmed","reservation confirmed","thank you",
                                            "booked","success","see you","your reservation"])
            fail = any(s in html for s in ["unavailable","fully booked","no availability",
                                            "sold out","not available","no tables"])

            await br.close()
            if ok:   return True,  "Booking confirmed!"
            if fail: return False, "No tables available — try again tomorrow."
            return False, "Submitted but result unclear — check screenshot."

        except Exception:
            tb = traceback.format_exc(); log(f"💥 {tb}")
            try: await page.screenshot(path=str(SS), full_page=True)
            except Exception: pass
            await br.close()
            return False, f"Error:<br><pre>{tb}</pre>"

# ── entry ─────────────────────────────────────────────────────────────────────
async def main():
    log("═"*60)
    log("🍕 Pizza 4P's Booking Agent v2 — starting")
    log(f"   {FIRST_NAME} {LAST_NAME} | {EMAIL_ADDR} | party of {PARTY_SIZE}")
    log("═"*60)
    await wait_until_10am()
    ok, detail = await book()

    subject = ("🎉 Pizza 4P's — booked!" if ok else "❌ Pizza 4P's — no slot today")
    body = (
        f"<h2>You're in! 🍕</h2><p>Reservation for <b>{PARTY_SIZE} people</b> confirmed.</p>"
        f"<p>Pizza 4P's, Indiranagar, Bengaluru</p>"
        if ok else
        f"<h2>No booking today 😔</h2><p>{detail}</p>"
        f"<p>Trying again tomorrow at <b>10:00 AM IST</b>.</p>"
    )
    send_email(subject, body, SS if SS.exists() else None)
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(asyncio.run(main()))
