"""V11 - 3-Mode Funding Engine tests.

Covers: funding router classify, payment links CRUD w/ UTM, campaigns
(generate/list/patch/enqueue/delete), sponsors (generate/list/patch/enqueue),
donations (create/list/summary/delete + campaign rollup), send queue (mark-sent/cancel/delete),
and V1-V10 regression.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://worldwide-grants-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@profund.ai"
ADMIN_PASSWORD = "ProFund2024!"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def created_ids():
    return {"payment_links": [], "campaigns": [], "sponsors": [], "donations": [], "queue": []}


# ---------- Funding Router Classify ----------
class TestRouter:
    def test_classify_small_donor_amount(self, client):
        r = client.post(f"{API}/v11/router/classify", json={"amount": 25}, timeout=20)
        assert r.status_code == 200
        assert r.json()["mode"] == "small_donor"

    def test_classify_sponsor_amount(self, client):
        r = client.post(f"{API}/v11/router/classify", json={"amount": 500}, timeout=20)
        assert r.status_code == 200
        assert r.json()["mode"] == "sponsor"

    def test_classify_big_grant_amount(self, client):
        r = client.post(f"{API}/v11/router/classify", json={"amount": 10000}, timeout=20)
        assert r.status_code == 200
        assert r.json()["mode"] == "big_grant"

    def test_classify_foundation_type(self, client):
        r = client.post(f"{API}/v11/router/classify", json={"target_type": "foundation"}, timeout=20)
        assert r.status_code == 200
        assert r.json()["mode"] == "big_grant"

    def test_classify_shop_type(self, client):
        r = client.post(f"{API}/v11/router/classify", json={"target_type": "shop"}, timeout=20)
        assert r.status_code == 200
        assert r.json()["mode"] == "sponsor"


# ---------- Payment Links ----------
class TestPaymentLinks:
    def test_create_link_with_utm(self, client, created_ids):
        payload = {
            "label": "TEST_PayPal Donate",
            "url": "https://paypal.me/profund",
            "provider": "paypal",
            "purpose": "donation",
            "utm_source": "whatsapp",
            "utm_medium": "social",
            "utm_campaign": "street_kids_2026",
            "active": True,
        }
        r = client.post(f"{API}/v11/payment-links", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data
        assert data["label"] == payload["label"]
        tu = data.get("tracking_url", "")
        assert "utm_source=whatsapp" in tu
        assert "utm_medium=social" in tu
        assert "utm_campaign=street_kids_2026" in tu
        created_ids["payment_links"].append(data["id"])

    def test_list_includes_created(self, client, created_ids):
        r = client.get(f"{API}/v11/payment-links", timeout=20)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert created_ids["payment_links"][0] in ids

    def test_patch_link(self, client, created_ids):
        pid = created_ids["payment_links"][0]
        r = client.patch(
            f"{API}/v11/payment-links/{pid}",
            json={"label": "TEST_PayPal Updated", "url": "https://paypal.me/profund2"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["label"] == "TEST_PayPal Updated"
        assert "paypal.me/profund2" in data.get("url", "")
        # tracking_url recomputed
        assert "utm_source=whatsapp" in data.get("tracking_url", "")


# ---------- Campaigns (small donor, AI) ----------
class TestCampaigns:
    def test_generate_campaign(self, client, created_ids):
        last_err = None
        data = None
        for attempt in range(3):
            try:
                r = client.post(
                    f"{API}/v11/campaigns/generate",
                    json={"theme": "Warm meals for Namibian street children", "amount_min": 5, "amount_max": 50},
                    timeout=120,
                )
                if r.status_code == 200:
                    data = r.json()
                    break
                last_err = f"{r.status_code}: {r.text[:200]}"
            except Exception as e:
                last_err = str(e)
            time.sleep(3)
        if data is None:
            pytest.skip(f"AI upstream unavailable after 3 retries: {last_err}")
        assert "id" in data
        for f in ["title", "story_hook", "short_post", "long_post",
                  "whatsapp_message", "ad_copy_facebook", "ad_copy_instagram",
                  "call_to_action", "hashtags"]:
            assert f in data, f"missing field {f}"
        assert data.get("status") == "draft"
        created_ids["campaigns"].append(data["id"])

    def test_list_campaigns(self, client, created_ids):
        if not created_ids["campaigns"]:
            pytest.skip("no campaign created")
        r = client.get(f"{API}/v11/campaigns", timeout=20)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert created_ids["campaigns"][0] in ids

    def test_patch_campaign(self, client, created_ids):
        if not created_ids["campaigns"] or not created_ids["payment_links"]:
            pytest.skip("deps missing")
        cid = created_ids["campaigns"][0]
        pid = created_ids["payment_links"][0]
        r = client.patch(f"{API}/v11/campaigns/{cid}", json={"payment_link_id": pid, "status": "active"}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["payment_link_id"] == pid
        assert d["status"] == "active"

    def test_enqueue_campaign(self, client, created_ids):
        if not created_ids["campaigns"]:
            pytest.skip("no campaign")
        cid = created_ids["campaigns"][0]
        r = client.post(
            f"{API}/v11/campaigns/{cid}/enqueue",
            json={"channel": "whatsapp", "recipient": "+264811234567"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        item = r.json()
        assert item.get("mock") in (1, True)
        assert "id" in item
        assert item.get("channel") == "whatsapp"
        created_ids["queue"].append(item["id"])


# ---------- Sponsors ----------
class TestSponsors:
    def test_generate_sponsor(self, client, created_ids):
        last_err = None
        data = None
        for attempt in range(3):
            try:
                r = client.post(
                    f"{API}/v11/sponsors/generate",
                    json={"sponsor_name": "Kalahari Sands Hotel", "offer_tier": "silver"},
                    timeout=120,
                )
                if r.status_code == 200:
                    data = r.json()
                    break
                last_err = f"{r.status_code}: {r.text[:200]}"
            except Exception as e:
                last_err = str(e)
            time.sleep(3)
        if data is None:
            pytest.skip(f"AI upstream unavailable: {last_err}")
        assert "id" in data
        assert data.get("sponsor_name") == "Kalahari Sands Hotel"
        assert data.get("status") == "draft"
        created_ids["sponsors"].append(data["id"])

    def test_list_sponsors(self, client, created_ids):
        if not created_ids["sponsors"]:
            pytest.skip()
        r = client.get(f"{API}/v11/sponsors", timeout=20)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert created_ids["sponsors"][0] in ids

    def test_patch_sponsor(self, client, created_ids):
        if not created_ids["sponsors"] or not created_ids["payment_links"]:
            pytest.skip()
        sid = created_ids["sponsors"][0]
        pid = created_ids["payment_links"][0]
        r = client.patch(f"{API}/v11/sponsors/{sid}", json={"payment_link_id": pid, "status": "contacted"}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["payment_link_id"] == pid
        assert d["status"] == "contacted"

    def test_enqueue_sponsor(self, client, created_ids):
        if not created_ids["sponsors"]:
            pytest.skip()
        sid = created_ids["sponsors"][0]
        r = client.post(
            f"{API}/v11/sponsors/{sid}/enqueue",
            json={"channel": "email", "recipient": "contact@example.com"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        item = r.json()
        assert item.get("mock") in (1, True)
        assert item.get("channel") == "email"
        created_ids["queue"].append(item["id"])


# ---------- Donations ----------
class TestDonations:
    def test_create_donation_rolls_up(self, client, created_ids):
        if not created_ids["campaigns"]:
            pytest.skip("needs a campaign")
        cid = created_ids["campaigns"][0]
        # baseline campaign
        pre = client.get(f"{API}/v11/campaigns/{cid}", timeout=20).json()
        pre_total = pre.get("total_raised") or 0
        pre_count = pre.get("donor_count") or 0

        r = client.post(
            f"{API}/v11/donations",
            json={"amount": 25, "currency": "USD", "campaign_id": cid, "donor_name": "TEST_Donor"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["amount"] == 25
        created_ids["donations"].append(d["id"])

        post = client.get(f"{API}/v11/campaigns/{cid}", timeout=20).json()
        assert (post.get("total_raised") or 0) == pre_total + 25
        assert (post.get("donor_count") or 0) == pre_count + 1

    def test_list_donations(self, client, created_ids):
        r = client.get(f"{API}/v11/donations", timeout=20)
        assert r.status_code == 200
        if created_ids["donations"]:
            ids = [x["id"] for x in r.json()]
            assert created_ids["donations"][0] in ids

    def test_summary_shape(self, client):
        r = client.get(f"{API}/v11/donations/summary", timeout=20)
        assert r.status_code == 200
        s = r.json()
        assert "totals" in s and "c" in s["totals"] and "total" in s["totals"]
        assert "by_campaign" in s and isinstance(s["by_campaign"], list)
        assert "by_sponsor" in s and isinstance(s["by_sponsor"], list)
        assert "by_month" in s and isinstance(s["by_month"], list)

    def test_delete_donation_decrements(self, client, created_ids):
        if not created_ids["donations"] or not created_ids["campaigns"]:
            pytest.skip()
        did = created_ids["donations"][0]
        cid = created_ids["campaigns"][0]
        pre = client.get(f"{API}/v11/campaigns/{cid}", timeout=20).json()
        pre_total = pre.get("total_raised") or 0

        r = client.delete(f"{API}/v11/donations/{did}", timeout=20)
        assert r.status_code == 200

        post = client.get(f"{API}/v11/campaigns/{cid}", timeout=20).json()
        assert (post.get("total_raised") or 0) == max(0, pre_total - 25)


# ---------- Send Queue ----------
class TestQueue:
    def test_list_queue(self, client, created_ids):
        r = client.get(f"{API}/v11/queue", timeout=20)
        assert r.status_code == 200
        items = r.json()
        if created_ids["queue"]:
            ids = [x["id"] for x in items]
            assert created_ids["queue"][0] in ids
            # Each item must be mock=1
            for it in items:
                assert it.get("mock") in (1, True)

    def test_mark_sent(self, client, created_ids):
        if not created_ids["queue"]:
            pytest.skip()
        qid = created_ids["queue"][0]
        r = client.post(f"{API}/v11/queue/{qid}/mark-sent", timeout=20)
        assert r.status_code == 200, r.text
        item = r.json()
        assert item.get("status") == "sent"
        assert item.get("sent_at")

    def test_cancel(self, client, created_ids):
        if len(created_ids["queue"]) < 2:
            pytest.skip()
        qid = created_ids["queue"][1]
        r = client.post(f"{API}/v11/queue/{qid}/cancel", timeout=20)
        assert r.status_code == 200
        # verify via list
        items = client.get(f"{API}/v11/queue", timeout=20).json()
        found = next((x for x in items if x["id"] == qid), None)
        assert found is not None
        assert found.get("status") == "cancelled"

    def test_delete_queue_item(self, client, created_ids):
        if not created_ids["queue"]:
            pytest.skip()
        qid = created_ids["queue"][0]
        r = client.delete(f"{API}/v11/queue/{qid}", timeout=20)
        assert r.status_code == 200


# ---------- Cleanup / teardown ----------
class TestZZCleanup:
    def test_delete_campaign(self, client, created_ids):
        for cid in created_ids["campaigns"]:
            r = client.delete(f"{API}/v11/campaigns/{cid}", timeout=20)
            assert r.status_code == 200

    def test_delete_sponsor(self, client, created_ids):
        for sid in created_ids["sponsors"]:
            r = client.delete(f"{API}/v11/sponsors/{sid}", timeout=20)
            assert r.status_code == 200

    def test_delete_payment_link(self, client, created_ids):
        for pid in created_ids["payment_links"]:
            r = client.delete(f"{API}/v11/payment-links/{pid}", timeout=20)
            assert r.status_code == 200


# ---------- V1-V10 Regression ----------
class TestRegression:
    def test_opps_dashboard(self, client):
        r = client.get(f"{API}/opportunities/dashboard", timeout=30)
        assert r.status_code == 200

    def test_saved(self, client):
        r = client.get(f"{API}/saved", timeout=20)
        assert r.status_code == 200

    def test_donors(self, client):
        r = client.get(f"{API}/donors", timeout=20)
        assert r.status_code == 200

    def test_follow_ups(self, client):
        r = client.get(f"{API}/follow-ups", timeout=20)
        assert r.status_code == 200
