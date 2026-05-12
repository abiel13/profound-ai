"""Payment Link Manager — generic payment-link CRUD with UTM tracking.

Provider is free-form (bank, paypal, stripe, mpesa, custom) so links can be swapped
per Namibia's payment landscape. Builds a tracking_url that appends UTMs.
"""
import uuid
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from deps import get_db, now_iso


def build_tracking_url(url: str, utm_source: str, utm_medium: str, utm_campaign: str) -> str:
    """Append UTM params to a URL without breaking existing ones."""
    if not url:
        return ""
    parsed = urlparse(url)
    existing = dict(parse_qsl(parsed.query))
    if utm_source:
        existing.setdefault("utm_source", utm_source)
    if utm_medium:
        existing.setdefault("utm_medium", utm_medium)
    if utm_campaign:
        existing.setdefault("utm_campaign", utm_campaign)
    new_query = urlencode(existing)
    return urlunparse(parsed._replace(query=new_query))


async def create_payment_link(data: dict) -> dict:
    """Insert a payment link row and return it with tracking_url computed."""
    pid = str(uuid.uuid4())
    tracking = build_tracking_url(
        data.get("url", ""),
        data.get("utm_source", ""),
        data.get("utm_medium", ""),
        data.get("utm_campaign", ""),
    )
    row = {
        "id": pid,
        "label": data.get("label", ""),
        "provider": data.get("provider", "generic"),
        "url": data.get("url", ""),
        "purpose": data.get("purpose", "donation"),
        "campaign_id": data.get("campaign_id", ""),
        "sponsor_offer_id": data.get("sponsor_offer_id", ""),
        "utm_source": data.get("utm_source", ""),
        "utm_medium": data.get("utm_medium", ""),
        "utm_campaign": data.get("utm_campaign", ""),
        "tracking_url": tracking,
        "active": 1 if data.get("active", True) else 0,
        "created_at": now_iso(),
    }
    db = await get_db()
    await db.execute(
        """INSERT INTO payment_links (id, label, provider, url, purpose, campaign_id,
           sponsor_offer_id, utm_source, utm_medium, utm_campaign, tracking_url, active, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (row["id"], row["label"], row["provider"], row["url"], row["purpose"], row["campaign_id"],
         row["sponsor_offer_id"], row["utm_source"], row["utm_medium"], row["utm_campaign"],
         row["tracking_url"], row["active"], row["created_at"]),
    )
    await db.commit()
    await db.close()
    return row


async def list_payment_links(active_only: bool = False) -> list:
    db = await get_db()
    if active_only:
        cursor = await db.execute("SELECT * FROM payment_links WHERE active = 1 ORDER BY created_at DESC")
    else:
        cursor = await db.execute("SELECT * FROM payment_links ORDER BY created_at DESC")
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


async def get_payment_link(pid: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM payment_links WHERE id = ?", (pid,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def update_payment_link(pid: str, data: dict) -> dict | None:
    existing = await get_payment_link(pid)
    if not existing:
        return None
    merged = {**existing, **{k: v for k, v in data.items() if v is not None}}
    merged["tracking_url"] = build_tracking_url(
        merged.get("url", ""),
        merged.get("utm_source", ""),
        merged.get("utm_medium", ""),
        merged.get("utm_campaign", ""),
    )
    db = await get_db()
    await db.execute(
        """UPDATE payment_links SET label=?, provider=?, url=?, purpose=?, utm_source=?,
           utm_medium=?, utm_campaign=?, tracking_url=?, active=? WHERE id=?""",
        (merged["label"], merged["provider"], merged["url"], merged["purpose"],
         merged["utm_source"], merged["utm_medium"], merged["utm_campaign"],
         merged["tracking_url"], 1 if merged.get("active") else 0, pid),
    )
    await db.commit()
    await db.close()
    return merged


async def delete_payment_link(pid: str) -> bool:
    db = await get_db()
    await db.execute("DELETE FROM payment_links WHERE id = ?", (pid,))
    await db.commit()
    await db.close()
    return True


# ---------- Default link helpers (V11 live-readiness) ----------

DEFAULT_ROLES = ("small_donor", "sponsor")


async def get_default_link(role: str) -> dict | None:
    """Return the row currently marked is_default_for=role, or None."""
    if role not in DEFAULT_ROLES:
        return None
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM payment_links WHERE is_default_for = ? ORDER BY created_at DESC LIMIT 1",
        (role,),
    )
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def upsert_default_link(role: str, url: str, label: str = "") -> dict:
    """Create-or-update the single default payment link for the given role.

    role: 'small_donor' | 'sponsor'. Any other role is rejected.
    UTM source/campaign are auto-filled if missing (utm_source=mode, utm_campaign=mode).
    """
    if role not in DEFAULT_ROLES:
        raise ValueError(f"invalid role: {role}")
    if not url or not url.strip():
        raise ValueError("url is required")

    existing = await get_default_link(role)
    now = now_iso()
    utm_source = role
    utm_campaign = role
    utm_medium = "auto"
    tracking = build_tracking_url(url, utm_source, utm_medium, utm_campaign)
    label = label or (f"Default {'Small Donor' if role == 'small_donor' else 'Sponsor'} Link")

    db = await get_db()
    if existing:
        await db.execute(
            """UPDATE payment_links SET label=?, url=?, tracking_url=?,
               utm_source=?, utm_medium=?, utm_campaign=?, active=1 WHERE id=?""",
            (label, url, tracking, utm_source, utm_medium, utm_campaign, existing["id"]),
        )
        pid = existing["id"]
    else:
        import uuid as _uuid
        pid = str(_uuid.uuid4())
        await db.execute(
            """INSERT INTO payment_links (id, label, provider, url, purpose, campaign_id,
               sponsor_offer_id, utm_source, utm_medium, utm_campaign, tracking_url,
               active, is_default_for, created_at)
               VALUES (?, ?, 'generic', ?, ?, '', '', ?, ?, ?, ?, 1, ?, ?)""",
            (pid, label, url, "donation" if role == "small_donor" else "sponsor",
             utm_source, utm_medium, utm_campaign, tracking, role, now),
        )
    await db.commit()
    cursor = await db.execute("SELECT * FROM payment_links WHERE id = ?", (pid,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row)


async def get_defaults_bundle() -> dict:
    """Return both defaults in one structure (either can be None)."""
    small = await get_default_link("small_donor")
    sponsor = await get_default_link("sponsor")
    return {"small_donor": small, "sponsor": sponsor}
