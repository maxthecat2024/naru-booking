"""
Pizza 4P's Indiranagar — automated booking script (v5 — VERIFIED)
Platform : TableCheck (tablecheck.com)
Schedule : Daily at 10:00 AM IST via GitHub Actions

VERIFIED FLOW (from live site, 2026-05-07 10:45 AM IST):
  1. /reserve/message    → "Confirm and continue" button
  2. /reserve/landing     → Guest count modal + Date calendar + Time picker
                            + "Find availability" button
  3. /reserve/availability → Either:
       a) Seating cards (Indoor / Balcony / Pizza Counter) — if slot is available
       b) "No availability" + alternative time buttons under future dates
  4. Click alternative time → /reserve/review (SKIPS seating selection!)
  5. /reserve/review      → "Complete Your Booking" form:
       - First name (REQ)
       - Last name (REQ)
       - Email (REQ)
       - Phone number (REQ) with 🇮🇳 flag, placeholder "081234 56789"
       - Reservation details (read-only summary)
       - Special Requests (textarea, optional)
       - Checkbox: "Receive offers..." (optional, skip it)
       - Purple button: "Confirm booking"

Strategy: Try the desired date/time first. If no availability, click the
  FIRST alternative time button shown. That takes us directly to review.
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

PREF_DAYS   = [4, 5, 6]  # Fri, Sat, Sun

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
            with open(attach, "rb") as f:
                p = MIMEBase("application", "octet-stream")
                p.set_payload(f.read())
            encoders.encode_base64(p)
            p.add_header("Content-Disposition", f"attachment; filename={attach.name}")
            msg.attach(p)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.sendmail(GMAIL_USER, EMAIL_ADDR, msg.as_string())
        log(f"📧 Email sent: {subject}")
    except Exception as e:
        log(f"❌ Email failed: {e}")

async def snap(page, label="screenshot"):
    SS_DIR.mkdir(exist_ok=True)
    p = SS_DIR / f"{label}.png"
    await page.screenshot(path=str(p), full_page=True)
    await page.screenshot(path=str(SS), full_page=True)
    log(f"📸 {label}")

def next_preferred_date():
    now = datetime.now(IST)
    for d in range(1, 8):
        dt = now + timedelta(days=d)
        if dt.weekday() in PREF_DAYS:
            return dt
    return now + timedelta(days=1)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN BOOKING FLOW
# ══════════════════════════════════════════════════════════════════════════════
async def book():
    async with async_playwright() as pw:
        br  = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        ctx = await br.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await ctx.new_page()

        try:
            # ── 1. OPEN + ACCEPT POLICY ──────────────────────────────────
            log(f"🌐 Opening {BASE_URL}/message")
            await page.goto(
                f"{BASE_URL}/message",
                wait_until="networkidle", timeout=30_000
            )
            await asyncio.sleep(3)
            await snap(page, "01_message_page")

            # Click "Confirm and continue" — button at bottom of long policy page
            # NOTE: Page has TWO matching elements (a div + a button).
            # The actual button has data-testid="Footer Button"
            policy_clicked = False

            # Method 1: Use the unique test ID (most reliable)
            try:
                btn = page.get_by_test_id("Footer Button")
                await btn.scroll_into_view_if_needed(timeout=5000)
                await asyncio.sleep(0.5)
                await btn.click()
                log("  ✓ 'Confirm and continue' (via test ID)")
                policy_clicked = True
            except Exception as e:
                log(f"  ⚠️ Test ID click failed: {e}")

            # Method 2: Target the <button> element specifically
            if not policy_clicked:
                try:
                    btn = page.locator("button:has-text('Confirm and continue')")
                    await btn.scroll_into_view_if_needed(timeout=5000)
                    await asyncio.sleep(0.5)
                    await btn.click()
                    log("  ✓ 'Confirm and continue' (via button selector)")
                    policy_clicked = True
                except Exception:
                    pass

            # Method 3: Scroll + JS click
            if not policy_clicked:
                log("  ⚠️ Fallback: JS click...")
                try:
                    await page.evaluate("""
                        const btn = document.querySelector('button[data-testid="Footer Button"]')
                            || document.querySelector('button[data-variant]');
                        if (btn) btn.click();
                    """)
                    log("  ✓ 'Confirm and continue' (via JS)")
                    policy_clicked = True
                except Exception as e:
                    log(f"  ❌ Could not click policy button: {e}")

            # Wait for landing page
            try:
                await page.wait_for_url("**/landing**", timeout=15_000)
            except Exception:
                # Maybe the URL didn't change but the page content did
                await asyncio.sleep(3)

            current = page.url
            log(f"  Current URL: {current}")
            await snap(page, "02_landing_page")

            if "landing" not in current:
                log("  ❌ FAILED to reach landing page!")
                log("  Attempting direct navigation to landing...")
                await page.goto(
                    f"{BASE_URL}/landing",
                    wait_until="networkidle", timeout=15_000
                )
                await asyncio.sleep(3)
                current = page.url
                log(f"  After direct nav: {current}")
                await snap(page, "02b_direct_landing")

                if "landing" not in current:
                    log("  ❌ Still not on landing — aborting")
                    await br.close()
                    return False, "Could not get past policy page"

            # ── 2. GUEST COUNT ───────────────────────────────────────────
            log(f"👥 Setting {PARTY_SIZE} guests")
            # Open guest modal
            for sel in ["text=Guests", "text=guests", "text=2 Guests",
                        "text=1 Guest"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        log("  ✓ Guest modal opened")
                        break
                except Exception:
                    continue
            await asyncio.sleep(1)

            # Adjust adults if needed (default is usually 2)
            if PARTY_SIZE != 2:
                try:
                    adults_row = page.locator("text=Adults").locator("..")
                    for _ in range(abs(PARTY_SIZE - 2)):
                        btn_sel = "button:has-text('+')" if PARTY_SIZE > 2 \
                                  else "button:has-text('-')"
                        await adults_row.locator(btn_sel).click()
                        await asyncio.sleep(0.3)
                except Exception as e:
                    log(f"  ⚠️ Guest adjust: {e}")

            # Confirm
            for txt in ["Confirm", "Done", "Apply"]:
                try:
                    btn = page.get_by_role("button", name=txt)
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        log(f"  ✓ Guests confirmed")
                        break
                except Exception:
                    continue
            await asyncio.sleep(1)

            # ── 3. SELECT DATE ───────────────────────────────────────────
            target = next_preferred_date()
            log(f"📅 Targeting {target.strftime('%A %b %d')}")

            # Open date picker
            for sel in ["text=Select a date", "text=Today", "text=Tomorrow"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        break
                except Exception:
                    continue
            await asyncio.sleep(1)

            # Click the target day number
            day_str = str(target.day)
            clicked = False
            try:
                btns = page.locator("button")
                count = await btns.count()
                for i in range(count):
                    txt = (await btns.nth(i).inner_text()).strip()
                    if txt == day_str:
                        disabled = await btns.nth(i).get_attribute("disabled")
                        aria = await btns.nth(i).get_attribute("aria-disabled")
                        if disabled is None and aria != "true":
                            await btns.nth(i).click()
                            log(f"  ✓ Selected day {day_str}")
                            clicked = True
                            break
            except Exception as e:
                log(f"  ⚠️ Date: {e}")

            if not clicked:
                log("  ⚠️ Could not select target date, trying first available")
            await asyncio.sleep(1)

            # ── 4. SELECT TIME ───────────────────────────────────────────
            log("🕐 Selecting time")
            for sel in ["text=Select a time"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        break
                except Exception:
                    continue
            await asyncio.sleep(1)

            # Pick first available time (prefer lunch/dinner)
            preferred = ["12:00", "12:30", "1:00", "1:30",
                         "7:00", "7:30", "8:00", "8:30",
                         "11:30", "11:00", "6:30", "6:00"]
            time_picked = False
            for slot in preferred:
                try:
                    el = page.get_by_text(slot, exact=False).first
                    if await el.is_visible(timeout=1000):
                        await el.click()
                        log(f"  ✓ Time: {slot}")
                        time_picked = True
                        break
                except Exception:
                    continue

            if not time_picked:
                log("  ⚠️ No preferred time, picking any available")
                try:
                    time_btns = page.locator(
                        "button:has-text('am'), button:has-text('pm')"
                    )
                    if await time_btns.count() > 0:
                        t = await time_btns.first.inner_text()
                        await time_btns.first.click()
                        log(f"  ✓ Time: {t.strip()}")
                except Exception:
                    pass
            await asyncio.sleep(1)

            # ── 5. FIND AVAILABILITY ─────────────────────────────────────
            log("🔍 Finding availability...")
            for txt in ["Find availability", "Search"]:
                try:
                    btn = page.get_by_role("button", name=txt)
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        log(f"  ✓ '{txt}'")
                        break
                except Exception:
                    continue

            await asyncio.sleep(3)

            # Wait for the availability page to FULLY load
            # The page shows loading skeleton cards initially, then fills
            # in with seating options (Indoor/Balcony/Pizza Counter) or
            # alternative dates. This can take 5-15 seconds.
            log("  ⏳ Waiting for availability page to load...")

            # Strategy: wait until buttons have actual text content
            for wait_i in range(20):
                # Check if any button has real text (not empty)
                btns = page.locator("button")
                count = await btns.count()
                has_text = False
                for bi in range(count):
                    try:
                        txt = (await btns.nth(bi).inner_text()).strip()
                        if len(txt) > 1 and txt not in ["<", ">"]:
                            has_text = True
                            break
                    except Exception:
                        pass

                html = (await page.content()).lower()
                if has_text or any(x in html for x in
                    ["indoor", "balcony", "pizza counter",
                     "no availability", "other dates with availability"]):
                    log(f"  ✓ Content loaded after {wait_i + 1}s")
                    break
                await asyncio.sleep(1)
            else:
                log("  ⚠️ Page may not have fully loaded after 20s")

            await snap(page, "03_availability")
            log(f"  URL: {page.url}")

            # Final wait + re-read
            await asyncio.sleep(2)
            html = (await page.content()).lower()

            # Debug: log all button texts
            btns = page.locator("button")
            count = await btns.count()
            log(f"  Buttons after load ({count}):")
            for bi in range(min(count, 15)):
                try:
                    txt = (await btns.nth(bi).inner_text()).strip()
                    log(f"    [{bi}]: '{txt}'")
                except Exception:
                    pass

            # ── 6. HANDLE AVAILABILITY PAGE ──────────────────────────────
            # NOTE: In headless mode, the page often shows seating cards as
            # empty skeleton buttons that never render text content.
            # The 9 empty buttons ARE the seating options (3 sections x 3 times).

            # CASE A: Try to find seating text (works in non-headless)
            seating_found = False
            for seat in ["Indoor", "Balcony", "Pizza Counter"]:
                try:
                    el = page.get_by_text(seat, exact=False).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        log(f"  🪑 Seating: {seat}")
                        seating_found = True
                        await asyncio.sleep(3)
                        break
                except Exception:
                    continue

            # CASE A2: If buttons are empty (skeleton), click the FIRST one
            # These ARE the seating cards, just not rendered with text
            if not seating_found:
                empty_btns = []
                all_btns = page.locator("button")
                total = await all_btns.count()
                for bi in range(total):
                    try:
                        txt = (await all_btns.nth(bi).inner_text()).strip()
                        if txt == "":
                            empty_btns.append(bi)
                    except Exception:
                        pass

                if len(empty_btns) >= 3:
                    # Multiple empty buttons = likely seating skeleton cards
                    log(f"  🪑 Clicking first empty button (skeleton seating card)")
                    try:
                        await all_btns.nth(empty_btns[0]).click()
                        await asyncio.sleep(3)
                        await snap(page, "04_after_skeleton_click")
                        log(f"  URL after click: {page.url}")
                        if "review" in page.url:
                            seating_found = True
                            log("  ✓ Reached review page via skeleton card!")
                    except Exception as e:
                        log(f"  ⚠️ Skeleton click failed: {e}")

            # CASE B: No availability — alternative times shown
            if not seating_found:
                log("  ⚠️ No direct availability — checking alternatives")
                await snap(page, "03b_checking_alts")

                # The alternative section shows dates like "Thu May 14"
                # with time buttons like "12:00 pm", "12:15 pm" etc.
                # Try multiple selectors for the time buttons
                alt_btns = None
                alt_count = 0

                for selector in [
                    "button:has-text('pm')",
                    "button:has-text('am')",
                    "button:has-text('PM')",
                    "button:has-text('AM')",
                    "button:has-text(':00')",
                    "button:has-text(':15')",
                    "button:has-text(':30')",
                    "button:has-text(':45')",
                ]:
                    try:
                        btns = page.locator(selector)
                        c = await btns.count()
                        if c > 0:
                            alt_btns = btns
                            alt_count = c
                            log(f"  Found {c} buttons via '{selector}'")
                            break
                    except Exception:
                        continue

                if alt_count == 0:
                    # Last resort: dump all button texts for debugging
                    all_btns = page.locator("button")
                    total = await all_btns.count()
                    log(f"  All buttons on page ({total}):")
                    for bi in range(min(total, 15)):
                        try:
                            t = await all_btns.nth(bi).inner_text()
                            log(f"    [{bi}]: '{t.strip()}'")
                        except Exception:
                            pass

                if alt_count > 0:
                    # Click the FIRST alternative time
                    alt_text = await alt_btns.first.inner_text()
                    await alt_btns.first.click()
                    log(f"  ✓ Selected alternative: {alt_text.strip()}")
                    await asyncio.sleep(3)
                    await snap(page, "04_after_alt_click")
                else:
                    # Also check for "Show dates after" button
                    try:
                        show_more = page.get_by_text("Show dates after", exact=False)
                        if await show_more.is_visible(timeout=2000):
                            await show_more.click()
                            log("  ✓ Clicked 'Show dates after'")
                            await asyncio.sleep(3)
                            # Try again
                            alt_btns = page.locator("button:has-text('pm'), button:has-text('am')")
                            if await alt_btns.count() > 0:
                                t = await alt_btns.first.inner_text()
                                await alt_btns.first.click()
                                log(f"  ✓ Alternative after expand: {t.strip()}")
                                await asyncio.sleep(3)
                            else:
                                log("  ❌ No alternatives even after expanding")
                                await snap(page, "no_alternatives")
                                await br.close()
                                return False, "No alternatives available."
                    except Exception:
                        log("  ❌ No alternatives available")
                        await snap(page, "no_alternatives")
                        await br.close()
                        return False, "No availability and no alternative times."

            # ── 7. FILL REVIEW FORM ──────────────────────────────────────
            # Should now be on /review page
            log(f"  URL: {page.url}")

            if "review" in page.url:
                log("📝 On review page — filling details")
            else:
                # Wait a moment for redirect
                await asyncio.sleep(3)
                log(f"  URL after wait: {page.url}")

            await snap(page, "05_review_page")

            # First name (REQ)
            for sel in ["input[name='first_name']", "input[name='firstName']",
                        "input[placeholder*='First' i]",
                        "input[autocomplete='given-name']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        await el.fill(FIRST_NAME)
                        log(f"  ✓ First name: {FIRST_NAME}")
                        break
                except Exception:
                    continue

            # Last name (REQ)
            for sel in ["input[name='last_name']", "input[name='lastName']",
                        "input[placeholder*='Last' i]",
                        "input[autocomplete='family-name']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        await el.fill(LAST_NAME)
                        log(f"  ✓ Last name: {LAST_NAME}")
                        break
                except Exception:
                    continue

            # Email (REQ)
            for sel in ["input[type='email']", "input[name*='email' i]",
                        "input[autocomplete='email']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        await el.fill(EMAIL_ADDR)
                        log(f"  ✓ Email: {EMAIL_ADDR}")
                        break
                except Exception:
                    continue

            # Phone number (REQ) — has intl-tel-input with 🇮🇳 flag
            for sel in ["input.iti__tel-input", "input[type='tel']",
                        "input[name*='phone' i]",
                        "input[placeholder*='081234' i]"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        await el.fill(PHONE)
                        log(f"  ✓ Phone: {PHONE}")
                        break
                except Exception:
                    continue

            # Special Requests (optional textarea)
            try:
                ta = page.locator("textarea").first
                if await ta.is_visible(timeout=1500):
                    await ta.fill("")
                    log("  ✓ Special requests: (empty)")
            except Exception:
                pass

            await asyncio.sleep(1)
            await snap(page, "06_form_filled")

            # ── 8. CONFIRM BOOKING ───────────────────────────────────────
            log("✅ Confirming booking...")
            confirmed = False
            for txt in ["Confirm booking", "Confirm Booking"]:
                try:
                    btn = page.get_by_role("button", name=txt)
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        log(f"  ✓ Clicked '{txt}'")
                        confirmed = True
                        break
                except Exception:
                    continue

            if not confirmed:
                # Fallback: find the purple submit button
                try:
                    btn = page.locator("button[type='submit']").first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        log("  ✓ Clicked submit button")
                        confirmed = True
                except Exception:
                    pass

            await asyncio.sleep(5)
            await snap(page, "07_final_result")

            # ── 9. CHECK RESULT ──────────────────────────────────────────
            html = (await page.content()).lower()
            final_url = page.url
            log(f"  Final URL: {final_url}")

            # Only count as success if we actually reached the review/confirm pages
            on_review = "review" in final_url
            on_confirm = "confirm" in final_url or "complete" in final_url

            ok = (on_review or on_confirm) and any(w in html for w in [
                "reservation confirmed", "thank you", "see you",
                "your reservation has been", "booking confirmed",
                "we look forward"
            ])
            fail = any(w in html for w in [
                "fully booked", "no availability",
                "sold out", "not available"
            ])

            await br.close()

            if ok:
                log("🎉 BOOKING CONFIRMED!")
                return True, "Booking confirmed!"
            elif confirmed and on_review:
                log("⚠️ Submitted from review page — check screenshot")
                return True, "Submitted from review page (check screenshot)"
            elif fail:
                log("😔 Booking failed")
                return False, "Booking failed — check screenshot."
            elif not on_review and not on_confirm:
                log("❌ Never reached the review page")
                return False, f"Stuck at {final_url} — never reached review."
            else:
                log("❌ Could not complete booking flow")
                return False, "Could not complete booking — check screenshots."

        except Exception:
            tb = traceback.format_exc()
            log(f"💥 {tb}")
            try:
                await page.screenshot(path=str(SS), full_page=True)
            except Exception:
                pass
            await br.close()
            return False, f"Script error — check logs."


# ── entry ─────────────────────────────────────────────────────────────────────
async def main():
    log("═" * 60)
    log("🍕 Pizza 4P's Booking Agent v5 (verified flow)")
    log(f"   {FIRST_NAME} {LAST_NAME} | {EMAIL_ADDR} | party of {PARTY_SIZE}")
    log("═" * 60)

    ok, detail = await book()

    subject = ("🎉 Pizza 4P's — BOOKED!" if ok
               else "❌ Pizza 4P's — no slot today")
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
    import sys
    sys.exit(asyncio.run(main()))
