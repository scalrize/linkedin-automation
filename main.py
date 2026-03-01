"""
main.py — Master pipeline: scrape → generate → send email → log

Run order:
  1. scraper.py   — Scrape LinkedIn profile + industry content (with fallback)
  2. generate_post.py — Generate 4 post options via Gemini 1.5 Pro
  3. send_email.py    — Send formatted weekly email via Gmail API
  4. Log results to post_log.txt (committed back to repo by GitHub Actions)

Retry logic:
  - Email sending: 1 retry after 30 seconds
  - Gemini API:    handled inside generate_post.py (3 attempts per day)
  - Scraping:      handled inside scraper.py (graceful fallback, never crashes)

On any fatal error, a failure notification email is sent to matthieu.jammers@gmail.com.
"""

import os
import sys
import time
import traceback
from datetime import datetime


# ── Logging Helper ─────────────────────────────────────────────────────────────

def section(title):
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def write_log(results, scraping_status):
    """
    Append a structured log entry to post_log.txt.
    This file is committed back to the GitHub repo by the Actions workflow
    so the rotation state persists across weekly runs.
    """
    rotation    = results["rotation"]
    today_str   = datetime.utcnow().strftime("%Y-%m-%d")

    tue_hook1 = results["tuesday_data"].get("option1_hook",   "")[:100]
    tue_hook2 = results["tuesday_data"].get("option2_hook",   "")[:100]
    thu_hook1 = results["thursday_data"].get("option1_hook",  "")[:100]
    thu_hook2 = results["thursday_data"].get("option2_hook",  "")[:100]

    entry = (
        f"[{today_str}] | Run: SUCCESS\n"
        f"Tuesday theme: {rotation['tuesday_theme']} | "
        f"Tuesday pillars: {rotation['tuesday_pillar1']} + {rotation['tuesday_pillar2']}\n"
        f"Thursday theme: {rotation['thursday_theme']} | "
        f"Thursday pillars: {rotation['thursday_pillar1']} + {rotation['thursday_pillar2']}\n"
        f'Tuesday hook 1: "{tue_hook1}"\n'
        f'Tuesday hook 2: "{tue_hook2}"\n'
        f'Thursday hook 1: "{thu_hook1}"\n'
        f'Thursday hook 2: "{thu_hook2}"\n'
        f"Email sent: YES | Scraping: {scraping_status}\n"
    )

    with open("post_log.txt", "a") as f:
        f.write("\n" + entry)


def write_failure_log(stage, error):
    """Append a failure entry to post_log.txt."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    entry = f"\n[{today_str}] | Run: FAILED at {stage}\nError: {str(error)[:300]}\n"
    try:
        with open("post_log.txt", "a") as f:
            f.write(entry)
    except Exception:
        pass  # Don't let log failure mask the real error


# ── Main Pipeline ──────────────────────────────────────────────────────────────

def main():
    start_time = datetime.utcnow()
    print(f"\nLinkedIn Automation Pipeline")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    scraping_status = "FALLBACK"
    scraping_context = (
        "Scraping unavailable. Write from professional expertise only. "
        "Do not fabricate market data."
    )
    results = None

    # ─────────────────────────────────────────────────────────────
    # STEP 1 — SCRAPING
    # Non-fatal: pipeline continues even if scraping fails entirely
    # ─────────────────────────────────────────────────────────────
    section("STEP 1/4 — Scraping (LinkedIn + Fallback Sources)")
    try:
        from scraper import run_scraper
        scraping_context, scraping_status = run_scraper()
        print(f"\n  Scraping status: {scraping_status}")
    except Exception as exc:
        print(f"\n  Scraping exception (non-fatal): {exc}")
        print("  Continuing with fallback context...")
        scraping_status = "FALLBACK"

    # ─────────────────────────────────────────────────────────────
    # STEP 2 — GENERATION
    # Fatal: if generation fails, send failure email and exit
    # ─────────────────────────────────────────────────────────────
    section("STEP 2/4 — Generating Posts with Gemini 1.5 Pro")
    try:
        from generate_post import generate_all_posts
        results = generate_all_posts(scraping_context)
        print("\n  Post generation complete.")
    except Exception as exc:
        error_msg = (
            f"Post generation failed:\n\n"
            f"{traceback.format_exc()}\n\n"
            f"Scraping status was: {scraping_status}"
        )
        print(f"\n  FATAL: {exc}")
        write_failure_log("generation", exc)
        _try_send_failure_email(error_msg)
        sys.exit(1)

    # ─────────────────────────────────────────────────────────────
    # STEP 3 — EMAIL
    # Retried once after 30 seconds; fatal if both attempts fail
    # ─────────────────────────────────────────────────────────────
    section("STEP 3/4 — Sending Weekly Email via Gmail")
    email_sent = False
    for attempt in range(1, 3):
        try:
            from send_email import send_weekly_email
            send_weekly_email(results)
            email_sent = True
            break
        except Exception as exc:
            print(f"\n  Email attempt {attempt} failed: {exc}")
            if attempt < 2:
                print("  Retrying in 30 seconds...")
                time.sleep(30)

    if not email_sent:
        error_msg = (
            f"Email sending failed after 2 attempts.\n\n"
            f"{traceback.format_exc()}\n\n"
            f"Posts WERE generated successfully but could not be delivered. "
            f"Check GMAIL_TOKEN secret — it may need refreshing."
        )
        write_failure_log("email", "Failed after 2 attempts")
        _try_send_failure_email(error_msg)
        sys.exit(1)

    # ─────────────────────────────────────────────────────────────
    # STEP 4 — LOGGING
    # Non-fatal: pipeline is considered successful even if log fails
    # ─────────────────────────────────────────────────────────────
    section("STEP 4/4 — Writing to post_log.txt")
    try:
        write_log(results, scraping_status)
        print("  post_log.txt updated successfully.")
    except Exception as exc:
        print(f"  Warning: Could not write log — {exc}")
        print("  (This is non-fatal — rotation will restart from defaults next week.)")

    # ─────────────────────────────────────────────────────────────
    # DONE
    # ─────────────────────────────────────────────────────────────
    elapsed = (datetime.utcnow() - start_time).seconds
    section(f"PIPELINE COMPLETE — {elapsed}s elapsed")
    print(f"  Scraping:  {scraping_status}")
    print(f"  Email:     SENT to matthieu.jammers@gmail.com")
    print(f"  Log:       post_log.txt updated")
    print(f"  Themes:    "
          f"Tue={results['rotation']['tuesday_theme'][:30]} | "
          f"Thu={results['rotation']['thursday_theme'][:30]}")
    print()


# ── Failure Email Helper ───────────────────────────────────────────────────────

def _try_send_failure_email(error_message):
    """Attempt to send failure notification — never raises."""
    try:
        from send_email import send_failure_email
        send_failure_email(error_message)
    except Exception as exc:
        print(f"  Could not send failure notification: {exc}")
        print("  Please check matthieu.jammers@gmail.com manually this week.")


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
