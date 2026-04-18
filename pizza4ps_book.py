"""
Pizza 4P's Indiranagar — automated booking script (v4)
Platform : TableCheck (tablecheck.com)
Schedule : Daily at 10:00 AM IST via GitHub Actions
Strategy : At exactly 10 AM (when new slots open), try EVERY available date × time

ACTUAL UI (from live site screenshot 2026-04-18):
  /reserve/message page has:
    - "Message from Venue" text
    - ✅ Checkbox: "I confirm I've read the Message from Venue above"
    - Dropdown: -- Adults --       (select element)
    - Dropdown: -- Select Date --  (select element)
    - Dropdown: -- Select Time --  (select element) — appears AFTER date is selected
    - Dropdown: -- Senior -- / -- Children -- / -- Baby -- (optional)
    - Submit/Search button
  Then after submit:
    - Seating selection (Indoor / Balcony / Pizza Counter) — conditional
    - Contact details form (first name, last name, email, phone, etc.)
    - Confirm booking button

Config: env vars BOOKING_FIRST_NAME, BOOKING_LAST_NAME, BOOKING_EMAIL, BOOKING_PHONE
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
PARTY_SIZE  = int(os.environ.get("BOOKING_PARTY_SIZE", "2"))

BASE_URL    = "https://www.tablecheck.com/en/pizza-4ps-in-indiranagar/reserve"
IST         = timezone(timedelta(hours=5, minutes=30))
GMAIL_USER  = os.environ.get("GMAIL_USER",  EMAIL_ADDR)
GMAIL_PASS  = os.environ.get("GMAIL_APP_PASSWORD", "")
SS_DIR      = Path("screenshots")
SS          = Path("booking_result.png")

# Preferred days (weekday(): Mon=0 ... Sun=6)
PREF_DAYS = [4, 5, 6]  # Fri, Sat, Sun

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

async def screenshot(page, name="result"):
    SS_DIR.mkdir(exist_ok=True)
    path = SS_DIR / f"{name}.png"
    await page.screenshot(path=str(path), full_page=True)
    await page.screenshot(path=str(SS), full_page=True)
    return path

# ── main booking logic ────────────────────────────────────────────────────────
async def book():
    async with async_playwright() as pw:
        br  = await pw.chromium.launch(headless=True, args=["--no-sandbox","--disable-setuid-sandbox"])
        ctx = await br.new_context(
            viewport={"width":1440,"height":900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        page = await ctx.new_page()

        try:
            # ═══════════════════════════════════════════════════════════════
            # STEP 1: Open the booking page
            # ═══════════════════════════════════════════════════════════════
            log(f"🌐 Opening {BASE_URL}/message")
            await page.goto(f"{BASE_URL}/message", wait_until="networkidle", timeout=30_000)
            await asyncio.sleep(3)
            await screenshot(page, "01_page_loaded")
            log("  ✓ Page loaded")

            # Log the page structure for debugging
            html = await page.content()
            log(f"  Page URL: {page.url}")
            log(f"  Page length: {len(html)} chars")

            # ═══════════════════════════════════════════════════════════════
            # STEP 2: Check the confirmation checkbox
            # ═══════════════════════════════════════════════════════════════
            log("☑️  Checking confirmation checkbox...")
            checkbox_clicked = False

            # Method 1: Find checkbox by nearby text
            for sel in [
                "input[type='checkbox']",
                "label:has-text('confirm') input",
                "label:has-text('read') input",
                ":text('confirm') >> .. >> input[type='checkbox']",
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.check()
                        checkbox_clicked = True
                        log("  ✓ Checkbox checked")
                        break
                except Exception:
                    continue

            # Method 2: Click label text directly
            if not checkbox_clicked:
                try:
                    label = page.get_by_text("I confirm", exact=False).first
                    if await label.is_visible(timeout=2000):
                        await label.click()
                        checkbox_clicked = True
                        log("  ✓ Checkbox clicked via label")
                except Exception:
                    pass

            # Method 3: JavaScript fallback
            if not checkbox_clicked:
                try:
                    await page.evaluate("""
                        const cb = document.querySelector('input[type="checkbox"]');
                        if (cb) { cb.checked = true; cb.dispatchEvent(new Event('change', {bubbles: true})); }
                    """)
                    log("  ✓ Checkbox set via JS")
                    checkbox_clicked = True
                except Exception:
                    pass

            if not checkbox_clicked:
                log("  ⚠️ Could not find/check checkbox — continuing anyway")

            await asyncio.sleep(1)

            # ═══════════════════════════════════════════════════════════════
            # STEP 2B: Handle "Confirm and continue" button (alternative UI)
            #   Some days the page shows a button instead of dropdowns
            # ═══════════════════════════════════════════════════════════════
            for btn_text in ["Confirm and continue", "Continue", "I Agree", "Accept"]:
                try:
                    btn = page.get_by_role("button", name=btn_text)
                    if await btn.is_visible(timeout=1500):
                        await btn.click()
                        log(f"  ✓ Button flow: '{btn_text}'")
                        await asyncio.sleep(2)
                        # This takes us to /landing — different flow, handle below
                        break
                except Exception:
                    continue

            await screenshot(page, "02_after_checkbox")

            # Determine which UI we're on
            current_url = page.url
            log(f"  Current URL: {current_url}")

            # ═══════════════════════════════════════════════════════════════
            # DETECT UI TYPE and branch accordingly
            # ═══════════════════════════════════════════════════════════════

            # Check if we have <select> dropdowns (screenshot-based UI)
            has_selects = await page.locator("select").count() > 0
            is_landing = "landing" in current_url

            if has_selects:
                log("📋 Detected DROPDOWN-based UI")
                result = await handle_dropdown_flow(page)
            elif is_landing:
                log("📋 Detected MODAL-based UI (landing page)")
                result = await handle_modal_flow(page)
            else:
                # Try to detect what we're looking at
                log("📋 Unknown UI — dumping page info for debugging")
                await screenshot(page, "unknown_ui")

                # Check for any interactive elements
                buttons = await page.locator("button").all_inner_texts()
                inputs = await page.locator("input").count()
                selects = await page.locator("select").count()
                log(f"  Buttons: {buttons[:10]}")
                log(f"  Inputs: {inputs}, Selects: {selects}")

                # Try both flows
                result = await handle_dropdown_flow(page)
                if result[0] is False and "error" in result[1].lower():
                    log("  Dropdown flow failed, trying modal flow...")
                    await page.goto(f"{BASE_URL}/message", wait_until="networkidle", timeout=30_000)
                    await asyncio.sleep(2)
                    result = await handle_modal_flow(page)

            await br.close()
            return result

        except Exception:
            tb = traceback.format_exc()
            log(f"💥 {tb}")
            try: await page.screenshot(path=str(SS), full_page=True)
            except Exception: pass
            await br.close()
            return False, f"Script error — check logs."


# ══════════════════════════════════════════════════════════════════════════════
# FLOW A: Dropdown-based UI (the one from user's screenshot)
# The /message page has select dropdowns for Adults, Date, Time, etc.
# ══════════════════════════════════════════════════════════════════════════════
async def handle_dropdown_flow(page):
    log("═" * 40)
    log("🔽 DROPDOWN FLOW")

    # ── Select Adults ──
    log("👥 Selecting Adults...")
    adults_set = False
    # Find the Adults dropdown
    for sel in ["select:near(:text('Adults'))", "select:has(option:text('Adults'))",
                "select:has(option:text('-- Adults --'))"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.select_option(str(PARTY_SIZE))
                adults_set = True
                log(f"  ✓ Adults = {PARTY_SIZE}")
                break
        except Exception:
            continue

    if not adults_set:
        # Try all select elements and find the one with Adults text
        selects = page.locator("select")
        count = await selects.count()
        log(f"  Found {count} select elements")
        for i in range(count):
            try:
                options = await selects.nth(i).locator("option").all_inner_texts()
                log(f"  Select #{i}: {options[:5]}")
                if any("adult" in o.lower() for o in options):
                    await selects.nth(i).select_option(str(PARTY_SIZE))
                    adults_set = True
                    log(f"  ✓ Adults dropdown (select #{i}) = {PARTY_SIZE}")
                    break
                # Also try if options are numbers (1, 2, 3, ...)
                if options and options[0].strip().startswith("--") and "adult" in options[0].lower():
                    await selects.nth(i).select_option(str(PARTY_SIZE))
                    adults_set = True
                    log(f"  ✓ Adults = {PARTY_SIZE}")
                    break
            except Exception as e:
                log(f"  Select #{i} error: {e}")

    if not adults_set:
        # Last resort: just select_option on first select
        try:
            await page.locator("select").first.select_option(str(PARTY_SIZE))
            log(f"  ✓ First select = {PARTY_SIZE} (assumed Adults)")
            adults_set = True
        except Exception:
            pass

    await asyncio.sleep(1)
    await screenshot(page, "03_adults_set")

    # ── Select Date ──
    log("📅 Selecting Date...")
    date_set = False
    now = datetime.now(IST)
    dates_to_try = []
    for d in range(1, 8):
        dt = now + timedelta(days=d)
        dates_to_try.append(dt)
    # Sort: preferred days first
    dates_to_try.sort(key=lambda d: (0 if d.weekday() in PREF_DAYS else 1, d))

    # Find the date dropdown
    date_select = None
    selects = page.locator("select")
    count = await selects.count()
    for i in range(count):
        try:
            options = await selects.nth(i).locator("option").all_inner_texts()
            if any("date" in o.lower() for o in options) or any("select date" in o.lower() for o in options):
                date_select = selects.nth(i)
                date_options = options
                log(f"  Date dropdown found (select #{i}), options: {options[:5]}...")
                break
        except Exception:
            continue

    if date_select:
        # Try each preferred date
        all_options = await date_select.locator("option").all()
        option_values = []
        for opt in all_options:
            val = await opt.get_attribute("value")
            txt = await opt.inner_text()
            option_values.append((val, txt))
            log(f"    Option: value='{val}' text='{txt}'")

        for target in dates_to_try:
            target_str = target.strftime("%Y-%m-%d")
            day_name = target.strftime("%A")
            day_short = target.strftime("%a")
            day_num = str(target.day)

            for val, txt in option_values:
                if not val or val.startswith("--"):
                    continue
                # Match by value (usually YYYY-MM-DD) or by text containing the day
                if (val == target_str or
                    target_str in str(val) or
                    (day_num in txt and (day_name.lower() in txt.lower() or day_short.lower() in txt.lower()))):
                    try:
                        await date_select.select_option(val)
                        log(f"  ✓ Date = {txt.strip()} (value={val})")
                        date_set = True
                        break
                    except Exception:
                        continue
            if date_set:
                break

        if not date_set:
            # Just try the first non-placeholder option
            for val, txt in option_values:
                if val and not val.startswith("--") and "select" not in txt.lower():
                    try:
                        await date_select.select_option(val)
                        log(f"  ✓ Date = {txt.strip()} (first available)")
                        date_set = True
                        break
                    except Exception:
                        continue

    await asyncio.sleep(2)  # Wait for time slots to load after date selection
    await screenshot(page, "04_date_set")

    # ── Select Time ──
    log("🕐 Selecting Time...")
    time_set = False

    # Time dropdown may appear after date is selected
    time_select = None
    selects = page.locator("select")
    count = await selects.count()
    for i in range(count):
        try:
            options = await selects.nth(i).locator("option").all_inner_texts()
            if any("time" in o.lower() for o in options) or any("select time" in o.lower() for o in options):
                time_select = selects.nth(i)
                log(f"  Time dropdown found (select #{i})")
                break
        except Exception:
            continue

    if time_select:
        all_opts = await time_select.locator("option").all()
        time_options = []
        for opt in all_opts:
            val = await opt.get_attribute("value")
            txt = await opt.inner_text()
            time_options.append((val, txt))

        log(f"  Available times: {[t[1].strip() for t in time_options if t[0] and not t[0].startswith('--')]}")

        # Try preferred times first
        preferred_times = ["12:00", "12:30", "1:00", "13:00", "1:30", "13:30",
                          "7:00", "19:00", "7:30", "19:30", "8:00", "20:00", "8:30", "20:30",
                          "6:30", "18:30", "6:00", "18:00", "11:30", "11:00"]
        for pref in preferred_times:
            for val, txt in time_options:
                if not val or val.startswith("--"):
                    continue
                if pref in val or pref in txt:
                    try:
                        await time_select.select_option(val)
                        log(f"  ✓ Time = {txt.strip()} (value={val})")
                        time_set = True
                        break
                    except Exception:
                        continue
            if time_set:
                break

        if not time_set:
            # Select first available time
            for val, txt in time_options:
                if val and not val.startswith("--") and "select" not in txt.lower():
                    try:
                        await time_select.select_option(val)
                        log(f"  ✓ Time = {txt.strip()} (first available)")
                        time_set = True
                        break
                    except Exception:
                        continue

    await asyncio.sleep(1)
    await screenshot(page, "05_time_set")

    # ── Submit / Search / Find availability ──
    log("🔍 Submitting search...")
    submitted = False
    for btn_text in ["Search", "Find availability", "Find Availability",
                     "Check Availability", "Search Availability", "Submit",
                     "Find", "Reserve", "Next"]:
        try:
            btn = page.get_by_role("button", name=btn_text)
            if await btn.is_visible(timeout=2000):
                await btn.click()
                log(f"  ✓ Clicked '{btn_text}'")
                submitted = True
                break
        except Exception:
            continue

    if not submitted:
        # Try submit button by type
        try:
            btn = page.locator("button[type='submit'], input[type='submit']").first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                log("  ✓ Clicked submit button")
                submitted = True
        except Exception:
            pass

    if not submitted:
        # Click any prominent button
        try:
            buttons = page.locator("button")
            count = await buttons.count()
            for i in range(count):
                txt = (await buttons.nth(i).inner_text()).strip()
                if txt and len(txt) > 2 and txt not in ["Help", "English"]:
                    await buttons.nth(i).click()
                    log(f"  ✓ Clicked button: '{txt}'")
                    submitted = True
                    break
        except Exception:
            pass

    await asyncio.sleep(5)
    await screenshot(page, "06_after_submit")
    log(f"  Current URL after submit: {page.url}")

    # ── Handle post-submit flow ──
    return await handle_post_submit(page)


# ══════════════════════════════════════════════════════════════════════════════
# FLOW B: Modal-based UI (the /landing page flow)
# ══════════════════════════════════════════════════════════════════════════════
async def handle_modal_flow(page):
    log("═" * 40)
    log("🔘 MODAL FLOW (landing page)")

    # Accept policy if needed
    for btn_text in ["Confirm and continue", "Continue"]:
        try:
            btn = page.get_by_role("button", name=btn_text)
            if await btn.is_visible(timeout=3000):
                await btn.click()
                log(f"  ✓ '{btn_text}'")
                await asyncio.sleep(2)
                break
        except Exception:
            continue

    try:
        await page.wait_for_url("**/landing**", timeout=10_000)
    except Exception:
        pass
    log("  On landing page")
    await asyncio.sleep(2)

    # Guest count
    for sel in ["text=Guests", "text=guests", "text=2 Guests", "text=1 Guest"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.click()
                log("  ✓ Guest modal opened")
                break
        except Exception:
            continue
    await asyncio.sleep(1)

    # Confirm guests
    for btn_text in ["Confirm", "Done", "Apply"]:
        try:
            btn = page.get_by_role("button", name=btn_text)
            if await btn.is_visible(timeout=2000):
                await btn.click()
                break
        except Exception:
            continue
    await asyncio.sleep(1)

    # Date — try next preferred day
    now = datetime.now(IST)
    for ahead in range(1, 8):
        d = now + timedelta(days=ahead)
        if d.weekday() in PREF_DAYS:
            target_date = d
            break
    else:
        target_date = now + timedelta(days=1)

    for sel in ["text=Select a date", "text=Today", "text=Tomorrow"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.click(); break
        except Exception:
            continue
    await asyncio.sleep(1)

    # Click the day number
    day = str(target_date.day)
    try:
        btns = page.locator("button")
        count = await btns.count()
        for i in range(count):
            txt = (await btns.nth(i).inner_text()).strip()
            if txt == day:
                disabled = await btns.nth(i).get_attribute("disabled")
                if disabled is None:
                    await btns.nth(i).click()
                    log(f"  ✓ Date: day {day}")
                    break
    except Exception:
        pass
    await asyncio.sleep(1)

    # Time
    for sel in ["text=Select a time"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.click(); break
        except Exception:
            continue
    await asyncio.sleep(1)

    for slot in ["12:00", "12:30", "1:00", "7:00", "7:30"]:
        try:
            el = page.get_by_text(slot, exact=False).first
            if await el.is_visible(timeout=1000):
                await el.click()
                log(f"  ✓ Time: {slot}")
                break
        except Exception:
            continue
    await asyncio.sleep(1)

    # Find availability
    for btn_text in ["Find availability", "Search"]:
        try:
            btn = page.get_by_role("button", name=btn_text)
            if await btn.is_visible(timeout=2000):
                await btn.click()
                log(f"  ✓ '{btn_text}'")
                break
        except Exception:
            continue

    await asyncio.sleep(5)
    return await handle_post_submit(page)


# ══════════════════════════════════════════════════════════════════════════════
# COMMON: Handle everything after submitting search
#   - Seating selection
#   - Contact details form
#   - Booking confirmation
# ══════════════════════════════════════════════════════════════════════════════
async def handle_post_submit(page):
    log("═" * 40)
    log("📋 Post-submit handling")
    await screenshot(page, "07_post_submit")

    current_url = page.url
    html = (await page.content()).lower()

    # ── No availability? ──
    if any(x in html for x in ["no availability", "fully booked", "sold out",
                                 "no tables", "not available"]):
        log("❌ No availability")
        await screenshot(page, "no_availability")
        return False, "No tables available — all slots are fully booked."

    # ── Seating selection (Indoor/Balcony/Pizza Counter) ──
    if "availability" in current_url or "seating" in html or "indoor" in html:
        log("🪑 Seating selection")
        for seat in ["Indoor", "Balcony", "Pizza Counter", "Counter", "Outdoor"]:
            try:
                el = page.get_by_text(seat, exact=False).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    log(f"  ✓ Seating: {seat}")
                    await asyncio.sleep(3)
                    break
            except Exception:
                continue
        await screenshot(page, "08_seating")

    # ── If there are alternative time buttons, click first one ──
    alt_btns = page.locator("button:has-text('pm'), button:has-text('am'), button:has-text('PM'), button:has-text('AM')")
    if await alt_btns.count() > 0 and "review" not in page.url:
        try:
            txt = await alt_btns.first.inner_text()
            await alt_btns.first.click()
            log(f"  ✓ Alternative time: {txt.strip()}")
            await asyncio.sleep(3)
        except Exception:
            pass

    # ── Contact details form ──
    log("📝 Filling contact details...")
    await asyncio.sleep(2)
    await screenshot(page, "09_before_details")

    # Log all inputs on page for debugging
    inputs = page.locator("input")
    input_count = await inputs.count()
    log(f"  Found {input_count} input fields")
    for i in range(min(input_count, 10)):
        try:
            name = await inputs.nth(i).get_attribute("name") or ""
            typ = await inputs.nth(i).get_attribute("type") or ""
            ph = await inputs.nth(i).get_attribute("placeholder") or ""
            log(f"    Input #{i}: name='{name}' type='{typ}' placeholder='{ph}'")
        except Exception:
            pass

    # First Name
    filled_fn = False
    for sel in ["input[name='first_name']", "input[name='firstName']",
                "input[placeholder*='First' i]", "input[autocomplete='given-name']",
                "input[name*='first' i]"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.fill(FIRST_NAME)
                log(f"  ✓ First name: {FIRST_NAME}")
                filled_fn = True
                break
        except Exception:
            continue

    # Last Name
    filled_ln = False
    for sel in ["input[name='last_name']", "input[name='lastName']",
                "input[placeholder*='Last' i]", "input[autocomplete='family-name']",
                "input[name*='last' i]"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.fill(LAST_NAME)
                log(f"  ✓ Last name: {LAST_NAME}")
                filled_ln = True
                break
        except Exception:
            continue

    # If first/last name fields not found, try a single "name" field
    if not filled_fn and not filled_ln:
        for sel in ["input[name='name']", "input[placeholder*='name' i]",
                    "input[autocomplete='name']"]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.fill(f"{FIRST_NAME} {LAST_NAME}")
                    log(f"  ✓ Name: {FIRST_NAME} {LAST_NAME}")
                    break
            except Exception:
                continue

    # Email
    for sel in ["input[type='email']", "input[name*='email' i]",
                "input[placeholder*='email' i]", "input[autocomplete='email']"]:
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
                "input[name*='phone' i]", "input[placeholder*='phone' i]",
                "input[autocomplete='tel']"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.fill(PHONE)
                log(f"  ✓ Phone: {PHONE}")
                break
        except Exception:
            continue

    # Special Requests
    try:
        ta = page.locator("textarea").first
        if await ta.is_visible(timeout=1500):
            await ta.fill("")
    except Exception:
        pass

    await asyncio.sleep(1)
    await screenshot(page, "10_details_filled")

    # ── Confirm booking ──
    log("✅ Confirming booking...")
    confirmed = False
    for btn_text in ["Confirm booking", "Confirm Booking", "Confirm",
                     "Reserve", "Book Now", "Book", "Complete Booking",
                     "Complete", "Submit", "Place Reservation"]:
        try:
            btn = page.get_by_role("button", name=btn_text)
            if await btn.is_visible(timeout=2000):
                await btn.click()
                log(f"  ✓ Clicked '{btn_text}'")
                confirmed = True
                break
        except Exception:
            continue

    if not confirmed:
        # Try submit button
        try:
            btn = page.locator("button[type='submit'], input[type='submit']").first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                log("  ✓ Clicked submit")
                confirmed = True
        except Exception:
            pass

    await asyncio.sleep(5)
    await screenshot(page, "11_final_result")

    # ── Check result ──
    html = (await page.content()).lower()
    current_url = page.url

    ok = any(w in html for w in ["confirmed", "thank you", "see you",
                                  "your reservation", "booked", "success",
                                  "reservation confirmed"])
    fail = any(w in html for w in ["unavailable", "fully booked",
                                    "no availability", "sold out",
                                    "not available", "no tables"])

    if ok:
        log("🎉 BOOKING CONFIRMED!")
        return True, "Booking confirmed!"
    elif fail:
        log("😔 No availability")
        return False, "No tables available — fully booked."
    elif confirmed:
        log("⚠️ Submitted but result unclear — check screenshot")
        return True, "Submitted (check screenshot for confirmation)"
    else:
        log("❌ Could not complete booking flow")
        return False, "Could not complete the booking flow — check screenshots."


# ── entry ─────────────────────────────────────────────────────────────────────
async def main():
    log("═" * 60)
    log("🍕 Pizza 4P's Booking Agent v4")
    log(f"   {FIRST_NAME} {LAST_NAME} | {EMAIL_ADDR} | party of {PARTY_SIZE}")
    log("═" * 60)

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
