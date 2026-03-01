"""
send_email.py — Send weekly LinkedIn post options via Gmail API (OAuth 2.0)

Authentication  : reads GMAIL_TOKEN JSON from environment variable
Token refresh   : handled automatically by google-auth library (uses refresh_token)
Recipient       : matthieu.jammers@gmail.com
Sender          : matthieu.jammers@gmail.com
Schedule        : called by main.py every Monday 00:00 UTC
"""

import os
import json
import base64
from datetime import datetime
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── Config ─────────────────────────────────────────────────────────────────────

RECIPIENT = "matthieu.jammers@gmail.com"
SENDER    = "matthieu.jammers@gmail.com"
SCOPES    = ["https://www.googleapis.com/auth/gmail.send"]

DIVIDER   = "════════════════════════════════════════"


# ── Gmail Authentication ───────────────────────────────────────────────────────

def get_gmail_service():
    """
    Build an authenticated Gmail service client.

    Reads the full token JSON (including refresh_token) from the GMAIL_TOKEN
    environment variable. The google-auth library automatically refreshes
    the access token when it expires — no manual intervention needed.
    """
    token_json = os.environ.get("GMAIL_TOKEN")
    if not token_json:
        raise EnvironmentError(
            "GMAIL_TOKEN environment variable is not set. "
            "Add it as a GitHub Secret (see README.md for instructions)."
        )

    token_data = json.loads(token_json)
    creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    # Refresh access token if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build("gmail", "v1", credentials=creds)
    return service


# ── Helpers ────────────────────────────────────────────────────────────────────

def read_time_seconds(text):
    """Estimate reading time at 200 words per minute."""
    words = len(text.split())
    return max(1, round((words / 200) * 60))


def char_count(text):
    return len(text)


# ── Email Body Builder ─────────────────────────────────────────────────────────

def format_day_section(day_label, date_str, theme,
                        data, warning, pillar1, pillar2):
    """
    Format one day's section (Tuesday or Thursday) of the weekly email.
    Follows the exact layout specified in the brief.
    """
    opt1    = data.get("option1_post",   "[Post generation failed — please write manually]")
    opt2    = data.get("option2_post",   "[Post generation failed — please write manually]")
    why1    = data.get("option1_why",    "Strategic angle unavailable.")
    why2    = data.get("option2_why",    "Strategic angle unavailable.")
    vis1    = data.get("option1_visual", "Image description unavailable.")
    vis2    = data.get("option2_visual", "Image description unavailable.")
    rec     = data.get("recommendation", "Option 1 — strong hook with clear educational value.")

    c1 = char_count(opt1)
    c2 = char_count(opt2)
    rt1 = read_time_seconds(opt1)
    rt2 = read_time_seconds(opt2)

    warning_block = f"\n{warning}\n" if warning else ""

    day_upper = day_label.upper()

    section = f"""
{DIVIDER}
{day_upper} {date_str} — Theme: {theme}
{DIVIDER}
{warning_block}
── OPTION 1 — {pillar1} ──
Why this works: {why1}

{opt1}

Character count: {c1} | Read time: {rt1} seconds
Suggested visual: {vis1}

── OPTION 2 — {pillar2} ──
Why this works: {why2}

{opt2}

Character count: {c2} | Read time: {rt2} seconds
Suggested visual: {vis2}

★ MY RECOMMENDATION FOR {day_upper}: {rec}
"""
    return section


def build_email_body(results):
    """
    Assemble the full email body from generation results.
    Follows the exact format specified in the brief.
    """
    rotation  = results["rotation"]
    tue_data  = results["tuesday_data"]
    thu_data  = results["thursday_data"]

    tue_section = format_day_section(
        "Tuesday",
        results["tuesday_date"],
        rotation["tuesday_theme"],
        tue_data,
        results["tuesday_warning"],
        rotation["tuesday_pillar1"],
        rotation["tuesday_pillar2"],
    )

    thu_section = format_day_section(
        "Thursday",
        results["thursday_date"],
        rotation["thursday_theme"],
        thu_data,
        results["thursday_warning"],
        rotation["thursday_pillar1"],
        rotation["thursday_pillar2"],
    )

    # Research summary — drawn from Tuesday's AI response
    research_summary = tue_data.get(
        "research_summary",
        "Research data unavailable this week — fallback sources were used."
    )
    profile_check = tue_data.get(
        "profile_check",
        "Profile analysis unavailable — LinkedIn scraping was restricted this week."
    )
    sources = tue_data.get(
        "sources",
        "Fallback news sources: The Jakarta Post, Rumah.com, The Bali Sun, Lamudi Indonesia."
    )

    body = f"""Hi Matthieu,

Here are your four LinkedIn post options for this week.

Tuesday post   → publish at 11:00 AM Bali time
Thursday post  → publish at 11:00 AM Bali time

{DIVIDER}
RESEARCH SUMMARY
{DIVIDER}

LinkedIn trends this week: {research_summary}

Profile check: {profile_check}

Sources used: {sources}
{tue_section}
{thu_section}

{DIVIDER}
NEXT DELIVERY
{DIVIDER}

Next email:      Monday {results['next_monday']} at 08:00 AM Bali time
Tuesday theme:   {results['next_tuesday_theme']}
Thursday theme:  {results['next_thursday_theme']}
"""
    return body


# ── Send Functions ─────────────────────────────────────────────────────────────

def send_weekly_email(results):
    """
    Build and send the weekly LinkedIn options email.
    Subject format: "Your LinkedIn Posts for the Week — 9 March 2026"
    """
    service = get_gmail_service()

    today       = datetime.utcnow()
    date_label  = today.strftime("%-d %B %Y")
    subject     = f"Your LinkedIn Posts for the Week — {date_label}"

    body    = build_email_body(results)
    message = MIMEText(body, "plain", "utf-8")
    message["to"]      = RECIPIENT
    message["from"]    = SENDER
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

    print(f"  ✓ Email sent to {RECIPIENT}")
    print(f"  ✓ Subject: {subject}")
    return True


def send_failure_email(error_message):
    """
    Send a failure notification email so Matthieu knows to post manually.
    Safe to call even if the main generation failed — uses minimal dependencies.
    """
    try:
        service = get_gmail_service()
    except Exception as e:
        print(f"  ✗ Could not authenticate Gmail for failure notification: {e}")
        return

    today   = datetime.utcnow().strftime("%-d %B %Y")
    subject = f"⚠️ LinkedIn Automation Failed — {today}"

    body = f"""Hi Matthieu,

The LinkedIn post automation system encountered an error this week and could not complete your posts.

Error details:
{error_message}

What to do:
Please generate your LinkedIn posts manually for this week.

You can also re-trigger the automation by going to:
https://github.com/scalrize/linkedin-automation
→ Click the "Actions" tab
→ Click "LinkedIn Weekly Post Generator"
→ Click "Run workflow"

If the error keeps happening, check that all four GitHub Secrets are still valid:
  • GEMINI_API_KEY
  • GMAIL_TOKEN
  • FIRECRAWL_API_KEY

See README.md for instructions on refreshing any expired credentials.

This message was sent automatically by the LinkedIn Automation system.
"""

    try:
        message = MIMEText(body, "plain", "utf-8")
        message["to"]      = RECIPIENT
        message["from"]    = SENDER
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print(f"  ✓ Failure notification sent to {RECIPIENT}")
    except Exception as e:
        print(f"  ✗ Could not send failure notification: {e}")
