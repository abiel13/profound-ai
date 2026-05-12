import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent / "profund.db"


async def get_db():
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT DEFAULT '',
            role TEXT DEFAULT 'admin',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS organization_profile (
            id TEXT PRIMARY KEY,
            name TEXT DEFAULT '',
            country TEXT DEFAULT '',
            mission TEXT DEFAULT '',
            focus_sectors TEXT DEFAULT '[]',
            beneficiaries TEXT DEFAULT '[]',
            funding_needs_min REAL DEFAULT 0,
            funding_needs_max REAL DEFAULT 0,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            donor_name TEXT DEFAULT '',
            donor_type TEXT DEFAULT '',
            donor_country TEXT DEFAULT '',
            region TEXT DEFAULT '',
            description TEXT DEFAULT '',
            eligibility TEXT DEFAULT '',
            funding_min REAL DEFAULT 0,
            funding_max REAL DEFAULT 0,
            deadline TEXT DEFAULT '',
            sector TEXT DEFAULT '',
            url TEXT DEFAULT '',
            africa_eligible INTEGER DEFAULT 1,
            source_id TEXT DEFAULT '',
            ai_summary TEXT DEFAULT '',
            ai_match_score INTEGER DEFAULT 0,
            ai_fit_explanation TEXT DEFAULT '',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS saved_opportunities (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL,
            status TEXT DEFAULT 'New',
            notes TEXT DEFAULT '',
            saved_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
        );

        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT DEFAULT '',
            type TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS proposals (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT DEFAULT '',
            opportunity_title TEXT DEFAULT '',
            project_idea TEXT DEFAULT '',
            beneficiaries_desc TEXT DEFAULT '',
            funding_amount REAL DEFAULT 0,
            donor_email TEXT DEFAULT '',
            letter_of_interest TEXT DEFAULT '',
            concept_note TEXT DEFAULT '',
            proposal_outline TEXT DEFAULT '',
            checklist TEXT DEFAULT '',
            created_at TEXT
        );
    """)
    await db.commit()

    # Migrations - add new columns safely
    migrations = [
        "ALTER TABLE opportunities ADD COLUMN fit_level TEXT DEFAULT ''",
        "ALTER TABLE opportunities ADD COLUMN decision_label TEXT DEFAULT ''",
        "ALTER TABLE opportunities ADD COLUMN last_analyzed TEXT DEFAULT ''",
        "ALTER TABLE opportunities ADD COLUMN opportunity_type TEXT DEFAULT 'grant'",
        "ALTER TABLE opportunities ADD COLUMN auto_draft_ready INTEGER DEFAULT 0",
        "ALTER TABLE opportunities ADD COLUMN queued_at TEXT DEFAULT ''",
        "ALTER TABLE sources ADD COLUMN source_type TEXT DEFAULT 'static_page'",
        "ALTER TABLE sources ADD COLUMN last_checked TEXT DEFAULT ''",
        "ALTER TABLE sources ADD COLUMN parsing_config TEXT DEFAULT ''",
        "ALTER TABLE proposals ADD COLUMN auto_generated INTEGER DEFAULT 0",
        # V11 live-readiness migrations
        "ALTER TABLE payment_links ADD COLUMN is_default_for TEXT DEFAULT ''",
        "ALTER TABLE send_queue ADD COLUMN approved_at TEXT DEFAULT ''",
        # V12: Grant submission data engine
        "ALTER TABLE opportunities ADD COLUMN submission_url TEXT DEFAULT ''",
        "ALTER TABLE opportunities ADD COLUMN submission_email TEXT DEFAULT ''",
        "ALTER TABLE opportunities ADD COLUMN submission_type TEXT DEFAULT ''",
        "ALTER TABLE opportunities ADD COLUMN apply_instructions TEXT DEFAULT ''",
        "ALTER TABLE opportunities ADD COLUMN submission_fetched_at TEXT DEFAULT ''",
    ]
    for sql in migrations:
        try:
            await db.execute(sql)
            await db.commit()
        except Exception:
            pass

    # New tables
    new_tables = [
        """CREATE TABLE IF NOT EXISTS smart_queue (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL,
            proposal_id TEXT DEFAULT '',
            score INTEGER DEFAULT 0,
            deadline TEXT DEFAULT '',
            funding_max REAL DEFAULT 0,
            status TEXT DEFAULT 'queued',
            queued_at TEXT,
            completed_at TEXT DEFAULT '',
            week_label TEXT DEFAULT '',
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
        )""",
        """CREATE TABLE IF NOT EXISTS monitoring_log (
            id TEXT PRIMARY KEY,
            scan_type TEXT DEFAULT 'scheduled',
            started_at TEXT,
            completed_at TEXT DEFAULT '',
            sources_checked INTEGER DEFAULT 0,
            new_found INTEGER DEFAULT 0,
            auto_queued INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            details TEXT DEFAULT ''
        )""",
        """CREATE TABLE IF NOT EXISTS application_outcomes (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL,
            saved_id TEXT DEFAULT '',
            outcome TEXT DEFAULT 'pending',
            amount_requested REAL DEFAULT 0,
            amount_awarded REAL DEFAULT 0,
            donor_name TEXT DEFAULT '',
            donor_type TEXT DEFAULT '',
            sector TEXT DEFAULT '',
            date_submitted TEXT DEFAULT '',
            date_decided TEXT DEFAULT '',
            rejection_reason TEXT DEFAULT '',
            success_notes TEXT DEFAULT '',
            created_at TEXT,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
        )""",
        """CREATE TABLE IF NOT EXISTS donors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            type TEXT DEFAULT '',
            country TEXT DEFAULT '',
            sectors TEXT DEFAULT '[]',
            funding_min REAL DEFAULT 0,
            funding_max REAL DEFAULT 0,
            website TEXT DEFAULT '',
            relationship_score INTEGER DEFAULT 0,
            relationship_level TEXT DEFAULT 'New',
            last_interaction TEXT DEFAULT '',
            total_applications INTEGER DEFAULT 0,
            total_approvals INTEGER DEFAULT 0,
            total_rejections INTEGER DEFAULT 0,
            total_funding_received REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS donor_interactions (
            id TEXT PRIMARY KEY,
            donor_id TEXT NOT NULL,
            type TEXT DEFAULT '',
            date TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            opportunity_id TEXT DEFAULT '',
            created_at TEXT,
            FOREIGN KEY (donor_id) REFERENCES donors(id)
        )""",
        """CREATE TABLE IF NOT EXISTS follow_ups (
            id TEXT PRIMARY KEY,
            donor_id TEXT NOT NULL,
            donor_name TEXT DEFAULT '',
            opportunity_id TEXT DEFAULT '',
            trigger_type TEXT DEFAULT '',
            email_type TEXT DEFAULT '',
            urgency TEXT DEFAULT 'medium',
            reason TEXT DEFAULT '',
            email_draft TEXT DEFAULT '',
            email_subject TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            due_date TEXT DEFAULT '',
            generated_at TEXT DEFAULT '',
            sent_at TEXT DEFAULT '',
            created_at TEXT,
            FOREIGN KEY (donor_id) REFERENCES donors(id)
        )""",
        """CREATE TABLE IF NOT EXISTS weekly_reports (
            id TEXT PRIMARY KEY,
            week_label TEXT DEFAULT '',
            executive_summary TEXT DEFAULT '',
            top_opportunities TEXT DEFAULT '',
            urgent_actions TEXT DEFAULT '',
            relationship_health TEXT DEFAULT '',
            pipeline_overview TEXT DEFAULT '',
            performance_insights TEXT DEFAULT '',
            ai_recommendations TEXT DEFAULT '',
            raw_data TEXT DEFAULT '',
            created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS application_wizards (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL,
            title TEXT DEFAULT '',
            donor_name TEXT DEFAULT '',
            current_step INTEGER DEFAULT 1,
            total_steps INTEGER DEFAULT 6,
            status TEXT DEFAULT 'in_progress',
            org_info TEXT DEFAULT '{}',
            grant_analysis TEXT DEFAULT '{}',
            documents TEXT DEFAULT '{}',
            review_checklist TEXT DEFAULT '{}',
            completion_pct INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
        )""",
        # V11: 3-Mode Funding Engine
        """CREATE TABLE IF NOT EXISTS donation_campaigns (
            id TEXT PRIMARY KEY,
            title TEXT DEFAULT '',
            theme TEXT DEFAULT '',
            target_audience TEXT DEFAULT 'small_donor',
            suggested_amount_min REAL DEFAULT 5,
            suggested_amount_max REAL DEFAULT 50,
            story_hook TEXT DEFAULT '',
            short_post TEXT DEFAULT '',
            long_post TEXT DEFAULT '',
            whatsapp_message TEXT DEFAULT '',
            ad_copy_facebook TEXT DEFAULT '',
            ad_copy_instagram TEXT DEFAULT '',
            call_to_action TEXT DEFAULT '',
            hashtags TEXT DEFAULT '',
            payment_link_id TEXT DEFAULT '',
            status TEXT DEFAULT 'draft',
            total_raised REAL DEFAULT 0,
            donor_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS sponsor_offers (
            id TEXT PRIMARY KEY,
            sponsor_name TEXT DEFAULT '',
            sponsor_type TEXT DEFAULT 'small_business',
            offer_tier TEXT DEFAULT 'bronze',
            suggested_amount_min REAL DEFAULT 100,
            suggested_amount_max REAL DEFAULT 1000,
            value_proposition TEXT DEFAULT '',
            benefits_list TEXT DEFAULT '',
            email_subject TEXT DEFAULT '',
            email_body TEXT DEFAULT '',
            whatsapp_message TEXT DEFAULT '',
            ad_copy TEXT DEFAULT '',
            follow_up_plan TEXT DEFAULT '',
            payment_link_id TEXT DEFAULT '',
            status TEXT DEFAULT 'draft',
            created_at TEXT,
            updated_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS payment_links (
            id TEXT PRIMARY KEY,
            label TEXT DEFAULT '',
            provider TEXT DEFAULT 'generic',
            url TEXT DEFAULT '',
            purpose TEXT DEFAULT 'donation',
            campaign_id TEXT DEFAULT '',
            sponsor_offer_id TEXT DEFAULT '',
            utm_source TEXT DEFAULT '',
            utm_medium TEXT DEFAULT '',
            utm_campaign TEXT DEFAULT '',
            tracking_url TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS donations_log (
            id TEXT PRIMARY KEY,
            amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            donor_name TEXT DEFAULT '',
            donor_email TEXT DEFAULT '',
            payment_method TEXT DEFAULT '',
            payment_link_id TEXT DEFAULT '',
            campaign_id TEXT DEFAULT '',
            sponsor_offer_id TEXT DEFAULT '',
            source TEXT DEFAULT '',
            note TEXT DEFAULT '',
            received_at TEXT DEFAULT '',
            created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS send_queue (
            id TEXT PRIMARY KEY,
            channel TEXT DEFAULT 'whatsapp',
            target_type TEXT DEFAULT 'campaign',
            target_id TEXT DEFAULT '',
            recipient TEXT DEFAULT '',
            recipient_label TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            message TEXT DEFAULT '',
            payment_link TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            scheduled_for TEXT DEFAULT '',
            sent_at TEXT DEFAULT '',
            error TEXT DEFAULT '',
            mock INTEGER DEFAULT 1,
            created_at TEXT
        )""",
        # V12.2 — TikTok donation campaigns
        """CREATE TABLE IF NOT EXISTS tiktok_campaigns (
            id TEXT PRIMARY KEY,
            campaign_title TEXT DEFAULT '',
            target_amount TEXT DEFAULT '',
            cause_category TEXT DEFAULT '',
            location TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            donation_link TEXT DEFAULT '',
            tone TEXT DEFAULT '',
            pack_json TEXT DEFAULT '{}',
            ai_used INTEGER DEFAULT 0,
            created_at TEXT
        )""",
        # V12.3 — Automation layer
        """CREATE TABLE IF NOT EXISTS scanner_results (
            id TEXT PRIMARY KEY,
            scan_id TEXT DEFAULT '',
            title TEXT DEFAULT '',
            funder TEXT DEFAULT '',
            amount_text TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            country_eligibility TEXT DEFAULT '',
            sector TEXT DEFAULT '',
            official_url TEXT DEFAULT '',
            submission_type TEXT DEFAULT '',
            submission_email TEXT DEFAULT '',
            fit_score INTEGER DEFAULT 0,
            summary TEXT DEFAULT '',
            status TEXT DEFAULT 'new',
            opportunity_id TEXT DEFAULT '',
            created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS email_drafts (
            id TEXT PRIMARY KEY,
            draft_type TEXT DEFAULT 'grant',
            recipient_name TEXT DEFAULT '',
            recipient_email TEXT DEFAULT '',
            organization TEXT DEFAULT '',
            context TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            body TEXT DEFAULT '',
            cta TEXT DEFAULT '',
            attachments TEXT DEFAULT '[]',
            status TEXT DEFAULT 'draft',
            linked_id TEXT DEFAULT '',
            sent_at TEXT DEFAULT '',
            follow_up_at TEXT DEFAULT '',
            created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS donor_prospects (
            id TEXT PRIMARY KEY,
            organization TEXT DEFAULT '',
            category TEXT DEFAULT '',
            country TEXT DEFAULT '',
            city TEXT DEFAULT '',
            website TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            contact_person TEXT DEFAULT '',
            suggested_amount TEXT DEFAULT '',
            suggested_campaign TEXT DEFAULT '',
            outreach_angle TEXT DEFAULT '',
            priority_score INTEGER DEFAULT 0,
            manual_lookup_required INTEGER DEFAULT 0,
            status TEXT DEFAULT 'new',
            notes TEXT DEFAULT '',
            created_at TEXT
        )""",
    ]
    for sql in new_tables:
        try:
            await db.execute(sql)
            await db.commit()
        except Exception:
            pass

    await db.close()
