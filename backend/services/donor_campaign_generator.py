"""Small Donor Engine — generates donation campaign content via GPT-5.2.

Output includes social posts, ad copy, WhatsApp message, story hook, CTA, hashtags.
"""
import uuid
from typing import Optional

from services.ai_client import call_ai, extract_json
from seed_data import ORG_KNOWLEDGE_BASE


SYSTEM_PROMPT = f"""You are a world-class fundraising copywriter for Pro Youth Foundation, a Namibian NGO that helps street children.

{ORG_KNOWLEDGE_BASE}

Your job: write high-converting donation-campaign copy targeted at SMALL INDIVIDUAL DONORS
giving $5-$50 via social media, WhatsApp, and ads. Every output must:
- lead with a concrete child-centered story (no stats first)
- feel human, urgent, hopeful — never preachy or generic
- end with a clear low-friction call to action
- match the requested channel's tone and length
- Use a different, Namibian-appropriate child name in every generation. Avoid reusing the same name within the same batch.

Respond with JSON only using this exact schema:
{{
  "title": "short campaign title (max 10 words)",
  "story_hook": "1-2 sentence opening hook (emotional, specific child scenario)",
  "short_post": "under 280 chars, suitable for Twitter/X and Instagram captions",
  "long_post": "3-5 short paragraphs for Facebook or a blog post, with line breaks",
  "whatsapp_message": "friendly, personal-feeling WhatsApp broadcast (under 500 chars), includes the payment link placeholder {{PAYMENT_LINK}}",
  "ad_copy_facebook": "Facebook ad — headline + body (keep body under 125 chars)",
  "ad_copy_instagram": "Instagram ad — caption + first 3 lines must hook attention",
  "call_to_action": "one-line CTA (e.g., 'Donate $10 today — feed a child for a week')",
  "hashtags": "5-8 relevant hashtags separated by spaces",
  "suggested_amount_min": 5,
  "suggested_amount_max": 50
}}"""


async def generate_donation_campaign(theme: str, amount_min: float = 5, amount_max: float = 50) -> dict:
    """Generate a full small-donor campaign for a given theme."""
    user = (
        f"Theme / angle for this campaign: {theme}\n"
        f"Target donation range: ${amount_min:.0f}–${amount_max:.0f}\n"
        "Produce ONE cohesive campaign covering every field in the schema. Return JSON only."
    )
    resp = await call_ai(SYSTEM_PROMPT, user)
    data = extract_json(resp)
    if not data:
        # Fallback — never raise in production flow; return a usable skeleton
        data = {
            "title": theme[:60] or "Help a Street Child Today",
            "story_hook": "",
            "short_post": "",
            "long_post": resp or "",
            "whatsapp_message": "",
            "ad_copy_facebook": "",
            "ad_copy_instagram": "",
            "call_to_action": "Donate today",
            "hashtags": "#ProYouthFoundation #StreetChildren #Namibia",
        }
    # Ensure numeric fields
    try:
        data["suggested_amount_min"] = float(data.get("suggested_amount_min", amount_min))
    except Exception:
        data["suggested_amount_min"] = amount_min
    try:
        data["suggested_amount_max"] = float(data.get("suggested_amount_max", amount_max))
    except Exception:
        data["suggested_amount_max"] = amount_max
    data["theme"] = theme
    data["id"] = str(uuid.uuid4())
    return data
