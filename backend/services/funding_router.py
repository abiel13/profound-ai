"""Funding Router — classifies a funding target into Small Donor / Sponsor / Big Grant.

Rules are deterministic (fast + free) and fall back to AI only when ambiguous.
"""
from typing import Optional

from services.ai_client import call_ai, extract_json


SMALL_DONOR = "small_donor"
SPONSOR = "sponsor"
BIG_GRANT = "big_grant"

VALID_MODES = {SMALL_DONOR, SPONSOR, BIG_GRANT}


def classify_by_amount(amount: Optional[float]) -> Optional[str]:
    """Simple amount-based routing (USD)."""
    if amount is None:
        return None
    if amount <= 50:
        return SMALL_DONOR
    if amount <= 1000:
        return SPONSOR
    return BIG_GRANT


def classify_by_type(target_type: str) -> Optional[str]:
    """Route based on explicit target_type string."""
    t = (target_type or "").lower().strip()
    if not t:
        return None
    if t in {"individual", "public", "crowdfund", "social", "community"}:
        return SMALL_DONOR
    if t in {"business", "small_business", "sme", "corporate_local", "shop", "brand"}:
        return SPONSOR
    if t in {"foundation", "government", "ngo_fund", "un", "embassy", "grant", "multilateral"}:
        return BIG_GRANT
    return None


def route(amount: Optional[float] = None, target_type: str = "", description: str = "") -> dict:
    """Return a routing decision dict: {mode, reason, confidence}."""
    # 1. Explicit type wins
    by_type = classify_by_type(target_type)
    if by_type:
        return {
            "mode": by_type,
            "reason": f"Target type '{target_type}' maps to {by_type}.",
            "confidence": "high",
        }
    # 2. Amount next
    by_amt = classify_by_amount(amount)
    if by_amt:
        return {
            "mode": by_amt,
            "reason": f"Amount ${amount:.0f} falls in the {by_amt} tier.",
            "confidence": "medium",
        }
    # 3. Fallback — description keyword hints
    d = (description or "").lower()
    if any(k in d for k in ["individual", "public", "social media", "crowdfund"]):
        return {"mode": SMALL_DONOR, "reason": "Description suggests a public/individual target.", "confidence": "low"}
    if any(k in d for k in ["shop", "business", "company", "sponsor", "brand"]):
        return {"mode": SPONSOR, "reason": "Description suggests a business sponsor.", "confidence": "low"}
    if any(k in d for k in ["foundation", "grant", "embassy", "ministry", "un "]):
        return {"mode": BIG_GRANT, "reason": "Description suggests a formal grant donor.", "confidence": "low"}
    # Default to Small Donor (safest, cheapest)
    return {"mode": SMALL_DONOR, "reason": "No strong signals — defaulting to Small Donor.", "confidence": "low"}


async def ai_route(description: str) -> dict:
    """Use AI to classify only when description is free-form and no amount/type is given."""
    system = (
        "You classify fundraising targets into exactly one of three tiers: "
        "'small_donor' ($5-$50, individuals), 'sponsor' ($100-$1000, local businesses), "
        "'big_grant' ($1000+, foundations/government). "
        "Respond with JSON only: {\"mode\": \"...\", \"reason\": \"...\"}"
    )
    user = f"Target description: {description}"
    resp = await call_ai(system, user)
    data = extract_json(resp)
    mode = data.get("mode", "").strip().lower()
    if mode not in VALID_MODES:
        return route(description=description)
    return {"mode": mode, "reason": data.get("reason", "AI classification"), "confidence": "ai"}
