"""
send_email.py — Send weekly LinkedIn post options via Gmail SMTP + App Password

Authentication  : GMAIL_APP_PASSWORD environment variable (never expires)
Recipient       : matthieu.jammers@gmail.com
Sender          : matthieu.jammers@gmail.com
Schedule        : called by main.py every Sunday night
"""

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

# ── Config ─────────────────────────────────────────────────────────────────────

RECIPIENT = "matthieu.jammers@gmail.com"
SENDER    = "matthieu.jammers@gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

DIVIDER   = "════════════════════════════════════════"


# ── Gmail Authentication ───────────────────────────────────────────────────────

def send_via_smtp(subject, body):
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not app_password:
        raise EnvironmentError(
            "GMAIL_APP_PASSWORD environment variable is not set. "
            "Add it as a GitHub Secret."
        )

    message = MIMEText(body, "plain", "utf-8")
    message["to"]      = RECIPIENT
    message["from"]    = SENDER
    message["subject"] = subject

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER, app_password.replace(" ", ""))
        server.sendmail(SENDER, RECIPIENT, message.as_bytes())


# ── Helpers ────────────────────────────────────────────────────────────────────

def read_time_seconds(text):
    words = len(text.split())
    return max(1, round((words / 200) * 60))


def char_count(text):
    return len(text)


# ── Email Body Builder ─────────────────────────────────────────────────────────

def format_day_section(day_label, date_str, theme,
                        data, warning, pillar1, pillar2):
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
    today      = datetime.utcnow()
    date_label = today.strftime("%-d %B %Y")
    subject    = f"Your LinkedIn Posts for the Week — {date_label}"
    body       = build_email_body(results)

    send_via_smtp(subject, body)
    print(f"  ✓ Email sent to {RECIPIENT}")
    print(f"  ✓ Subject: {subject}")
    return True


def send_failure_email(error_message):
    today   = datetime.utcnow().strftime("%-d %B %Y")
    subject = f"LinkedIn Automation Failed — {today}"

    body = f"""Hi Matthieu,

The LinkedIn post automation encountered an error and could not generate your posts this week.

Error details:
{error_message}

What to do:
Re-trigger manually: GitHub → scalrize/linkedin-automation → Actions → LinkedIn Weekly Post Generator → Run workflow

If the error keeps happening, check that all GitHub Secrets are still valid:
  ANTHROPIC_API_KEY
  GMAIL_APP_PASSWORD
  FIRECRAWL_API_KEY

This message was sent automatically by the LinkedIn Automation system.
"""

    try:
        send_via_smtp(subject, body)
        print(f"  ✓ Failure notification sent to {RECIPIENT}")
    except Exception as e:
        print(f"  ✗ Could not send failure notification: {e}")
