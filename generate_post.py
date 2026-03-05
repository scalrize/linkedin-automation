"""
generate_post.py — LinkedIn Post Generator using Claude (Anthropic API)

Reads linkedin_prompt.md, injects scraping context, generates 4 validated
post options per week (2 for Tuesday + 2 for Thursday).

Theme rotation  : Sales Techniques → Bali Market → Legal → Construction → repeat
Pillar rotation : The Educator → The Perspective → The Human → The Proof → repeat
Validation      : hook < 200 chars, total 1200-1600 chars, no banned phrases
Retry logic     : up to 3 attempts per day; includes best version with warning on failure
"""

import os
import time
from datetime import datetime, timedelta

import anthropic

# ── Constants ──────────────────────────────────────────────────────────────────

THEMES = [
    "Sales Techniques in Real Estate",
    "Bali, Lombok & Surrounding Islands Real Estate Market",
    "Legal Framework for Foreign Buyers in Indonesia",
    "Construction Due Diligence in Bali",
]

PILLARS = [
    "The Educator",
    "The Perspective",
    "The Human",
    "The Proof",
]

BANNED_PHRASES = [
    "Exciting news",
    "Thrilled to announce",
    "Game-changer",
    "Synergy",
    "In today's fast-paced world",
    "I am pleased to share",
    "Leverage",
    "Innovative",
    "Passionate",
    "Thought leader",
    "Best practices",
]

POST_LOG_PATH = "post_log.txt"
PROMPT_PATH = "linkedin_prompt.md"

# ── Log Parsing ────────────────────────────────────────────────────────────────

def read_last_log():
    """Read the last entry from post_log.txt to determine rotation state."""
    if not os.path.exists(POST_LOG_PATH) or os.path.getsize(POST_LOG_PATH) == 0:
        return {}

    with open(POST_LOG_PATH, "r") as f:
        content = f.read().strip()

    blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
    if not blocks:
        return {}

    last = blocks[-1]
    result = {}

    for line in last.split("\n"):
        if "Tuesday theme:" in line:
            part = line.split("Tuesday theme:")[1]
            result["tuesday_theme"] = part.split("|")[0].strip()
        if "Thursday theme:" in line:
            part = line.split("Thursday theme:")[1]
            result["thursday_theme"] = part.split("|")[0].strip()
        if "Tuesday pillars:" in line:
            part = line.split("Tuesday pillars:")[1].strip()
            result["tuesday_pillars"] = [p.strip() for p in part.split("+")]
        if "Thursday pillars:" in line:
            part = line.split("Thursday pillars:")[1].strip()
            result["thursday_pillars"] = [p.strip() for p in part.split("+")]

    return result


def _theme_index(name):
    """Return index of theme matching name, or -1."""
    for i, t in enumerate(THEMES):
        if t.lower() in name.lower() or name.lower() in t.lower():
            return i
    return -1


def _pillar_index(name):
    """Return index of pillar matching name, or -1."""
    for i, p in enumerate(PILLARS):
        if p.lower() in name.lower() or name.lower() in p.lower():
            return i
    return -1


def get_rotation(last_log=None):
    """
    Determine themes and pillars for this week using the ISO week number.

    This approach requires NO persistent state — it is always deterministic.
    Each ISO week maps to a fixed combination of theme and pillar, so the
    rotation cycles automatically without any file storage or git commits.

    4-week theme cycle:  Sales → Bali Market → Legal → Construction → repeat
    4-week pillar cycle: rotates 2 pillars per day, offset between Tue/Thu
    """
    week_num = datetime.utcnow().isocalendar()[1]   # ISO week 1-53

    n = len(THEMES)    # 4
    p = len(PILLARS)   # 4

    tue_theme_idx  = week_num % n
    thu_theme_idx  = (week_num + 1) % n

    # Pillars: each week advances by 2 so both options change every week
    tue_p1_idx = (week_num * 2) % p
    tue_p2_idx = (week_num * 2 + 1) % p
    # Thursday offset by +2 so it never duplicates Tuesday's pillars in the same week
    thu_p1_idx = (week_num * 2 + 2) % p
    thu_p2_idx = (week_num * 2 + 3) % p

    return {
        "tuesday_theme":    THEMES[tue_theme_idx],
        "thursday_theme":   THEMES[thu_theme_idx],
        "tuesday_pillar1":  PILLARS[tue_p1_idx],
        "tuesday_pillar2":  PILLARS[tue_p2_idx],
        "thursday_pillar1": PILLARS[thu_p1_idx],
        "thursday_pillar2": PILLARS[thu_p2_idx],
    }


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_post(post_text, hook):
    """Return (is_valid, list_of_issues)."""
    issues = []

    if len(hook) > 200:
        issues.append(f"Hook too long: {len(hook)} chars (max 200)")

    total = len(post_text)
    if total < 1200:
        issues.append(f"Post too short: {total} chars (min 1200)")
    if total > 1600:
        issues.append(f"Post too long: {total} chars (max 1600)")

    for phrase in BANNED_PHRASES:
        if phrase.lower() in post_text.lower():
            issues.append(f"Banned phrase: '{phrase}'")

    return (len(issues) == 0), issues


# ── Output Parsing ─────────────────────────────────────────────────────────────

def _extract(text, tag):
    """
    Extract text between XML tags: <TAG>...</TAG>.
    Claude outputs XML tags reliably. Falls back to case-insensitive search.
    """
    open_tag  = f"<{tag}>"
    close_tag = f"</{tag}>"
    try:
        s = text.index(open_tag) + len(open_tag)
        e = text.index(close_tag)
        return text[s:e].strip()
    except ValueError:
        # Case-insensitive fallback
        text_lower = text.lower()
        try:
            s = text_lower.index(open_tag.lower()) + len(open_tag)
            e = text_lower.index(close_tag.lower())
            return text[s:e].strip()
        except ValueError:
            return ""


def parse_day_response(text):
    """Parse structured Gemini response for one day's two options."""
    return {
        "research_summary": _extract(text, "RESEARCH_SUMMARY"),
        "profile_check":    _extract(text, "PROFILE_CHECK"),
        "sources":          _extract(text, "SOURCES"),
        "option1_post":     _extract(text, "OPTION1_POST"),
        "option1_hook":     _extract(text, "OPTION1_HOOK"),
        "option1_why":      _extract(text, "OPTION1_WHY"),
        "option1_visual":   _extract(text, "OPTION1_VISUAL"),
        "option2_post":     _extract(text, "OPTION2_POST"),
        "option2_hook":     _extract(text, "OPTION2_HOOK"),
        "option2_why":      _extract(text, "OPTION2_WHY"),
        "option2_visual":   _extract(text, "OPTION2_VISUAL"),
        "recommendation":   _extract(text, "RECOMMENDATION"),
    }


# ── Prompt Builder ─────────────────────────────────────────────────────────────

def build_day_prompt(base_prompt, day, date_str, theme, pillar1, pillar2, scraping_context):
    """Assemble the full prompt for one day's generation."""
    banned_str = ", ".join(f'"{p}"' for p in BANNED_PHRASES)

    return f"""{base_prompt}

---

## CURRENT GENERATION TASK

Generate exactly TWO LinkedIn post options for **{day} {date_str}**.

- **THEME (both options):** {theme}
- **OPTION 1 CONTENT PILLAR:** {pillar1}
- **OPTION 2 CONTENT PILLAR:** {pillar2}

### SCRAPING CONTEXT
{scraping_context}

---

## MANDATORY VALIDATION RULES — CHECK BEFORE OUTPUTTING

- Hook (first line) must be UNDER 200 characters
- Total post length must be 1,200 to 1,600 characters (inclusive)
- Banned phrases — NEVER use any of these: {banned_str}
- Both options must cover the same theme but from different angles
- Both options must use their specified content pillar
- Active voice throughout — no passive constructions

---

## STRICT OUTPUT FORMAT

CRITICAL: Use ONLY the XML tags below. Do not write anything outside them.
Do NOT use markdown, code blocks, or backticks anywhere in your response.

<RESEARCH_SUMMARY>
2-3 sentences on what is trending in Bali/Indonesia real estate right now, based on scraping context. If scraping failed, note it briefly.
</RESEARCH_SUMMARY>

<PROFILE_CHECK>
Topics covered in Matthieu's last 60 days that were avoided this week. Note the top performing post style observed from his profile. If profile was unavailable, state so.
</PROFILE_CHECK>

<SOURCES>
Comma-separated list of publication or source names used for this week's research
</SOURCES>

<OPTION1_POST>
Full LinkedIn post — {pillar1} pillar — 1,200 to 1,600 characters, hook under 200 chars, no banned phrases, ends with low-friction question CTA, max 5 hashtags at the bottom
</OPTION1_POST>

<OPTION1_HOOK>
First line of Option 1 only — must be under 200 characters
</OPTION1_HOOK>

<OPTION1_WHY>
One sentence explaining the strategic angle that makes Option 1 effective this week
</OPTION1_WHY>

<OPTION1_VISUAL>
Specific image or graphic description for Option 1 — e.g. "Aerial photo of a Pererenan villa with pool, golden hour lighting"
</OPTION1_VISUAL>

<OPTION2_POST>
Full LinkedIn post — {pillar2} pillar — 1,200 to 1,600 characters, hook under 200 chars, no banned phrases, meaningfully different angle from Option 1, ends with low-friction question CTA, max 5 hashtags at the bottom
</OPTION2_POST>

<OPTION2_HOOK>
First line of Option 2 only — must be under 200 characters
</OPTION2_HOOK>

<OPTION2_WHY>
One sentence explaining the strategic angle that makes Option 2 effective this week
</OPTION2_WHY>

<OPTION2_VISUAL>
Specific image or graphic description for Option 2
</OPTION2_VISUAL>

<RECOMMENDATION>
Option [1 or 2] — One sentence explaining why this option is the stronger choice this specific week
</RECOMMENDATION>
"""


# ── Generation with Retry ──────────────────────────────────────────────────────

def generate_for_day(client, base_prompt, day, date_str,
                     theme, pillar1, pillar2, scraping_context):
    """
    Generate two post options for one day with up to 3 validation attempts.
    Returns (parsed_dict, warning_string_or_None).
    """
    prompt = build_day_prompt(
        base_prompt, day, date_str, theme, pillar1, pillar2, scraping_context
    )

    last_parsed = None
    last_issues = []

    for attempt in range(1, 4):
        print(f"  [{day}] Attempt {attempt}/3 ...")
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = parse_day_response(message.content[0].text)
            last_parsed = parsed

            opt1  = parsed.get("option1_post", "")
            opt2  = parsed.get("option2_post", "")
            hook1 = parsed.get("option1_hook", "")
            hook2 = parsed.get("option2_hook", "")

            if not opt1 or not opt2:
                print(f"  [{day}] Attempt {attempt}: Could not parse posts — retrying")
                time.sleep(5)
                continue

            valid1, issues1 = validate_post(opt1, hook1)
            valid2, issues2 = validate_post(opt2, hook2)

            if valid1 and valid2:
                print(f"  [{day}] Attempt {attempt}: Validation passed ✓")
                return parsed, None

            all_issues = (
                [f"Opt1 — {i}" for i in issues1] +
                [f"Opt2 — {i}" for i in issues2]
            )
            last_issues = all_issues
            print(f"  [{day}] Attempt {attempt}: Issues — {'; '.join(all_issues)}")
            time.sleep(3)

        except Exception as exc:
            print(f"  [{day}] Attempt {attempt}: Exception — {exc}")
            time.sleep(10)

    # All 3 attempts failed — return best available with a manual review warning
    warning = (
        "⚠️  MANUAL REVIEW NEEDED: This post failed automated validation after "
        "3 attempts. Please check character count (target 1,200–1,600), ensure the "
        f"hook is under 200 characters, and remove any banned phrases before posting. "
        f"Validation issues detected: {'; '.join(last_issues)}"
    )
    print(f"  [{day}] All 3 attempts failed — including best version with warning.")
    return last_parsed or {}, warning


# ── Helpers ────────────────────────────────────────────────────────────────────

def read_time_seconds(text):
    """Estimate reading time in seconds at 200 wpm."""
    words = len(text.split())
    return max(1, round((words / 200) * 60))


# ── Main Entry Point ───────────────────────────────────────────────────────────

def generate_all_posts(scraping_context):
    """
    Generate all four posts and return a structured results dict.
    Called by main.py with the scraping context string.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    print("  Using Claude model: claude-sonnet-4-6")

    with open(PROMPT_PATH, "r") as f:
        base_prompt = f.read()

    rotation = get_rotation()

    # ── Calculate target dates ──
    today = datetime.utcnow()
    dow   = today.weekday()          # 0 = Monday … 6 = Sunday
    days_to_tue = (1 - dow) % 7 or 7
    tuesday  = today + timedelta(days=days_to_tue)
    thursday = tuesday + timedelta(days=2)

    tue_str = tuesday.strftime("%-d %B %Y")
    thu_str = thursday.strftime("%-d %B %Y")

    # ── Generate ──
    print(f"\n  Generating Tuesday posts — Theme: {rotation['tuesday_theme']}")
    tue_data, tue_warning = generate_for_day(
        client, base_prompt,
        "Tuesday", tue_str,
        rotation["tuesday_theme"],
        rotation["tuesday_pillar1"],
        rotation["tuesday_pillar2"],
        scraping_context,
    )

    print(f"\n  Generating Thursday posts — Theme: {rotation['thursday_theme']}")
    thu_data, thu_warning = generate_for_day(
        client, base_prompt,
        "Thursday", thu_str,
        rotation["thursday_theme"],
        rotation["thursday_pillar1"],
        rotation["thursday_pillar2"],
        scraping_context,
    )

    # ── Next week preview (for NEXT DELIVERY section of email) ──
    thu_idx       = _theme_index(rotation["thursday_theme"])
    next_tue_theme = THEMES[(thu_idx + 1) % len(THEMES)]
    next_thu_theme = THEMES[(thu_idx + 2) % len(THEMES)]

    days_to_next_mon = (7 - dow) % 7 or 7
    next_monday = today + timedelta(days=days_to_next_mon)
    next_monday_str = next_monday.strftime("%-d %B %Y")

    return {
        "rotation":           rotation,
        "tuesday_date":       tue_str,
        "thursday_date":      thu_str,
        "tuesday_data":       tue_data,
        "tuesday_warning":    tue_warning,
        "thursday_data":      thu_data,
        "thursday_warning":   thu_warning,
        "next_monday":        next_monday_str,
        "next_tuesday_theme": next_tue_theme,
        "next_thursday_theme": next_thu_theme,
    }
