"""Send Queue — mock WhatsApp/Email/SMS sender.

All items are logged to the DB with mock=1. When WhatsApp / Meta integrations
are added later, flip the 'mock' flag and call the real provider here.

Never auto-sends. Items stay 'pending' until user clicks "Mark Sent".
"""
import uuid
import logging

from deps import get_db, now_iso

logger = logging.getLogger(__name__)


async def enqueue(
    channel: str,
    target_type: str,
    target_id: str,
    recipient: str,
    message: str,
    subject: str = "",
    recipient_label: str = "",
    payment_link: str = "",
    scheduled_for: str = "",
) -> dict:
    """Add a message to the send queue (always mock=1 until real API is wired)."""
    qid = str(uuid.uuid4())
    row = {
        "id": qid,
        "channel": channel,
        "target_type": target_type,
        "target_id": target_id,
        "recipient": recipient,
        "recipient_label": recipient_label,
        "subject": subject,
        "message": message,
        "payment_link": payment_link,
        "status": "pending",
        "scheduled_for": scheduled_for,
        "sent_at": "",
        "error": "",
        "mock": 1,
        "created_at": now_iso(),
    }
    db = await get_db()
    await db.execute(
        """INSERT INTO send_queue (id, channel, target_type, target_id, recipient, recipient_label,
           subject, message, payment_link, status, scheduled_for, sent_at, error, mock, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (row["id"], row["channel"], row["target_type"], row["target_id"], row["recipient"],
         row["recipient_label"], row["subject"], row["message"], row["payment_link"],
         row["status"], row["scheduled_for"], row["sent_at"], row["error"], row["mock"],
         row["created_at"]),
    )
    await db.commit()
    await db.close()
    return row


async def list_queue(status: str = "") -> list:
    db = await get_db()
    if status:
        cursor = await db.execute("SELECT * FROM send_queue WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cursor = await db.execute("SELECT * FROM send_queue ORDER BY created_at DESC")
    rows = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return rows


async def approve_item(qid: str) -> dict | None:
    """Transition a pending item to 'approved'. Only pending items may be approved."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM send_queue WHERE id = ?", (qid,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        return None
    if row["status"] != "pending":
        await db.close()
        return dict(row)  # idempotent — already in a different state
    now = now_iso()
    await db.execute(
        "UPDATE send_queue SET status = 'approved', approved_at = ? WHERE id = ?",
        (now, qid),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM send_queue WHERE id = ?", (qid,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row)


async def mark_sent(qid: str) -> dict | None:
    """Mark an APPROVED item as sent and simulate a donation log entry.

    State rule: only 'approved' items can move to 'sent'. Returns the updated
    queue row plus the simulated donation row at key 'simulated_donation'.
    Returns {"error": "...", "status": current} if state check fails.
    """
    db = await get_db()
    cursor = await db.execute("SELECT * FROM send_queue WHERE id = ?", (qid,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        return None
    item = dict(row)
    if item["status"] != "approved":
        await db.close()
        return {"error": "only approved items may be marked sent",
                "current_status": item["status"]}

    now = now_iso()
    await db.execute(
        "UPDATE send_queue SET status = 'sent', sent_at = ? WHERE id = ?",
        (now, qid),
    )

    # Simulate a donation proportional to the target's suggested amount range (min).
    simulated = None
    if item["target_type"] == "campaign":
        cursor = await db.execute(
            "SELECT suggested_amount_min, title FROM donation_campaigns WHERE id = ?",
            (item["target_id"],),
        )
        t = await cursor.fetchone()
        amount = float(t["suggested_amount_min"]) if t else 0.0
        if t and amount > 0:
            import uuid as _uuid
            did = str(_uuid.uuid4())
            await db.execute(
                """INSERT INTO donations_log (id, amount, currency, donor_name, donor_email,
                   payment_method, payment_link_id, campaign_id, sponsor_offer_id, source, note,
                   received_at, created_at)
                   VALUES (?, ?, 'USD', ?, '', ?, '', ?, '', ?, ?, ?, ?)""",
                (did, amount, item.get("recipient_label") or item.get("recipient") or "Simulated donor",
                 item["channel"], item["target_id"], item["channel"],
                 f"SIMULATED donation from send-queue mark-sent (item {qid})", now, now),
            )
            await db.execute(
                """UPDATE donation_campaigns
                   SET total_raised = total_raised + ?, donor_count = donor_count + 1
                   WHERE id = ?""",
                (amount, item["target_id"]),
            )
            simulated = {"id": did, "amount": amount, "campaign_id": item["target_id"]}
    elif item["target_type"] == "sponsor":
        cursor = await db.execute(
            "SELECT suggested_amount_min FROM sponsor_offers WHERE id = ?",
            (item["target_id"],),
        )
        t = await cursor.fetchone()
        amount = float(t["suggested_amount_min"]) if t else 0.0
        if t and amount > 0:
            import uuid as _uuid
            did = str(_uuid.uuid4())
            await db.execute(
                """INSERT INTO donations_log (id, amount, currency, donor_name, donor_email,
                   payment_method, payment_link_id, campaign_id, sponsor_offer_id, source, note,
                   received_at, created_at)
                   VALUES (?, ?, 'USD', ?, '', ?, '', '', ?, ?, ?, ?, ?)""",
                (did, amount, item.get("recipient_label") or item.get("recipient") or "Simulated sponsor",
                 item["channel"], item["target_id"], item["channel"],
                 f"SIMULATED sponsorship from send-queue mark-sent (item {qid})", now, now),
            )
            simulated = {"id": did, "amount": amount, "sponsor_offer_id": item["target_id"]}

    await db.commit()
    cursor = await db.execute("SELECT * FROM send_queue WHERE id = ?", (qid,))
    row = await cursor.fetchone()
    await db.close()
    updated = dict(row)
    updated["simulated_donation"] = simulated
    logger.info(f"[MOCK SEND] queue={qid} marked sent; simulated={simulated}")
    return updated


async def delete_item(qid: str) -> bool:
    db = await get_db()
    await db.execute("DELETE FROM send_queue WHERE id = ?", (qid,))
    await db.commit()
    await db.close()
    return True


async def cancel_item(qid: str) -> bool:
    db = await get_db()
    await db.execute("UPDATE send_queue SET status = 'cancelled' WHERE id = ?", (qid,))
    await db.commit()
    await db.close()
    return True
