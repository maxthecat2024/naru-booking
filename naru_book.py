"""
Naru Noodle Bar — automated booking script
Config via env vars: BOOKING_NAME, BOOKING_EMAIL, BOOKING_PHONE
Target slots: 12:30 PM or 2:30 PM | Any day Tue–Sun
"""

import asyncio
import os
import smtplib
import traceback
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# ── Config ────────────────────────────────────────────────────────────────────
NAME       = os.environ.get("BOOKING_NAME", "Your Name")
PHONE      = os.environ.get("BOOKING_PHONE", "0000000000")
EMAIL      = os.environ.get("BOOKING_EMAIL", "you@example.com")
PARTY_SIZE = "1"

# Slots in priority order — script tries each until one is available
SLOT_PRIORITY = ["12:30", "2:30", "12:30 PM", "2:30 PM", "12:30pm", "2:30pm"]
PREFERRED_DAYS = ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
                  "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

BOOKING_URL = "https://bookings.airmenus.in/eatnaru/order"
IST         = timezone(timedelta(hours=5, minutes=30))

# Email credentials from GitHub secrets
GMAIL_USER  = os.environ.get("GMAIL_USER", EMAIL)
GMAIL_PASS  = os.environ.get("GMAIL_APP_PASSWORD", "")   # Gmail App Password

SCREENSHOT_PATH = Path("booking_result.png")

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now(IST).strftime("%H:%M:%S IST")
    print(f"[{ts}] {msg}")


def send_email(subject: str, body: str, attachment: Path | None = None):
    """Send result email."""
    if not GMAIL_PASS:
        log("⚠️  GMAIL_APP_PASSWORD not set — skipping email notification")
        return
    try:
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_USER
        msg["To"]      = EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        if attachment and attachment.exists():
            with open(attachment, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={attachment.name}")
            msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, EMAIL, msg.as_string())
        log(f"📧 Email sent: {subject}")
    except Exception as e:
        log(f"❌ Email failed: {e}")


async def wait_until_8pm():
    """Async wait until 8:00:00 PM IST (with a tiny 50 ms head-start)."""
    now = datetime.now(IST)
    target = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if now >= target:
        log("Already past 8 PM IST — running immediately")
        return
    wait_sec = (target - now).total_seconds() - 0.05
    if wait_sec > 300:
        # If more than 5 min away, we're in a manual/test run — skip wait
        log(f"⚡ Manual/test run detected (>{wait_sec:.0f}s until 8 PM) — skipping wait, running now")
        return
    if wait_sec > 0:
        log(f"⏳ Waiting {wait_sec:.1f}s until 8:00 PM IST …")
        await asyncio.sleep(wait_sec)
    log("🚀 8:00 PM — GO!")


# ── Core automation ───────────────────────────────────────────────────────────

async def attempt_booking() -> tuple[bool, str]:
    """
    Open the Naru booking page and try to grab a slot.
    Returns (success: bool, detail_message: str).
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            log(f"🌐 Opening {BOOKING_URL}")
            await page.goto(BOOKING_URL, wait_until="networkidle", timeout=30_000)
            await asyncio.sleep(2)

            # ── Step 1: Select party size ──────────────────────────────────
            log("👤 Setting party size to 1 …")
            # Try common patterns: a dropdown, a radio, or a +/- counter
            try:
                # Pattern A: select element
                await page.select_option("select", PARTY_SIZE, timeout=4_000)
                log("  ✓ via <select>")
            except Exception:
                pass

            try:
                # Pattern B: number input
                num_input = page.locator("input[type='number']").first
                await num_input.fill(PARTY_SIZE, timeout=4_000)
                log("  ✓ via number input")
            except Exception:
                pass

            # Pattern C: click a "1" option button / radio
            for label in ["1", "1 Person", "1 Guest", "Party of 1"]:
                try:
                    btn = page.get_by_role("button", name=label).or_(
                          page.get_by_text(label, exact=True))
                    await btn.first.click(timeout=3_000)
                    log(f"  ✓ clicked '{label}'")
                    break
                except Exception:
                    continue

            await asyncio.sleep(1)

            # ── Step 2: Pick a day ─────────────────────────────────────────
            log("📅 Selecting a preferred day …")
            day_clicked = False
            for day in PREFERRED_DAYS:
                try:
                    day_el = page.get_by_text(day, exact=False).first
                    await day_el.click(timeout=3_000)
                    log(f"  ✓ selected day: {day}")
                    day_clicked = True
                    break
                except Exception:
                    continue
            if not day_clicked:
                log("  ⚠️  Could not identify day selector — proceeding anyway")

            await asyncio.sleep(1)

            # ── Step 3: Pick a time slot ───────────────────────────────────
            log("🕐 Selecting preferred time slot …")
            slot_clicked = False
            for slot in SLOT_PRIORITY:
                try:
                    slot_el = page.get_by_text(slot, exact=False).first
                    await slot_el.click(timeout=3_000)
                    log(f"  ✓ selected slot: {slot}")
                    slot_clicked = True
                    break
                except Exception:
                    continue

            if not slot_clicked:
                # Fallback: click the first available slot-like button
                try:
                    first_slot = page.locator(
                        "button, [role='button'], .slot, .time-slot"
                    ).first
                    text = await first_slot.inner_text()
                    await first_slot.click(timeout=3_000)
                    log(f"  ✓ clicked first available option: '{text.strip()}'")
                    slot_clicked = True
                except Exception:
                    log("  ❌ No slot found — all full or page structure changed")
                    await page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
                    await browser.close()
                    return False, "No slots available or page layout changed. Screenshot attached."

            await asyncio.sleep(1)

            # ── Step 4: Fill personal details ─────────────────────────────
            log("📝 Filling in personal details …")

            # Name
            for sel in ["input[placeholder*='name' i]", "input[name*='name' i]",
                        "input[id*='name' i]", "input[type='text']"]:
                try:
                    await page.fill(sel, NAME, timeout=3_000)
                    log(f"  ✓ name filled via '{sel}'")
                    break
                except Exception:
                    continue

            # Phone
            for sel in ["input[placeholder*='phone' i]", "input[name*='phone' i]",
                        "input[type='tel']", "input[id*='phone' i]"]:
                try:
                    await page.fill(sel, PHONE, timeout=3_000)
                    log(f"  ✓ phone filled via '{sel}'")
                    break
                except Exception:
                    continue

            # Email
            for sel in ["input[type='email']", "input[placeholder*='email' i]",
                        "input[name*='email' i]"]:
                try:
                    await page.fill(sel, EMAIL, timeout=3_000)
                    log(f"  ✓ email filled via '{sel}'")
                    break
                except Exception:
                    continue

            await asyncio.sleep(1)

            # ── Step 5: Submit ─────────────────────────────────────────────
            log("✅ Submitting booking …")
            for label in ["Confirm", "Book", "Reserve", "Submit", "Place Booking",
                          "Book Now", "Confirm Booking"]:
                try:
                    btn = page.get_by_role("button", name=label)
                    await btn.click(timeout=4_000)
                    log(f"  ✓ clicked '{label}'")
                    break
                except Exception:
                    continue

            await asyncio.sleep(3)
            await page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)

            # ── Step 6: Check result ───────────────────────────────────────
            content = (await page.content()).lower()
            success_signals = ["confirmed", "booking confirmed", "reservation confirmed",
                               "thank you", "booked", "success", "see you"]
            fail_signals    = ["unavailable", "fully booked", "no slots", "sold out",
                               "not available", "sorry"]

            if any(s in content for s in success_signals):
                log("🎉 BOOKING CONFIRMED!")
                await browser.close()
                return True, "Booking confirmed! Screenshot attached."
            elif any(s in content for s in fail_signals):
                log("😢 No slots available this week.")
                await browser.close()
                return False, "All slots were full by the time we got in. Try again next Monday!"
            else:
                log("⚠️  Unclear result — screenshot attached for manual review.")
                await browser.close()
                return False, "Submission sent but result unclear. Check the screenshot and your email for confirmation."

        except Exception:
            tb = traceback.format_exc()
            log(f"💥 Error:\n{tb}")
            try:
                await page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
            except Exception:
                pass
            await browser.close()
            return False, f"Script error:\n\n<pre>{tb}</pre>"


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    log("═" * 60)
    log("🍜 Naru Noodle Bar Booking Agent — starting")
    log(f"   Name:  {NAME}")
    log(f"   Email: {EMAIL}")
    log(f"   Phone: {PHONE}")
    log(f"   Slots: 12:30 PM → 2:30 PM (in preference order)")
    log("═" * 60)

    await wait_until_8pm()

    success, detail = await attempt_booking()

    if success:
        subject = "🎉 Naru booked! See you at the ramen bar"
        body = f"""
        <h2>You're in! 🍜</h2>
        <p>Your Naru Noodle Bar booking for <strong>1 person</strong> has been confirmed.</p>
        <p>Check the screenshot below for full details.</p>
        <p>Address: Ground Floor, Courtyard, 105, Kengal Hanumanthaiah Road, Shanti Nagar, Bengaluru</p>
        <hr/>
        <p style="color:#888;font-size:12px;">Booked automatically by your Naru booking agent.</p>
        """
    else:
        subject = "❌ Naru booking attempt — no luck this week"
        body = f"""
        <h2>No booking this week 😔</h2>
        <p>{detail}</p>
        <p>The agent will try again next <strong>Monday at 8:00 PM IST</strong> automatically.</p>
        <p>Screenshot of the page at submission time is attached.</p>
        <hr/>
        <p style="color:#888;font-size:12px;">Naru Booking Agent</p>
        """

    send_email(subject, body, SCREENSHOT_PATH if SCREENSHOT_PATH.exists() else None)
    log("Done." if success else "No booking secured — will retry next week.")
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
