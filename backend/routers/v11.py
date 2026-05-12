"""V11 — 3-Mode Funding Engine routes.

Prefix: /api/v11

Routes:
  - POST   /v11/router/classify          — classify a target into small_donor/sponsor/big_grant
  - GET    /v11/campaigns                — list donation campaigns
  - POST   /v11/campaigns/generate       — AI-generate a new small-donor campaign (saves as draft)
  - GET    /v11/campaigns/{id}           — get one campaign
  - PATCH  /v11/campaigns/{id}           — update fields (link payment, edit copy, change status)
  - DELETE /v11/campaigns/{id}
  - POST   /v11/campaigns/{id}/enqueue   — push generated copy to the send queue (mock)

  - GET    /v11/sponsors                 — list sponsor offers
  - POST   /v11/sponsors/generate        — AI-generate a new sponsor offer
  - GET    /v11/sponsors/{id}
  - PATCH  /v11/sponsors/{id}
  - DELETE /v11/sponsors/{id}
  - POST   /v11/sponsors/{id}/enqueue    — push offer to send queue (mock)

  - GET    /v11/payment-links
  - POST   /v11/payment-links
  - GET    /v11/payment-links/{id}
  - PATCH  /v11/payment-links/{id}
  - DELETE /v11/payment-links/{id}

  - GET    /v11/donations                — list donation log
  - POST   /v11/donations                — record a donation manually
  - DELETE /v11/donations/{id}
  - GET    /v11/donations/summary        — totals by campaign / sponsor / month

  - GET    /v11/queue                    — list queue (optional ?status=pending|sent|cancelled)
  - POST   /v11/queue/{id}/mark-sent     — mock send (logs only)
  - POST   /v11/queue/{id}/cancel
  - DELETE /v11/queue/{id}
"""
from typing import Optional
import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from deps import get_current_user, get_db, now_iso
from services import funding_router as fr
from services.donor_campaign_generator import generate_donation_campaign
from services.sponsor_offer_generator import generate_sponsor_offer
from services import payment_link_manager as plm
from services import send_queue_service as queue
from services.tiktok_campaign_generator import generate_tiktok_pack

router = APIRouter(prefix="/v11")


# ---------- TikTok Campaign Models ----------
class TikTokGenerateReq(BaseModel):
    campaign_title: Optional[str] = ""
    target_amount: Optional[str] = ""
    cause_category: Optional[str] = ""
    location: Optional[str] = ""
    deadline: Optional[str] = ""
    donation_link: Optional[str] = ""
    tone: Optional[str] = "emotional"
    save: Optional[bool] = True


# ---------- Models ----------
class ClassifyReq(BaseModel):
    amount: Optional[float] = None
    target_type: Optional[str] = ""
    description: Optional[str] = ""
    use_ai: Optional[bool] = False


class CampaignGenerateReq(BaseModel):
    theme: str
    amount_min: Optional[float] = 5
    amount_max: Optional[float] = 50


class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    theme: Optional[str] = None
    story_hook: Optional[str] = None
    short_post: Optional[str] = None
    long_post: Optional[str] = None
    whatsapp_message: Optional[str] = None
    ad_copy_facebook: Optional[str] = None
    ad_copy_instagram: Optional[str] = None
    call_to_action: Optional[str] = None
    hashtags: Optional[str] = None
    payment_link_id: Optional[str] = None
    status: Optional[str] = None


class SponsorGenerateReq(BaseModel):
    sponsor_name: str
    sponsor_type: Optional[str] = "small_business"
    offer_tier: Optional[str] = "silver"


class SponsorUpdate(BaseModel):
    sponsor_name: Optional[str] = None
    sponsor_type: Optional[str] = None
    offer_tier: Optional[str] = None
    value_proposition: Optional[str] = None
    benefits_list: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    whatsapp_message: Optional[str] = None
    ad_copy: Optional[str] = None
    follow_up_plan: Optional[str] = None
    payment_link_id: Optional[str] = None
    status: Optional[str] = None


class PaymentLinkCreate(BaseModel):
    label: str
    provider: Optional[str] = "generic"
    url: str
    purpose: Optional[str] = "donation"
    campaign_id: Optional[str] = ""
    sponsor_offer_id: Optional[str] = ""
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    active: Optional[bool] = True


class PaymentLinkUpdate(BaseModel):
    label: Optional[str] = None
    provider: Optional[str] = None
    url: Optional[str] = None
    purpose: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    active: Optional[bool] = None


class DonationCreate(BaseModel):
    amount: float
    currency: Optional[str] = "USD"
    donor_name: Optional[str] = ""
    donor_email: Optional[str] = ""
    payment_method: Optional[str] = ""
    payment_link_id: Optional[str] = ""
    campaign_id: Optional[str] = ""
    sponsor_offer_id: Optional[str] = ""
    source: Optional[str] = ""
    note: Optional[str] = ""
    received_at: Optional[str] = ""


class EnqueueReq(BaseModel):
    channel: str  # whatsapp | email | sms
    recipient: str
    recipient_label: Optional[str] = ""
    variant: Optional[str] = "whatsapp"  # which pre-generated text to use
    payment_link: Optional[str] = ""


class SetDefaultLinksReq(BaseModel):
    small_donor_link: Optional[str] = None
    sponsor_link: Optional[str] = None


class BulkAddReq(BaseModel):
    campaign_top_n: Optional[int] = 3
    sponsor_top_n: Optional[int] = 3
    channel_campaign: Optional[str] = "whatsapp"
    channel_sponsor: Optional[str] = "email"
    recipient_campaign: Optional[str] = "broadcast-list"
    recipient_sponsor: Optional[str] = "sponsor-list"


# ---------- Router: classification ----------
@router.post("/router/classify")
async def classify(data: ClassifyReq, request: Request):
    await get_current_user(request)
    if data.use_ai and (data.description or ""):
        return await fr.ai_route(data.description or "")
    return fr.route(amount=data.amount, target_type=data.target_type or "", description=data.description or "")


# ---------- Campaigns (Small Donor) ----------
@router.get("/campaigns")
async def list_campaigns(request: Request, status: Optional[str] = None):
    await get_current_user(request)
    db = await get_db()
    if status:
        cursor = await db.execute("SELECT * FROM donation_campaigns WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cursor = await db.execute("SELECT * FROM donation_campaigns ORDER BY created_at DESC")
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


@router.post("/campaigns/generate")
async def generate_campaign(data: CampaignGenerateReq, request: Request):
    await get_current_user(request)
    pack = await generate_donation_campaign(data.theme, data.amount_min or 5, data.amount_max or 50)
    # Auto-attach the default small-donor payment link if one is configured.
    default_link = await plm.get_default_link("small_donor")
    default_link_id = default_link["id"] if default_link else ""
    now = now_iso()
    db = await get_db()
    await db.execute(
        """INSERT INTO donation_campaigns (id, title, theme, target_audience,
           suggested_amount_min, suggested_amount_max, story_hook, short_post, long_post,
           whatsapp_message, ad_copy_facebook, ad_copy_instagram, call_to_action, hashtags,
           payment_link_id, status, created_at, updated_at)
           VALUES (?, ?, ?, 'small_donor', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)""",
        (pack["id"], pack.get("title", ""), pack.get("theme", ""),
         pack.get("suggested_amount_min", 5), pack.get("suggested_amount_max", 50),
         pack.get("story_hook", ""), pack.get("short_post", ""), pack.get("long_post", ""),
         pack.get("whatsapp_message", ""), pack.get("ad_copy_facebook", ""),
         pack.get("ad_copy_instagram", ""), pack.get("call_to_action", ""),
         pack.get("hashtags", ""), default_link_id, now, now),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM donation_campaigns WHERE id = ?", (pack["id"],))
    row = await cursor.fetchone()
    await db.close()
    return dict(row)


@router.get("/campaigns/{cid}")
async def get_campaign(cid: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM donation_campaigns WHERE id = ?", (cid,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(404, "Campaign not found")
    return dict(row)


@router.patch("/campaigns/{cid}")
async def update_campaign(cid: str, data: CampaignUpdate, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM donation_campaigns WHERE id = ?", (cid,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(404, "Campaign not found")
    existing = dict(row)
    updates = data.dict(exclude_none=True)
    merged = {**existing, **updates, "updated_at": now_iso()}
    await db.execute(
        """UPDATE donation_campaigns SET title=?, theme=?, story_hook=?, short_post=?, long_post=?,
           whatsapp_message=?, ad_copy_facebook=?, ad_copy_instagram=?, call_to_action=?,
           hashtags=?, payment_link_id=?, status=?, updated_at=? WHERE id=?""",
        (merged.get("title", ""), merged.get("theme", ""), merged.get("story_hook", ""),
         merged.get("short_post", ""), merged.get("long_post", ""),
         merged.get("whatsapp_message", ""), merged.get("ad_copy_facebook", ""),
         merged.get("ad_copy_instagram", ""), merged.get("call_to_action", ""),
         merged.get("hashtags", ""), merged.get("payment_link_id", ""),
         merged.get("status", "draft"), merged["updated_at"], cid),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM donation_campaigns WHERE id = ?", (cid,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row)


@router.delete("/campaigns/{cid}")
async def delete_campaign(cid: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("DELETE FROM donation_campaigns WHERE id = ?", (cid,))
    await db.commit()
    await db.close()
    return {"ok": True}


@router.post("/campaigns/{cid}/enqueue")
async def enqueue_campaign(cid: str, data: EnqueueReq, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM donation_campaigns WHERE id = ?", (cid,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(404, "Campaign not found")
    c = dict(row)
    # Resolve payment link (if campaign has one)
    resolved_link = data.payment_link or ""
    if not resolved_link and c.get("payment_link_id"):
        pl = await plm.get_payment_link(c["payment_link_id"])
        if pl:
            resolved_link = pl.get("tracking_url") or pl.get("url", "")
    # Choose the right copy variant for the channel
    variant_map = {
        "whatsapp": c.get("whatsapp_message", ""),
        "email": c.get("long_post", ""),
        "sms": c.get("short_post", ""),
    }
    text = variant_map.get(data.channel, c.get("whatsapp_message", ""))
    # Substitute payment link placeholder
    if "{PAYMENT_LINK}" in text:
        text = text.replace("{PAYMENT_LINK}", resolved_link or "[add payment link]")
    subject = c.get("title", "") if data.channel == "email" else ""
    await db.close()
    item = await queue.enqueue(
        channel=data.channel,
        target_type="campaign",
        target_id=cid,
        recipient=data.recipient,
        recipient_label=data.recipient_label or "",
        subject=subject,
        message=text,
        payment_link=resolved_link,
    )
    return item


# ---------- Sponsors ----------
@router.get("/sponsors")
async def list_sponsors(request: Request, status: Optional[str] = None):
    await get_current_user(request)
    db = await get_db()
    if status:
        cursor = await db.execute("SELECT * FROM sponsor_offers WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cursor = await db.execute("SELECT * FROM sponsor_offers ORDER BY created_at DESC")
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


@router.post("/sponsors/generate")
async def generate_sponsor(data: SponsorGenerateReq, request: Request):
    await get_current_user(request)
    pack = await generate_sponsor_offer(data.sponsor_name, data.sponsor_type or "small_business", data.offer_tier or "silver")
    # Auto-attach the default sponsor payment link if configured.
    default_link = await plm.get_default_link("sponsor")
    default_link_id = default_link["id"] if default_link else ""
    now = now_iso()
    db = await get_db()
    await db.execute(
        """INSERT INTO sponsor_offers (id, sponsor_name, sponsor_type, offer_tier,
           suggested_amount_min, suggested_amount_max, value_proposition, benefits_list,
           email_subject, email_body, whatsapp_message, ad_copy, follow_up_plan,
           payment_link_id, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)""",
        (pack["id"], pack["sponsor_name"], pack["sponsor_type"], pack["offer_tier"],
         pack["suggested_amount_min"], pack["suggested_amount_max"],
         pack.get("value_proposition", ""), pack.get("benefits_list", ""),
         pack.get("email_subject", ""), pack.get("email_body", ""),
         pack.get("whatsapp_message", ""), pack.get("ad_copy", ""),
         pack.get("follow_up_plan", ""), default_link_id, now, now),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM sponsor_offers WHERE id = ?", (pack["id"],))
    row = await cursor.fetchone()
    await db.close()
    return dict(row)


@router.get("/sponsors/{sid}")
async def get_sponsor(sid: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM sponsor_offers WHERE id = ?", (sid,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(404, "Sponsor offer not found")
    return dict(row)


@router.patch("/sponsors/{sid}")
async def update_sponsor(sid: str, data: SponsorUpdate, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM sponsor_offers WHERE id = ?", (sid,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(404, "Sponsor offer not found")
    existing = dict(row)
    updates = data.dict(exclude_none=True)
    merged = {**existing, **updates, "updated_at": now_iso()}
    await db.execute(
        """UPDATE sponsor_offers SET sponsor_name=?, sponsor_type=?, offer_tier=?,
           value_proposition=?, benefits_list=?, email_subject=?, email_body=?,
           whatsapp_message=?, ad_copy=?, follow_up_plan=?, payment_link_id=?,
           status=?, updated_at=? WHERE id=?""",
        (merged.get("sponsor_name", ""), merged.get("sponsor_type", ""),
         merged.get("offer_tier", ""), merged.get("value_proposition", ""),
         merged.get("benefits_list", ""), merged.get("email_subject", ""),
         merged.get("email_body", ""), merged.get("whatsapp_message", ""),
         merged.get("ad_copy", ""), merged.get("follow_up_plan", ""),
         merged.get("payment_link_id", ""), merged.get("status", "draft"),
         merged["updated_at"], sid),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM sponsor_offers WHERE id = ?", (sid,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row)


@router.delete("/sponsors/{sid}")
async def delete_sponsor(sid: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("DELETE FROM sponsor_offers WHERE id = ?", (sid,))
    await db.commit()
    await db.close()
    return {"ok": True}


@router.post("/sponsors/{sid}/enqueue")
async def enqueue_sponsor(sid: str, data: EnqueueReq, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM sponsor_offers WHERE id = ?", (sid,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(404, "Sponsor offer not found")
    s = dict(row)
    resolved_link = data.payment_link or ""
    if not resolved_link and s.get("payment_link_id"):
        pl = await plm.get_payment_link(s["payment_link_id"])
        if pl:
            resolved_link = pl.get("tracking_url") or pl.get("url", "")
    variant_map = {
        "email": s.get("email_body", ""),
        "whatsapp": s.get("whatsapp_message", ""),
        "sms": s.get("whatsapp_message", "")[:500],
    }
    text = variant_map.get(data.channel, s.get("email_body", ""))
    if "{PAYMENT_LINK}" in text:
        text = text.replace("{PAYMENT_LINK}", resolved_link or "[add payment link]")
    subject = s.get("email_subject", "") if data.channel == "email" else ""
    await db.close()
    item = await queue.enqueue(
        channel=data.channel,
        target_type="sponsor",
        target_id=sid,
        recipient=data.recipient,
        recipient_label=data.recipient_label or s.get("sponsor_name", ""),
        subject=subject,
        message=text,
        payment_link=resolved_link,
    )
    return item


# ---------- Payment Links ----------
@router.post("/payment-links/set")
async def set_default_payment_links(data: SetDefaultLinksReq, request: Request):
    """Upsert the two default payment links (small_donor + sponsor).

    After this is called, every newly generated campaign auto-attaches the
    small_donor link, and every newly generated sponsor offer auto-attaches
    the sponsor link. Existing rows are NOT modified by this endpoint.
    """
    await get_current_user(request)
    result = {}
    if data.small_donor_link:
        result["small_donor"] = await plm.upsert_default_link("small_donor", data.small_donor_link)
    if data.sponsor_link:
        result["sponsor"] = await plm.upsert_default_link("sponsor", data.sponsor_link)
    if not result:
        raise HTTPException(400, "Provide at least one of small_donor_link or sponsor_link")
    return result


@router.get("/payment-links/defaults")
async def get_default_payment_links(request: Request):
    await get_current_user(request)
    return await plm.get_defaults_bundle()


@router.get("/payment-links")
async def list_payments(request: Request, active_only: bool = False):
    await get_current_user(request)
    return await plm.list_payment_links(active_only)


@router.post("/payment-links")
async def create_payment(data: PaymentLinkCreate, request: Request):
    await get_current_user(request)
    return await plm.create_payment_link(data.dict())


@router.get("/payment-links/{pid}")
async def get_payment(pid: str, request: Request):
    await get_current_user(request)
    pl = await plm.get_payment_link(pid)
    if not pl:
        raise HTTPException(404, "Payment link not found")
    return pl


@router.patch("/payment-links/{pid}")
async def update_payment(pid: str, data: PaymentLinkUpdate, request: Request):
    await get_current_user(request)
    updated = await plm.update_payment_link(pid, data.dict(exclude_none=True))
    if not updated:
        raise HTTPException(404, "Payment link not found")
    return updated


@router.delete("/payment-links/{pid}")
async def delete_payment(pid: str, request: Request):
    await get_current_user(request)
    await plm.delete_payment_link(pid)
    return {"ok": True}


# ---------- Donations ----------
@router.get("/donations")
async def list_donations(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM donations_log ORDER BY received_at DESC, created_at DESC")
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


@router.post("/donations")
async def create_donation(data: DonationCreate, request: Request):
    await get_current_user(request)
    import uuid
    did = str(uuid.uuid4())
    now = now_iso()
    received = data.received_at or now
    db = await get_db()
    await db.execute(
        """INSERT INTO donations_log (id, amount, currency, donor_name, donor_email,
           payment_method, payment_link_id, campaign_id, sponsor_offer_id, source, note,
           received_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (did, data.amount, data.currency or "USD", data.donor_name or "",
         data.donor_email or "", data.payment_method or "",
         data.payment_link_id or "", data.campaign_id or "",
         data.sponsor_offer_id or "", data.source or "", data.note or "",
         received, now),
    )
    # Roll-up into campaign totals
    if data.campaign_id:
        await db.execute(
            """UPDATE donation_campaigns
               SET total_raised = total_raised + ?, donor_count = donor_count + 1
               WHERE id = ?""",
            (data.amount, data.campaign_id),
        )
    await db.commit()
    cursor = await db.execute("SELECT * FROM donations_log WHERE id = ?", (did,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row)


@router.delete("/donations/{did}")
async def delete_donation(did: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    # Reverse rollup
    cursor = await db.execute("SELECT amount, campaign_id FROM donations_log WHERE id = ?", (did,))
    row = await cursor.fetchone()
    if row and row["campaign_id"]:
        await db.execute(
            """UPDATE donation_campaigns
               SET total_raised = MAX(0, total_raised - ?), donor_count = MAX(0, donor_count - 1)
               WHERE id = ?""",
            (row["amount"], row["campaign_id"]),
        )
    await db.execute("DELETE FROM donations_log WHERE id = ?", (did,))
    await db.commit()
    await db.close()
    return {"ok": True}


@router.get("/donations/summary")
async def donations_summary(request: Request):
    await get_current_user(request)
    db = await get_db()
    # Totals
    cursor = await db.execute("SELECT COUNT(*) as c, COALESCE(SUM(amount),0) as total FROM donations_log")
    totals = dict(await cursor.fetchone())
    # By campaign
    cursor = await db.execute("""
        SELECT c.id, c.title, COALESCE(SUM(d.amount),0) as total, COUNT(d.id) as count
        FROM donation_campaigns c
        LEFT JOIN donations_log d ON d.campaign_id = c.id
        GROUP BY c.id
        ORDER BY total DESC
    """)
    by_campaign = [dict(r) for r in await cursor.fetchall()]
    # By sponsor
    cursor = await db.execute("""
        SELECT s.id, s.sponsor_name as title, COALESCE(SUM(d.amount),0) as total, COUNT(d.id) as count
        FROM sponsor_offers s
        LEFT JOIN donations_log d ON d.sponsor_offer_id = s.id
        GROUP BY s.id
        ORDER BY total DESC
    """)
    by_sponsor = [dict(r) for r in await cursor.fetchall()]
    # By month (last 12)
    cursor = await db.execute("""
        SELECT substr(received_at, 1, 7) as month, COALESCE(SUM(amount),0) as total, COUNT(id) as count
        FROM donations_log
        WHERE received_at != ''
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """)
    by_month = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return {
        "totals": totals,
        "by_campaign": by_campaign,
        "by_sponsor": by_sponsor,
        "by_month": by_month,
    }


# ---------- Send Queue ----------
@router.get("/queue")
async def list_send_queue(request: Request, status: Optional[str] = None):
    await get_current_user(request)
    return await queue.list_queue(status or "")


@router.post("/queue/{qid}/approve")
async def approve_queue_item(qid: str, request: Request):
    await get_current_user(request)
    item = await queue.approve_item(qid)
    if not item:
        raise HTTPException(404, "Queue item not found")
    return item


@router.post("/queue/{qid}/mark-sent")
async def mark_sent(qid: str, request: Request):
    await get_current_user(request)
    item = await queue.mark_sent(qid)
    if not item:
        raise HTTPException(404, "Queue item not found")
    if isinstance(item, dict) and item.get("error"):
        raise HTTPException(409, item["error"])
    return item


@router.post("/queue/{qid}/cancel")
async def cancel(qid: str, request: Request):
    await get_current_user(request)
    await queue.cancel_item(qid)
    return {"ok": True}


@router.delete("/queue/{qid}")
async def delete_queue_item(qid: str, request: Request):
    await get_current_user(request)
    await queue.delete_item(qid)
    return {"ok": True}


@router.post("/send-queue/bulk-add")
async def bulk_add_to_queue(data: BulkAddReq, request: Request):
    """Pick the top-N most recent campaigns + top-N most recent sponsor offers
    and push them into the send queue as pending / mock.

    The default link (small_donor for campaigns, sponsor for sponsors) is used
    for the payment link substitution if the individual row doesn't already have
    one attached.
    """
    await get_current_user(request)
    db = await get_db()
    # Top-N campaigns
    cursor = await db.execute(
        "SELECT * FROM donation_campaigns ORDER BY created_at DESC LIMIT ?",
        (data.campaign_top_n or 3,),
    )
    campaigns_top = [dict(r) for r in await cursor.fetchall()]
    # Top-N sponsors
    cursor = await db.execute(
        "SELECT * FROM sponsor_offers ORDER BY created_at DESC LIMIT ?",
        (data.sponsor_top_n or 3,),
    )
    sponsors_top = [dict(r) for r in await cursor.fetchall()]
    await db.close()

    default_sd = await plm.get_default_link("small_donor")
    default_sp = await plm.get_default_link("sponsor")
    default_sd_url = (default_sd or {}).get("tracking_url") or (default_sd or {}).get("url", "")
    default_sp_url = (default_sp or {}).get("tracking_url") or (default_sp or {}).get("url", "")

    added = []
    for c in campaigns_top:
        # Prefer the campaign's own linked URL; fall back to the default small-donor link.
        link_url = ""
        if c.get("payment_link_id"):
            pl = await plm.get_payment_link(c["payment_link_id"])
            if pl:
                link_url = pl.get("tracking_url") or pl.get("url", "")
        if not link_url:
            link_url = default_sd_url
        text = c.get("whatsapp_message", "") or c.get("short_post", "")
        if "{PAYMENT_LINK}" in text:
            text = text.replace("{PAYMENT_LINK}", link_url or "[add payment link]")
        item = await queue.enqueue(
            channel=data.channel_campaign or "whatsapp",
            target_type="campaign",
            target_id=c["id"],
            recipient=data.recipient_campaign or "broadcast-list",
            recipient_label=c.get("title", "")[:60],
            subject="",
            message=text,
            payment_link=link_url,
        )
        added.append({"kind": "campaign", "queue_id": item["id"], "target_id": c["id"], "title": c.get("title", "")})

    for s in sponsors_top:
        link_url = ""
        if s.get("payment_link_id"):
            pl = await plm.get_payment_link(s["payment_link_id"])
            if pl:
                link_url = pl.get("tracking_url") or pl.get("url", "")
        if not link_url:
            link_url = default_sp_url
        text = s.get("email_body", "") or s.get("whatsapp_message", "")
        if "{PAYMENT_LINK}" in text:
            text = text.replace("{PAYMENT_LINK}", link_url or "[add payment link]")
        item = await queue.enqueue(
            channel=data.channel_sponsor or "email",
            target_type="sponsor",
            target_id=s["id"],
            recipient=data.recipient_sponsor or "sponsor-list",
            recipient_label=s.get("sponsor_name", ""),
            subject=s.get("email_subject", ""),
            message=text,
            payment_link=link_url,
        )
        added.append({"kind": "sponsor", "queue_id": item["id"], "target_id": s["id"], "sponsor_name": s.get("sponsor_name", "")})

    return {"added": added, "count": len(added)}


# =====================================================================
#                       TikTok Campaign Engine (V12.2)
# =====================================================================

@router.post("/tiktok/generate")
async def tiktok_generate(data: TikTokGenerateReq, request: Request):
    """Generate a complete TikTok donation campaign pack.

    Always succeeds: if AI is missing or upstream errors, falls back to a
    high-quality deterministic template so the user is never blocked.
    """
    await get_current_user(request)
    payload = data.dict()
    pack = await generate_tiktok_pack(payload)

    saved_id = None
    if data.save:
        import uuid
        db = await get_db()
        saved_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO tiktok_campaigns
               (id, campaign_title, target_amount, cause_category, location,
                deadline, donation_link, tone, pack_json, ai_used, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                saved_id,
                data.campaign_title or "",
                str(data.target_amount or ""),
                data.cause_category or "",
                data.location or "",
                data.deadline or "",
                data.donation_link or "",
                data.tone or "",
                json.dumps(pack),
                1 if pack.get("scripts") and len(pack["scripts"]) >= 5 else 0,
                now_iso(),
            ),
        )
        await db.commit()
        await db.close()

    return {**pack, "id": saved_id}


@router.get("/tiktok")
async def tiktok_list(request: Request):
    """List saved TikTok campaigns (newest first)."""
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM tiktok_campaigns ORDER BY created_at DESC"
    )
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    out = []
    for r in rows:
        try:
            r["pack"] = json.loads(r.pop("pack_json", "") or "{}")
        except Exception:
            r["pack"] = {}
        out.append(r)
    return out


@router.get("/tiktok/{tt_id}")
async def tiktok_get(tt_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tiktok_campaigns WHERE id = ?", (tt_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="TikTok campaign not found")
    r = dict(row)
    try:
        r["pack"] = json.loads(r.pop("pack_json", "") or "{}")
    except Exception:
        r["pack"] = {}
    return r


@router.delete("/tiktok/{tt_id}")
async def tiktok_delete(tt_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("DELETE FROM tiktok_campaigns WHERE id = ?", (tt_id,))
    await db.commit()
    await db.close()
    return {"deleted": tt_id}

