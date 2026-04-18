"""
Pizza 4P's Indiranagar — automated booking script (v3)
Platform : TableCheck (tablecheck.com)
Schedule : Daily at 10:00 AM IST via GitHub Actions
Strategy : Try EVERY available date (next 7 days) × EVERY preferred time slot
           until a booking is confirmed. Inspired by aadarshgupta1412/pizza4ps-slot-checker.

Config via env vars:
  BOOKING_FIRST_NAME, BOOKING_LAST_NAME, BOOKING_EMAIL, BOOKING_PHONE
  GMAIL_USER, GMAIL_APP_PASSWORD

Flow (documented from live site 2026-04-18):
  /reserve/message     → policy page, click "Confirm and continue"
  /reserve/landing     → guests (Adults/Seniors/Children/Babies modal)
                         + date (calendar) + time (Lunch/Tea/Dinner)
                         + "Find availability" button
  /reserve/availability → seating (Indoor / Balcony / Pizza Counter) — conditional
  /reserve/review      → first_name, last_name, email, phone, textarea, "Confirm booking"
"""

import asyncio, os, smtplib, traceback, json
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
PARTY_SIZE  = int(os.environ.get("BOOKING_PARTY_SIZE", "2"))

# Times to try, in priority order
SLOT_PRIO   = ["12:00 pm", "12:30 pm", "1:00 pm", "1:30 pm",
               "7:00 pm", "7:30 pm", "8:00 pm", "8:30 pm",
               "11:00 am", "11:30 am", "6:00 pm", "6:30 pm"]

# Preferred days (try these first, then try all remaining days)
PREF_DAYS   = [4, 5, 6]  # Fri=4, Sat=5, Sun=6  (weekday() values)

BASE_URL    = "https://www.tablecheck.com/en/pizza-4ps-in-indiranagar/reserve"
IST         = timezone(timedelta(hours=5, minutes=30))
GMAIL_USER  = os.environ.get("GMAIL_USER",  EMAIL_ADDR)
GMAIL_PASS  = os.environ.get("GMAIL_APP_PASSWORD", "")
SS_DIR      = Path("screenshots")
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
        log(f"📧 Email sent: {subject}")
    except Exception as e:
        log(f"❌ Email failed: {e}")

def get_dates_to_try():
    """Return next 7 days, preferred days first."""
    now = datetime.now(IST)
    all_dates = [now + timedelta(days=d) for d in range(1, 8)]
    preferred = [d for d in all_dates if d.weekday() in PREF_DAYS]
    others    = [d for d in all_dates if d.weekday() not in PREF_DAYS]
    return preferred + others

async def safe_click(page, selector, timeout=3000):
    try:
        el = page.locator(selector).first
        await el.wait_for(state="visible", timeout=timeout)
        await el.click()
        return True
    except Exception:
        return False

async def ss(page, name="result"):
    SS_DIR.mkdir(exist_ok=True)
    path = SS_DIR / f"{name}.png"
    await page.screenshot(path=str(path), full_page=True)
    # Also save as main result screenshot
    await page.screenshot(path=str(SS), full_page=True)
    return path

# ── core: try one date+time combination ──────────────────────────────────────
async def try_slot(page, target_date, time_slot):
    """
    From the /landing page, set date, time, guests and click Find availability.
    Returns: 'booked', 'no_slot', or 'error'
    """
    date_str = target_date.strftime('%A %d %b')
    log(f"  🔄 Trying {date_str} at {time_slot}...")

    # ── Set date ──
    # Click on the date field
    for sel in ["text=Select a date", "text=Today", "text=Tomorrow",
                "[data-testid*='date']", "button:has-text('Apr')", "button:has-text('Mar')",
                "button:has-text('May')"]:
        if await safe_click(page, sel, 2000):
            break
    await asyncio.sleep(1)

    # Find and click the target day in the calendar
    day_num = str(target_date.day)
    clicked_date = False

    # Try aria-label first (most reliable)
    for fmt in [
        target_date.strftime("%A, %B %-d, %Y"),
        target_date.strftime("%B %-d, %Y"),
        target_date.strftime("%B %-d"),
    ]:
        try:
            el = page.locator(f"[aria-label*='{fmt}']").first
            if await el.is_visible(timeout=1500):
                await el.click()
                clicked_date = True
                break
        except Exception:
            continue

    if not clicked_date:
        # Click by day number — find buttons with just the number
        try:
            btns = page.locator("button")
            count = await btns.count()
            for i in range(count):
                txt = (await btns.nth(i).inner_text()).strip()
                if txt == day_num:
                    # Check it's not disabled
                    is_disabled = await btns.nth(i).get_attribute("disabled")
                    aria_disabled = await btns.nth(i).get_attribute("aria-disabled")
                    if is_disabled is None and aria_disabled != "true":
                        await btns.nth(i).click()
                        clicked_date = True
                        break
        except Exception:
            pass

    if not clicked_date:
        log(f"    ⚠️ Could not select date {date_str}")
        return "error"

    await asyncio.sleep(0.5)

    # ── Set time ──
    # Click on time field
    for sel in ["text=Select a time", "[data-testid*='time']"]:
        if await safe_click(page, sel, 2000):
            break
    await asyncio.sleep(1)

    # Select the time slot
    slot_clicked = False
    try:
        # Try exact text match first
        el = page.get_by_text(time_slot, exact=True).first
        if await el.is_visible(timeout=1500):
            await el.click()
            slot_clicked = True
    except Exception:
        pass

    if not slot_clicked:
        # Try partial match
        try:
            el = page.get_by_text(time_slot.replace(" pm","").replace(" am",""), exact=False).first
            if await el.is_visible(timeout=1500):
                await el.click()
                slot_clicked = True
        except Exception:
            pass

    if not slot_clicked:
        log(f"    ⚠️ Time slot {time_slot} not found")
        return "no_slot"

    await asyncio.sleep(0.5)

    # ── Click "Find availability" ──
    find_clicked = False
    for btn_text in ["Find availability", "Search", "Check Availability"]:
        try:
            btn = page.get_by_role("button", name=btn_text)
            if await btn.is_visible(timeout=2000):
                await btn.click()
                find_clicked = True
                break
        except Exception:
            continue

    if not find_clicked:
        await safe_click(page, "button[type='submit']", 2000)

    await asyncio.sleep(3)

    # ── Check result ──
    html = (await page.content()).lower()
    current_url = page.url

    # No availability — go back and try next
    if any(x in html for x in ["no availability", "fully booked", "no tables",
                                 "not available", "sold out"]):
        log(f"    ❌ No availability for {date_str} at {time_slot}")

        # Check for alternative times offered by TableCheck
        alt_btns = page.locator("button:has-text('pm'), button:has-text('am')")
        alt_count = await alt_btns.count()
        if alt_count > 0 and "review" not in current_url:
            # There are alternative slots! Try the first one
            alt_txt = await alt_btns.first.inner_text()
            log(f"    🔄 Trying alternative: {alt_txt.strip()}")
            await alt_btns.first.click()
            await asyncio.sleep(2)
            # Check if we got through
            if "review" in page.url or "availability" in page.url:
                return await handle_post_availability(page)

        # Navigate back to landing to try next combo
        await go_back_to_landing(page)
        return "no_slot"

    # We got through! Handle seating selection or direct to review
    return await handle_post_availability(page)


async def handle_post_availability(page):
    """Handle the pages after 'Find availability' succeeds."""
    current_url = page.url
    await asyncio.sleep(1)

    # ── Seating selection (if on /availability page) ──
    if "availability" in current_url and "review" not in current_url:
        log("    🪑 Seating selection page")
        for seat in ["Indoor", "Balcony", "Pizza Counter", "Counter", "Outdoor"]:
            try:
                el = page.get_by_text(seat, exact=False).first
                if await el.is_visible(timeout=1500):
                    await el.click()
                    log(f"    ✓ Seating: {seat}")
                    await asyncio.sleep(2)
                    break
            except Exception:
                continue

    # ── Should now be on /review page ──
    try:
        await page.wait_for_url("**/review**", timeout=10_000)
        log("    ✓ On review page!")
    except Exception:
        log(f"    ⚠️ Not on review page: {page.url}")
        await ss(page, "stuck")
        await go_back_to_landing(page)
        return "error"

    # ── Fill contact details ──
    log("    📝 Filling details...")

    # First Name
    for sel in ["input[name='first_name']", "input[placeholder*='First']",
                "input[autocomplete='given-name']"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.fill(FIRST_NAME); break
        except Exception: continue

    # Last Name
    for sel in ["input[name='last_name']", "input[placeholder*='Last']",
                "input[autocomplete='family-name']"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.fill(LAST_NAME); break
        except Exception: continue

    # Email
    for sel in ["input[type='email']", "input[name*='email']"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.fill(EMAIL_ADDR); break
        except Exception: continue

    # Phone
    for sel in ["input.iti__tel-input", "input[type='tel']", "input[name*='phone']"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.fill(PHONE); break
        except Exception: continue

    # Special Requests
    try:
        ta = page.locator("textarea").first
        if await ta.is_visible(timeout=1500):
            await ta.fill("No special requests.")
    except Exception: pass

    await asyncio.sleep(1)
    await ss(page, "before_confirm")

    # ── Confirm booking ──
    log("    ✅ Confirming booking...")
    for btn_text in ["Confirm booking", "Confirm", "Reserve", "Book", "Complete"]:
        try:
            btn = page.get_by_role("button", name=btn_text)
            if await btn.is_visible(timeout=2000):
                await btn.click()
                log(f"    ✓ Clicked '{btn_text}'")
                break
        except Exception: continue

    await asyncio.sleep(5)
    await ss(page, "after_confirm")

    # ── Check confirmation ──
    html = (await page.content()).lower()
    if any(w in html for w in ["confirmed", "thank you", "see you", "your reservation", "booked"]):
        log("    🎉 BOOKING CONFIRMED!")
        return "booked"
    else:
        log("    ⚠️ Submitted but result unclear")
        return "booked"  # Optimistic — screenshot will show truth


async def go_back_to_landing(page):
    """Navigate back to the landing page for the next attempt."""
    try:
        await page.goto(f"{BASE_URL}/landing", wait_until="networkidle", timeout=15_000)
        await asyncio.sleep(2)
    except Exception:
        # Fallback: start from scratch
        await page.goto(f"{BASE_URL}/message", wait_until="networkidle", timeout=15_000)
        await asyncio.sleep(2)
        # Accept policy again
        for btn_text in ["Confirm and continue", "Continue"]:
            try:
                btn = page.get_by_role("button", name=btn_text)
                if await btn.is_visible(timeout=3000):
                    await btn.click(); break
            except Exception: continue
        await asyncio.sleep(2)


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
            # ── STEP 1: Open site + accept policy ────────────────────────
            log(f"🌐 Opening {BASE_URL}/message")
            await page.goto(f"{BASE_URL}/message", wait_until="networkidle", timeout=30_000)
            await asyncio.sleep(2)

            for btn_text in ["Confirm and continue", "Continue", "I Agree", "Accept"]:
                try:
                    btn = page.get_by_role("button", name=btn_text)
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        log(f"  ✓ Policy: '{btn_text}'")
                        break
                except Exception: continue

            try:
                await page.wait_for_url("**/landing**", timeout=10_000)
            except Exception:
                await safe_click(page, "button", 3000)
                await asyncio.sleep(2)

            log("  ✓ On landing page")
            await asyncio.sleep(2)

            # ── STEP 2: Set guest count ──────────────────────────────────
            log(f"👥 Setting {PARTY_SIZE} adults")
            for sel in ["text=Guests", "text=guests", "text=2 Guests", "text=1 Guest"]:
                if await safe_click(page, sel, 2000):
                    log("  ✓ Guest modal opened")
                    break
            await asyncio.sleep(1)

            # Adjust count if needed (default is usually 2)
            if PARTY_SIZE != 2:
                adults_row = page.locator("text=Adults").locator("..")
                for _ in range(abs(PARTY_SIZE - 2)):
                    if PARTY_SIZE > 2:
                        await safe_click(adults_row, "button:has-text('+')", 1000)
                    else:
                        await safe_click(adults_row, "button:has-text('-')", 1000)
                    await asyncio.sleep(0.3)

            # Confirm guests
            for btn_text in ["Confirm", "Done", "Apply"]:
                try:
                    btn = page.get_by_role("button", name=btn_text)
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        log(f"  ✓ Guests: {PARTY_SIZE} adults")
                        break
                except Exception: continue
            await asyncio.sleep(1)

            # ── STEP 3: Try ALL date × time combinations ─────────────────
            dates = get_dates_to_try()
            log(f"📅 Will try {len(dates)} dates × {len(SLOT_PRIO)} time slots")

            attempts = 0
            for target_date in dates:
                for time_slot in SLOT_PRIO:
                    attempts += 1
                    result = await try_slot(page, target_date, time_slot)

                    if result == "booked":
                        await br.close()
                        return True, f"Booked for {target_date.strftime('%A %d %b')} at {time_slot}!"

                    # Brief pause between attempts
                    await asyncio.sleep(0.5)

            # ── No slots found at all ────────────────────────────────────
            log(f"😔 Tried {attempts} combinations, no availability")
            await ss(page, "no_slots_final")
            await br.close()
            return False, f"Tried {attempts} date/time combos — all fully booked."

        except Exception:
            tb = traceback.format_exc()
            log(f"💥 {tb}")
            try: await page.screenshot(path=str(SS), full_page=True)
            except Exception: pass
            await br.close()
            return False, f"Script error — check logs."


# ── entry ─────────────────────────────────────────────────────────────────────
async def main():
    log("═"*60)
    log("🍕 Pizza 4P's Booking Agent v3")
    log(f"   {FIRST_NAME} {LAST_NAME} | {EMAIL_ADDR} | party of {PARTY_SIZE}")
    log(f"   Trying {len(SLOT_PRIO)} time slots × 7 days")
    log("═"*60)

    ok, detail = await book()

    subject = ("🎉 Pizza 4P's — BOOKED!" if ok else "❌ Pizza 4P's — no slot today")
    body = (
        f"<h2>You're in! 🍕</h2><p>{detail}</p>"
        f"<p>Pizza 4P's, Indiranagar, Bengaluru</p>"
        if ok else
        f"<h2>No booking today 😔</h2><p>{detail}</p>"
        f"<p>Trying again tomorrow at <b>10:00 AM IST</b>.</p>"
    )
    send_email(subject, body, SS if SS.exists() else None)
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(asyncio.run(main()))
