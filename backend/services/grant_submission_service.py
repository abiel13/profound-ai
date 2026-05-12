"""
Grant Submission Data Engine
============================

For a given grant opportunity URL we try to extract:
  - submission_url     : where to actually apply (portal, form, or main page)
  - submission_email   : a mail-to / 'apply via email' contact
  - submission_type    : 'portal' | 'email' | 'form' | 'unknown'
  - apply_instructions : short human-readable hint pulled from the page

Design choices:
  - Single-page scrape only (no crawling) — fast (<3s typical).
  - Robust to bad SSL / missing pages — never raises, returns ('unknown', None).
  - No 3rd-party listings (no idealist / opportunitydesk / fundsforngos
    URLs are filtered out — we keep only what looks like an official donor
    domain, i.e. the domain of the opportunity URL itself).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

# ---- Heuristics --------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

APPLY_KEYWORDS = (
    "apply now", "apply online", "apply here", "submit application",
    "submit proposal", "submit your application", "start application",
    "begin application", "application form", "apply", "submission",
)

PORTAL_HINTS = (
    "submittable.com", "fluxx.io", "smartsimple", "wizehive", "foundant",
    "grantsplatform", "openwater.com", "/portal", "/apply", "/submit",
)

EMAIL_HINTS = (
    "send your", "email your proposal", "submit by email", "via email to",
    "send to", "mail to", "applications should be sent",
)

# Filter out 3rd-party aggregators when extracting "apply" links.
EXCLUDED_DOMAINS = (
    "facebook.com", "twitter.com", "x.com", "linkedin.com", "youtube.com",
    "instagram.com", "fundsforngos.org", "opportunitydesk.org",
    "opportunitiesforafricans.com", "fundsforngosjobs.com", "idealist.org",
)


# ---- Public API --------------------------------------------------------

def extract_emails_from_page(html: str) -> List[str]:
    """Return unique emails found in the page, deprioritising no-reply/info."""
    if not html:
        return []
    raw = EMAIL_RE.findall(html)
    seen: List[str] = []
    for e in raw:
        e = e.lower().strip(".,;)")
        if e in seen:
            continue
        # Drop image/asset false positives like @2x.png addresses
        if any(e.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
            continue
        seen.append(e)

    def _rank(em: str) -> int:
        # Lower number = higher priority
        if em.startswith(("grants@", "grant@", "applications@", "apply@",
                          "proposals@", "submissions@", "funding@")):
            return 0
        if em.startswith(("info@", "contact@", "hello@")):
            return 2
        if em.startswith(("noreply@", "no-reply@", "donotreply@")):
            return 5
        return 1

    seen.sort(key=_rank)
    return seen[:5]


def extract_apply_link(html: str, base_url: str) -> Optional[str]:
    """Find the most likely 'Apply' link on the page."""
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    candidates: List[tuple[int, str]] = []  # (score, abs_url)

    base_host = urlparse(base_url).netloc.lower()

    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip().lower()
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        abs_url = urljoin(base_url, href)
        host = urlparse(abs_url).netloc.lower()
        if any(bad in host for bad in EXCLUDED_DOMAINS):
            continue

        score = 0
        for kw in APPLY_KEYWORDS:
            if kw in text:
                score += 5
                break
        for hint in PORTAL_HINTS:
            if hint in abs_url.lower():
                score += 4
                break
        # Prefer same-domain or known portal domains
        if host == base_host:
            score += 1
        elif any(hint in host for hint in PORTAL_HINTS):
            score += 3

        if score > 0:
            candidates.append((score, abs_url))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def detect_submission_type(html: str, apply_link: Optional[str], emails: List[str]) -> str:
    """Return 'portal' | 'email' | 'form' | 'unknown'."""
    if apply_link:
        low = apply_link.lower()
        if any(p in low for p in PORTAL_HINTS):
            return "portal"
        if low.endswith((".pdf", ".doc", ".docx")):
            return "form"
        # An apply link going to the same site is usually a portal/form page.
        return "portal"

    text = (html or "").lower()
    if emails and any(hint in text for hint in EMAIL_HINTS):
        return "email"
    if emails:
        # We have an email but no specific 'send to' instruction — best guess.
        return "email"
    return "unknown"


def _short_instructions(html: str) -> str:
    """Pull a short, human-readable hint from the page (~250 chars)."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(soup.stripped_strings)
    text = re.sub(r"\s+", " ", text)
    # Find a sentence containing 'apply' / 'submit'
    for kw in ("how to apply", "to apply", "submission", "submit your",
               "applications should", "deadline"):
        m = re.search(rf"([^.]{{0,150}}{re.escape(kw)}[^.]{{0,150}}\.)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:300]
    return text[:250]


async def fetch_submission_details(grant_url: str, timeout: float = 8.0) -> Dict[str, Optional[str]]:
    """
    Scrape a single grant page and return submission metadata.

    Always returns a dict — never raises. Missing/failed fields are returned
    as empty strings so the caller can store them as-is.
    """
    out: Dict[str, Optional[str]] = {
        "submission_url": "",
        "submission_email": "",
        "submission_type": "unknown",
        "apply_instructions": "",
    }
    if not grant_url or not grant_url.startswith(("http://", "https://")):
        return out

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers=headers, verify=False
        ) as client:
            resp = await client.get(grant_url)
            html = resp.text if resp.status_code < 400 else ""
    except Exception:
        return out

    if not html:
        return out

    emails = extract_emails_from_page(html)
    apply_link = extract_apply_link(html, grant_url)
    sub_type = detect_submission_type(html, apply_link, emails)
    instructions = _short_instructions(html)

    out["submission_url"] = apply_link or grant_url
    out["submission_email"] = emails[0] if emails else ""
    out["submission_type"] = sub_type
    out["apply_instructions"] = instructions
    return out
