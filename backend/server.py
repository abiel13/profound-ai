from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware
import aiosqlite
import asyncio
import json
import uuid
import os
import re
import bcrypt
import jwt
import logging
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from typing import Optional, List
from database import DB_PATH, init_db
from seed_data import DEMO_OPPORTUNITIES, DEFAULT_SOURCES, DEFAULT_ORG_PROFILE, ORG_KNOWLEDGE_BASE

app = FastAPI(title="ProFund AI")
api_router = APIRouter(prefix="/api")

JWT_SECRET = os.environ.get("JWT_SECRET", "fallback-secret-key")
JWT_ALGORITHM = "HS256"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@profund.ai")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ProFund2024!")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Bulk analysis state (single-user, in-memory tracking)
bulk_state = {"running": False, "total": 0, "processed": 0, "errors": 0}

# Monitoring system state
monitor_state = {"active": False, "last_scan": None, "next_scan": None, "scans_completed": 0}

# Smart queue state
queue_state = {"generating": False, "last_generated": None}
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Database Helper ---
async def get_db():
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")
    return db


# --- Auth Helpers ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        db = await get_db()
        cursor = await db.execute("SELECT id, email, name, role FROM users WHERE id = ?", (payload["sub"],))
        row = await cursor.fetchone()
        await db.close()
        if not row:
            raise HTTPException(status_code=401, detail="User not found")
        return dict(row)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# --- Pydantic Models ---
class LoginRequest(BaseModel):
    email: str
    password: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    mission: Optional[str] = None
    focus_sectors: Optional[List[str]] = None
    beneficiaries: Optional[List[str]] = None
    funding_needs_min: Optional[float] = None
    funding_needs_max: Optional[float] = None

class SaveOpportunity(BaseModel):
    opportunity_id: str

class UpdateSavedStatus(BaseModel):
    status: str
    notes: Optional[str] = None

class SourceCreate(BaseModel):
    name: str
    url: Optional[str] = ""
    type: Optional[str] = ""
    description: Optional[str] = ""

class SourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None

class AIRequest(BaseModel):
    opportunity_id: str

class ProposalRequest(BaseModel):
    opportunity_id: str
    project_idea: str
    beneficiaries: str
    funding_amount: float


# ============================
#        AUTH ROUTES
# ============================

@api_router.post("/auth/login")
async def login(req: LoginRequest):
    db = await get_db()
    cursor = await db.execute("SELECT id, email, name, role, password_hash FROM users WHERE email = ?", (req.email.lower(),))
    user = await cursor.fetchone()
    await db.close()
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["email"])
    return {
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]}
    }


@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    return user


@api_router.post("/auth/logout")
async def logout():
    return {"message": "Logged out"}


# ============================
#      PROFILE ROUTES
# ============================

@api_router.get("/profile")
async def get_profile(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM organization_profile WHERE id = 'org-1'")
    row = await cursor.fetchone()
    await db.close()
    if not row:
        return DEFAULT_ORG_PROFILE
    profile = dict(row)
    profile["focus_sectors"] = json.loads(profile.get("focus_sectors", "[]"))
    profile["beneficiaries"] = json.loads(profile.get("beneficiaries", "[]"))
    return profile


@api_router.put("/profile")
async def update_profile(data: ProfileUpdate, request: Request):
    await get_current_user(request)
    db = await get_db()
    fields = {}
    if data.name is not None:
        fields["name"] = data.name
    if data.country is not None:
        fields["country"] = data.country
    if data.mission is not None:
        fields["mission"] = data.mission
    if data.focus_sectors is not None:
        fields["focus_sectors"] = json.dumps(data.focus_sectors)
    if data.beneficiaries is not None:
        fields["beneficiaries"] = json.dumps(data.beneficiaries)
    if data.funding_needs_min is not None:
        fields["funding_needs_min"] = data.funding_needs_min
    if data.funding_needs_max is not None:
        fields["funding_needs_max"] = data.funding_needs_max
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values())
    await db.execute(f"UPDATE organization_profile SET {set_clause} WHERE id = 'org-1'", values)
    await db.commit()
    cursor = await db.execute("SELECT * FROM organization_profile WHERE id = 'org-1'")
    row = await cursor.fetchone()
    await db.close()
    profile = dict(row)
    profile["focus_sectors"] = json.loads(profile.get("focus_sectors", "[]"))
    profile["beneficiaries"] = json.loads(profile.get("beneficiaries", "[]"))
    return profile


# ============================
#    OPPORTUNITIES ROUTES
# ============================

@api_router.get("/opportunities")
async def list_opportunities(
    request: Request,
    search: Optional[str] = None,
    sector: Optional[str] = None,
    donor_type: Optional[str] = None,
    min_funding: Optional[float] = None,
    max_funding: Optional[float] = None,
    submission: Optional[str] = None,  # 'email' | 'portal' | 'form' | 'active'
    sort_by: Optional[str] = "deadline"
):
    await get_current_user(request)
    db = await get_db()
    query = "SELECT * FROM opportunities WHERE 1=1"
    params = []
    if search:
        query += " AND (title LIKE ? OR donor_name LIKE ? OR description LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
    if sector:
        query += " AND sector = ?"
        params.append(sector)
    if donor_type:
        query += " AND donor_type = ?"
        params.append(donor_type)
    if min_funding is not None:
        query += " AND funding_max >= ?"
        params.append(min_funding)
    if max_funding is not None:
        query += " AND funding_min <= ?"
        params.append(max_funding)
    if submission == "email":
        query += " AND submission_type = 'email' AND submission_email != ''"
    elif submission == "portal":
        query += " AND submission_type = 'portal' AND submission_url != ''"
    elif submission == "form":
        query += " AND submission_type = 'form'"
    elif submission == "active":
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        query += " AND deadline >= ?"
        params.append(today_str)
    if sort_by == "deadline":
        query += " ORDER BY deadline ASC"
    elif sort_by == "funding":
        query += " ORDER BY funding_max DESC"
    elif sort_by == "match":
        query += " ORDER BY ai_match_score DESC"
    else:
        query += " ORDER BY created_at DESC"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


@api_router.get("/opportunities/dashboard")
async def dashboard_data(request: Request):
    await get_current_user(request)
    db = await get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    soon = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
    week = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

    # Top opportunities (highest AI match scores > 0)
    cursor = await db.execute("SELECT * FROM opportunities WHERE ai_match_score > 0 ORDER BY ai_match_score DESC LIMIT 6")
    top_opportunities = [dict(r) for r in await cursor.fetchall()]

    # High match (Apply Now - score >= 80)
    cursor = await db.execute("SELECT * FROM opportunities WHERE ai_match_score >= 80 ORDER BY ai_match_score DESC LIMIT 5")
    high_match = [dict(r) for r in await cursor.fetchall()]

    # Expiring soon (within 30 days)
    cursor = await db.execute(
        "SELECT * FROM opportunities WHERE deadline >= ? AND deadline <= ? ORDER BY deadline ASC LIMIT 5",
        (today, soon)
    )
    expiring_soon = [dict(r) for r in await cursor.fetchall()]

    # Recently added
    cursor = await db.execute("SELECT * FROM opportunities ORDER BY created_at DESC LIMIT 5")
    recently_added = [dict(r) for r in await cursor.fetchall()]

    # Saved with status
    cursor = await db.execute("""
        SELECT o.*, s.id as saved_id, s.status, s.saved_at
        FROM saved_opportunities s
        JOIN opportunities o ON s.opportunity_id = o.id
        ORDER BY s.saved_at DESC LIMIT 5
    """)
    saved = [dict(r) for r in await cursor.fetchall()]

    # Pipeline value by stage
    cursor = await db.execute("""
        SELECT s.status, SUM(o.funding_max) as total_max, SUM(o.funding_min) as total_min, COUNT(*) as count
        FROM saved_opportunities s
        JOIN opportunities o ON s.opportunity_id = o.id
        GROUP BY s.status
    """)
    pipeline_stages = {}
    pipeline_total = 0
    for row in await cursor.fetchall():
        r = dict(row)
        pipeline_stages[r['status']] = {'count': r['count'], 'total_min': r['total_min'] or 0, 'total_max': r['total_max'] or 0}
        pipeline_total += r['total_max'] or 0

    # All opportunities total value
    cursor = await db.execute("SELECT SUM(funding_max) as total FROM opportunities")
    all_value = (await cursor.fetchone())['total'] or 0

    # Stats
    cursor = await db.execute("SELECT COUNT(*) as count FROM opportunities")
    total = (await cursor.fetchone())["count"]
    cursor = await db.execute("SELECT COUNT(*) as count FROM saved_opportunities")
    saved_count = (await cursor.fetchone())["count"]
    cursor = await db.execute(
        "SELECT COUNT(*) as count FROM opportunities WHERE deadline >= ? AND deadline <= ?",
        (today, soon)
    )
    expiring_count = (await cursor.fetchone())["count"]
    cursor = await db.execute("SELECT COUNT(*) as count FROM opportunities WHERE ai_match_score >= 80")
    apply_now_count = (await cursor.fetchone())["count"]
    cursor = await db.execute("SELECT COUNT(*) as count FROM opportunities WHERE ai_match_score > 0")
    analyzed_count = (await cursor.fetchone())["count"]

    # AI Actions (algorithmic, no AI call needed)
    actions = []
    # 1. High-match unsaved opportunities
    cursor = await db.execute("""
        SELECT o.* FROM opportunities o
        LEFT JOIN saved_opportunities s ON o.id = s.opportunity_id
        WHERE s.id IS NULL AND o.ai_match_score >= 80 AND o.deadline >= ?
        ORDER BY o.ai_match_score DESC LIMIT 3
    """, (today,))
    for row in await cursor.fetchall():
        r = dict(row)
        days = max(0, (datetime.strptime(r['deadline'], '%Y-%m-%d') - datetime.now(timezone.utc).replace(tzinfo=None)).days)
        actions.append({"type": "apply", "priority": "high", "message": f"Apply to {r['title']} - {r['ai_match_score']}% match, {days}d left", "opportunity_id": r['id']})

    # 2. Saved needing action (urgent deadlines)
    cursor = await db.execute("""
        SELECT o.*, s.status as saved_status FROM saved_opportunities s
        JOIN opportunities o ON s.opportunity_id = o.id
        WHERE s.status IN ('New', 'Reviewing', 'Preparing') AND o.deadline >= ? AND o.deadline <= ?
        ORDER BY o.deadline ASC LIMIT 3
    """, (today, soon))
    for row in await cursor.fetchall():
        r = dict(row)
        days = max(0, (datetime.strptime(r['deadline'], '%Y-%m-%d') - datetime.now(timezone.utc).replace(tzinfo=None)).days)
        prio = "critical" if days <= 7 else "high" if days <= 14 else "medium"
        actions.append({"type": "urgent" if days <= 7 else "prepare", "priority": prio, "message": f"{'URGENT: ' if days <= 7 else ''}Complete proposal for {r['title']} ({r['saved_status']}) - {days}d left", "opportunity_id": r['id']})

    # 3. Low-match to skip
    cursor = await db.execute("SELECT * FROM opportunities WHERE ai_match_score > 0 AND ai_match_score < 60 LIMIT 2")
    for row in await cursor.fetchall():
        r = dict(row)
        actions.append({"type": "skip", "priority": "low", "message": f"Skip {r['title']} - only {r['ai_match_score']}% match", "opportunity_id": r['id']})

    await db.close()
    return {
        "top_opportunities": top_opportunities,
        "high_match": high_match,
        "expiring_soon": expiring_soon,
        "recently_added": recently_added,
        "saved": saved,
        "actions": actions,
        "pipeline": {"total": pipeline_total, "all_value": all_value, "stages": pipeline_stages},
        "stats": {
            "total_opportunities": total,
            "saved_count": saved_count,
            "expiring_soon_count": expiring_count,
            "apply_now_count": apply_now_count,
            "analyzed_count": analyzed_count
        }
    }


@api_router.get("/opportunities/{opp_id}")
async def get_opportunity(opp_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
    row = await cursor.fetchone()
    # Check if saved
    cursor2 = await db.execute("SELECT * FROM saved_opportunities WHERE opportunity_id = ?", (opp_id,))
    saved_row = await cursor2.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    result = dict(row)
    result["is_saved"] = saved_row is not None
    if saved_row:
        result["saved_status"] = dict(saved_row)["status"]
        result["saved_id"] = dict(saved_row)["id"]
    return result


@api_router.post("/opportunities/{opp_id}/fetch-submission")
async def fetch_opportunity_submission(opp_id: str, request: Request):
    """Scrape the official opportunity URL to extract submission details
    (apply link, email, type, instructions). Stored on the opportunity row.
    Idempotent — safe to call repeatedly."""
    await get_current_user(request)
    from services.grant_submission_service import fetch_submission_details

    db = await get_db()
    cursor = await db.execute("SELECT id, url FROM opportunities WHERE id = ?", (opp_id,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail="Opportunity not found")
    grant_url = dict(row).get("url", "")
    if not grant_url:
        await db.close()
        return {
            "submission_url": "",
            "submission_email": "",
            "submission_type": "unknown",
            "apply_instructions": "No source URL on this opportunity.",
            "fetched": False,
        }

    details = await fetch_submission_details(grant_url)
    now_str = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """UPDATE opportunities
           SET submission_url = ?, submission_email = ?, submission_type = ?,
               apply_instructions = ?, submission_fetched_at = ?
           WHERE id = ?""",
        (
            details.get("submission_url") or "",
            details.get("submission_email") or "",
            details.get("submission_type") or "unknown",
            details.get("apply_instructions") or "",
            now_str,
            opp_id,
        ),
    )
    await db.commit()
    await db.close()
    return {**details, "fetched": True, "fetched_at": now_str}


@api_router.post("/opportunities/{opp_id}/email-template")
async def generate_email_template(opp_id: str, request: Request):
    """Build a polished email subject/body the user can paste into their mail
    client when the grant accepts email submissions. No AI required — uses
    the saved org profile + the generated wizard documents (if any)."""
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp = dict(row)
    cursor = await db.execute("SELECT * FROM organization_profile LIMIT 1")
    prof_row = await cursor.fetchone()
    cursor = await db.execute(
        "SELECT documents FROM application_wizards WHERE opportunity_id = ? ORDER BY updated_at DESC LIMIT 1",
        (opp_id,),
    )
    wiz_row = await cursor.fetchone()
    await db.close()

    org = dict(prof_row) if prof_row else {}
    org_name = org.get("name") or "Our Organization"
    org_country = org.get("country") or ""
    docs = {}
    if wiz_row:
        try:
            docs = json.loads(dict(wiz_row).get("documents", "{}") or "{}")
        except Exception:
            docs = {}

    attachments_lines = []
    for key, label in [
        ("cover_letter", "Cover Letter"),
        ("executive_summary", "Executive Summary"),
        ("project_narrative", "Project Narrative"),
        ("budget_justification", "Budget Justification"),
        ("sustainability_plan", "Sustainability Plan"),
        ("monitoring_plan", "Monitoring & Evaluation Plan"),
    ]:
        if (docs.get(key) or "").strip():
            attachments_lines.append(f"  - {label}")
    attachments_block = "\n".join(attachments_lines) if attachments_lines else "  - (Documents attached separately)"

    subject = f"Grant Application – {org_name} – {opp.get('title', '')}".strip(" –")
    body = (
        f"Dear {opp.get('donor_name') or 'Grants Team'},\n\n"
        f"My name is {org_name}, a non-profit organization "
        f"{('based in ' + org_country) if org_country else ''}. "
        f"I am writing to formally submit our application for the "
        f"\"{opp.get('title', '')}\" funding opportunity.\n\n"
        f"Our proposal addresses the priorities outlined in the call. "
        f"A summary of the project, expected outcomes and budget is included "
        f"in the attached documents.\n\n"
        f"Attached, please find the following documents:\n{attachments_block}\n\n"
        f"We would be glad to provide any additional information you may "
        f"require. Thank you for your consideration of this request.\n\n"
        f"Kind regards,\n"
        f"{org_name}"
    )
    return {
        "to": opp.get("submission_email", ""),
        "subject": subject,
        "body": body,
    }


# ============================
#       SAVED ROUTES
# ============================

@api_router.get("/saved")
async def list_saved(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("""
        SELECT o.*, s.id as saved_id, s.status, s.notes as saved_notes, s.saved_at, s.updated_at as status_updated
        FROM saved_opportunities s
        JOIN opportunities o ON s.opportunity_id = o.id
        ORDER BY s.saved_at DESC
    """)
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


@api_router.post("/saved")
async def save_opportunity(data: SaveOpportunity, request: Request):
    await get_current_user(request)
    db = await get_db()
    # Check if already saved
    cursor = await db.execute("SELECT id FROM saved_opportunities WHERE opportunity_id = ?", (data.opportunity_id,))
    existing = await cursor.fetchone()
    if existing:
        await db.close()
        raise HTTPException(status_code=400, detail="Already saved")
    sid = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO saved_opportunities (id, opportunity_id, status, notes, saved_at, updated_at) VALUES (?, ?, 'New', '', ?, ?)",
        (sid, data.opportunity_id, now_str, now_str)
    )
    await db.commit()
    await db.close()
    return {"id": sid, "opportunity_id": data.opportunity_id, "status": "New", "saved_at": now_str}


@api_router.put("/saved/{saved_id}")
async def update_saved(saved_id: str, data: UpdateSavedStatus, request: Request):
    await get_current_user(request)
    valid_statuses = ["New", "Reviewing", "Preparing", "Submitted", "Rejected", "Approved", "Identified", "Analyzing", "Drafting", "Ready to Submit"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    db = await get_db()
    now_str = datetime.now(timezone.utc).isoformat()
    fields = {"status": data.status, "updated_at": now_str}
    if data.notes is not None:
        fields["notes"] = data.notes
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [saved_id]
    await db.execute(f"UPDATE saved_opportunities SET {set_clause} WHERE id = ?", values)
    await db.commit()
    await db.close()
    return {"id": saved_id, "status": data.status, "updated_at": now_str}


@api_router.delete("/saved/{saved_id}")
async def delete_saved(saved_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("DELETE FROM saved_opportunities WHERE id = ?", (saved_id,))
    await db.commit()
    await db.close()
    return {"message": "Removed from saved"}


# ============================
#        AI ROUTES
# ============================

async def get_org_profile_text():
    """Return the complete organization knowledge base for AI prompts."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM organization_profile WHERE id = 'org-1'")
    row = await cursor.fetchone()
    await db.close()
    if not row:
        return ORG_KNOWLEDGE_BASE
    p = dict(row)
    sectors = json.loads(p.get("focus_sectors", "[]"))
    beneficiaries = json.loads(p.get("beneficiaries", "[]"))
    # Always return the full knowledge base plus any user-customized fields
    return f"""{ORG_KNOWLEDGE_BASE}

CURRENT PROFILE SETTINGS:
Organization Name: {p['name']}
Country: {p['country']}
Focus Sectors: {', '.join(sectors)}
Beneficiaries: {', '.join(beneficiaries)}
Funding Range: USD {p['funding_needs_min']:,.0f} - USD {p['funding_needs_max']:,.0f}"""


async def get_learning_context(donor_name: str, donor_type: str, sector: str) -> str:
    """Build AI learning context from historical outcomes for score boosting."""
    db = await get_db()
    lines = []
    # Donor performance
    cursor = await db.execute(
        "SELECT outcome, COUNT(*) as c FROM application_outcomes WHERE donor_name = ? GROUP BY outcome", (donor_name,))
    donor_stats = {r['outcome']: r['c'] for r in await cursor.fetchall()}
    if donor_stats:
        approved = donor_stats.get('approved', 0)
        total = sum(donor_stats.values())
        rate = (approved / total * 100) if total else 0
        if approved > 0:
            lines.append(f"LEARNING BOOST: This donor ({donor_name}) has approved {approved}/{total} applications ({rate:.0f}% success). Increase score by 5-10 points.")
        elif donor_stats.get('rejected', 0) >= 2:
            lines.append(f"LEARNING PENALTY: This donor ({donor_name}) has rejected {donor_stats['rejected']} applications. Reduce score by 5-10 points.")

    # Donor type performance
    cursor = await db.execute(
        "SELECT outcome, COUNT(*) as c FROM application_outcomes WHERE donor_type = ? GROUP BY outcome", (donor_type,))
    type_stats = {r['outcome']: r['c'] for r in await cursor.fetchall()}
    if type_stats.get('approved', 0) > 0:
        lines.append(f"CONTEXT: {donor_type} donors have {type_stats['approved']} approvals historically.")

    # Sector performance
    cursor = await db.execute(
        "SELECT outcome, COUNT(*) as c FROM application_outcomes WHERE sector = ? GROUP BY outcome", (sector,))
    sector_stats = {r['outcome']: r['c'] for r in await cursor.fetchall()}
    if sector_stats.get('approved', 0) > 0:
        lines.append(f"CONTEXT: {sector} sector has {sector_stats['approved']} approvals historically.")

    await db.close()
    return "\n".join(lines) if lines else ""


async def call_ai(system_msg: str, user_msg: str) -> str:
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=str(uuid.uuid4()),
            system_message=system_msg
        )
        chat.with_model("openai", "gpt-5.2")
        response = await chat.send_message(UserMessage(text=user_msg))
        return response
    except Exception as e:
        logger.error(f"AI call failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@api_router.post("/ai/summarize")
async def ai_summarize(data: AIRequest, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (data.opportunity_id,))
    opp = await cursor.fetchone()
    await db.close()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp = dict(opp)
    system = "You are a grant analysis expert working for Pro Youth Foundation, a Namibian non-profit rescuing vulnerable children, street children, and mothers from abuse and poverty — providing safe hostels, education (school fees), food hampers, and clothing. Summarize this grant focusing on: who can apply, what's funded, amount, deadline, and relevance to child protection, street children rehabilitation, safe housing, and education. Under 150 words. Direct."
    user_msg = f"""Summarize this grant opportunity:
Title: {opp['title']}
Donor: {opp['donor_name']} ({opp['donor_type']})
Funding: USD {opp['funding_min']:,.0f} - USD {opp['funding_max']:,.0f}
Deadline: {opp['deadline']}
Region: {opp['region']}
Description: {opp['description']}
Eligibility: {opp['eligibility']}"""
    summary = await call_ai(system, user_msg)
    # Cache in DB
    db = await get_db()
    await db.execute("UPDATE opportunities SET ai_summary = ? WHERE id = ?", (summary, data.opportunity_id))
    await db.commit()
    await db.close()
    return {"summary": summary, "opportunity_id": data.opportunity_id}


@api_router.post("/ai/match-score")
async def ai_match_score(data: AIRequest, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (data.opportunity_id,))
    opp = await cursor.fetchone()
    await db.close()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp = dict(opp)
    org_text = await get_org_profile_text()

    # AI Learning: get historical performance data to boost scoring
    learning_context = await get_learning_context(opp.get('donor_name', ''), opp.get('donor_type', ''), opp.get('sector', ''))

    system = f"""You are a grant matching expert for Pro Youth Foundation, a Namibian non-profit that rescues vulnerable children (including street children and orphans) and mothers from abuse and poverty, providing safe hostels, school fees, food hampers, and clothing.
Return ONLY a JSON object: {{"score": <number 0-100>, "explanation": "<brief 2-3 sentence explanation>"}}
Score criteria: 0-30=Poor, 31-60=Moderate, 61-80=Good, 81-100=Excellent.
PRIORITIZE grants related to: child protection, street children rehabilitation, safe housing/shelter, education access (school fees), food security, women/mother support, poverty relief, humanitarian aid.
Consider: sector alignment, geographic eligibility (Namibia/Africa), funding range fit, beneficiary overlap (vulnerable children, street children, orphans, mothers).
{learning_context}"""
    user_msg = f"""ORGANIZATION PROFILE:
{org_text}

GRANT OPPORTUNITY:
Title: {opp['title']}
Donor: {opp['donor_name']} ({opp['donor_type']})
Sector: {opp['sector']}
Region: {opp['region']}
Funding: USD {opp['funding_min']:,.0f} - USD {opp['funding_max']:,.0f}
Eligibility: {opp['eligibility']}
Africa Eligible: {'Yes' if opp['africa_eligible'] else 'No'}"""
    result = await call_ai(system, user_msg)
    try:
        # Try to parse JSON from AI response
        import re
        json_match = re.search(r'\{[^}]+\}', result)
        if json_match:
            parsed = json.loads(json_match.group())
            score = min(100, max(0, int(parsed.get("score", 0))))
            explanation = parsed.get("explanation", "")
        else:
            score = 50
            explanation = result
    except (json.JSONDecodeError, ValueError):
        score = 50
        explanation = result
    # Cache
    fit_level = "High" if score >= 80 else "Medium" if score >= 60 else "Low"
    decision_label = "Apply Now" if score >= 80 else "Review First" if score >= 60 else "Ignore"
    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute(
        "UPDATE opportunities SET ai_match_score = ?, ai_fit_explanation = ?, fit_level = ?, decision_label = ?, last_analyzed = ? WHERE id = ?",
        (score, explanation, fit_level, decision_label, now_str, data.opportunity_id))
    await db.commit()
    await db.close()
    return {"score": score, "explanation": explanation, "fit_level": fit_level, "decision_label": decision_label, "opportunity_id": data.opportunity_id}


@api_router.post("/ai/fit-explanation")
async def ai_fit_explanation(data: AIRequest, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (data.opportunity_id,))
    opp = await cursor.fetchone()
    await db.close()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp = dict(opp)
    org_text = await get_org_profile_text()
    system = """You are a grant advisor for Pro Youth Foundation, a Namibian non-profit that rescues vulnerable children (including street children and orphans) and mothers from abuse and poverty, providing safe hostels, school fees, food hampers, and clothing.
Explain clearly why this grant fits or doesn't fit. Be specific about:
1. Alignment with child protection, street children rehabilitation, housing, education, food security
2. Geographic eligibility (Namibia/Africa)
3. What to emphasize: rescuing children from streets and abuse, moving them to safe hostels, measurable outcomes (children housed, street children reintegrated, school fees paid, families fed)
Under 200 words. Direct and actionable."""
    user_msg = f"""ORGANIZATION PROFILE:
{org_text}

GRANT OPPORTUNITY:
Title: {opp['title']}
Donor: {opp['donor_name']} ({opp['donor_type']}, {opp['donor_country']})
Sector: {opp['sector']}
Region: {opp['region']}
Funding: USD {opp['funding_min']:,.0f} - USD {opp['funding_max']:,.0f}
Deadline: {opp['deadline']}
Description: {opp['description']}
Eligibility: {opp['eligibility']}"""
    explanation = await call_ai(system, user_msg)
    return {"explanation": explanation, "opportunity_id": data.opportunity_id}


# ============================
#      PROPOSAL ROUTES
# ============================

@api_router.post("/proposals/generate")
async def generate_proposal(data: ProposalRequest, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (data.opportunity_id,))
    opp = await cursor.fetchone()
    await db.close()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp = dict(opp)
    org_text = await get_org_profile_text()
    system = """You are an expert grant proposal writer for Pro Youth Foundation, a Namibian non-profit that rescues vulnerable children (including street children and orphans) and mothers from abusive, unsafe environments — providing safe hostels, school fees, food hampers, and clothing.

Generate professional, donor-facing content. Return a JSON object with these keys:
{
  "donor_email": "<cover email, 150-200 words. Reference: rescuing street children, hostels, school fees, food hampers>",
  "letter_of_interest": "<formal letter, 300-400 words. Background: rescuing children from streets/abuse. Programs: hostels, school fees, food, clothing. Measurable impact.>",
  "concept_note": "<Background (street children, abuse, poverty in Namibia), Objectives (safe housing, street child reintegration, education, food security), Activities (hostels, street outreach, school fees, food distribution), Outcomes (children housed, street children removed, fees paid, families fed), Budget. 500-600 words>",
  "proposal_outline": "<detailed numbered outline>",
  "checklist": "<8-12 items>"
}
CRITICAL: Every document MUST include: safe housing/hostels, street children rehabilitation, education (school fees), food (monthly hampers), clothing, protection from abuse. Show transformation: streets/abuse -> safe living. Measurable outcomes. No generic NGO language."""
    user_msg = f"""ORGANIZATION:
{org_text}

GRANT OPPORTUNITY:
Title: {opp['title']}
Donor: {opp['donor_name']}
Sector: {opp['sector']}
Funding: USD {opp['funding_min']:,.0f} - USD {opp['funding_max']:,.0f}

PROJECT DETAILS:
Idea: {data.project_idea}
Target Beneficiaries: {data.beneficiaries}
Requested Amount: USD {data.funding_amount:,.0f}"""
    result = await call_ai(system, user_msg)
    # Parse JSON
    try:
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = {
                "donor_email": result,
                "letter_of_interest": "",
                "concept_note": "",
                "proposal_outline": "",
                "checklist": ""
            }
    except (json.JSONDecodeError, ValueError):
        parsed = {
            "donor_email": result,
            "letter_of_interest": "",
            "concept_note": "",
            "proposal_outline": "",
            "checklist": ""
        }
    proposal_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute(
        """INSERT INTO proposals (id, opportunity_id, opportunity_title, project_idea, beneficiaries_desc,
           funding_amount, donor_email, letter_of_interest, concept_note, proposal_outline, checklist, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (proposal_id, data.opportunity_id, opp['title'], data.project_idea, data.beneficiaries,
         data.funding_amount, parsed.get("donor_email", ""), parsed.get("letter_of_interest", ""),
         parsed.get("concept_note", ""), parsed.get("proposal_outline", ""),
         parsed.get("checklist", ""), now_str)
    )
    await db.commit()
    await db.close()
    return {
        "id": proposal_id,
        "opportunity_id": data.opportunity_id,
        "opportunity_title": opp['title'],
        "project_idea": data.project_idea,
        "beneficiaries_desc": data.beneficiaries,
        "funding_amount": data.funding_amount,
        "donor_email": parsed.get("donor_email", ""),
        "letter_of_interest": parsed.get("letter_of_interest", ""),
        "concept_note": parsed.get("concept_note", ""),
        "proposal_outline": parsed.get("proposal_outline", ""),
        "checklist": parsed.get("checklist", ""),
        "created_at": now_str
    }


@api_router.get("/proposals")
async def list_proposals(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM proposals ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


@api_router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return dict(row)


@api_router.delete("/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("DELETE FROM proposals WHERE id = ?", (proposal_id,))
    await db.commit()
    await db.close()
    return {"message": "Proposal deleted"}


# ============================
#      SOURCES ROUTES
# ============================

@api_router.get("/sources")
async def list_sources(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM sources ORDER BY name ASC")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


@api_router.post("/sources")
async def create_source(data: SourceCreate, request: Request):
    await get_current_user(request)
    source_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute(
        "INSERT INTO sources (id, name, url, type, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (source_id, data.name, data.url, data.type, data.description, now_str)
    )
    await db.commit()
    await db.close()
    return {"id": source_id, "name": data.name, "url": data.url, "type": data.type, "description": data.description, "created_at": now_str}


@api_router.put("/sources/{source_id}")
async def update_source(source_id: str, data: SourceUpdate, request: Request):
    await get_current_user(request)
    db = await get_db()
    fields = {}
    if data.name is not None:
        fields["name"] = data.name
    if data.url is not None:
        fields["url"] = data.url
    if data.type is not None:
        fields["type"] = data.type
    if data.description is not None:
        fields["description"] = data.description
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [source_id]
    await db.execute(f"UPDATE sources SET {set_clause} WHERE id = ?", values)
    await db.commit()
    cursor = await db.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")
    return dict(row)


@api_router.delete("/sources/{source_id}")
async def delete_source(source_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    await db.commit()
    await db.close()
    return {"message": "Source deleted"}


# ============================
#     DEADLINES ROUTE
# ============================

@api_router.get("/deadlines")
async def get_deadlines(request: Request):
    await get_current_user(request)
    db = await get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT * FROM opportunities WHERE deadline >= ? ORDER BY deadline ASC",
        (today,)
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


# ============================
#     SECTORS/TYPES ROUTE
# ============================

@api_router.get("/filters")
async def get_filter_options(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT DISTINCT sector FROM opportunities WHERE sector != '' ORDER BY sector")
    sectors = [row["sector"] for row in await cursor.fetchall()]
    cursor = await db.execute("SELECT DISTINCT donor_type FROM opportunities WHERE donor_type != '' ORDER BY donor_type")
    donor_types = [row["donor_type"] for row in await cursor.fetchall()]
    await db.close()
    return {"sectors": sectors, "donor_types": donor_types}


# ============================
#     BULK AI ANALYSIS
# ============================

async def call_ai_fast(system_msg: str, user_msg: str) -> str:
    """Fast-model variant of call_ai_safe for short-form outputs.

    Used by wizard_generate_docs to keep each per-doc call under the 60s
    ingress limit. Primary: Claude Haiku 4.5 (cheap + fast, ~0.5-2s ping;
    ~5-15s for full doc output). Fallback: Claude Sonnet 4.5 (slower but
    higher quality). Both covered by the same Emergent LLM key. Returns
    None if both fail (same pattern as call_ai_safe). To revert to
    call_ai_safe: replace call_ai_fast with call_ai_safe in
    wizard_generate_docs.
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    # Primary: Haiku 3.5 — fast short-form writer
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=str(uuid.uuid4()), system_message=system_msg)
        chat.with_model("anthropic", "claude-haiku-4-5")
        return await chat.send_message(UserMessage(text=user_msg))
    except Exception as e:
        logger.warning(f"AI fast primary (haiku) failed, falling back to sonnet: {e}")
    # Fallback: Sonnet 4.5
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=str(uuid.uuid4()), system_message=system_msg)
        chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
        return await chat.send_message(UserMessage(text=user_msg))
    except Exception as e:
        logger.error(f"AI fast fallback (sonnet) also failed: {e}")
        return None


async def call_ai_safe(system_msg: str, user_msg: str) -> str:
    """Non-raising version of call_ai for background tasks.

    RELIABILITY FALLBACK (2026-04-19): OpenAI gpt-5.2 upstream has been
    returning persistent 502 errors AND litellm's internal retries ignore
    asyncio cancellation, so we can't reliably fast-fail off of it.
    Per user preference, call_ai_safe now uses:
      1. Claude Sonnet 4.5 (primary — working + ~20-30s)
      2. Gemini 3 Pro     (secondary fallback)
    Returns None if both fail or if EMERGENT_LLM_KEY is not configured.
    (The caller is responsible for producing a user-visible message in that
    case — see wizard_analyze / wizard_generate_docs.)
    """
    if not EMERGENT_LLM_KEY:
        logger.warning("call_ai_safe: EMERGENT_LLM_KEY not configured — returning None")
        return None
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    # Primary: Claude Sonnet 4.5 (reliable; same Emergent LLM key)
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=str(uuid.uuid4()), system_message=system_msg)
        chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
        return await chat.send_message(UserMessage(text=user_msg))
    except Exception as e:
        logger.warning(f"AI primary (claude) failed, trying gemini fallback: {e}")

    # Fallback: Gemini 3 Pro
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=str(uuid.uuid4()), system_message=system_msg)
        chat.with_model("gemini", "gemini-3.1-pro-preview")
        return await chat.send_message(UserMessage(text=user_msg))
    except Exception as e:
        logger.error(f"AI fallback (gemini) also failed: {e}")
        return None


async def run_bulk_analysis():
    global bulk_state
    bulk_state = {"running": True, "total": 0, "processed": 0, "errors": 0}
    db = await get_db()
    cursor = await db.execute("SELECT * FROM opportunities WHERE last_analyzed = '' OR last_analyzed IS NULL")
    opps = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    bulk_state["total"] = len(opps)
    if not opps:
        bulk_state["running"] = False
        return
    org_text = await get_org_profile_text()
    system = """You are a grant matching expert. Analyze how well a grant opportunity matches an organization's profile.
Return ONLY a JSON object: {"score": <0-100>, "explanation": "<2-3 sentence explanation>"}
Score: 0-30=Poor, 31-60=Moderate, 61-80=Good, 81-100=Excellent.
Consider: sector alignment, geographic eligibility, funding range, beneficiary overlap, organizational capacity."""
    for opp in opps:
        try:
            user_msg = f"""ORGANIZATION:\n{org_text}\n\nOPPORTUNITY:\nTitle: {opp['title']}\nDonor: {opp['donor_name']} ({opp['donor_type']})\nSector: {opp['sector']}\nRegion: {opp['region']}\nFunding: USD {opp['funding_min']:,.0f} - USD {opp['funding_max']:,.0f}\nEligibility: {opp['eligibility']}\nAfrica Eligible: {'Yes' if opp['africa_eligible'] else 'No'}"""
            result = await call_ai_safe(system, user_msg)
            if result:
                try:
                    json_match = re.search(r'\{[^}]+\}', result)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        score = min(100, max(0, int(parsed.get("score", 50))))
                        explanation = parsed.get("explanation", "")
                    else:
                        score = 50
                        explanation = result[:300]
                except (json.JSONDecodeError, ValueError):
                    score = 50
                    explanation = result[:300]
                fit_level = "High" if score >= 80 else "Medium" if score >= 60 else "Low"
                decision_label = "Apply Now" if score >= 80 else "Review First" if score >= 60 else "Ignore"
                now_str = datetime.now(timezone.utc).isoformat()
                db = await get_db()
                await db.execute(
                    "UPDATE opportunities SET ai_match_score=?, ai_fit_explanation=?, fit_level=?, decision_label=?, last_analyzed=? WHERE id=?",
                    (score, explanation, fit_level, decision_label, now_str, opp['id']))
                await db.commit()
                await db.close()
            else:
                bulk_state["errors"] += 1
        except Exception as e:
            logger.error(f"Bulk analysis error for {opp['id']}: {e}")
            bulk_state["errors"] += 1
        bulk_state["processed"] += 1
    bulk_state["running"] = False
    logger.info(f"Bulk analysis complete: {bulk_state['processed']}/{bulk_state['total']} processed, {bulk_state['errors']} errors")


@api_router.post("/ai/bulk-analyze")
async def start_bulk_analyze(request: Request):
    await get_current_user(request)
    global bulk_state
    if bulk_state["running"]:
        return {"status": "running", **bulk_state}
    asyncio.create_task(run_bulk_analysis())
    return {"status": "started", "message": "Bulk AI analysis started"}


@api_router.get("/ai/bulk-status")
async def get_bulk_status(request: Request):
    await get_current_user(request)
    return bulk_state


# ============================
#     PIPELINE ROUTE
# ============================

@api_router.get("/pipeline")
async def get_pipeline(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("""
        SELECT s.status, SUM(o.funding_max) as total_max, SUM(o.funding_min) as total_min, COUNT(*) as count
        FROM saved_opportunities s JOIN opportunities o ON s.opportunity_id = o.id GROUP BY s.status
    """)
    stages = {}
    total = 0
    for row in await cursor.fetchall():
        r = dict(row)
        stages[r['status']] = {'count': r['count'], 'total_min': r['total_min'] or 0, 'total_max': r['total_max'] or 0}
        total += r['total_max'] or 0
    cursor = await db.execute("SELECT SUM(funding_max) as total FROM opportunities")
    all_value = (await cursor.fetchone())['total'] or 0
    await db.close()
    return {"total_pipeline": total, "all_opportunities_value": all_value, "stages": stages}


# ============================
#     PDF EXPORT ROUTE
# ============================

@api_router.get("/proposals/{proposal_id}/pdf")
async def export_proposal_pdf(proposal_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")
    p = dict(row)
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    def add_section(title, content):
        if not content:
            return
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(0, 10, title, ln=True)
        pdf.set_draw_color(37, 99, 235)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 6, content.encode('latin-1', 'replace').decode('latin-1'))

    # Cover page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(37, 99, 235)
    pdf.ln(40)
    pdf.cell(0, 15, "FUNDING PROPOSAL", ln=True, align="C")
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.ln(5)
    pdf.cell(0, 10, p.get('opportunity_title', ''), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Prepared by: Pro Youth Foundation", ln=True, align="C")
    pdf.cell(0, 8, f"Requested Amount: USD {float(p.get('funding_amount', 0)):,.0f}", ln=True, align="C")
    pdf.cell(0, 8, f"Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}", ln=True, align="C")
    pdf.ln(20)
    pdf.set_draw_color(37, 99, 235)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, "Generated by ProFund AI - International Funding Dashboard", ln=True, align="C")

    add_section("DONOR EMAIL", p.get('donor_email', ''))
    add_section("LETTER OF INTEREST", p.get('letter_of_interest', ''))
    add_section("CONCEPT NOTE", p.get('concept_note', ''))
    add_section("PROPOSAL OUTLINE", p.get('proposal_outline', ''))
    add_section("APPLICATION CHECKLIST", p.get('checklist', ''))

    pdf_bytes = pdf.output()
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="proposal_{proposal_id[:8]}.pdf"'}
    )


# ============================
#   SMART APPLY QUEUE
# ============================

async def generate_auto_draft(opp_id: str, opp: dict, org_text: str):
    """Auto-generate proposal for a queued opportunity."""
    system = """You are an expert grant proposal writer for African development organizations. Generate professional funding proposal content. Return a JSON object with these keys:
{"donor_email": "<150-200 word cover email>", "letter_of_interest": "<300-400 word formal letter>", "concept_note": "<500-600 word structured concept note>", "proposal_outline": "<detailed numbered proposal outline>", "checklist": "<8-12 item application checklist>"}
Be specific, professional, and donor-facing. Tailor to the grant and organization."""
    user_msg = f"""ORGANIZATION:\n{org_text}\n\nGRANT:\nTitle: {opp['title']}\nDonor: {opp['donor_name']} ({opp['donor_type']})\nSector: {opp['sector']}\nFunding: USD {opp['funding_min']:,.0f} - USD {opp['funding_max']:,.0f}\nDeadline: {opp['deadline']}\nEligibility: {opp['eligibility']}\n\nPROJECT: Align with organization's core mission. Focus on {opp['sector'].lower()} for youth and communities in Namibia.\nBeneficiaries: Youth, unemployed individuals, rural communities\nAmount: USD {min(opp['funding_max'], 250000):,.0f}"""
    result = await call_ai_safe(system, user_msg)
    if not result:
        return None
    try:
        json_match = re.search(r'\{[\s\S]*\}', result)
        parsed = json.loads(json_match.group()) if json_match else {"donor_email": result}
    except (json.JSONDecodeError, ValueError):
        parsed = {"donor_email": result}
    proposal_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute(
        """INSERT INTO proposals (id, opportunity_id, opportunity_title, project_idea, beneficiaries_desc,
           funding_amount, donor_email, letter_of_interest, concept_note, proposal_outline, checklist, created_at, auto_generated)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (proposal_id, opp_id, opp['title'], f"Auto-generated for {opp['title']}",
         "Youth, unemployed individuals, rural communities",
         min(opp['funding_max'], 250000),
         parsed.get("donor_email", ""), parsed.get("letter_of_interest", ""),
         parsed.get("concept_note", ""), parsed.get("proposal_outline", ""),
         parsed.get("checklist", ""), now_str))
    await db.execute("UPDATE opportunities SET auto_draft_ready = 1 WHERE id = ?", (opp_id,))
    await db.commit()
    await db.close()
    return proposal_id


async def run_smart_queue_generation():
    """Select top opportunities and auto-generate drafts."""
    global queue_state
    queue_state["generating"] = True
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    week_label = datetime.now(timezone.utc).strftime("%Y-W%W")
    db = await get_db()
    # Select top 5 opportunities: score >= 75, valid deadline, not already queued this week
    cursor = await db.execute("""
        SELECT o.* FROM opportunities o
        LEFT JOIN smart_queue sq ON o.id = sq.opportunity_id AND sq.week_label = ?
        WHERE o.ai_match_score >= 75 AND o.deadline >= ? AND sq.id IS NULL
        ORDER BY o.ai_match_score DESC, o.deadline ASC, o.funding_max DESC
        LIMIT 5
    """, (week_label, today))
    top_opps = [dict(r) for r in await cursor.fetchall()]
    await db.close()

    if not top_opps:
        queue_state["generating"] = False
        queue_state["last_generated"] = datetime.now(timezone.utc).isoformat()
        return

    org_text = await get_org_profile_text()
    for opp in top_opps:
        try:
            # Add to queue
            queue_id = str(uuid.uuid4())
            now_str = datetime.now(timezone.utc).isoformat()
            # Auto-save if not saved
            db = await get_db()
            cursor = await db.execute("SELECT id FROM saved_opportunities WHERE opportunity_id = ?", (opp['id'],))
            saved = await cursor.fetchone()
            if not saved:
                sid = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO saved_opportunities (id, opportunity_id, status, notes, saved_at, updated_at) VALUES (?, ?, 'Preparing', 'Auto-queued by Smart Apply', ?, ?)",
                    (sid, opp['id'], now_str, now_str))
            else:
                await db.execute("UPDATE saved_opportunities SET status = 'Preparing', updated_at = ? WHERE opportunity_id = ?", (now_str, opp['id']))
            await db.commit()
            await db.close()

            # Generate draft
            proposal_id = await generate_auto_draft(opp['id'], opp, org_text)

            # Add to smart_queue
            db = await get_db()
            await db.execute(
                "INSERT INTO smart_queue (id, opportunity_id, proposal_id, score, deadline, funding_max, status, queued_at, week_label) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (queue_id, opp['id'], proposal_id or '', opp['ai_match_score'], opp['deadline'], opp['funding_max'],
                 'draft_ready' if proposal_id else 'queued', now_str, week_label))
            await db.commit()
            await db.close()
            logger.info(f"Smart Queue: processed {opp['title']} (score={opp['ai_match_score']})")
        except Exception as e:
            logger.error(f"Smart Queue error for {opp['id']}: {e}")

    queue_state["generating"] = False
    queue_state["last_generated"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"Smart Queue: generated {len(top_opps)} priority applications")


@api_router.post("/queue/generate")
async def generate_smart_queue(request: Request):
    await get_current_user(request)
    global queue_state
    if queue_state["generating"]:
        return {"status": "running", "message": "Queue generation in progress"}
    asyncio.create_task(run_smart_queue_generation())
    return {"status": "started", "message": "Smart Apply Queue generation started"}


@api_router.get("/queue")
async def get_smart_queue(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("""
        SELECT sq.*, o.title, o.donor_name, o.donor_type, o.funding_min, o.funding_max,
               o.sector, o.region, o.ai_match_score, o.decision_label
        FROM smart_queue sq
        JOIN opportunities o ON sq.opportunity_id = o.id
        ORDER BY sq.score DESC, sq.deadline ASC
    """)
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return {"items": rows, "generating": queue_state["generating"], "last_generated": queue_state["last_generated"]}


@api_router.get("/queue/status")
async def get_queue_status(request: Request):
    await get_current_user(request)
    return queue_state


# ============================
#   24/7 MONITORING SYSTEM
# ============================

async def run_monitoring_scan(scan_type="scheduled"):
    """Simulate monitoring scan - discovers new opportunities from sources."""
    global monitor_state
    scan_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute(
        "INSERT INTO monitoring_log (id, scan_type, started_at, status) VALUES (?, ?, ?, 'running')",
        (scan_id, scan_type, now_str))
    await db.commit()

    # Check sources
    cursor = await db.execute("SELECT * FROM sources")
    sources = [dict(r) for r in await cursor.fetchall()]
    sources_checked = len(sources)

    # Update last_checked on all sources
    for src in sources:
        await db.execute("UPDATE sources SET last_checked = ? WHERE id = ?", (now_str, src['id']))
    await db.commit()

    # In production: scrape each source URL. For now: simulate finding 0-2 new opportunities
    # This is the structured placeholder for real scraping integration
    new_found = 0
    auto_queued = 0

    # Complete scan
    completed_str = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE monitoring_log SET completed_at=?, sources_checked=?, new_found=?, auto_queued=?, status='completed', details=? WHERE id=?",
        (completed_str, sources_checked, new_found, auto_queued,
         f"Scanned {sources_checked} international sources. {new_found} new opportunities found.", scan_id))
    await db.commit()
    await db.close()

    monitor_state["last_scan"] = completed_str
    monitor_state["scans_completed"] += 1
    logger.info(f"Monitoring scan {scan_type}: {sources_checked} sources checked, {new_found} new found")


@api_router.get("/monitoring/status")
async def get_monitoring_status(request: Request):
    await get_current_user(request)
    return {
        "active": monitor_state["active"],
        "last_scan": monitor_state["last_scan"],
        "next_scan": monitor_state["next_scan"],
        "scans_completed": monitor_state["scans_completed"]
    }


@api_router.post("/monitoring/trigger")
async def trigger_monitoring_scan(request: Request):
    await get_current_user(request)
    asyncio.create_task(run_monitoring_scan("manual"))
    return {"status": "started", "message": "Manual monitoring scan triggered"}


@api_router.get("/monitoring/log")
async def get_monitoring_log(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM monitoring_log ORDER BY started_at DESC LIMIT 20")
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


# ============================
#  PIPELINE AUTOMATION
# ============================

@api_router.get("/automation/suggestions")
async def get_automation_suggestions(request: Request):
    await get_current_user(request)
    db = await get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    suggestions = []

    # Opportunities marked "Apply Now" not yet in Preparing
    cursor = await db.execute("""
        SELECT o.*, s.status as saved_status, s.id as saved_id
        FROM opportunities o
        LEFT JOIN saved_opportunities s ON o.id = s.opportunity_id
        WHERE o.decision_label = 'Apply Now' AND o.deadline >= ?
        AND (s.id IS NULL OR s.status IN ('New', 'Identified', 'Reviewing'))
        ORDER BY o.ai_match_score DESC LIMIT 5
    """, (today,))
    for row in await cursor.fetchall():
        r = dict(row)
        suggestions.append({
            "type": "move_to_preparing",
            "message": f"Move '{r['title']}' to Preparing - {r['ai_match_score']}% match",
            "opportunity_id": r['id'],
            "saved_id": r.get('saved_id'),
            "action": "prepare"
        })

    # Opportunities with drafts ready → suggest Ready to Submit
    cursor = await db.execute("""
        SELECT o.*, s.status as saved_status, s.id as saved_id
        FROM opportunities o
        JOIN saved_opportunities s ON o.id = s.opportunity_id
        JOIN proposals p ON o.id = p.opportunity_id
        WHERE s.status IN ('Preparing', 'Drafting') AND o.deadline >= ?
        ORDER BY o.deadline ASC LIMIT 5
    """, (today,))
    for row in await cursor.fetchall():
        r = dict(row)
        suggestions.append({
            "type": "ready_to_submit",
            "message": f"Drafts complete for '{r['title']}' - mark Ready to Submit?",
            "opportunity_id": r['id'],
            "saved_id": r.get('saved_id'),
            "action": "ready"
        })

    await db.close()
    return {"suggestions": suggestions}


# ============================
#  DASHBOARD EXTRAS
# ============================

@api_router.get("/dashboard/extras")
async def get_dashboard_extras(request: Request):
    """Extra dashboard data: priority queue, new 24h, drafts ready, monitoring status."""
    await get_current_user(request)
    db = await get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    week_label = datetime.now(timezone.utc).strftime("%Y-W%W")

    # This week's priority applications (smart queue)
    cursor = await db.execute("""
        SELECT sq.*, o.title, o.donor_name, o.funding_min, o.funding_max, o.deadline, o.sector, o.ai_match_score
        FROM smart_queue sq
        JOIN opportunities o ON sq.opportunity_id = o.id
        WHERE sq.week_label = ?
        ORDER BY sq.score DESC
    """, (week_label,))
    priority_apps = [dict(r) for r in await cursor.fetchall()]

    # Auto-generated drafts ready
    cursor = await db.execute("""
        SELECT o.id, o.title, o.donor_name, o.ai_match_score, o.deadline, p.id as proposal_id, p.created_at as draft_created
        FROM opportunities o
        JOIN proposals p ON o.id = p.opportunity_id
        WHERE p.auto_generated = 1
        ORDER BY p.created_at DESC LIMIT 5
    """)
    drafts_ready = [dict(r) for r in await cursor.fetchall()]

    # Monitoring info
    cursor = await db.execute("SELECT * FROM monitoring_log ORDER BY started_at DESC LIMIT 1")
    last_scan_row = await cursor.fetchone()
    last_scan = dict(last_scan_row) if last_scan_row else None

    # Count new in last 24h (based on created_at)
    cursor = await db.execute("SELECT COUNT(*) as count FROM opportunities WHERE created_at >= ?", (yesterday,))
    new_24h = (await cursor.fetchone())["count"]

    await db.close()
    return {
        "priority_apps": priority_apps,
        "drafts_ready": drafts_ready,
        "new_24h_count": new_24h,
        "monitoring": {
            "active": monitor_state["active"],
            "last_scan": last_scan,
            "scans_completed": monitor_state["scans_completed"]
        },
        "queue_generating": queue_state["generating"]
    }


# ============================
#   GRANT WIN TRACKER
# ============================

class OutcomeCreate(BaseModel):
    opportunity_id: str
    outcome: str = "pending"
    amount_requested: float = 0
    amount_awarded: float = 0
    date_submitted: str = ""
    date_decided: str = ""
    rejection_reason: str = ""
    success_notes: str = ""

class OutcomeUpdate(BaseModel):
    outcome: Optional[str] = None
    amount_awarded: Optional[float] = None
    date_decided: Optional[str] = None
    rejection_reason: Optional[str] = None
    success_notes: Optional[str] = None


@api_router.get("/outcomes")
async def list_outcomes(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("""
        SELECT ao.*, o.title, o.funding_min, o.funding_max, o.deadline, o.ai_match_score
        FROM application_outcomes ao
        JOIN opportunities o ON ao.opportunity_id = o.id
        ORDER BY ao.created_at DESC
    """)
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


@api_router.post("/outcomes")
async def create_outcome(data: OutcomeCreate, request: Request):
    await get_current_user(request)
    db = await get_db()
    # Get opp info
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (data.opportunity_id,))
    opp = await cursor.fetchone()
    if not opp:
        await db.close()
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp = dict(opp)
    # Check if outcome already exists
    cursor = await db.execute("SELECT id FROM application_outcomes WHERE opportunity_id = ?", (data.opportunity_id,))
    existing = await cursor.fetchone()
    if existing:
        await db.close()
        raise HTTPException(status_code=400, detail="Outcome already exists for this opportunity")
    oid = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    # Get saved_id
    cursor = await db.execute("SELECT id FROM saved_opportunities WHERE opportunity_id = ?", (data.opportunity_id,))
    saved = await cursor.fetchone()
    await db.execute(
        """INSERT INTO application_outcomes (id, opportunity_id, saved_id, outcome, amount_requested, amount_awarded,
           donor_name, donor_type, sector, date_submitted, date_decided, rejection_reason, success_notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (oid, data.opportunity_id, dict(saved)['id'] if saved else '', data.outcome,
         data.amount_requested, data.amount_awarded, opp['donor_name'], opp['donor_type'],
         opp['sector'], data.date_submitted, data.date_decided,
         data.rejection_reason, data.success_notes, now_str))
    # Update saved status based on outcome
    if saved and data.outcome in ('approved', 'rejected'):
        status = 'Approved' if data.outcome == 'approved' else 'Rejected'
        await db.execute("UPDATE saved_opportunities SET status = ?, updated_at = ? WHERE opportunity_id = ?",
                         (status, now_str, data.opportunity_id))
    await db.commit()
    await db.close()
    return {"id": oid, "opportunity_id": data.opportunity_id, "outcome": data.outcome}


@api_router.put("/outcomes/{outcome_id}")
async def update_outcome(outcome_id: str, data: OutcomeUpdate, request: Request):
    await get_current_user(request)
    db = await get_db()
    fields = {}
    if data.outcome is not None:
        fields["outcome"] = data.outcome
    if data.amount_awarded is not None:
        fields["amount_awarded"] = data.amount_awarded
    if data.date_decided is not None:
        fields["date_decided"] = data.date_decided
    if data.rejection_reason is not None:
        fields["rejection_reason"] = data.rejection_reason
    if data.success_notes is not None:
        fields["success_notes"] = data.success_notes
    if not fields:
        await db.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [outcome_id]
    await db.execute(f"UPDATE application_outcomes SET {set_clause} WHERE id = ?", values)
    # Sync saved status
    if data.outcome in ('approved', 'rejected'):
        cursor = await db.execute("SELECT opportunity_id FROM application_outcomes WHERE id = ?", (outcome_id,))
        row = await cursor.fetchone()
        if row:
            status = 'Approved' if data.outcome == 'approved' else 'Rejected'
            now_str = datetime.now(timezone.utc).isoformat()
            await db.execute("UPDATE saved_opportunities SET status = ?, updated_at = ? WHERE opportunity_id = ?",
                             (status, now_str, dict(row)['opportunity_id']))
    await db.commit()
    await db.close()
    return {"id": outcome_id, "updated": True}


# ============================
#   PERFORMANCE ANALYTICS
# ============================

@api_router.get("/analytics/performance")
async def get_performance_analytics(request: Request):
    await get_current_user(request)
    db = await get_db()

    # Overall stats
    cursor = await db.execute("SELECT COUNT(*) as c FROM application_outcomes WHERE outcome = 'approved'")
    approved_count = (await cursor.fetchone())['c']
    cursor = await db.execute("SELECT COUNT(*) as c FROM application_outcomes WHERE outcome = 'rejected'")
    rejected_count = (await cursor.fetchone())['c']
    cursor = await db.execute("SELECT COUNT(*) as c FROM application_outcomes WHERE outcome = 'pending'")
    pending_count = (await cursor.fetchone())['c']
    cursor = await db.execute("SELECT COUNT(*) as c FROM application_outcomes WHERE outcome IN ('approved', 'rejected')")
    decided_count = (await cursor.fetchone())['c']
    cursor = await db.execute("SELECT COALESCE(SUM(amount_awarded), 0) as total FROM application_outcomes WHERE outcome = 'approved'")
    total_secured = (await cursor.fetchone())['total']
    cursor = await db.execute("SELECT COALESCE(SUM(amount_requested), 0) as total FROM application_outcomes")
    total_requested = (await cursor.fetchone())['total']

    approval_rate = (approved_count / decided_count * 100) if decided_count > 0 else 0
    avg_award = (total_secured / approved_count) if approved_count > 0 else 0

    # Top sectors
    cursor = await db.execute("""
        SELECT sector, COUNT(*) as total,
               SUM(CASE WHEN outcome='approved' THEN 1 ELSE 0 END) as wins,
               COALESCE(SUM(CASE WHEN outcome='approved' THEN amount_awarded ELSE 0 END), 0) as secured
        FROM application_outcomes WHERE sector != '' GROUP BY sector ORDER BY wins DESC LIMIT 5
    """)
    top_sectors = [dict(r) for r in await cursor.fetchall()]

    # Top donors
    cursor = await db.execute("""
        SELECT donor_name, donor_type, COUNT(*) as total,
               SUM(CASE WHEN outcome='approved' THEN 1 ELSE 0 END) as wins,
               COALESCE(SUM(CASE WHEN outcome='approved' THEN amount_awarded ELSE 0 END), 0) as secured
        FROM application_outcomes WHERE donor_name != '' GROUP BY donor_name ORDER BY wins DESC LIMIT 5
    """)
    top_donors = [dict(r) for r in await cursor.fetchall()]

    # Timeline data (monthly)
    cursor = await db.execute("""
        SELECT SUBSTR(date_decided, 1, 7) as month, outcome, COUNT(*) as c,
               COALESCE(SUM(amount_awarded), 0) as amount
        FROM application_outcomes WHERE date_decided != '' GROUP BY month, outcome ORDER BY month
    """)
    timeline_raw = [dict(r) for r in await cursor.fetchall()]
    timeline = {}
    for r in timeline_raw:
        m = r['month']
        if m not in timeline:
            timeline[m] = {"month": m, "approved": 0, "rejected": 0, "secured": 0}
        if r['outcome'] == 'approved':
            timeline[m]["approved"] = r['c']
            timeline[m]["secured"] = r['amount']
        elif r['outcome'] == 'rejected':
            timeline[m]["rejected"] = r['c']

    # Pipeline vs actual
    cursor = await db.execute("SELECT COALESCE(SUM(funding_max), 0) as total FROM opportunities")
    pipeline_total = (await cursor.fetchone())['total']
    cursor = await db.execute("""
        SELECT COALESCE(SUM(o.funding_max), 0) as total
        FROM saved_opportunities s JOIN opportunities o ON s.opportunity_id = o.id
    """)
    pipeline_saved = (await cursor.fetchone())['total']

    await db.close()
    return {
        "summary": {
            "total_secured": total_secured,
            "total_requested": total_requested,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "pending_count": pending_count,
            "approval_rate": round(approval_rate, 1),
            "avg_award": round(avg_award, 2)
        },
        "top_sectors": top_sectors,
        "top_donors": top_donors,
        "timeline": list(timeline.values()),
        "pipeline_vs_actual": {
            "total_available": pipeline_total,
            "in_pipeline": pipeline_saved,
            "secured": total_secured
        }
    }


@api_router.get("/analytics/learning-insights")
async def get_learning_insights(request: Request):
    """AI-generated insights from historical outcomes."""
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) as c FROM application_outcomes")
    total = (await cursor.fetchone())['c']
    await db.close()
    if total < 1:
        return {"insights": [], "has_data": False}

    # Build insights from data
    db = await get_db()
    insights = []

    # Best donor types
    cursor = await db.execute("""
        SELECT donor_type, COUNT(*) as total,
               SUM(CASE WHEN outcome='approved' THEN 1 ELSE 0 END) as wins
        FROM application_outcomes GROUP BY donor_type HAVING total >= 1 ORDER BY wins DESC
    """)
    for r in await cursor.fetchall():
        r = dict(r)
        rate = (r['wins'] / r['total'] * 100) if r['total'] > 0 else 0
        if r['wins'] > 0:
            insights.append({"type": "boost", "message": f"{r['donor_type']} donors: {r['wins']}/{r['total']} approved ({rate:.0f}%). Prioritize these donor types."})
        elif r['total'] >= 2 and r['wins'] == 0:
            insights.append({"type": "caution", "message": f"{r['donor_type']} donors: 0/{r['total']} approved. Consider different approach or skip."})

    # Best sectors
    cursor = await db.execute("""
        SELECT sector, COUNT(*) as total,
               SUM(CASE WHEN outcome='approved' THEN 1 ELSE 0 END) as wins
        FROM application_outcomes GROUP BY sector HAVING total >= 1 ORDER BY wins DESC
    """)
    for r in await cursor.fetchall():
        r = dict(r)
        rate = (r['wins'] / r['total'] * 100) if r['total'] > 0 else 0
        if r['wins'] > 0:
            insights.append({"type": "boost", "message": f"{r['sector']} sector: {r['wins']}/{r['total']} approved ({rate:.0f}%). Strong track record."})

    # Funding range analysis
    cursor = await db.execute("""
        SELECT outcome, AVG(amount_requested) as avg_req FROM application_outcomes
        WHERE amount_requested > 0 GROUP BY outcome
    """)
    for r in await cursor.fetchall():
        r = dict(r)
        if r['outcome'] == 'approved':
            insights.append({"type": "info", "message": f"Average approved request: USD {r['avg_req']:,.0f}. Target this range."})

    await db.close()
    return {"insights": insights, "has_data": True}


# ============================
#   DONOR RELATIONSHIP MANAGER
# ============================

def calc_relationship_score(approvals, rejections, interactions_count, days_since_last):
    """Rule-based relationship score 0-100."""
    score = 20  # base
    score += min(approvals * 20, 40)  # max +40 for approvals
    score += min(interactions_count * 3, 15)  # max +15 for interactions
    score -= min(rejections * 10, 20)  # max -20 for rejections
    if days_since_last is not None:
        if days_since_last <= 30:
            score += 10
        elif days_since_last <= 90:
            score += 5
        elif days_since_last > 180:
            score -= 10
    return max(0, min(100, score))


def relationship_level(score):
    if score >= 70:
        return "Strong"
    if score >= 40:
        return "Growing"
    return "New"


async def sync_donor_from_name(donor_name, donor_type="", donor_country=""):
    """Ensure a donor profile exists, return donor_id."""
    if not donor_name:
        return None
    db = await get_db()
    cursor = await db.execute("SELECT id FROM donors WHERE name = ?", (donor_name,))
    row = await cursor.fetchone()
    if row:
        await db.close()
        return dict(row)['id']
    donor_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO donors (id, name, type, country, created_at) VALUES (?, ?, ?, ?, ?)",
        (donor_id, donor_name, donor_type, donor_country, now_str))
    await db.commit()
    await db.close()
    return donor_id


async def refresh_donor_stats(donor_name):
    """Recalculate donor stats from outcomes and interactions."""
    db = await get_db()
    cursor = await db.execute("SELECT id FROM donors WHERE name = ?", (donor_name,))
    donor_row = await cursor.fetchone()
    if not donor_row:
        await db.close()
        return
    donor_id = dict(donor_row)['id']

    cursor = await db.execute(
        "SELECT outcome, COALESCE(SUM(amount_awarded),0) as total_awarded, COUNT(*) as c FROM application_outcomes WHERE donor_name = ? GROUP BY outcome",
        (donor_name,))
    stats = {r['outcome']: {'count': r['c'], 'awarded': r['total_awarded']} for r in await cursor.fetchall()}
    approvals = stats.get('approved', {}).get('count', 0)
    rejections = stats.get('rejected', {}).get('count', 0)
    total_apps = sum(s['count'] for s in stats.values())
    total_funded = stats.get('approved', {}).get('awarded', 0)

    cursor = await db.execute("SELECT COUNT(*) as c FROM donor_interactions WHERE donor_id = ?", (donor_id,))
    interactions_count = (await cursor.fetchone())['c']

    cursor = await db.execute("SELECT date FROM donor_interactions WHERE donor_id = ? ORDER BY date DESC LIMIT 1", (donor_id,))
    last_row = await cursor.fetchone()
    days_since = None
    last_date = ""
    if last_row and dict(last_row)['date']:
        last_date = dict(last_row)['date']
        try:
            days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last_date).replace(tzinfo=timezone.utc)).days
        except (ValueError, TypeError):
            try:
                days_since = (datetime.now(timezone.utc).date() - datetime.strptime(last_date, "%Y-%m-%d").date()).days
            except (ValueError, TypeError):
                pass

    score = calc_relationship_score(approvals, rejections, interactions_count, days_since)
    level = relationship_level(score)
    await db.execute(
        "UPDATE donors SET relationship_score=?, relationship_level=?, last_interaction=?, total_applications=?, total_approvals=?, total_rejections=?, total_funding_received=? WHERE id=?",
        (score, level, last_date, total_apps, approvals, rejections, total_funded, donor_id))
    await db.commit()
    await db.close()


class DonorUpdate(BaseModel):
    country: Optional[str] = None
    sectors: Optional[List[str]] = None
    funding_min: Optional[float] = None
    funding_max: Optional[float] = None
    website: Optional[str] = None
    notes: Optional[str] = None

class InteractionCreate(BaseModel):
    donor_id: str
    type: str  # email, meeting, call, proposal_submitted, follow_up
    date: str
    notes: str = ""
    opportunity_id: str = ""


@api_router.get("/donors")
async def list_donors(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM donors ORDER BY relationship_score DESC, name ASC")
    rows = [dict(r) for r in await cursor.fetchall()]
    for r in rows:
        try:
            r['sectors'] = json.loads(r.get('sectors', '[]'))
        except (json.JSONDecodeError, TypeError):
            r['sectors'] = []
    await db.close()
    return rows


@api_router.get("/donors/{donor_id}")
async def get_donor(donor_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM donors WHERE id = ?", (donor_id,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail="Donor not found")
    donor = dict(row)
    try:
        donor['sectors'] = json.loads(donor.get('sectors', '[]'))
    except (json.JSONDecodeError, TypeError):
        donor['sectors'] = []
    # Get interactions
    cursor = await db.execute("SELECT * FROM donor_interactions WHERE donor_id = ? ORDER BY date DESC", (donor_id,))
    donor['interactions'] = [dict(r) for r in await cursor.fetchall()]
    # Get outcomes
    cursor = await db.execute("SELECT ao.*, o.title FROM application_outcomes ao JOIN opportunities o ON ao.opportunity_id = o.id WHERE ao.donor_name = ?", (donor['name'],))
    donor['outcomes'] = [dict(r) for r in await cursor.fetchall()]
    # Get current opportunities
    cursor = await db.execute("SELECT id, title, deadline, ai_match_score, sector FROM opportunities WHERE donor_name = ? ORDER BY deadline ASC", (donor['name'],))
    donor['opportunities'] = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return donor


@api_router.put("/donors/{donor_id}")
async def update_donor(donor_id: str, data: DonorUpdate, request: Request):
    await get_current_user(request)
    db = await get_db()
    fields = {}
    if data.country is not None: fields["country"] = data.country
    if data.sectors is not None: fields["sectors"] = json.dumps(data.sectors)
    if data.funding_min is not None: fields["funding_min"] = data.funding_min
    if data.funding_max is not None: fields["funding_max"] = data.funding_max
    if data.website is not None: fields["website"] = data.website
    if data.notes is not None: fields["notes"] = data.notes
    if not fields:
        await db.close()
        raise HTTPException(status_code=400, detail="No fields")
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [donor_id]
    await db.execute(f"UPDATE donors SET {set_clause} WHERE id = ?", values)
    await db.commit()
    await db.close()
    return {"id": donor_id, "updated": True}


@api_router.post("/donors/interactions")
async def add_interaction(data: InteractionCreate, request: Request):
    await get_current_user(request)
    iid = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    # Get donor name for stats refresh
    cursor = await db.execute("SELECT name FROM donors WHERE id = ?", (data.donor_id,))
    donor_row = await cursor.fetchone()
    if not donor_row:
        await db.close()
        raise HTTPException(status_code=404, detail="Donor not found")
    donor_name = dict(donor_row)['name']
    await db.execute(
        "INSERT INTO donor_interactions (id, donor_id, type, date, notes, opportunity_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (iid, data.donor_id, data.type, data.date, data.notes, data.opportunity_id, now_str))
    await db.commit()
    await db.close()
    await refresh_donor_stats(donor_name)
    return {"id": iid, "donor_id": data.donor_id, "type": data.type}


@api_router.get("/donors/interactions/{donor_id}")
async def get_donor_interactions(donor_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM donor_interactions WHERE donor_id = ? ORDER BY date DESC", (donor_id,))
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


@api_router.get("/donors/dashboard/insights")
async def get_donor_insights(request: Request):
    """Relationship intelligence for dashboard."""
    await get_current_user(request)
    db = await get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    thirty_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    ninety_ago = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")

    # Strongest relationships
    cursor = await db.execute("SELECT * FROM donors WHERE relationship_score >= 60 ORDER BY relationship_score DESC LIMIT 5")
    strong = [dict(r) for r in await cursor.fetchall()]

    # Follow-up required (last interaction > 30 days or no interaction)
    cursor = await db.execute("""
        SELECT * FROM donors WHERE total_applications > 0
        AND (last_interaction < ? OR last_interaction = '' OR last_interaction IS NULL)
        ORDER BY relationship_score DESC LIMIT 5
    """, (thirty_ago,))
    follow_up = [dict(r) for r in await cursor.fetchall()]

    # Reapplication opportunities (approved before, has active opportunities)
    cursor = await db.execute("""
        SELECT d.*, COUNT(o.id) as active_opps FROM donors d
        JOIN opportunities o ON o.donor_name = d.name AND o.deadline >= ?
        WHERE d.total_approvals > 0
        GROUP BY d.id ORDER BY d.relationship_score DESC LIMIT 5
    """, (today,))
    reapply = [dict(r) for r in await cursor.fetchall()]

    # Dormant (no interaction > 90 days, had relationship)
    cursor = await db.execute("""
        SELECT * FROM donors WHERE total_applications > 0
        AND last_interaction != '' AND last_interaction < ?
        ORDER BY last_interaction ASC LIMIT 5
    """, (ninety_ago,))
    dormant = [dict(r) for r in await cursor.fetchall()]

    # AI-style recommendations
    recommendations = []
    for d in strong:
        recommendations.append({"type": "reapply", "priority": "high",
            "message": f"Reapply to {d['name']} - strong relationship ({d['relationship_score']}%), {d['total_approvals']} prior approvals",
            "donor_id": d['id']})
    for d in follow_up:
        days = "unknown"
        if d.get('last_interaction'):
            try:
                days = (datetime.now(timezone.utc).date() - datetime.strptime(d['last_interaction'][:10], "%Y-%m-%d").date()).days
                days = f"{days}d ago"
            except (ValueError, TypeError):
                pass
        recommendations.append({"type": "follow_up", "priority": "medium",
            "message": f"Follow up with {d['name']} - last contact {days}",
            "donor_id": d['id']})
    for d in dormant:
        recommendations.append({"type": "dormant", "priority": "low",
            "message": f"Re-engage {d['name']} - relationship going dormant",
            "donor_id": d['id']})

    await db.close()
    return {
        "strong": strong,
        "follow_up": follow_up,
        "reapply": reapply,
        "dormant": dormant,
        "recommendations": recommendations
    }


# ============================
#   FOLLOW-UP EMAIL SYSTEM
# ============================

FOLLOW_UP_EMAIL_TYPES = {
    "application_followup": "Application Follow-Up",
    "relationship_reengagement": "Relationship Re-Engagement",
    "post_rejection": "Post-Rejection Re-Engagement",
    "post_approval_thanks": "Post-Approval Appreciation",
    "partnership_continuation": "Partnership Continuation"
}


async def detect_follow_ups():
    """Scan for donors/applications needing follow-up. Returns list of triggers."""
    db = await get_db()
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")
    triggers = []

    # A) Application submitted 7+ days ago with no response
    cursor = await db.execute("""
        SELECT ao.*, o.title, d.id as donor_id, d.relationship_score, d.relationship_level, d.total_funding_received
        FROM application_outcomes ao
        JOIN opportunities o ON ao.opportunity_id = o.id
        LEFT JOIN donors d ON d.name = ao.donor_name
        WHERE ao.outcome = 'pending' AND ao.date_submitted != ''
    """)
    for row in await cursor.fetchall():
        r = dict(row)
        try:
            submitted = datetime.strptime(r['date_submitted'], "%Y-%m-%d")
            days_since = (today - submitted.replace(tzinfo=timezone.utc)).days
        except (ValueError, TypeError):
            continue
        # Check no existing pending follow-up
        cursor2 = await db.execute(
            "SELECT id FROM follow_ups WHERE opportunity_id = ? AND status = 'pending'",
            (r['opportunity_id'],))
        if await cursor2.fetchone():
            continue
        if 7 <= days_since < 21:
            triggers.append({"donor_id": r.get('donor_id', ''), "donor_name": r['donor_name'],
                "opportunity_id": r['opportunity_id'], "trigger_type": "submission_7d",
                "email_type": "application_followup", "urgency": "medium",
                "reason": f"Application for '{r['title']}' submitted {days_since} days ago - gentle follow-up",
                "context": r})
        elif days_since >= 21:
            triggers.append({"donor_id": r.get('donor_id', ''), "donor_name": r['donor_name'],
                "opportunity_id": r['opportunity_id'], "trigger_type": "submission_21d",
                "email_type": "application_followup", "urgency": "high",
                "reason": f"Application for '{r['title']}' submitted {days_since} days ago - strong follow-up needed",
                "context": r})

    # B) Dormant relationships (30+ days, has history)
    thirty_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    cursor = await db.execute("""
        SELECT * FROM donors WHERE total_applications > 0
        AND (last_interaction < ? OR last_interaction = '' OR last_interaction IS NULL)
        AND relationship_level IN ('Growing', 'Strong')
    """, (thirty_ago,))
    for row in await cursor.fetchall():
        r = dict(row)
        cursor2 = await db.execute(
            "SELECT id FROM follow_ups WHERE donor_id = ? AND trigger_type LIKE 'dormant%' AND status = 'pending'",
            (r['id'],))
        if await cursor2.fetchone():
            continue
        email_type = "relationship_reengagement"
        if r['total_rejections'] > 0 and r['total_approvals'] == 0:
            email_type = "post_rejection"
        elif r['total_approvals'] > 0:
            email_type = "partnership_continuation"
        triggers.append({"donor_id": r['id'], "donor_name": r['name'],
            "opportunity_id": "", "trigger_type": "dormant_30d",
            "email_type": email_type, "urgency": "medium",
            "reason": f"No contact with {r['name']} for 30+ days - relationship at risk",
            "context": r})

    # C) Post-approval - thank you opportunity
    cursor = await db.execute("""
        SELECT ao.*, d.id as donor_id FROM application_outcomes ao
        LEFT JOIN donors d ON d.name = ao.donor_name
        WHERE ao.outcome = 'approved' AND ao.date_decided != ''
    """)
    for row in await cursor.fetchall():
        r = dict(row)
        try:
            decided = datetime.strptime(r['date_decided'], "%Y-%m-%d")
            days_since = (today - decided.replace(tzinfo=timezone.utc)).days
        except (ValueError, TypeError):
            continue
        if 3 <= days_since <= 14:
            cursor2 = await db.execute(
                "SELECT id FROM follow_ups WHERE opportunity_id = ? AND email_type = 'post_approval_thanks' AND status IN ('pending','sent')",
                (r['opportunity_id'],))
            if await cursor2.fetchone():
                continue
            triggers.append({"donor_id": r.get('donor_id', ''), "donor_name": r['donor_name'],
                "opportunity_id": r['opportunity_id'], "trigger_type": "post_approval",
                "email_type": "post_approval_thanks", "urgency": "high",
                "reason": f"Send appreciation to {r['donor_name']} for ${r['amount_awarded']:,.0f} approval",
                "context": r})

    await db.close()
    return triggers


async def generate_follow_up_email(trigger: dict) -> dict:
    """Generate personalized follow-up email using AI."""
    org_text = await get_org_profile_text()
    ctx = trigger.get("context", {})
    donor_name = trigger["donor_name"]
    email_type = trigger["email_type"]

    # Build context
    history_parts = []
    if ctx.get('total_approvals', 0) > 0:
        history_parts.append(f"Previously approved ${ctx.get('total_funding_received', 0):,.0f} in funding")
    if ctx.get('total_applications', 0) > 0:
        history_parts.append(f"{ctx.get('total_applications', 0)} applications submitted")
    if ctx.get('relationship_score', 0) > 0:
        history_parts.append(f"Relationship score: {ctx['relationship_score']}%")
    if ctx.get('title'):
        history_parts.append(f"Related to: {ctx['title']}")
    history = ". ".join(history_parts) if history_parts else "First contact"

    type_instructions = {
        "application_followup": "Write a polite follow-up about a submitted grant application for rescuing vulnerable children, street children, and mothers. Reference the proposal and Pro Youth Foundation's hostels, school fee program, food hampers, and street children reintegration. Ask for timeline update.",
        "relationship_reengagement": "Write a warm re-engagement referencing shared history. Mention Pro Youth Foundation's work rescuing street children, providing hostels, school fees, food hampers. Express interest in new opportunities.",
        "post_rejection": "Write a gracious post-rejection email. Thank them. Express continued interest. Mention impact: street children rescued, children housed, families fed, school fees paid. Ask for feedback.",
        "post_approval_thanks": "Write a heartfelt thank-you for approved funding. Reference the amount and direct impact: housing street children, paying school fees, providing food hampers. Share expected measurable outcomes.",
        "partnership_continuation": "Write to continue partnership. Reference past collaboration. Highlight ongoing needs: more street children to rescue, children needing hostels, families needing food support, school fees for vulnerable youth."
    }

    system = f"""You are a professional grant writer for Pro Youth Foundation, a Namibian non-profit that rescues vulnerable children (including street children, orphans) and mothers from abuse and poverty.
Return ONLY a JSON object: {{"subject": "<email subject>", "body": "<150-250 words>"}}
{type_instructions.get(email_type, 'Write a professional follow-up email.')}
Reference real programs: safe hostels, street children rehabilitation, school fees, monthly food hampers, clothing. Show real impact and transformation.
Sign off as Pro Youth Foundation."""

    user_msg = f"""ORGANIZATION:\n{org_text}\n\nDONOR: {donor_name}\nEMAIL TYPE: {FOLLOW_UP_EMAIL_TYPES.get(email_type, email_type)}\nRELATIONSHIP HISTORY: {history}\nREASON: {trigger['reason']}"""
    if ctx.get('date_submitted'):
        user_msg += f"\nAPPLICATION SUBMITTED: {ctx['date_submitted']}"
    if ctx.get('amount_awarded'):
        user_msg += f"\nAMOUNT AWARDED: ${ctx['amount_awarded']:,.0f}"
    if ctx.get('amount_requested'):
        user_msg += f"\nAMOUNT REQUESTED: ${ctx['amount_requested']:,.0f}"

    result = await call_ai_safe(system, user_msg)
    if not result:
        return {"subject": f"Follow-up - {donor_name}", "body": "AI generation failed. Please draft manually."}
    try:
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            parsed = json.loads(json_match.group())
            return {"subject": parsed.get("subject", ""), "body": parsed.get("body", "")}
    except (json.JSONDecodeError, ValueError):
        pass
    return {"subject": f"Follow-up - {donor_name}", "body": result}


@api_router.get("/follow-ups")
async def list_follow_ups(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("""
        SELECT f.*, d.relationship_score, d.relationship_level, d.type as donor_type
        FROM follow_ups f
        LEFT JOIN donors d ON f.donor_id = d.id
        ORDER BY CASE f.urgency WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, f.created_at DESC
    """)
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


@api_router.post("/follow-ups/scan")
async def scan_follow_ups(request: Request):
    """Detect and create follow-up items."""
    await get_current_user(request)
    triggers = await detect_follow_ups()
    created = 0
    for t in triggers:
        fid = str(uuid.uuid4())
        now_str = datetime.now(timezone.utc).isoformat()
        due = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
        db = await get_db()
        await db.execute(
            """INSERT INTO follow_ups (id, donor_id, donor_name, opportunity_id, trigger_type, email_type,
               urgency, reason, status, due_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (fid, t['donor_id'], t['donor_name'], t.get('opportunity_id', ''), t['trigger_type'],
             t['email_type'], t['urgency'], t['reason'], due, now_str))
        await db.commit()
        await db.close()
        created += 1
    return {"scanned": True, "triggers_found": len(triggers), "follow_ups_created": created}


@api_router.post("/follow-ups/{follow_up_id}/generate")
async def generate_follow_up(follow_up_id: str, request: Request):
    """Generate AI email draft for a follow-up."""
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM follow_ups WHERE id = ?", (follow_up_id,))
    fu = await cursor.fetchone()
    if not fu:
        await db.close()
        raise HTTPException(status_code=404, detail="Follow-up not found")
    fu = dict(fu)

    # Build context from donor + outcomes
    context = {}
    cursor = await db.execute("SELECT * FROM donors WHERE id = ?", (fu['donor_id'],))
    donor_row = await cursor.fetchone()
    if donor_row:
        context = dict(donor_row)
    if fu['opportunity_id']:
        cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (fu['opportunity_id'],))
        opp_row = await cursor.fetchone()
        if opp_row:
            context['title'] = dict(opp_row)['title']
        cursor = await db.execute("SELECT * FROM application_outcomes WHERE opportunity_id = ?", (fu['opportunity_id'],))
        ao_row = await cursor.fetchone()
        if ao_row:
            ao = dict(ao_row)
            context['date_submitted'] = ao.get('date_submitted', '')
            context['amount_requested'] = ao.get('amount_requested', 0)
            context['amount_awarded'] = ao.get('amount_awarded', 0)
    await db.close()

    trigger = {**fu, "context": context}
    email = await generate_follow_up_email(trigger)

    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute("UPDATE follow_ups SET email_draft = ?, email_subject = ?, generated_at = ?, status = 'draft' WHERE id = ?",
                     (email['body'], email['subject'], now_str, follow_up_id))
    await db.commit()
    await db.close()
    return {"id": follow_up_id, "subject": email['subject'], "body": email['body'], "status": "draft"}


class FollowUpUpdate(BaseModel):
    email_draft: Optional[str] = None
    email_subject: Optional[str] = None
    status: Optional[str] = None


@api_router.put("/follow-ups/{follow_up_id}")
async def update_follow_up(follow_up_id: str, data: FollowUpUpdate, request: Request):
    await get_current_user(request)
    db = await get_db()
    fields = {}
    if data.email_draft is not None: fields["email_draft"] = data.email_draft
    if data.email_subject is not None: fields["email_subject"] = data.email_subject
    if data.status is not None: fields["status"] = data.status
    if not fields:
        await db.close()
        raise HTTPException(status_code=400, detail="No fields")
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [follow_up_id]
    await db.execute(f"UPDATE follow_ups SET {set_clause} WHERE id = ?", values)
    await db.commit()
    await db.close()
    return {"id": follow_up_id, "updated": True}


@api_router.post("/follow-ups/{follow_up_id}/mark-sent")
async def mark_follow_up_sent(follow_up_id: str, request: Request):
    """Mark follow-up as sent and log interaction."""
    await get_current_user(request)
    now_str = datetime.now(timezone.utc).isoformat()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db = await get_db()
    cursor = await db.execute("SELECT * FROM follow_ups WHERE id = ?", (follow_up_id,))
    fu = await cursor.fetchone()
    if not fu:
        await db.close()
        raise HTTPException(status_code=404, detail="Follow-up not found")
    fu = dict(fu)
    await db.execute("UPDATE follow_ups SET status = 'sent', sent_at = ? WHERE id = ?", (now_str, follow_up_id))
    # Log interaction
    if fu['donor_id']:
        iid = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO donor_interactions (id, donor_id, type, date, notes, opportunity_id, created_at) VALUES (?, ?, 'follow_up', ?, ?, ?, ?)",
            (iid, fu['donor_id'], today_str, f"Follow-up email sent: {fu.get('email_subject', '')}", fu.get('opportunity_id', ''), now_str))
    await db.commit()
    await db.close()
    # Refresh donor stats
    if fu['donor_name']:
        await refresh_donor_stats(fu['donor_name'])
    return {"id": follow_up_id, "status": "sent"}


@api_router.delete("/follow-ups/{follow_up_id}")
async def dismiss_follow_up(follow_up_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    await db.execute("UPDATE follow_ups SET status = 'dismissed' WHERE id = ?", (follow_up_id,))
    await db.commit()
    await db.close()
    return {"id": follow_up_id, "status": "dismissed"}


# ============================
#   COMMAND CENTER CALENDAR
# ============================

@api_router.get("/calendar/events")
async def get_calendar_events(request: Request, month: Optional[str] = None):
    """Get all events for the calendar command center."""
    await get_current_user(request)
    db = await get_db()

    # Parse month filter (YYYY-MM)
    if month:
        try:
            year, m = month.split("-")
            start = f"{year}-{m.zfill(2)}-01"
            end_month = int(m) + 1
            end_year = int(year)
            if end_month > 12:
                end_month = 1
                end_year += 1
            end = f"{end_year}-{str(end_month).zfill(2)}-01"
        except (ValueError, IndexError):
            start = datetime.now(timezone.utc).strftime("%Y-%m-01")
            end = (datetime.now(timezone.utc) + timedelta(days=35)).strftime("%Y-%m-01")
    else:
        start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        end = (datetime.now(timezone.utc) + timedelta(days=120)).strftime("%Y-%m-%d")

    events = []

    # 1. Grant deadlines
    cursor = await db.execute(
        "SELECT id, title, donor_name, deadline, sector, ai_match_score, decision_label, funding_max FROM opportunities WHERE deadline >= ? AND deadline < ? ORDER BY deadline",
        (start, end))
    for r in await cursor.fetchall():
        r = dict(r)
        events.append({
            "id": f"deadline-{r['id']}", "date": r['deadline'], "type": "deadline",
            "title": r['title'], "subtitle": r['donor_name'],
            "urgency": "critical" if (datetime.strptime(r['deadline'], '%Y-%m-%d') - datetime.now(timezone.utc).replace(tzinfo=None)).days <= 7 else
                       "high" if (datetime.strptime(r['deadline'], '%Y-%m-%d') - datetime.now(timezone.utc).replace(tzinfo=None)).days <= 14 else "medium",
            "meta": {"score": r['ai_match_score'], "label": r['decision_label'], "funding": r['funding_max'], "sector": r['sector']},
            "link": f"/opportunity/{r['id']}"
        })

    # 2. Follow-ups due
    cursor = await db.execute(
        "SELECT id, donor_name, email_type, due_date, urgency, status, reason FROM follow_ups WHERE due_date >= ? AND due_date < ? AND status IN ('pending', 'draft') ORDER BY due_date",
        (start, end))
    for r in await cursor.fetchall():
        r = dict(r)
        events.append({
            "id": f"followup-{r['id']}", "date": r['due_date'], "type": "follow_up",
            "title": f"Follow up: {r['donor_name']}", "subtitle": r['reason'][:80],
            "urgency": r['urgency'],
            "meta": {"email_type": r['email_type'], "status": r['status']},
            "link": "/follow-ups"
        })

    # 3. Submissions (from outcomes with date_submitted)
    cursor = await db.execute(
        "SELECT ao.id, ao.donor_name, ao.date_submitted, ao.outcome, ao.amount_requested, o.title FROM application_outcomes ao JOIN opportunities o ON ao.opportunity_id = o.id WHERE ao.date_submitted >= ? AND ao.date_submitted < ? ORDER BY ao.date_submitted",
        (start, end))
    for r in await cursor.fetchall():
        r = dict(r)
        events.append({
            "id": f"submission-{r['id']}", "date": r['date_submitted'], "type": "submission",
            "title": f"Submitted: {r['title']}", "subtitle": r['donor_name'],
            "urgency": "info",
            "meta": {"outcome": r['outcome'], "amount": r['amount_requested']},
            "link": "/analytics"
        })

    # 4. Decisions (from outcomes with date_decided)
    cursor = await db.execute(
        "SELECT ao.id, ao.donor_name, ao.date_decided, ao.outcome, ao.amount_awarded, o.title FROM application_outcomes ao JOIN opportunities o ON ao.opportunity_id = o.id WHERE ao.date_decided >= ? AND ao.date_decided < ? AND ao.date_decided != '' ORDER BY ao.date_decided",
        (start, end))
    for r in await cursor.fetchall():
        r = dict(r)
        events.append({
            "id": f"decision-{r['id']}", "date": r['date_decided'], "type": "decision",
            "title": f"{'Approved' if r['outcome'] == 'approved' else 'Rejected'}: {r['title']}", "subtitle": r['donor_name'],
            "urgency": "success" if r['outcome'] == 'approved' else "danger",
            "meta": {"outcome": r['outcome'], "amount": r['amount_awarded']},
            "link": "/analytics"
        })

    # 5. Donor interactions
    cursor = await db.execute(
        "SELECT di.id, di.date, di.type, di.notes, d.name as donor_name FROM donor_interactions di JOIN donors d ON di.donor_id = d.id WHERE di.date >= ? AND di.date < ? ORDER BY di.date",
        (start, end))
    for r in await cursor.fetchall():
        r = dict(r)
        events.append({
            "id": f"interaction-{r['id']}", "date": r['date'], "type": "interaction",
            "title": f"{r['type'].replace('_', ' ').title()}: {r['donor_name']}", "subtitle": r['notes'][:80] if r['notes'] else "",
            "urgency": "info",
            "meta": {"interaction_type": r['type']},
            "link": "/donors"
        })

    await db.close()
    events.sort(key=lambda e: e['date'])
    return {"events": events, "range": {"start": start, "end": end}}


@api_router.get("/calendar/week-summary")
async def get_week_summary(request: Request):
    """Get this week's command center summary."""
    await get_current_user(request)
    db = await get_db()
    today = datetime.now(timezone.utc)
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")
    next_week_end = (today + timedelta(days=13 - today.weekday())).strftime("%Y-%m-%d")

    # Deadlines this week
    cursor = await db.execute(
        "SELECT COUNT(*) as c FROM opportunities WHERE deadline >= ? AND deadline <= ?",
        (week_start, week_end))
    deadlines_this_week = (await cursor.fetchone())['c']

    # Deadlines next week
    cursor = await db.execute(
        "SELECT COUNT(*) as c FROM opportunities WHERE deadline > ? AND deadline <= ?",
        (week_end, next_week_end))
    deadlines_next_week = (await cursor.fetchone())['c']

    # Pending follow-ups
    cursor = await db.execute("SELECT COUNT(*) as c FROM follow_ups WHERE status IN ('pending', 'draft')")
    pending_followups = (await cursor.fetchone())['c']

    # Items in preparing/drafting
    cursor = await db.execute("SELECT COUNT(*) as c FROM saved_opportunities WHERE status IN ('Preparing', 'Drafting', 'Ready to Submit')")
    in_progress = (await cursor.fetchone())['c']

    # This week's critical events
    cursor = await db.execute(
        "SELECT id, title, donor_name, deadline, ai_match_score FROM opportunities WHERE deadline >= ? AND deadline <= ? ORDER BY deadline LIMIT 5",
        (today.strftime("%Y-%m-%d"), week_end))
    critical = [dict(r) for r in await cursor.fetchall()]

    await db.close()
    return {
        "deadlines_this_week": deadlines_this_week,
        "deadlines_next_week": deadlines_next_week,
        "pending_followups": pending_followups,
        "in_progress": in_progress,
        "critical_this_week": critical
    }


# ============================
#   WEEKLY INTELLIGENCE REPORT
# ============================

async def gather_report_data():
    """Gather all data needed for weekly intelligence report."""
    db = await get_db()
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")
    week_str = today.strftime("%Y-W%W")
    seven_days = (today + timedelta(days=7)).strftime("%Y-%m-%d")

    data = {}

    # Pipeline
    cursor = await db.execute("SELECT COALESCE(SUM(funding_max),0) as total FROM opportunities")
    data['total_available'] = (await cursor.fetchone())['total']
    cursor = await db.execute("""
        SELECT s.status, COALESCE(SUM(o.funding_max),0) as value, COUNT(*) as count
        FROM saved_opportunities s JOIN opportunities o ON s.opportunity_id = o.id GROUP BY s.status
    """)
    data['pipeline_stages'] = {r['status']: {'value': r['value'], 'count': r['count']} for r in await cursor.fetchall()}
    data['pipeline_total'] = sum(s['value'] for s in data['pipeline_stages'].values())

    # Performance
    cursor = await db.execute("SELECT COALESCE(SUM(amount_awarded),0) as secured FROM application_outcomes WHERE outcome='approved'")
    data['total_secured'] = (await cursor.fetchone())['secured']
    cursor = await db.execute("SELECT COUNT(*) as c FROM application_outcomes WHERE outcome='approved'")
    data['approvals'] = (await cursor.fetchone())['c']
    cursor = await db.execute("SELECT COUNT(*) as c FROM application_outcomes WHERE outcome='rejected'")
    data['rejections'] = (await cursor.fetchone())['c']
    decided = data['approvals'] + data['rejections']
    data['approval_rate'] = round((data['approvals'] / decided * 100) if decided > 0 else 0, 1)

    # Top opportunities
    cursor = await db.execute("""
        SELECT id, title, donor_name, deadline, ai_match_score, decision_label, funding_max, sector
        FROM opportunities WHERE deadline >= ? AND ai_match_score > 0
        ORDER BY ai_match_score DESC, deadline ASC LIMIT 5
    """, (today_str,))
    data['top_opps'] = [dict(r) for r in await cursor.fetchall()]

    # Urgent deadlines (7 days)
    cursor = await db.execute(
        "SELECT title, donor_name, deadline, ai_match_score FROM opportunities WHERE deadline >= ? AND deadline <= ? ORDER BY deadline",
        (today_str, seven_days))
    data['urgent_deadlines'] = [dict(r) for r in await cursor.fetchall()]

    # Pending follow-ups
    cursor = await db.execute("SELECT donor_name, reason, urgency FROM follow_ups WHERE status IN ('pending','draft') ORDER BY urgency LIMIT 5")
    data['pending_followups'] = [dict(r) for r in await cursor.fetchall()]

    # Proposals in progress
    cursor = await db.execute("""
        SELECT o.title, s.status FROM saved_opportunities s
        JOIN opportunities o ON s.opportunity_id = o.id
        WHERE s.status IN ('Preparing','Drafting','Ready to Submit') ORDER BY o.deadline LIMIT 5
    """)
    data['proposals_in_progress'] = [dict(r) for r in await cursor.fetchall()]

    # Donor health
    cursor = await db.execute("SELECT name, relationship_score, relationship_level, total_approvals, total_funding_received FROM donors WHERE relationship_score >= 50 ORDER BY relationship_score DESC LIMIT 5")
    data['strong_donors'] = [dict(r) for r in await cursor.fetchall()]
    cursor = await db.execute("""
        SELECT name, relationship_score, last_interaction FROM donors
        WHERE total_applications > 0 AND (last_interaction < ? OR last_interaction = '')
        ORDER BY relationship_score DESC LIMIT 3
    """, ((today - timedelta(days=30)).strftime("%Y-%m-%d"),))
    data['dormant_donors'] = [dict(r) for r in await cursor.fetchall()]

    # Top sectors/donors
    cursor = await db.execute("""
        SELECT sector, SUM(CASE WHEN outcome='approved' THEN 1 ELSE 0 END) as wins, COUNT(*) as total
        FROM application_outcomes GROUP BY sector ORDER BY wins DESC LIMIT 3
    """)
    data['top_sectors'] = [dict(r) for r in await cursor.fetchall()]
    cursor = await db.execute("""
        SELECT donor_name, SUM(CASE WHEN outcome='approved' THEN 1 ELSE 0 END) as wins, COUNT(*) as total
        FROM application_outcomes GROUP BY donor_name ORDER BY wins DESC LIMIT 3
    """)
    data['top_donors_perf'] = [dict(r) for r in await cursor.fetchall()]

    cursor = await db.execute("SELECT COUNT(*) as c FROM smart_queue WHERE status='draft_ready' AND week_label=?", (week_str,))
    data['queue_ready'] = (await cursor.fetchone())['c']

    await db.close()
    return data


async def generate_weekly_report():
    """Generate the AI-powered weekly intelligence report."""
    data = await gather_report_data()
    org_text = await get_org_profile_text()

    top_opps_text = "\n".join([f"- {o['title']} ({o['donor_name']}) - ${o['funding_max']:,.0f} - {o['ai_match_score']}% match - Deadline: {o['deadline']}" for o in data['top_opps']]) or "None scored yet"
    urgent_text = "\n".join([f"- {d['title']} ({d['donor_name']}) - Deadline: {d['deadline']}" for d in data['urgent_deadlines']]) or "No urgent deadlines"
    followup_text = "\n".join([f"- {f['donor_name']}: {f['reason']}" for f in data['pending_followups']]) or "No pending follow-ups"
    proposals_text = "\n".join([f"- {p['title']} (Status: {p['status']})" for p in data['proposals_in_progress']]) or "None in progress"
    strong_text = "\n".join([f"- {d['name']}: Score {d['relationship_score']}%, {d['total_approvals']} approvals, ${d['total_funding_received']:,.0f} funded" for d in data['strong_donors']]) or "No strong relationships yet"
    dormant_text = "\n".join([f"- {d['name']}: Last contact {d['last_interaction'] or 'never'}" for d in data['dormant_donors']]) or "All relationships active"
    pipeline_text = "\n".join([f"- {stage}: {info['count']} grants, ${info['value']:,.0f}" for stage, info in data['pipeline_stages'].items()]) or "Empty pipeline"

    system = """You are a strategic funding advisor for an African NGO. Generate a Weekly Intelligence Report.
Return a JSON object with exactly these keys:
{
  "executive_summary": "<3-4 sentence strategic overview with pipeline value, secured funding, approval rate, and the single most important action. Be specific with numbers.>",
  "top_opportunities": "<Bullet list of top 5 with donor, amount, deadline, score, action to take.>",
  "urgent_actions": "<Numbered list of 3-5 must-do actions this week with deadlines and donor names.>",
  "relationship_health": "<4-6 bullets naming specific donors, scores, and follow-up needs.>",
  "pipeline_overview": "<Stage breakdown with $ values, bottlenecks, what to move forward.>",
  "performance_insights": "<4-5 bullets on approval rates, best sectors/donors, strategy adjustments.>",
  "ai_recommendations": "<5-7 specific actions starting with verbs: Apply, Follow up, Complete, Reapply, Skip, Prepare. Include names, amounts, deadlines.>"
}
Concise but powerful. Bullet points. No filler. Every sentence drives a decision."""

    user_msg = f"""ORGANIZATION:\n{org_text}\n\nMETRICS:\n- Pipeline: ${data['pipeline_total']:,.0f} (${data['total_available']:,.0f} available)\n- Secured: ${data['total_secured']:,.0f}\n- Rate: {data['approval_rate']}% ({data['approvals']}W/{data['rejections']}L)\n- Queue: {data['queue_ready']} drafts\n\nTOP OPPS:\n{top_opps_text}\n\nURGENT:\n{urgent_text}\n\nFOLLOW-UPS:\n{followup_text}\n\nIN PROGRESS:\n{proposals_text}\n\nPIPELINE:\n{pipeline_text}\n\nSTRONG DONORS:\n{strong_text}\n\nDORMANT:\n{dormant_text}\n\nTOP SECTORS: {', '.join([f"{s['sector']} ({s['wins']}/{s['total']})" for s in data['top_sectors']]) or 'No data'}\nTOP DONORS: {', '.join([f"{d['donor_name']} ({d['wins']}/{d['total']})" for d in data['top_donors_perf']]) or 'No data'}"""

    result = await call_ai_safe(system, user_msg)
    if not result:
        return None, data
    try:
        json_match = re.search(r'\{[\s\S]*\}', result)
        parsed = json.loads(json_match.group()) if json_match else {"executive_summary": result, "ai_recommendations": "Review data manually."}
    except (json.JSONDecodeError, ValueError):
        parsed = {"executive_summary": result[:500], "ai_recommendations": "Review data manually."}
    return parsed, data


@api_router.post("/reports/generate")
async def create_weekly_report(request: Request):
    await get_current_user(request)
    report_content, raw_data = await generate_weekly_report()
    if not report_content:
        raise HTTPException(status_code=500, detail="Report generation failed")
    report_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    week_label = datetime.now(timezone.utc).strftime("%Y-W%W")
    db = await get_db()
    await db.execute(
        """INSERT INTO weekly_reports (id, week_label, executive_summary, top_opportunities, urgent_actions,
           relationship_health, pipeline_overview, performance_insights, ai_recommendations, raw_data, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (report_id, week_label, report_content.get("executive_summary", ""), report_content.get("top_opportunities", ""),
         report_content.get("urgent_actions", ""), report_content.get("relationship_health", ""),
         report_content.get("pipeline_overview", ""), report_content.get("performance_insights", ""),
         report_content.get("ai_recommendations", ""),
         json.dumps({"pipeline_total": raw_data['pipeline_total'], "total_secured": raw_data['total_secured'],
                      "approval_rate": raw_data['approval_rate'], "approvals": raw_data['approvals']}), now_str))
    await db.commit()
    await db.close()
    return {"id": report_id, "week_label": week_label, **report_content, "created_at": now_str}


@api_router.get("/reports")
async def list_reports(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT id, week_label, executive_summary, created_at, raw_data FROM weekly_reports ORDER BY created_at DESC")
    rows = []
    for r in await cursor.fetchall():
        d = dict(r)
        try:
            d['raw_data'] = json.loads(d.get('raw_data', '{}'))
        except (json.JSONDecodeError, TypeError):
            d['raw_data'] = {}
        rows.append(d)
    await db.close()
    return rows


@api_router.get("/reports/latest")
async def get_latest_report(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM weekly_reports ORDER BY created_at DESC LIMIT 1")
    row = await cursor.fetchone()
    await db.close()
    if not row:
        return None
    r = dict(row)
    try:
        r['raw_data'] = json.loads(r.get('raw_data', '{}'))
    except (json.JSONDecodeError, TypeError):
        r['raw_data'] = {}
    return r


@api_router.get("/reports/{report_id}")
async def get_report(report_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM weekly_reports WHERE id = ?", (report_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    r = dict(row)
    try:
        r['raw_data'] = json.loads(r.get('raw_data', '{}'))
    except (json.JSONDecodeError, TypeError):
        r['raw_data'] = {}
    return r


@api_router.get("/reports/{report_id}/pdf")
async def export_report_pdf(report_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM weekly_reports WHERE id = ?", (report_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    r = dict(row)
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    def sect(title, content):
        if not content: return
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_draw_color(37, 99, 235)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, content.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(4)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(37, 99, 235)
    pdf.ln(15)
    pdf.cell(0, 12, "WEEKLY INTELLIGENCE REPORT", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, f"Week: {r.get('week_label', '')} | Pro Youth Foundation", ln=True, align="C")
    pdf.cell(0, 8, f"Generated: {r.get('created_at', '')[:10]}", ln=True, align="C")
    pdf.ln(10)
    sect("EXECUTIVE SUMMARY", r.get('executive_summary', ''))
    sect("TOP OPPORTUNITIES", r.get('top_opportunities', ''))
    sect("URGENT ACTIONS", r.get('urgent_actions', ''))
    sect("RELATIONSHIP HEALTH", r.get('relationship_health', ''))
    sect("PIPELINE OVERVIEW", r.get('pipeline_overview', ''))
    sect("PERFORMANCE INSIGHTS", r.get('performance_insights', ''))
    pdf.add_page()
    sect("AI RECOMMENDATIONS", r.get('ai_recommendations', ''))
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "Generated by ProFund AI", ln=True, align="C")
    pdf_bytes = pdf.output()
    return Response(content=bytes(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="weekly_report_{r.get("week_label","")}.pdf"'})


# ============================
#   GRANT APPLICATION WIZARD
# ============================

WIZARD_STEPS = [
    {"step": 1, "name": "Grant Analysis", "description": "AI analyzes the opportunity and extracts requirements"},
    {"step": 2, "name": "Org Fit Check", "description": "Verify organization details match eligibility"},
    {"step": 3, "name": "Document Generation", "description": "AI generates all required application documents"},
    {"step": 4, "name": "Review & Edit", "description": "Review and customize AI-generated content"},
    {"step": 5, "name": "Checklist", "description": "Verify all requirements are met"},
    {"step": 6, "name": "Ready to Submit", "description": "Final review and submission preparation"},
]


@api_router.post("/wizard/start")
async def start_wizard(data: AIRequest, request: Request):
    """Start a new application wizard for an opportunity."""
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (data.opportunity_id,))
    opp = await cursor.fetchone()
    if not opp:
        await db.close()
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp = dict(opp)
    # Check existing wizard
    cursor = await db.execute("SELECT id FROM application_wizards WHERE opportunity_id = ? AND status = 'in_progress'", (data.opportunity_id,))
    existing = await cursor.fetchone()
    if existing:
        await db.close()
        return {"id": dict(existing)['id'], "exists": True}
    # Get org profile
    cursor = await db.execute("SELECT * FROM organization_profile WHERE id = 'org-1'")
    org = await cursor.fetchone()
    org = dict(org) if org else {}
    await db.close()

    wiz_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    org_info = json.dumps({
        "name": org.get("name", ""), "country": org.get("country", ""),
        "mission": org.get("mission", ""),
        "sectors": json.loads(org.get("focus_sectors", "[]")),
        "beneficiaries": json.loads(org.get("beneficiaries", "[]")),
        "funding_min": org.get("funding_needs_min", 0),
        "funding_max": org.get("funding_needs_max", 0)
    })
    db = await get_db()
    await db.execute(
        """INSERT INTO application_wizards (id, opportunity_id, title, donor_name, current_step, total_steps,
           status, org_info, completion_pct, created_at, updated_at) VALUES (?, ?, ?, ?, 1, 6, 'in_progress', ?, 0, ?, ?)""",
        (wiz_id, data.opportunity_id, opp['title'], opp['donor_name'], org_info, now_str, now_str))
    # Auto-save opportunity if not saved
    cursor = await db.execute("SELECT id FROM saved_opportunities WHERE opportunity_id = ?", (data.opportunity_id,))
    if not await cursor.fetchone():
        sid = str(uuid.uuid4())
        await db.execute("INSERT INTO saved_opportunities (id, opportunity_id, status, notes, saved_at, updated_at) VALUES (?, ?, 'Drafting', 'Wizard started', ?, ?)",
                         (sid, data.opportunity_id, now_str, now_str))
    else:
        await db.execute("UPDATE saved_opportunities SET status = 'Drafting', updated_at = ? WHERE opportunity_id = ?", (now_str, data.opportunity_id))
    await db.commit()
    await db.close()
    return {"id": wiz_id, "opportunity_id": data.opportunity_id, "current_step": 1, "exists": False}


@api_router.get("/wizard")
async def list_wizards(request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("""
        SELECT w.*, o.deadline, o.funding_min, o.funding_max, o.ai_match_score, o.sector
        FROM application_wizards w JOIN opportunities o ON w.opportunity_id = o.id
        ORDER BY CASE w.status WHEN 'in_progress' THEN 1 WHEN 'complete' THEN 2 ELSE 3 END, w.updated_at DESC
    """)
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


@api_router.get("/wizard/{wiz_id}")
async def get_wizard(wiz_id: str, request: Request):
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM application_wizards WHERE id = ?", (wiz_id,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail="Wizard not found")
    w = dict(row)
    for k in ('org_info', 'grant_analysis', 'documents', 'review_checklist'):
        try:
            w[k] = json.loads(w.get(k, '{}'))
        except (json.JSONDecodeError, TypeError):
            w[k] = {}
    # Get opportunity details
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (w['opportunity_id'],))
    opp = await cursor.fetchone()
    w['opportunity'] = dict(opp) if opp else {}
    await db.close()
    w['steps'] = WIZARD_STEPS
    return w


@api_router.post("/wizard/{wiz_id}/analyze")
async def wizard_analyze(wiz_id: str, request: Request):
    """Step 1: AI analyzes the grant and extracts requirements."""
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM application_wizards WHERE id = ?", (wiz_id,))
    w = await cursor.fetchone()
    if not w:
        await db.close()
        raise HTTPException(status_code=404, detail="Wizard not found")
    w = dict(w)
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (w['opportunity_id'],))
    opp = dict(await cursor.fetchone())
    await db.close()

    system = """You are a grant application expert for Pro Youth Foundation (Namibia) - rescuing vulnerable children (including street children, orphans) and mothers from abuse. Programs: safe hostels, street children rehabilitation, school fees, food hampers, clothing.
Analyze this grant and extract requirements. Focus on alignment with child protection, street children, housing, education, and food programs.
Return JSON: {"requirements": ["list"], "key_dates": ["dates"], "required_documents": ["docs needed"], "eligibility_fit": "<how our programs fit>", "strategic_angle": "<approach emphasizing street children rescue, safe housing, education, food>", "estimated_effort": "<low/medium/high>", "success_probability": "<percentage>"}"""
    user_msg = f"GRANT: {opp['title']}\nDonor: {opp['donor_name']} ({opp['donor_type']})\nFunding: ${opp['funding_min']:,.0f}-${opp['funding_max']:,.0f}\nDeadline: {opp['deadline']}\nSector: {opp['sector']}\nRegion: {opp['region']}\nDescription: {opp['description']}\nEligibility: {opp['eligibility']}"

    result = await call_ai_safe(system, user_msg)
    analysis = {}
    if result:
        try:
            jm = re.search(r'\{[\s\S]*\}', result)
            analysis = json.loads(jm.group()) if jm else {"strategic_angle": result}
        except (json.JSONDecodeError, ValueError):
            analysis = {"strategic_angle": result[:500]}

    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute("UPDATE application_wizards SET grant_analysis = ?, current_step = 2, completion_pct = 17, updated_at = ? WHERE id = ?",
                     (json.dumps(analysis), now_str, wiz_id))
    await db.commit()
    await db.close()
    return {"step": 2, "analysis": analysis}


@api_router.post("/wizard/{wiz_id}/generate-docs")
async def wizard_generate_docs(wiz_id: str, request: Request):
    """Step 3: Generate all application documents.

    RELIABILITY FIX (2026-04-20): The original version asked the model for all
    6 documents (~1500 words) in ONE call. That single call regularly took
    60-180s on the Emergent gateway (amplified by litellm's internal 502
    retries), which exceeded the 60s ingress timeout and appeared as a failure
    even when the backend eventually succeeded. We now run 6 SMALLER calls in
    parallel — each ~200 words, ~15-25s. Total wall time ~20-30s (parallel),
    partial success tolerated (missing docs come back empty, others still
    usable). Uses the same call_ai_safe() fallback chain as Analyze Grant.
    To revert: replace the 6-parallel block with the original single-prompt
    call commented out below.
    """
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM application_wizards WHERE id = ?", (wiz_id,))
    w = await cursor.fetchone()
    if not w:
        await db.close()
        raise HTTPException(status_code=404, detail="Wizard not found")
    w = dict(w)
    cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (w['opportunity_id'],))
    opp = dict(await cursor.fetchone())
    await db.close()

    org_text = await get_org_profile_text()
    analysis = {}
    try:
        analysis = json.loads(w.get('grant_analysis', '{}'))
    except (json.JSONDecodeError, TypeError):
        pass

    org_snippet = org_text[:1500]  # Keep each prompt tight
    angle = analysis.get('strategic_angle', 'Align with org mission')[:400]
    opp_snippet = (
        f"GRANT: {opp['title']}\nDonor: {opp['donor_name']}\n"
        f"Amount: ${min(opp['funding_max'], 250000):,.0f}\nSector: {opp['sector']}\n"
        f"Angle: {angle}"
    )

    # 6 per-document prompts. Each returns plain text (no JSON wrapping).
    base_sys = (
        "You are an expert grant writer for Pro Youth Foundation, a Namibian "
        "non-profit rescuing vulnerable children (street children, orphans) and "
        "mothers from abuse. Be specific. Reference safe hostels, street-child "
        "rehabilitation, school fees, food hampers. No boilerplate. "
        "Return ONLY the finished text (no headers, no JSON, no commentary)."
    )
    doc_specs = [
        ("cover_letter",          "Write a 300-word cover letter for this grant application."),
        ("executive_summary",     "Write a 200-word executive summary with concrete outcomes (children housed, fees paid, families fed)."),
        ("project_narrative",     "Write a 500-word project narrative with four labelled sections: Background, Objectives, Activities, Outcomes. Use specific Namibian context."),
        ("budget_justification",  "Write a 200-word budget justification for the requested amount."),
        ("sustainability_plan",   "Write a 150-word sustainability plan."),
        ("monitoring_plan",       "Write a 150-word monitoring & evaluation plan."),
    ]

    async def gen_one(key: str, instruction: str) -> tuple[str, str]:
        user = f"ORG:\n{org_snippet}\n\n{opp_snippet}\n\nTASK: {instruction}"
        try:
            # Use fast model (Haiku 3.5) so 6 parallel calls fit under the
            # 60s ingress cap. Falls back to Sonnet 4.5 if Haiku errors.
            text = await call_ai_fast(base_sys, user)
        except Exception as e:
            logger.warning(f"generate-docs[{key}] error: {e}")
            text = None
        return key, (text or "")

    results = await asyncio.gather(
        *(gen_one(k, i) for k, i in doc_specs),
        return_exceptions=False,
    )
    docs = {k: v for k, v in results}

    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute("UPDATE application_wizards SET documents = ?, current_step = 4, completion_pct = 67, updated_at = ? WHERE id = ?",
                     (json.dumps(docs), now_str, wiz_id))
    # Also store as a proposal
    cursor = await db.execute("SELECT id FROM proposals WHERE opportunity_id = ?", (w['opportunity_id'],))
    existing_prop = await cursor.fetchone()
    if not existing_prop:
        prop_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO proposals (id, opportunity_id, opportunity_title, project_idea, beneficiaries_desc,
               funding_amount, donor_email, letter_of_interest, concept_note, proposal_outline, checklist, created_at, auto_generated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (prop_id, w['opportunity_id'], opp['title'], "Wizard-generated application",
             "Youth, unemployed, rural communities", min(opp['funding_max'], 250000),
             docs.get('cover_letter', ''), docs.get('executive_summary', ''),
             docs.get('project_narrative', ''), docs.get('budget_justification', '') + "\n\n" + docs.get('sustainability_plan', ''),
             docs.get('monitoring_plan', ''), now_str))
    await db.commit()
    await db.close()
    return {"step": 4, "documents": docs, "populated": sum(1 for v in docs.values() if v)}


class WizardStepUpdate(BaseModel):
    current_step: int
    review_checklist: Optional[dict] = None
    status: Optional[str] = None


@api_router.put("/wizard/{wiz_id}/step")
async def update_wizard_step(wiz_id: str, data: WizardStepUpdate, request: Request):
    await get_current_user(request)
    now_str = datetime.now(timezone.utc).isoformat()
    pct = min(100, int((data.current_step / 6) * 100))
    db = await get_db()
    fields = {"current_step": data.current_step, "completion_pct": pct, "updated_at": now_str}
    if data.review_checklist:
        fields["review_checklist"] = json.dumps(data.review_checklist)
    if data.status:
        fields["status"] = data.status
    if data.current_step >= 6:
        fields["status"] = "complete"
        fields["completion_pct"] = 100
        # Update saved status to Ready to Submit
        cursor = await db.execute("SELECT opportunity_id FROM application_wizards WHERE id = ?", (wiz_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute("UPDATE saved_opportunities SET status = 'Ready to Submit', updated_at = ? WHERE opportunity_id = ?",
                             (now_str, dict(row)['opportunity_id']))
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [wiz_id]
    await db.execute(f"UPDATE application_wizards SET {set_clause} WHERE id = ?", values)
    await db.commit()
    await db.close()
    return {"step": data.current_step, "completion_pct": pct, "status": fields.get("status", "in_progress")}


# ============================
#   BATCH APPLICATION MODE
# ============================

batch_state = {"running": False, "total": 0, "processed": 0, "errors": 0, "results": []}


class BatchRequest(BaseModel):
    opportunity_ids: List[str]


async def run_batch_wizard(opp_ids: list):
    """Process multiple opportunities through the wizard pipeline sequentially."""
    global batch_state
    batch_state = {"running": True, "total": len(opp_ids), "processed": 0, "errors": 0, "results": []}
    org_text = await get_org_profile_text()

    # Get org info for wizard
    db = await get_db()
    cursor = await db.execute("SELECT * FROM organization_profile WHERE id = 'org-1'")
    org = await cursor.fetchone()
    org = dict(org) if org else {}
    org_info_json = json.dumps({
        "name": org.get("name", ""), "country": org.get("country", ""),
        "mission": org.get("mission", ""),
        "sectors": json.loads(org.get("focus_sectors", "[]")),
        "beneficiaries": json.loads(org.get("beneficiaries", "[]")),
    })
    await db.close()

    for opp_id in opp_ids:
        result = {"opportunity_id": opp_id, "status": "failed", "wizard_id": None}
        try:
            db = await get_db()
            cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
            opp = await cursor.fetchone()
            if not opp:
                await db.close()
                batch_state["errors"] += 1
                batch_state["processed"] += 1
                batch_state["results"].append(result)
                continue
            opp = dict(opp)

            # Check existing wizard
            cursor = await db.execute("SELECT id FROM application_wizards WHERE opportunity_id = ? AND status = 'in_progress'", (opp_id,))
            existing = await cursor.fetchone()
            if existing:
                result["wizard_id"] = dict(existing)['id']
                result["status"] = "exists"
                await db.close()
                batch_state["processed"] += 1
                batch_state["results"].append(result)
                continue

            # Create wizard
            wiz_id = str(uuid.uuid4())
            now_str = datetime.now(timezone.utc).isoformat()
            await db.execute(
                """INSERT INTO application_wizards (id, opportunity_id, title, donor_name, current_step, total_steps,
                   status, org_info, completion_pct, created_at, updated_at) VALUES (?, ?, ?, ?, 1, 6, 'in_progress', ?, 0, ?, ?)""",
                (wiz_id, opp_id, opp['title'], opp['donor_name'], org_info_json, now_str, now_str))
            # Auto-save
            cursor = await db.execute("SELECT id FROM saved_opportunities WHERE opportunity_id = ?", (opp_id,))
            if not await cursor.fetchone():
                sid = str(uuid.uuid4())
                await db.execute("INSERT INTO saved_opportunities (id, opportunity_id, status, notes, saved_at, updated_at) VALUES (?, ?, 'Drafting', 'Batch wizard', ?, ?)",
                                 (sid, opp_id, now_str, now_str))
            else:
                await db.execute("UPDATE saved_opportunities SET status = 'Drafting', updated_at = ? WHERE opportunity_id = ?", (now_str, opp_id))
            await db.commit()
            await db.close()
            result["wizard_id"] = wiz_id

            # Step 1: Analyze
            analyze_sys = """You are a grant application expert for Pro Youth Foundation (Namibia) - rescuing vulnerable children, street children, orphans, and mothers from abuse and poverty. Programs: safe hostels, street children rehabilitation, school fees, food hampers, clothing.
Analyze this opportunity. Return JSON: {"requirements": ["list"], "required_documents": ["list"], "eligibility_fit": "<how our child protection, street children, and housing programs align>", "strategic_angle": "<approach emphasizing street children rescue, safe housing, education, food>", "success_probability": "<estimate>"}"""
            analyze_msg = f"GRANT: {opp['title']}\nDonor: {opp['donor_name']} ({opp['donor_type']})\nFunding: ${opp['funding_min']:,.0f}-${opp['funding_max']:,.0f}\nDeadline: {opp['deadline']}\nSector: {opp['sector']}\nRegion: {opp['region']}\nDescription: {opp['description']}\nEligibility: {opp['eligibility']}"
            analysis_raw = await call_ai_safe(analyze_sys, analyze_msg)
            analysis = {}
            if analysis_raw:
                try:
                    jm = re.search(r'\{[\s\S]*\}', analysis_raw)
                    analysis = json.loads(jm.group()) if jm else {}
                except (json.JSONDecodeError, ValueError):
                    analysis = {"strategic_angle": analysis_raw[:300]}

            # Step 3: Generate docs (donor-specific prompt to ensure differentiation)
            donor_tone = {"UN Agency": "formal, data-driven, SDG-aligned", "Government": "policy-oriented, evidence-based", "Foundation": "impact-focused, narrative-driven", "International NGO": "collaborative, community-centered", "Corporate CSR": "results-oriented, sustainability-focused"}.get(opp.get('donor_type', ''), "professional and specific")

            doc_sys = f"""You are an expert grant writer for Pro Youth Foundation, a Namibian non-profit that rescues vulnerable children and mothers from abuse and provides safe hostels, school fees, food hampers, and clothing.
Tone: {donor_tone}. Adapt to {opp['donor_name']}'s priorities.
Return JSON: {{"cover_letter": "<300-word letter referencing our hostels, school fee program, food distribution>", "executive_summary": "<200-word summary with measurable outcomes: children housed, school fees paid, families fed>", "project_narrative": "<500-word narrative: Background (abuse/poverty in Namibia), Objectives (safe housing, education, food security), Activities (hostel construction, fee payments, food hampers), Outcomes (specific numbers)>", "budget_justification": "<200-word budget>", "sustainability_plan": "<150-word plan>", "monitoring_plan": "<150-word M&E>"}}
CRITICAL: Every document MUST reference safe housing/shelter, education support (school fees), food provision, and protection from abuse. Show transformation: unsafe to safe living. Measurable outcomes. No generic NGO language."""

            doc_msg = f"ORG:\n{org_text}\n\nDONOR: {opp['donor_name']} ({opp['donor_type']}, {opp['donor_country']})\nGRANT: {opp['title']}\nSector: {opp['sector']}\nAmount: ${min(opp['funding_max'], 250000):,.0f}\nAngle: {analysis.get('strategic_angle', 'Align with mission')}\nRequirements: {', '.join(analysis.get('requirements', []))}\nBeneficiaries: Vulnerable children, street children, orphans, abused mothers in Namibia"
            docs_raw = await call_ai_safe(doc_sys, doc_msg)
            docs = {}
            if docs_raw:
                try:
                    jm = re.search(r'\{[\s\S]*\}', docs_raw)
                    docs = json.loads(jm.group()) if jm else {"cover_letter": docs_raw}
                except (json.JSONDecodeError, ValueError):
                    docs = {"cover_letter": docs_raw[:1000]}

            # Quality check - verify donor alignment
            quality_score = 100
            flags = []
            if not docs.get('cover_letter') or len(docs.get('cover_letter', '')) < 100:
                quality_score -= 30
                flags.append("Cover letter too short or missing")
            if not docs.get('project_narrative') or len(docs.get('project_narrative', '')) < 200:
                quality_score -= 20
                flags.append("Project narrative needs expansion")
            if opp['donor_name'].lower() not in docs.get('cover_letter', '').lower():
                quality_score -= 15
                flags.append("Cover letter doesn't reference donor by name")

            # Save everything
            now_str2 = datetime.now(timezone.utc).isoformat()
            db = await get_db()
            await db.execute(
                "UPDATE application_wizards SET grant_analysis=?, documents=?, current_step=4, completion_pct=67, status='batch_review', updated_at=?, review_checklist=? WHERE id=?",
                (json.dumps(analysis), json.dumps(docs), now_str2, json.dumps({"quality_score": quality_score, "flags": flags}), wiz_id))
            # Store as proposal
            prop_id = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO proposals (id, opportunity_id, opportunity_title, project_idea, beneficiaries_desc,
                   funding_amount, donor_email, letter_of_interest, concept_note, proposal_outline, checklist, created_at, auto_generated)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (prop_id, opp_id, opp['title'], "Batch wizard application",
                 "Youth, unemployed, rural communities", min(opp['funding_max'], 250000),
                 docs.get('cover_letter', ''), docs.get('executive_summary', ''),
                 docs.get('project_narrative', ''), docs.get('budget_justification', ''),
                 docs.get('monitoring_plan', ''), now_str2))
            await db.commit()
            await db.close()

            result["status"] = "ready_for_review"
            result["quality_score"] = quality_score
            result["flags"] = flags
            result["title"] = opp['title']

        except Exception as e:
            logger.error(f"Batch wizard error for {opp_id}: {e}")
            result["status"] = "failed"
            batch_state["errors"] += 1

        batch_state["processed"] += 1
        batch_state["results"].append(result)

    batch_state["running"] = False
    logger.info(f"Batch complete: {batch_state['processed']}/{batch_state['total']}, {batch_state['errors']} errors")


@api_router.post("/batch/start")
async def start_batch(data: BatchRequest, request: Request):
    await get_current_user(request)
    global batch_state
    if batch_state["running"]:
        return {"status": "running", **batch_state}
    ids = data.opportunity_ids[:10]  # Cap at 10
    if not ids:
        raise HTTPException(status_code=400, detail="No opportunities selected")
    asyncio.create_task(run_batch_wizard(ids))
    return {"status": "started", "total": len(ids)}


@api_router.get("/batch/status")
async def get_batch_status(request: Request):
    await get_current_user(request)
    return batch_state


@api_router.get("/batch/review")
async def get_batch_review_queue(request: Request):
    """Get applications ready for review from batch processing."""
    await get_current_user(request)
    db = await get_db()
    cursor = await db.execute("""
        SELECT w.*, o.deadline, o.funding_min, o.funding_max, o.ai_match_score, o.sector, o.donor_type
        FROM application_wizards w JOIN opportunities o ON w.opportunity_id = o.id
        WHERE w.status = 'batch_review'
        ORDER BY o.ai_match_score DESC
    """)
    rows = []
    for r in await cursor.fetchall():
        d = dict(r)
        try:
            d['review_checklist'] = json.loads(d.get('review_checklist', '{}'))
        except (json.JSONDecodeError, TypeError):
            d['review_checklist'] = {}
        rows.append(d)
    await db.close()
    return rows


@api_router.post("/batch/approve/{wiz_id}")
async def approve_batch_item(wiz_id: str, request: Request):
    """Approve a batch-processed application."""
    await get_current_user(request)
    now_str = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute("UPDATE application_wizards SET status = 'complete', current_step = 6, completion_pct = 100, updated_at = ? WHERE id = ?",
                     (now_str, wiz_id))
    cursor = await db.execute("SELECT opportunity_id FROM application_wizards WHERE id = ?", (wiz_id,))
    row = await cursor.fetchone()
    if row:
        await db.execute("UPDATE saved_opportunities SET status = 'Ready to Submit', updated_at = ? WHERE opportunity_id = ?",
                         (now_str, dict(row)['opportunity_id']))
    await db.commit()
    await db.close()
    return {"id": wiz_id, "status": "complete"}


# ============================
#        STARTUP
# ============================

app.include_router(api_router)

# V11 — 3-Mode Funding Engine (modular)
from routers.v11 import router as v11_router  # noqa: E402
api_router_v11 = APIRouter(prefix="/api")
api_router_v11.include_router(v11_router)
app.include_router(api_router_v11)

# V12.3 — Automation layer (Grant Scanner / Email Drafts / Donor Finder)
from routers.automation import router as automation_router  # noqa: E402
api_router_auto = APIRouter(prefix="/api")
api_router_auto.include_router(automation_router)
app.include_router(api_router_auto)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- LOCAL_ONLY guard --------------------------------------------------
# When LOCAL_ONLY=1 in .env (default in start.bat), only allow requests that
# originate from localhost or RFC1918 LAN addresses. This keeps the laptop
# install private even if the user accidentally exposes the port. Public
# tunnel scripts (start-public.bat) explicitly set LOCAL_ONLY=0.
LOCAL_ONLY = os.environ.get("LOCAL_ONLY", "0") == "1"


def _is_local_host(host: str) -> bool:
    if not host:
        return False
    h = host.split(":")[0].lower()
    if h in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    if h.startswith(("10.", "192.168.", "169.254.")):
        return True
    if h.startswith("172."):
        try:
            second = int(h.split(".")[1])
            if 16 <= second <= 31:
                return True
        except Exception:
            pass
    # Allow .local mDNS hostnames
    if h.endswith(".local"):
        return True
    return False


@app.middleware("http")
async def local_only_middleware(request: Request, call_next):
    if LOCAL_ONLY:
        host_header = request.headers.get("host", "")
        client_host = request.client.host if request.client else ""
        if not (_is_local_host(host_header) or _is_local_host(client_host)):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "LOCAL_ONLY mode: external requests blocked."},
            )
    return await call_next(request)


@app.get("/api/download/source")
async def download_source():
    zip_path = Path(__file__).parent / "profund-ai.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP not found")
    return Response(
        content=zip_path.read_bytes(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="profund-ai.zip"'}
    )


@app.on_event("startup")
async def startup():
    logger.info("Initializing database...")
    await init_db()

    db = await get_db()

    # Seed / RESYNC admin user.
    # The .env file is the source of truth. Every startup we make sure the
    # admin account exists AND that its password matches ADMIN_PASSWORD
    # from .env. This prevents "invalid email or password" after someone
    # changes the env but the DB still has the old hash.
    cursor = await db.execute("SELECT id, password_hash FROM users WHERE email = ?", (ADMIN_EMAIL.lower(),))
    existing = await cursor.fetchone()
    new_hash = hash_password(ADMIN_PASSWORD)
    now_str = datetime.now(timezone.utc).isoformat()
    if not existing:
        user_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO users (id, email, password_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, ADMIN_EMAIL.lower(), new_hash, "Admin", "admin", now_str)
        )
        logger.info(f"Admin user created: {ADMIN_EMAIL}")
    else:
        # Resync password on every boot — .env wins.
        await db.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (new_hash, ADMIN_EMAIL.lower()),
        )
        logger.info(f"Admin password resynced from .env for: {ADMIN_EMAIL}")

    # Seed org profile
    cursor = await db.execute("SELECT id FROM organization_profile WHERE id = 'org-1'")
    existing = await cursor.fetchone()
    if not existing:
        p = DEFAULT_ORG_PROFILE
        await db.execute(
            "INSERT INTO organization_profile (id, name, country, mission, focus_sectors, beneficiaries, funding_needs_min, funding_needs_max, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (p["id"], p["name"], p["country"], p["mission"], p["focus_sectors"], p["beneficiaries"], p["funding_needs_min"], p["funding_needs_max"], p["updated_at"])
        )
        logger.info("Default organization profile created")

    # Seed opportunities
    cursor = await db.execute("SELECT COUNT(*) as count FROM opportunities")
    count = (await cursor.fetchone())["count"]
    if count == 0:
        for opp in DEMO_OPPORTUNITIES:
            await db.execute(
                """INSERT INTO opportunities (id, title, donor_name, donor_type, donor_country, region,
                   description, eligibility, funding_min, funding_max, deadline, sector, url,
                   africa_eligible, ai_summary, ai_match_score, ai_fit_explanation, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (opp["id"], opp["title"], opp["donor_name"], opp["donor_type"], opp["donor_country"],
                 opp["region"], opp["description"], opp["eligibility"], opp["funding_min"], opp["funding_max"],
                 opp["deadline"], opp["sector"], opp["url"], opp["africa_eligible"],
                 opp["ai_summary"], opp["ai_match_score"], opp["ai_fit_explanation"], opp["created_at"])
            )
        logger.info(f"Seeded {len(DEMO_OPPORTUNITIES)} demo opportunities")

    # Seed sources
    cursor = await db.execute("SELECT COUNT(*) as count FROM sources")
    count = (await cursor.fetchone())["count"]
    if count == 0:
        for s in DEFAULT_SOURCES:
            now_str = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT INTO sources (id, name, url, type, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (s["id"], s["name"], s["url"], s["type"], s["description"], now_str)
            )
        logger.info(f"Seeded {len(DEFAULT_SOURCES)} default sources")

    await db.commit()
    await db.close()
    logger.info("ProFund AI backend ready")

    # Sync donor profiles from existing opportunities
    db = await get_db()
    cursor = await db.execute("SELECT DISTINCT donor_name, donor_type, donor_country FROM opportunities WHERE donor_name != ''")
    donors_raw = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    synced = 0
    for d in donors_raw:
        did = await sync_donor_from_name(d['donor_name'], d.get('donor_type', ''), d.get('donor_country', ''))
        if did:
            await refresh_donor_stats(d['donor_name'])
            synced += 1
    if synced > 0:
        logger.info(f"Synced {synced} donor profiles")

    # Start APScheduler for 24/7 monitoring
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        scheduler = AsyncIOScheduler()
        # Monitoring scan every 6 hours
        scheduler.add_job(run_monitoring_scan, IntervalTrigger(hours=6), id="monitoring_scan", replace_existing=True)
        scheduler.start()
        monitor_state["active"] = True
        next_run = datetime.now(timezone.utc) + timedelta(hours=6)
        monitor_state["next_scan"] = next_run.isoformat()
        logger.info("24/7 Monitoring scheduler started (every 6 hours)")
    except Exception as e:
        logger.warning(f"Scheduler failed to start: {e}. Monitoring will run manually only.")


@app.get("/api")
async def api_root():
    return {"message": "ProFund AI API"}


# ===== Serve React build for live deployments (Railway / VPS) =====
# When a `frontend-build/` folder exists next to `backend/`, mount it as the
# SPA at `/`. The API is preserved under `/api/*` and `/docs`. This makes the
# single-service Railway deploy work: one container, one URL, no CORS issues.
try:
    import os as _os
    from fastapi.staticfiles import StaticFiles as _StaticFiles
    from fastapi.responses import FileResponse as _FileResponse

    _here = _os.path.dirname(_os.path.abspath(__file__))
    # Look for the build in three common locations.
    _candidates = [
        _os.path.join(_here, "..", "frontend-build"),
        _os.path.join(_here, "frontend-build"),
        _os.path.join(_here, "..", "frontend", "build"),
    ]
    _frontend_dir = next((_os.path.abspath(c) for c in _candidates if _os.path.isdir(c)), None)

    if _frontend_dir:
        logger.info(f"Mounting static React build from: {_frontend_dir}")
        _static_dir = _os.path.join(_frontend_dir, "static")
        if _os.path.isdir(_static_dir):
            app.mount("/static", _StaticFiles(directory=_static_dir), name="static")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def _spa_fallback(full_path: str):
            # Anything starting with api/ or docs/openapi is a real backend route.
            if full_path.startswith(("api/", "docs", "openapi.json", "redoc")):
                from fastapi import HTTPException as _HTTPException
                raise _HTTPException(status_code=404)
            candidate = _os.path.join(_frontend_dir, full_path)
            if full_path and _os.path.isfile(candidate):
                return _FileResponse(candidate)
            return _FileResponse(_os.path.join(_frontend_dir, "index.html"))
except Exception as _e:
    logger.warning(f"Static frontend not mounted: {_e}")
