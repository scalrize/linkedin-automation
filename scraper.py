"""
scraper.py — Scrape LinkedIn profile and industry content using Firecrawl.

Scrape 1 : Matthieu's LinkedIn profile → voice analysis, recent posts, topics covered
Scrape 2 : Industry LinkedIn posts → trending topics, questions, formats
Fallback  : If LinkedIn blocks scraping, use verified real estate news sources
Safety    : Never crashes the pipeline — always returns a usable context string
"""

import os
import time
import json

try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    print("  Warning: firecrawl-py not installed — running in fallback mode.")

# ── Config ─────────────────────────────────────────────────────────────────────

LINKEDIN_PROFILE_URL = "https://www.linkedin.com/in/matthieu-jammers-a40a0726/"

# Verified fallback sources (from the brief)
FALLBACK_NEWS_URLS = [
    "https://www.thejakartapost.com/topic/property",
    "https://www.rumah.com/panduan-properti",
    "https://thebalibible.com",
    "https://www.balisun.com",
    "https://indonesia-expat.biz/category/business-finance/property/",
    "https://www.lamudi.co.id/journal/",
]

# Industry search keywords for Bali/Indonesia real estate
INDUSTRY_KEYWORDS = [
    "bali real estate investment 2025 2026",
    "indonesia property law foreign buyers leasehold freehold",
    "bali villa construction permit PBG IMB",
    "lombok property development investment",
    "PT PMA nominee structure indonesia property risk",
]

# Max characters per scraped document (to avoid token overload)
MAX_CHARS_PROFILE  = 4000
MAX_CHARS_INDUSTRY = 2000
MAX_CHARS_FALLBACK = 2000


# ── Firecrawl Initialisation ───────────────────────────────────────────────────

def get_firecrawl():
    """Return an initialised FirecrawlApp or None if unavailable."""
    if not FIRECRAWL_AVAILABLE:
        return None
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("  Warning: FIRECRAWL_API_KEY not set — running in fallback mode.")
        return None
    return FirecrawlApp(api_key=api_key)


# ── Scrape Helpers ─────────────────────────────────────────────────────────────

def safe_scrape(app, url, max_chars=3000, timeout=25000):
    """
    Scrape a single URL with Firecrawl. Returns markdown string or None.
    Never raises — logs and returns None on any failure.
    """
    try:
        result = app.scrape_url(
            url,
            params={"formats": ["markdown"], "timeout": timeout},
        )
        if result and result.get("markdown"):
            return result["markdown"][:max_chars]
    except Exception as exc:
        print(f"    Scrape failed for {url}: {exc}")
    return None


# ── Scrape 1: LinkedIn Profile ─────────────────────────────────────────────────

def scrape_profile(app):
    """
    Scrape Matthieu's LinkedIn profile.
    Returns structured dict or None on failure.
    """
    print("  → Scraping Matthieu's LinkedIn profile...")
    content = safe_scrape(app, LINKEDIN_PROFILE_URL, max_chars=MAX_CHARS_PROFILE)
    if content:
        print("    ✓ Profile scraped successfully.")
        return {"success": True, "content": content, "url": LINKEDIN_PROFILE_URL}
    print("    ✗ Profile scraping failed — using fallback guidance.")
    return None


# ── Scrape 2: Industry LinkedIn Content ───────────────────────────────────────

def scrape_industry(app):
    """
    Search for industry LinkedIn posts via Google site-search through Firecrawl.
    Returns list of {keyword, content} dicts (may be empty if all fail).
    """
    print("  → Scraping LinkedIn industry content...")
    results = []

    for keyword in INDUSTRY_KEYWORDS[:3]:  # Limit to 3 to avoid rate limiting
        search_url = (
            f"https://www.google.com/search?q="
            f"site:linkedin.com+{keyword.replace(' ', '+')}"
        )
        content = safe_scrape(app, search_url, max_chars=MAX_CHARS_INDUSTRY, timeout=20000)
        if content:
            results.append({"keyword": keyword, "content": content})
            print(f"    ✓ Industry content found for: {keyword}")
        else:
            print(f"    ✗ No industry content for: {keyword}")
        time.sleep(1.5)  # Polite rate limiting

    return results


# ── Fallback: Verified News Sources ───────────────────────────────────────────

def scrape_fallback_sources(app):
    """
    Scrape verified Bali/Indonesia real estate news sources as fallback.
    Returns list of {source, content} dicts.
    """
    print("  → Scraping fallback news sources...")
    results = []

    for url in FALLBACK_NEWS_URLS[:4]:  # Limit to 4 sources
        content = safe_scrape(app, url, max_chars=MAX_CHARS_FALLBACK, timeout=20000)
        if content:
            results.append({"source": url, "content": content})
            print(f"    ✓ Fallback source scraped: {url}")
        else:
            print(f"    ✗ Fallback source failed: {url}")
        time.sleep(1)

    return results


# ── Context Builder ────────────────────────────────────────────────────────────

def build_scraping_context(profile_data, industry_data, fallback_data, status):
    """
    Assemble the scraping results into a single readable context string
    that will be injected into the Gemini prompt.
    """
    lines = [f"[SCRAPING STATUS: {status}]\n"]

    # ── Profile section ──
    lines.append("=== MATTHIEU'S LINKEDIN PROFILE ===")
    if profile_data and profile_data.get("success"):
        lines.append(profile_data["content"])
    else:
        lines.append(
            "Profile scraping was unavailable this week. "
            "Write in the established voice based on previous posts. "
            "Avoid repeating any themes likely covered in the past 60 days for "
            "an active Bali real estate professional."
        )
    lines.append("")

    # ── Industry content section ──
    if industry_data:
        lines.append("=== LINKEDIN INDUSTRY CONTENT (Bali/Indonesia Real Estate) ===")
        for item in industry_data:
            lines.append(f"[Search: {item['keyword']}]")
            lines.append(item["content"])
            lines.append("")

    # ── Fallback news section ──
    if fallback_data:
        lines.append("=== VERIFIED NEWS SOURCES (Fallback) ===")
        for item in fallback_data:
            lines.append(f"[Source: {item['source']}]")
            lines.append(item["content"])
            lines.append("")

    # ── No data available ──
    if not profile_data and not industry_data and not fallback_data:
        lines.append("=== SCRAPING UNAVAILABLE ===")
        lines.append(
            "All scraping attempts failed. Write posts based on deep professional "
            "expertise in Bali/Indonesia real estate using only verified knowledge. "
            "Do NOT fabricate market data. Note in the research summary that "
            "live scraping was unavailable this week and that posts rely on "
            "established market knowledge as of 2025-2026."
        )

    return "\n".join(lines)


# ── Main Entry Point ───────────────────────────────────────────────────────────

def run_scraper():
    """
    Run the full scraping pipeline.
    Returns (context_string, status_string).
    Status: "SUCCESS" | "PARTIAL" | "FALLBACK"
    Never raises — all failures are handled gracefully.
    """
    app = get_firecrawl()

    if not app:
        context = build_scraping_context(None, [], [], "FALLBACK")
        return context, "FALLBACK"

    profile_data  = None
    industry_data = []
    fallback_data = []
    status        = "SUCCESS"

    # ── Step 1: Profile ──
    profile_data = scrape_profile(app)
    if not profile_data:
        status = "PARTIAL"

    # ── Step 2: Industry content ──
    industry_data = scrape_industry(app)
    if not industry_data:
        status = "PARTIAL"

        # ── Step 3: Fallback sources (only if industry failed) ──
        fallback_data = scrape_fallback_sources(app)
        if fallback_data:
            print("  ✓ Fallback sources retrieved.")
        else:
            status = "FALLBACK"
            print("  ✗ All fallback sources also failed — proceeding without scraped data.")

    context = build_scraping_context(profile_data, industry_data, fallback_data, status)
    print(f"\n  Scraping complete — Status: {status}")
    return context, status
