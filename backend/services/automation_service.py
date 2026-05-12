"""
Automation Service (V12.3)
==========================

Three compact, single-user automation primitives:

1. scan_grants(filters)  — returns a batch of grant leads from well-known
   international donors. Uses AI if EMERGENT_LLM_KEY is set; otherwise
   returns a curated static list of real funder entry URLs.

2. generate_email_draft(kind, ctx) — returns subject + body + CTA +
   attachments checklist. AI path with deterministic fallback.

3. generate_donor_prospects(filters) — returns a list of prospect orgs.
   HARD RULE: NEVER invent contact emails or phones. If a contact isn't
   a well-known public address, email/phone are left blank and
   manual_lookup_required = True.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from services.ai_client import call_ai, extract_json

logger = logging.getLogger(__name__)


KNOWN_SOURCES = [
    "UNICEF", "UNDP", "EU Funding & Tenders", "USAID", "GIZ",
    "African Development Bank", "GlobalGiving", "Gates Foundation",
    "Ford Foundation", "Embassy small grants", "NGO funding calls",
]


# ====================================================================
# 1. GRANT SCANNER
# ====================================================================

async def scan_grants(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    sectors = filters.get("sectors") or []
    region = filters.get("region") or "Africa"
    sources = filters.get("sources") or KNOWN_SOURCES

    ai_items = await _ai_scan(sectors, region, sources)
    if ai_items:
        return ai_items
    return _static_scan(sectors, region, sources)


async def _ai_scan(sectors, region, sources) -> List[Dict[str, Any]]:
    try:
        system = (
            "You are a grant-intelligence assistant for Pro Youth Foundation, "
            "a Namibian non-profit helping vulnerable children. Return a JSON "
            "array of current, real, well-known grant / funding opportunities "
            "from the specified funders. For each item, include the official "
            "donor URL if you are confident. If you are not confident about a "
            "URL or email, leave it blank rather than invent one. Output JSON only."
        )
        user = f"""Scan these funders: {', '.join(sources)}
Sectors of interest: {', '.join(sectors) if sectors else 'child protection, education, food security, housing'}
Region focus: {region}

Return JSON:
{{
  "items": [
    {{
      "title": "",
      "funder": "",
      "amount_text": "e.g. USD 10,000 - 100,000",
      "deadline": "e.g. 2026-06-30 or 'Rolling'",
      "country_eligibility": "",
      "sector": "",
      "official_url": "",
      "submission_type": "portal | email | form | unknown",
      "submission_email": "",
      "fit_score": 0,
      "summary": "1-2 sentences, concrete."
    }}
  ]
}}

Rules:
- 6 to 10 items
- fit_score 0-100 for Pro Youth Foundation (child protection in Namibia)
- Never invent contact emails. Leave submission_email blank if unknown."""
        text = await call_ai(system, user)
        data = extract_json(text)
        items = data.get("items") if isinstance(data, dict) else None
        if isinstance(items, list) and len(items) >= 3:
            return [_clean_scan_item(i) for i in items[:12]]
        return []
    except Exception as e:
        logger.info("grant scan AI fallback: %s", e)
        return []


def _clean_scan_item(i: Dict[str, Any]) -> Dict[str, Any]:
    i = dict(i or {})
    i.setdefault("title", "")
    i.setdefault("funder", "")
    i.setdefault("amount_text", "")
    i.setdefault("deadline", "")
    i.setdefault("country_eligibility", "")
    i.setdefault("sector", "")
    i.setdefault("official_url", "")
    i.setdefault("submission_type", "unknown")
    i.setdefault("submission_email", "")
    i["fit_score"] = int(i.get("fit_score") or 0)
    i.setdefault("summary", "")
    return i


def _static_scan(sectors, region, sources) -> List[Dict[str, Any]]:
    """Curated real-world entry URLs. Zero invented contact details."""
    base = [
        {"title": "UNICEF Venture Fund — child-focused innovation",
         "funder": "UNICEF",
         "amount_text": "USD 100,000 equity-free + mentorship",
         "deadline": "Rolling",
         "country_eligibility": "UNICEF programme countries (Namibia included)",
         "sector": "child protection",
         "official_url": "https://www.unicef.org/innovation/venturefund",
         "submission_type": "portal",
         "submission_email": "",
         "fit_score": 78,
         "summary": "Equity-free investment for tech-for-good start-ups helping children. "
                    "Strong fit for digital safeguarding / education tools."},
        {"title": "UNDP Small Grants Programme",
         "funder": "UNDP",
         "amount_text": "USD 5,000 - 50,000",
         "deadline": "Announced annually per country office",
         "country_eligibility": "Namibia (UNDP country office)",
         "sector": "poverty relief",
         "official_url": "https://sgp.undp.org/",
         "submission_type": "portal",
         "submission_email": "",
         "fit_score": 72,
         "summary": "Community-led projects in SDG priority areas. Submit via SGP national office."},
        {"title": "EU Funding & Tenders Portal — Global Gateway calls",
         "funder": "European Union",
         "amount_text": "EUR 100,000+",
         "deadline": "Rolling (per call)",
         "country_eligibility": "Africa-wide",
         "sector": "education",
         "official_url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
         "submission_type": "portal",
         "submission_email": "",
         "fit_score": 60,
         "summary": "Subscribe to the EU portal and filter by 'child protection' and 'Namibia'."},
        {"title": "USAID small grants — Development Innovation Ventures",
         "funder": "USAID",
         "amount_text": "USD 200,000 - 5M",
         "deadline": "Rolling",
         "country_eligibility": "USAID-supported countries",
         "sector": "education",
         "official_url": "https://www.usaid.gov/div",
         "submission_type": "portal",
         "submission_email": "",
         "fit_score": 55,
         "summary": "Stage-gated funding for evidence-based social innovations."},
        {"title": "GIZ civil-society cooperation calls",
         "funder": "GIZ",
         "amount_text": "EUR 10,000 - 200,000",
         "deadline": "Announced per call",
         "country_eligibility": "Namibia (active GIZ country)",
         "sector": "safe housing",
         "official_url": "https://www.giz.de/en/worldwide/296.html",
         "submission_type": "portal",
         "submission_email": "",
         "fit_score": 68,
         "summary": "GIZ Namibia runs several civil-society grant windows each year."},
        {"title": "African Development Bank — Youth Entrepreneurship & Innovation Trust Fund",
         "funder": "African Development Bank",
         "amount_text": "USD 100,000 - 500,000",
         "deadline": "Announced per window",
         "country_eligibility": "Africa-wide",
         "sector": "education",
         "official_url": "https://www.afdb.org/en/topics-and-sectors/initiatives-partnerships/youth-entrepreneurship-innovation-multi-donor-trust-fund",
         "submission_type": "portal",
         "submission_email": "",
         "fit_score": 62,
         "summary": "Supports youth-focused NGOs and social enterprises in Africa."},
        {"title": "GlobalGiving — join a campaign",
         "funder": "GlobalGiving",
         "amount_text": "USD 5,000+ matching",
         "deadline": "Rolling",
         "country_eligibility": "Worldwide",
         "sector": "food security",
         "official_url": "https://www.globalgiving.org/apply/",
         "submission_type": "portal",
         "submission_email": "",
         "fit_score": 75,
         "summary": "Become a vetted partner, run matching campaigns."},
        {"title": "Gates Foundation — Open Calls",
         "funder": "Gates Foundation",
         "amount_text": "Varies",
         "deadline": "Per call",
         "country_eligibility": "Global",
         "sector": "child protection",
         "official_url": "https://www.gatesfoundation.org/about/committed-grants",
         "submission_type": "portal",
         "submission_email": "",
         "fit_score": 50,
         "summary": "Periodic thematic calls. Watch the 'Open Opportunities' page."},
    ]
    # Optional filter by sector keyword
    if sectors:
        low = [s.lower() for s in sectors]
        filtered = [b for b in base
                    if any(s in (b["sector"] + " " + b["summary"]).lower() for s in low)]
        return filtered or base
    return base


# ====================================================================
# 2. EMAIL DRAFT GENERATOR
# ====================================================================

DRAFT_TYPES = ("grant", "sponsor", "thank_you", "follow_up", "reapply")


async def generate_email_draft(kind: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    kind = (kind or "grant").lower()
    if kind not in DRAFT_TYPES:
        kind = "grant"
    ai = await _ai_draft(kind, ctx)
    if ai:
        return ai
    return _template_draft(kind, ctx)


async def _ai_draft(kind: str, ctx: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        recipient = ctx.get("recipient_name") or "Grants Team"
        org = ctx.get("organization") or ""
        context = ctx.get("context") or ""
        system = (
            "You write professional non-profit emails for Pro Youth Foundation "
            "(Namibia). Be warm, specific, short. Output JSON only."
        )
        user = f"""Generate an email of type: {kind}
Recipient: {recipient}
Their organization: {org}
Extra context: {context}

Return JSON:
{{
  "subject": "",
  "body": "<plain text, 3-6 short paragraphs>",
  "cta": "<1-line call-to-action>",
  "attachments": ["Cover Letter", "Proposal", ...]
}}"""
        text = await call_ai(system, user)
        data = extract_json(text)
        if isinstance(data, dict) and data.get("subject") and data.get("body"):
            data.setdefault("cta", "")
            data.setdefault("attachments", [])
            return data
        return None
    except Exception:
        return None


def _template_draft(kind: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    recipient = ctx.get("recipient_name") or "Grants Team"
    org = ctx.get("organization") or ""
    topic = ctx.get("context") or "our current funding priorities"
    org_name = ctx.get("sender_org") or "Pro Youth Foundation"

    catalogue = {
        "grant": {
            "subject": f"Grant Application — {org_name}",
            "body": (f"Dear {recipient},\n\nI am writing on behalf of {org_name}, a Namibian "
                     f"non-profit working with vulnerable children. We would like to apply for "
                     f"{topic}.\n\nOur proposal, budget and supporting documents are attached. "
                     f"We would be glad to provide any additional information.\n\nKind regards,\n{org_name}"),
            "cta": "Kindly acknowledge receipt of this application.",
            "attachments": ["Cover Letter", "Project Narrative", "Budget", "Monitoring Plan", "Org Profile"],
        },
        "sponsor": {
            "subject": f"Partnership proposal — {org_name} × {org or 'your company'}",
            "body": (f"Dear {recipient},\n\n{org_name} works with vulnerable children in Namibia. "
                     f"I am reaching out to explore a partnership with {org or 'your company'} around "
                     f"{topic}.\n\nAttached you will find a short sponsorship brief with tiers, benefits "
                     f"and expected impact. We can tailor a package for your CSR priorities.\n\n"
                     f"Would you be open to a 15-minute introduction call next week?\n\n"
                     f"Kind regards,\n{org_name}"),
            "cta": "Could we book 15 minutes next week for a quick intro call?",
            "attachments": ["Sponsorship Brief", "Org Profile", "Recent Impact Report"],
        },
        "thank_you": {
            "subject": f"Thank you — your gift changed a day at {org_name}",
            "body": (f"Dear {recipient},\n\nOn behalf of every child we serve, thank you. Your gift "
                     f"was received and directly supports {topic}.\n\nAttached you will find your "
                     f"receipt and our latest delivery update. We will keep you posted with photos "
                     f"and totals as we progress.\n\nWith gratitude,\n{org_name}"),
            "cta": "Reply to this email if you'd like a dedicated donor update.",
            "attachments": ["Receipt", "Delivery Update Photos"],
        },
        "follow_up": {
            "subject": f"Quick follow-up — {org_name}",
            "body": (f"Dear {recipient},\n\nJust following up on my note about {topic}. I know how "
                     f"busy your team is, so this is a short nudge in case the earlier email slipped "
                     f"past.\n\nHappy to resend any document or to answer questions.\n\n"
                     f"Kind regards,\n{org_name}"),
            "cta": "Could you share an update or the best next step?",
            "attachments": ["(resend previous attachments if needed)"],
        },
        "reapply": {
            "subject": f"Renewed application — {org_name}",
            "body": (f"Dear {recipient},\n\nThank you for reviewing our previous application. "
                     f"We have incorporated the feedback and would like to resubmit a strengthened "
                     f"proposal for {topic}.\n\nKey improvements: clearer outcomes, updated budget, "
                     f"stronger M&E plan. All documents are attached.\n\nKind regards,\n{org_name}"),
            "cta": "Please confirm the renewed application is under review.",
            "attachments": ["Updated Cover Letter", "Revised Proposal", "Updated Budget", "M&E Plan"],
        },
    }
    return catalogue[kind]


# ====================================================================
# 3. DONOR PROSPECT GENERATOR
# ====================================================================

PROSPECT_CATEGORIES = (
    "Namibian companies", "banks", "pharmacies", "supermarkets",
    "lodges/hotels", "churches", "embassies", "CSR departments",
    "foundations", "NGOs", "international donors", "local businesses",
)


async def generate_donor_prospects(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    categories = filters.get("categories") or list(PROSPECT_CATEGORIES[:6])
    country = filters.get("country") or "Namibia"
    city = filters.get("city") or "Windhoek"

    ai_items = await _ai_prospects(categories, country, city)
    if ai_items:
        return [_clean_prospect(p) for p in ai_items]
    return [_clean_prospect(p) for p in _static_prospects(categories, country, city)]


async def _ai_prospects(categories, country, city) -> List[Dict[str, Any]]:
    try:
        system = (
            "You are a fundraising researcher for Pro Youth Foundation (Namibia). "
            "Suggest real, well-known organizations that are plausible donor or "
            "sponsor prospects. HARD RULE: do NOT invent contact emails or phone "
            "numbers. If you are not 100% sure of a public contact, leave email "
            "and phone empty strings and set manual_lookup_required to true. "
            "Output JSON only."
        )
        user = f"""Generate 10-16 prospect organizations for Pro Youth Foundation.

Categories: {', '.join(categories)}
Country: {country}
City: {city}

Return JSON:
{{
  "prospects": [
    {{
      "organization": "",
      "category": "",
      "country": "",
      "city": "",
      "website": "",
      "email": "",          // ONLY if confident public address, else ""
      "phone": "",          // ONLY if confident public number, else ""
      "contact_person": "", // usually ""
      "suggested_amount": "e.g. NAD 5,000 - 50,000",
      "suggested_campaign": "e.g. school fees drive",
      "outreach_angle": "1-line angle that connects their brand to children",
      "priority_score": 0,   // 0-100
      "manual_lookup_required": true
    }}
  ]
}}

Reminders:
- Focus on well-known, real Namibian institutions + international donors.
- Never invent contact details.
- priority_score reflects how well they align with child-protection CSR."""
        text = await call_ai(system, user)
        data = extract_json(text)
        items = data.get("prospects") if isinstance(data, dict) else None
        if isinstance(items, list) and len(items) >= 4:
            return items[:16]
        return []
    except Exception as e:
        logger.info("donor prospects AI fallback: %s", e)
        return []


def _clean_prospect(p: Dict[str, Any]) -> Dict[str, Any]:
    p = dict(p or {})
    for k in ("organization", "category", "country", "city", "website",
              "email", "phone", "contact_person", "suggested_amount",
              "suggested_campaign", "outreach_angle"):
        p.setdefault(k, "")
    p["priority_score"] = int(p.get("priority_score") or 0)
    # Hard rule enforcement: blank email/phone => manual lookup
    has_contact = bool((p.get("email") or "").strip() or (p.get("phone") or "").strip())
    p["manual_lookup_required"] = not has_contact
    return p


def _static_prospects(categories, country, city) -> List[Dict[str, Any]]:
    """Fallback: real Namibian orgs + well-known international donors.
    Contact fields are intentionally BLANK — user must look them up."""
    base = [
        {"organization": "Bank Windhoek", "category": "banks", "website": "https://www.bankwindhoek.com.na",
         "suggested_amount": "NAD 50,000 - 200,000", "suggested_campaign": "School fees drive",
         "outreach_angle": "CSR flagship: education and youth empowerment in Namibia",
         "priority_score": 78},
        {"organization": "First National Bank Namibia", "category": "banks", "website": "https://www.fnbnamibia.com.na",
         "suggested_amount": "NAD 50,000 - 250,000", "suggested_campaign": "Safe housing pilot",
         "outreach_angle": "FNB Foundation community-impact stream",
         "priority_score": 80},
        {"organization": "Standard Bank Namibia", "category": "banks", "website": "https://www.standardbank.com.na",
         "suggested_amount": "NAD 30,000 - 150,000", "suggested_campaign": "Food parcels",
         "outreach_angle": "Standard Bank CSI: community uplift",
         "priority_score": 70},
        {"organization": "Nedbank Namibia", "category": "banks", "website": "https://www.nedbank.com.na",
         "suggested_amount": "NAD 20,000 - 100,000", "suggested_campaign": "Warm clothes winter",
         "outreach_angle": "Nedbank Green & Caring partners",
         "priority_score": 65},
        {"organization": "Namib Mills", "category": "Namibian companies", "website": "https://www.namibmills.com.na",
         "suggested_amount": "Food donations in-kind + NAD 30,000",
         "suggested_campaign": "Monthly food parcels",
         "outreach_angle": "Food manufacturer — natural fit for food-security cause",
         "priority_score": 85},
        {"organization": "Pick n Pay Namibia", "category": "supermarkets", "website": "https://www.picknpay.co.na",
         "suggested_amount": "Vouchers + cash up to NAD 50,000",
         "suggested_campaign": "Back-to-school pack",
         "outreach_angle": "Store CSR — emergency packs for families",
         "priority_score": 72},
        {"organization": "Shoprite Namibia", "category": "supermarkets", "website": "https://www.shoprite.com.na",
         "suggested_amount": "Vouchers + NAD 20,000", "suggested_campaign": "Holiday food parcel",
         "outreach_angle": "Act for Change CSR programme",
         "priority_score": 70},
        {"organization": "Namibia Breweries Limited", "category": "Namibian companies",
         "website": "https://www.nambrew.com.na",
         "suggested_amount": "NAD 50,000 - 300,000", "suggested_campaign": "Safe house refurb",
         "outreach_angle": "NBL Foundation community grants",
         "priority_score": 76},
        {"organization": "Namib Pharmacy Group", "category": "pharmacies",
         "website": "",
         "suggested_amount": "In-kind medicine + NAD 10,000", "suggested_campaign": "First-aid for street children",
         "outreach_angle": "Chain with community-health identity",
         "priority_score": 60},
        {"organization": "Gondwana Collection Namibia", "category": "lodges/hotels",
         "website": "https://www.gondwana-collection.com",
         "suggested_amount": "NAD 30,000 - 120,000", "suggested_campaign": "Education sponsorship",
         "outreach_angle": "Gondwana Care Trust already funds education",
         "priority_score": 82},
        {"organization": "Embassy of Finland (Windhoek)", "category": "embassies",
         "website": "https://finlandabroad.fi/web/nam",
         "suggested_amount": "EUR 5,000 - 30,000 (Fund for Local Cooperation)",
         "suggested_campaign": "Child-protection training",
         "outreach_angle": "Finnish FLC funds small-NGO projects",
         "priority_score": 78},
        {"organization": "Embassy of Japan (Windhoek)", "category": "embassies",
         "website": "https://www.za.emb-japan.go.jp",
         "suggested_amount": "USD 10,000 - 90,000 (GGP scheme)",
         "suggested_campaign": "Safe house equipment",
         "outreach_angle": "Grant Assistance for Grass-roots Human Security Projects",
         "priority_score": 80},
        {"organization": "United States Embassy (Windhoek)", "category": "embassies",
         "website": "https://na.usembassy.gov",
         "suggested_amount": "USD 5,000 - 25,000 (small grants)",
         "suggested_campaign": "Women & mothers empowerment",
         "outreach_angle": "Ambassador's Special Self-Help + PEPFAR small grants",
         "priority_score": 74},
        {"organization": "German Embassy (Windhoek)", "category": "embassies",
         "website": "https://windhuk.diplo.de",
         "suggested_amount": "EUR 5,000 - 25,000 (small grants)",
         "suggested_campaign": "Street children rescue",
         "outreach_angle": "Micro-projects fund for civil society",
         "priority_score": 76},
    ]
    for p in base:
        p.setdefault("country", country)
        p.setdefault("city", city)
        p.setdefault("email", "")
        p.setdefault("phone", "")
        p.setdefault("contact_person", "")
    low = [c.lower() for c in categories] if categories else []
    if low:
        filtered = [p for p in base if any(c in p.get("category", "").lower() for c in low)]
        if filtered:
            return filtered
    return base
