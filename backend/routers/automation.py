"""
Automation routes (V12.3).

Prefix mounted as /api/automation via server.py.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from deps import get_current_user, get_db, now_iso
from services.automation_service import (
    scan_grants,
    generate_email_draft,
    generate_donor_prospects,
)

router = APIRouter(prefix="/automation")


# -------------------- Models --------------------

class ScanReq(BaseModel):
    sectors: Optional[List[str]] = None
    region: Optional[str] = "Africa"
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    deadline_within_days: Optional[int] = None
    sources: Optional[List[str]] = None
    save: Optional[bool] = True


class EmailDraftReq(BaseModel):
    kind: str = "grant"           # grant | sponsor | thank_you | follow_up | reapply
    recipient_name: Optional[str] = ""
    recipient_email: Optional[str] = ""
    organization: Optional[str] = ""
    context: Optional[str] = ""
    linked_id: Optional[str] = ""
    save: Optional[bool] = True


class DonorGenReq(BaseModel):
    categories: Optional[List[str]] = None
    country: Optional[str] = "Namibia"
    city: Optional[str] = "Windhoek"
    save: Optional[bool] = True


class StatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = ""


# -------------------- 1. GRANT SCANNER --------------------

@router.post("/grants/scan")
async def grants_scan(req: ScanReq, request: Request):
    await get_current_user(request)
    try:
        items = await scan_grants(req.dict())
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Scan failed: {e}")

    scan_id = str(uuid.uuid4())
    saved_ids: List[str] = []
    if req.save and items:
        db = await get_db()
        for it in items:
            rid = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO scanner_results
                   (id, scan_id, title, funder, amount_text, deadline,
                    country_eligibility, sector, official_url, submission_type,
                    submission_email, fit_score, summary, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rid, scan_id, it.get("title", ""), it.get("funder", ""),
                 it.get("amount_text", ""), it.get("deadline", ""),
                 it.get("country_eligibility", ""), it.get("sector", ""),
                 it.get("official_url", ""), it.get("submission_type", "unknown"),
                 it.get("submission_email", ""), int(it.get("fit_score") or 0),
                 it.get("summary", ""), "new", now_iso()),
            )
            saved_ids.append(rid)
        await db.commit()
        await db.close()
    return {"scan_id": scan_id, "items": items, "saved": len(saved_ids)}


@router.get("/grants/results")
async def grants_results(request: Request, status: Optional[str] = None):
    await get_current_user(request)
    db = await get_db()
    if status:
        cursor = await db.execute(
            "SELECT * FROM scanner_results WHERE status = ? ORDER BY fit_score DESC, created_at DESC",
            (status,),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM scanner_results ORDER BY fit_score DESC, created_at DESC LIMIT 200"
        )
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


@router.put("/grants/results/{rid}/status")
async def grants_result_status(rid: str, body: StatusUpdate, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute(
        "UPDATE scanner_results SET status = ? WHERE id = ?",
        (body.status, rid),
    )
    await db.commit()
    await db.close()
    return {"id": rid, "status": body.status}


@router.delete("/grants/results/{rid}")
async def grants_result_delete(rid: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("DELETE FROM scanner_results WHERE id = ?", (rid,))
    await db.commit()
    await db.close()
    return {"deleted": rid}


# -------------------- 2. EMAIL DRAFTS --------------------

@router.post("/email-drafts/generate")
async def email_draft_generate(req: EmailDraftReq, request: Request):
    await get_current_user(request)
    draft = await generate_email_draft(req.kind, req.dict())
    saved_id = None
    if req.save:
        db = await get_db()
        saved_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO email_drafts
               (id, draft_type, recipient_name, recipient_email, organization,
                context, subject, body, cta, attachments, status, linked_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (saved_id, req.kind, req.recipient_name or "",
             req.recipient_email or "", req.organization or "",
             req.context or "", draft.get("subject", ""),
             draft.get("body", ""), draft.get("cta", ""),
             json.dumps(draft.get("attachments") or []),
             "draft", req.linked_id or "", now_iso()),
        )
        await db.commit()
        await db.close()
    return {**draft, "id": saved_id, "draft_type": req.kind}


@router.get("/email-drafts")
async def email_drafts_list(request: Request, status: Optional[str] = None):
    await get_current_user(request)
    db = await get_db()
    if status:
        cursor = await db.execute(
            "SELECT * FROM email_drafts WHERE status = ? ORDER BY created_at DESC",
            (status,),
        )
    else:
        cursor = await db.execute("SELECT * FROM email_drafts ORDER BY created_at DESC")
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    out = []
    for r in rows:
        try:
            r["attachments"] = json.loads(r.get("attachments") or "[]")
        except Exception:
            r["attachments"] = []
        out.append(r)
    return out


@router.put("/email-drafts/{did}/mark-sent")
async def email_draft_mark_sent(did: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute(
        "UPDATE email_drafts SET status = 'sent', sent_at = ? WHERE id = ?",
        (now_iso(), did),
    )
    await db.commit()
    await db.close()
    return {"id": did, "status": "sent"}


@router.put("/email-drafts/{did}/follow-up")
async def email_draft_follow_up(did: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute(
        "UPDATE email_drafts SET status = 'follow_up_needed', follow_up_at = ? WHERE id = ?",
        (now_iso(), did),
    )
    await db.commit()
    await db.close()
    return {"id": did, "status": "follow_up_needed"}


@router.delete("/email-drafts/{did}")
async def email_draft_delete(did: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("DELETE FROM email_drafts WHERE id = ?", (did,))
    await db.commit()
    await db.close()
    return {"deleted": did}


# -------------------- 3. DONOR PROSPECTS --------------------

@router.post("/donors/generate")
async def donors_generate(req: DonorGenReq, request: Request):
    await get_current_user(request)
    prospects = await generate_donor_prospects(req.dict())
    saved_ids: List[str] = []
    if req.save and prospects:
        db = await get_db()
        for p in prospects:
            pid = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO donor_prospects
                   (id, organization, category, country, city, website, email,
                    phone, contact_person, suggested_amount, suggested_campaign,
                    outreach_angle, priority_score, manual_lookup_required,
                    status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pid, p.get("organization", ""), p.get("category", ""),
                 p.get("country", ""), p.get("city", ""), p.get("website", ""),
                 p.get("email", ""), p.get("phone", ""),
                 p.get("contact_person", ""), p.get("suggested_amount", ""),
                 p.get("suggested_campaign", ""), p.get("outreach_angle", ""),
                 int(p.get("priority_score") or 0),
                 1 if p.get("manual_lookup_required") else 0,
                 "new", now_iso()),
            )
            saved_ids.append(pid)
        await db.commit()
        await db.close()
    return {"prospects": prospects, "saved": len(saved_ids)}


@router.get("/donors")
async def donors_list(request: Request, status: Optional[str] = None):
    await get_current_user(request)
    db = await get_db()
    if status:
        cursor = await db.execute(
            "SELECT * FROM donor_prospects WHERE status = ? ORDER BY priority_score DESC, created_at DESC",
            (status,),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM donor_prospects ORDER BY priority_score DESC, created_at DESC LIMIT 500"
        )
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


@router.put("/donors/{pid}/status")
async def donor_status(pid: str, body: StatusUpdate, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute(
        "UPDATE donor_prospects SET status = ?, notes = COALESCE(?, notes) WHERE id = ?",
        (body.status, body.notes or None, pid),
    )
    await db.commit()
    await db.close()
    return {"id": pid, "status": body.status}


@router.delete("/donors/{pid}")
async def donor_delete(pid: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("DELETE FROM donor_prospects WHERE id = ?", (pid,))
    await db.commit()
    await db.close()
    return {"deleted": pid}


# -------------------- DASHBOARD WIDGET --------------------

@router.get("/summary")
async def automation_summary(request: Request):
    """Counts for the dashboard Automation Center widget."""
    await get_current_user(request)
    db = await get_db()
    async def count(sql: str, params: tuple = ()) -> int:
        cur = await db.execute(sql, params)
        row = await cur.fetchone()
        return int(dict(row or {}).get("c") or 0)

    out: Dict[str, Any] = {
        "grants_new": await count("SELECT COUNT(*) AS c FROM scanner_results WHERE status='new'"),
        "grants_high_fit": await count(
            "SELECT COUNT(*) AS c FROM scanner_results WHERE status='new' AND fit_score >= 70"
        ),
        "donors_new": await count("SELECT COUNT(*) AS c FROM donor_prospects WHERE status='new'"),
        "drafts_pending": await count("SELECT COUNT(*) AS c FROM email_drafts WHERE status='draft'"),
        "follow_ups_due": await count(
            "SELECT COUNT(*) AS c FROM email_drafts WHERE status='follow_up_needed'"
        ),
    }
    await db.close()
    return out
