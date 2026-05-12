"""Sponsor Engine — generates sponsor-outreach packages via GPT-5.2.

Targets local businesses in Namibia at $100-$1000 tier with benefits-based ROI pitch.
"""
import uuid

from services.ai_client import call_ai, extract_json
from seed_data import ORG_KNOWLEDGE_BASE


TIER_GUIDE = {
    "bronze": ("$100-$250", ["Logo on our thank-you poster", "Social media shout-out", "Certificate of appreciation"]),
    "silver": ("$250-$500", ["Logo on our event banner", "Dedicated social media post", "Quarterly impact report"]),
    "gold":   ("$500-$1000", ["Logo on all campaign materials", "Video testimonial from beneficiaries", "Invitation to site visit", "Press release mention"]),
}


SYSTEM_PROMPT = f"""You are a corporate-partnerships specialist writing a sponsorship pitch
for Pro Youth Foundation, a Namibian NGO helping street children.

{ORG_KNOWLEDGE_BASE}

Your job: write a sponsorship package for a specific LOCAL BUSINESS in Namibia giving $100-$1000.
Frame it as a win-win — the business gets visible community-impact branding and tax-deductible giving;
the children get dignity, education, and safety.

Tone: warm, professional, concise. Avoid begging. Speak the language of ROI + social impact.
Keep "email_body" under 1600 characters. Keep only the strongest child story, concrete sponsor benefits, and one clear CTA.

Respond with JSON only using this exact schema:
{{
  "value_proposition": "2-3 sentence pitch — why THIS business should sponsor (reference their industry if given)",
  "benefits_list": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"],
  "email_subject": "compelling subject line (under 60 chars)",
  "email_body": "full outreach email with greeting, hook, offer, benefits, CTA, signature — include the payment link placeholder {{PAYMENT_LINK}}",
  "whatsapp_message": "shorter WhatsApp version under 500 chars, still professional, includes {{PAYMENT_LINK}}",
  "ad_copy": "LinkedIn/local-newspaper ad targeting similar businesses (2-3 short lines)",
  "follow_up_plan": "3-step follow-up sequence (Day 3, Day 7, Day 14) — 1 line each"
}}"""


async def generate_sponsor_offer(
    sponsor_name: str,
    sponsor_type: str = "small_business",
    offer_tier: str = "silver",
) -> dict:
    """Generate a full sponsor package for a named business at a given tier."""
    tier_key = offer_tier.lower() if offer_tier.lower() in TIER_GUIDE else "silver"
    amount_range, default_benefits = TIER_GUIDE[tier_key]

    user = (
        f"Sponsor name: {sponsor_name}\n"
        f"Business type: {sponsor_type}\n"
        f"Sponsorship tier: {tier_key.upper()} ({amount_range})\n"
        f"Default benefits to include (you may enhance): {default_benefits}\n"
        "Return the JSON package only."
    )
    resp = await call_ai(SYSTEM_PROMPT, user)
    data = extract_json(resp)
    if not data:
        data = {
            "value_proposition": "Partner with Pro Youth Foundation to visibly support street children in Namibia.",
            "benefits_list": default_benefits,
            "email_subject": f"Partnership Opportunity — Pro Youth Foundation × {sponsor_name}",
            "email_body": resp or "",
            "whatsapp_message": "",
            "ad_copy": "",
            "follow_up_plan": "",
        }

    # Normalize benefits_list
    benefits = data.get("benefits_list", default_benefits)
    if isinstance(benefits, list):
        data["benefits_list"] = "\n".join(f"- {b}" for b in benefits)
    elif not isinstance(benefits, str):
        data["benefits_list"] = "\n".join(f"- {b}" for b in default_benefits)

    # Parse tier amounts from guide
    lo, hi = amount_range.replace("$", "").split("-")
    data["suggested_amount_min"] = float(lo)
    data["suggested_amount_max"] = float(hi)
    data["sponsor_name"] = sponsor_name
    data["sponsor_type"] = sponsor_type
    data["offer_tier"] = tier_key
    data["id"] = str(uuid.uuid4())
    return data
