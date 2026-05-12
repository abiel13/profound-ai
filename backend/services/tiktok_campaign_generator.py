"""
TikTok Donation Campaign Generator
==================================

Generates a complete TikTok-ready content pack for a single small-donor
campaign:
    - 5 short video scripts (hook, visual, voice-over, on-screen, CTA, length)
    - 10 captions
    - 30 hashtags (Namibia + charity + child support + donor)
    - 1 WhatsApp share message
    - 1 Facebook post
    - donor trust checklist

Strategy:
- Try AI (Claude Sonnet 4.5 via Emergent LLM key) for richer copy
- Fall back to a high-quality deterministic template if AI is missing,
  rate-limited, or returns malformed JSON.
- Never raise — we always return a usable pack.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from services.ai_client import call_ai, extract_json

logger = logging.getLogger(__name__)


CAUSE_LABELS = {
    "school_fees": "school fees for vulnerable children",
    "food_parcels": "monthly food parcels for hungry families",
    "clothing": "warm clothing for children in winter",
    "abuse_protection": "abuse protection and safe-house support",
    "safe_housing": "safe overnight housing for at-risk children",
    "street_children": "street children rescue and rehabilitation",
    "emergency_support": "emergency family support",
}


# ----------------- Public entry point ----------------------------------

async def generate_tiktok_pack(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a full TikTok pack. Always returns a dict with all 6 keys.
    Order:
      1. Try AI
      2. If AI fails / not configured / bad JSON, return template fallback
    """
    pack = await _try_ai_pack(payload)
    if pack and _looks_complete(pack):
        return _normalize_pack(pack)
    template = _template_pack(payload)
    return _normalize_pack(template)


# ----------------- AI path ---------------------------------------------

async def _try_ai_pack(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    # Wrapped so this whole function is sync-friendly when called by gather
    try:
        title = payload.get("campaign_title") or "Help vulnerable children in Namibia"
        amount = payload.get("target_amount") or "1,000"
        cause_key = payload.get("cause_category") or "school_fees"
        cause_label = CAUSE_LABELS.get(cause_key, cause_key.replace("_", " "))
        location = payload.get("location") or "Namibia"
        deadline = payload.get("deadline") or "30 days"
        donation_link = payload.get("donation_link") or ""
        tone = payload.get("tone") or "emotional"

        system = (
            "You are a TikTok donation campaign writer for the Pro Youth "
            "Foundation, a Namibian non-profit helping vulnerable children. "
            "Write content that is honest, warm, specific, and avoids any "
            "stereotype that exploits children. Always show practical impact "
            "(receipts, deliveries, real names). Output JSON only."
        )
        user = f"""Build a complete TikTok donation campaign pack as strict JSON.

Campaign: {title}
Target: NAD {amount}
Cause: {cause_label}
Location: {location}
Deadline: {deadline}
Donation link: {donation_link or '(none provided yet)'}
Tone: {tone}

Return JSON with exactly these keys:
{{
  "scripts": [   // EXACTLY 5 items
     {{ "hook": "<3-second hook>",
        "visual": "<what to show on camera>",
        "voiceover": "<voice-over text>",
        "on_screen_text": "<on-screen text overlay>",
        "cta": "<call-to-action>",
        "length_seconds": 15 }}
  ],
  "captions": [   // EXACTLY 10 short captions, each <120 chars
    "..."
  ],
  "hashtags": [   // EXACTLY 30 hashtags. Mix Namibia + charity + child support + donor + cause
    "#namibia", "..."
  ],
  "whatsapp_message": "<short message to send to contacts/groups, <300 chars, plain text, includes the donation link>",
  "facebook_post": "<longer emotional post, 3-6 sentences, includes the donation link>",
  "trust_checklist": [   // 6-10 items
    "Show donation receipt within 24h", "..."
  ]
}}

Rules:
- Never use language that exploits children.
- Be concrete: name the impact in NAD amounts (e.g. 'NAD 50 = one food parcel').
- Hashtags must start with # and be lowercase.
- Output only the JSON. No prose, no markdown."""

        text = await call_ai(system, user)
        data = extract_json(text)
        if not data:
            return None
        return data
    except Exception as e:  # AI key missing or upstream fail
        logger.info("TikTok AI path skipped: %s", e)
        return None


# ----------------- Template fallback -----------------------------------

def _template_pack(p: Dict[str, Any]) -> Dict[str, Any]:
    title = p.get("campaign_title") or "Help a Namibian child today"
    amount = str(p.get("target_amount") or "1000")
    cause_key = p.get("cause_category") or "school_fees"
    cause = CAUSE_LABELS.get(cause_key, cause_key.replace("_", " "))
    location = p.get("location") or "Namibia"
    deadline = p.get("deadline") or "30 days"
    link = p.get("donation_link") or "(add your donation link)"
    tone = (p.get("tone") or "emotional").lower()

    tone_word = {
        "emotional": "It only takes one of us to change a child's day.",
        "urgent": "We have only days left. Every minute matters.",
        "hopeful": "Small acts. Big futures. You can be part of this.",
        "transparent": "You give. We deliver. We show you the receipt.",
    }.get(tone, "Every donation is a real meal, a real uniform, a real night of safety.")

    scripts = [
        {
            "hook": f"This {location} child has 3 days to find {amount} NAD.",
            "visual": "Slow zoom on a child's hands holding an empty school bag.",
            "voiceover": f"Right now, in {location}, a child needs {cause}. Just NAD 50 from you covers one full week.",
            "on_screen_text": f"NAD {amount} needed in {deadline}",
            "cta": f"Tap the link in bio. {link}",
            "length_seconds": 15,
        },
        {
            "hook": "Would you skip one coffee for this?",
            "visual": "Quick cuts: a coffee cup, a bag of mealie meal, a smiling child.",
            "voiceover": "One coffee here. One full meal there. NAD 30 changes a day.",
            "on_screen_text": "NAD 30 = 1 meal",
            "cta": f"Donate now -> {link}",
            "length_seconds": 12,
        },
        {
            "hook": "We will show you EVERY receipt. Watch.",
            "visual": "Hands holding a paper receipt; phone screen showing a SMS proof of payment.",
            "voiceover": tone_word,
            "on_screen_text": "100% transparent. Every cent tracked.",
            "cta": f"Be part of it: {link}",
            "length_seconds": 18,
        },
        {
            "hook": "Day 1 vs Day 30. Same child.",
            "visual": "Before/after: hungry vs fed, no uniform vs uniform, no shoes vs shoes.",
            "voiceover": f"Thirty days of {cause}. This is what your NAD does.",
            "on_screen_text": f"{title}",
            "cta": f"Help us hit NAD {amount}: {link}",
            "length_seconds": 20,
        },
        {
            "hook": f"Only {deadline} left to reach NAD {amount}.",
            "visual": "A live progress bar over a candle slowly burning down.",
            "voiceover": "We are not asking for a lot. We are asking for many. Many small donations build a wall of safety.",
            "on_screen_text": "Be donor #100",
            "cta": f"Donate any amount -> {link}",
            "length_seconds": 15,
        },
    ]

    captions = [
        f"{title} — NAD {amount} in {deadline}. Help us. {link}",
        f"NAD 50 = one school week for a {location} child.",
        "We show every receipt. Watch the proof in pinned comments.",
        f"This is {cause}. Your NAD 30 is real food today.",
        "Skip one coffee. Save one day. Change one life.",
        "100% of donations go to children. Pro Youth Foundation Namibia.",
        "Want to see where your money went? We post the proof.",
        f"Goal: NAD {amount}. Days left: {deadline}. Donors needed: you.",
        "Small gift. Big future. Tap the link.",
        "Not asking for a lot. Asking for many. Be one of us.",
    ]

    hashtags = [
        "#namibia", "#namibian", "#windhoek", "#proudlynamibian", "#africangiving",
        "#donatenamibia", "#charitynamibia", "#savethechildrenamibia", "#namibianngo",
        "#proyouthfoundation", "#charity", "#donate", "#donation", "#donatetoday",
        "#fundraiser", "#fundraising", "#crowdfund", "#smalldonationsbigimpact",
        "#donortok", "#donortiktok", "#donateforchange", "#child", "#childprotection",
        "#vulnerablechildren", "#orphanagecare", "#streetchildren", "#schoolfees",
        "#foodparcel", "#warmclothing", "#safehousing",
    ]

    whatsapp_message = (
        f"Hi friend - I'm helping the Pro Youth Foundation raise NAD {amount} in {deadline} "
        f"for {cause} in {location}. Even NAD 30 helps. We post every receipt. "
        f"Donate here: {link}. Please share with one friend. Thank you!"
    )

    facebook_post = (
        f"{title}\n\n"
        f"In the next {deadline}, the Pro Youth Foundation is raising NAD {amount} for "
        f"{cause} in {location}. Every NAD 30 is one real meal. Every NAD 50 is one school "
        f"week. We post every receipt and every delivery photo so you always know exactly "
        f"where your gift went.\n\n"
        f"If 100 of us each give NAD {max(10, int(float(str(amount).replace(',','')) // 100)) if str(amount).replace(',','').isdigit() else 50}, "
        f"we are done. Will you be one of the 100?\n\n"
        f"Donate here: {link}"
    )

    trust_checklist = [
        "Post the donation receipt within 24h of every gift",
        "Show before/after photos with parental consent",
        "Blur or hide every child's face that doesn't have written consent",
        "Publish a weekly delivery update with photos",
        "Share the bank statement screenshot at the end of the campaign",
        "List every beneficiary by initials only and amount delivered",
        "Use a single named treasurer to handle every payout",
        "Pin a comment with the exact totals raised vs goal",
    ]

    return {
        "scripts": scripts,
        "captions": captions,
        "hashtags": hashtags,
        "whatsapp_message": whatsapp_message,
        "facebook_post": facebook_post,
        "trust_checklist": trust_checklist,
    }


# ----------------- Helpers ---------------------------------------------

def _looks_complete(pack: Dict[str, Any]) -> bool:
    if not isinstance(pack, dict):
        return False
    needed = ("scripts", "captions", "hashtags", "whatsapp_message",
              "facebook_post", "trust_checklist")
    return all(k in pack for k in needed) and \
        isinstance(pack.get("scripts"), list) and len(pack["scripts"]) >= 3 and \
        isinstance(pack.get("captions"), list) and len(pack["captions"]) >= 5 and \
        isinstance(pack.get("hashtags"), list) and len(pack["hashtags"]) >= 10


def _normalize_pack(pack: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure every key exists and arrays are right-sized for client UX."""
    pack = dict(pack)
    pack.setdefault("scripts", [])
    pack.setdefault("captions", [])
    pack.setdefault("hashtags", [])
    pack.setdefault("whatsapp_message", "")
    pack.setdefault("facebook_post", "")
    pack.setdefault("trust_checklist", [])

    # Cap to expected sizes so UI does not explode.
    pack["scripts"] = list(pack["scripts"])[:5]
    pack["captions"] = list(pack["captions"])[:10]

    # Hashtags: lower-case, ensure leading #, dedupe, cap at 30
    seen = set()
    cleaned: List[str] = []
    for h in pack["hashtags"]:
        if not isinstance(h, str):
            continue
        h2 = h.strip().lower()
        if not h2:
            continue
        if not h2.startswith("#"):
            h2 = "#" + h2.replace(" ", "")
        if h2 in seen:
            continue
        seen.add(h2)
        cleaned.append(h2)
        if len(cleaned) >= 30:
            break
    pack["hashtags"] = cleaned

    return pack
