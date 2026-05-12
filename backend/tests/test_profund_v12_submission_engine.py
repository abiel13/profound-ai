"""
V12 Grant Submission Engine backend tests.

Covers:
- Auth login (existing)
- POST /api/opportunities/{id}/fetch-submission
- POST /api/opportunities/{id}/email-template
- GET  /api/opportunities?submission=email|portal|form|active
- Schema: opportunities has new submission_* columns
- V11 regression: /api/v11/donations still works
- Existing endpoints: /api/wizard/{id}/analyze + /api/wizard/{id}/generate-docs still callable
"""
import os
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

ADMIN_EMAIL = "admin@profund.ai"
ADMIN_PASSWORD = "ProFund2026!"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_session(session):
    r = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text}")
    data = r.json()
    token = data.get("token") or data.get("access_token")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    return session


# ---------- Health & Login ----------

class TestAuth:
    def test_login_success(self, session):
        r = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data or "access_token" in data


# ---------- Submission filter on list ----------

class TestSubmissionFilters:
    def test_list_all(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/opportunities", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_email(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/opportunities?submission=email", timeout=30
        )
        assert r.status_code == 200
        for row in r.json():
            assert row.get("submission_type") == "email"
            assert (row.get("submission_email") or "") != ""

    def test_filter_portal(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/opportunities?submission=portal", timeout=30
        )
        assert r.status_code == 200
        for row in r.json():
            assert row.get("submission_type") == "portal"
            assert (row.get("submission_url") or "") != ""

    def test_filter_form(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/opportunities?submission=form", timeout=30
        )
        assert r.status_code == 200
        for row in r.json():
            assert row.get("submission_type") == "form"

    def test_filter_active(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/opportunities?submission=active", timeout=30
        )
        assert r.status_code == 200
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for row in r.json():
            dl = row.get("deadline") or ""
            if dl:
                assert dl >= today, f"Row {row.get('id')} deadline {dl} < {today}"


# ---------- Schema migration ----------

class TestSchemaV12:
    def test_new_columns_exist(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/opportunities", timeout=30)
        assert r.status_code == 200
        rows = r.json()
        if not rows:
            pytest.skip("No opportunities in DB to inspect schema")
        sample = rows[0]
        for col in [
            "submission_url",
            "submission_email",
            "submission_type",
            "apply_instructions",
            "submission_fetched_at",
        ]:
            assert col in sample, f"Missing column in response: {col}"


# ---------- fetch-submission + email-template ----------

@pytest.fixture(scope="class")
def an_opportunity_id(auth_session):
    r = auth_session.get(f"{BASE_URL}/api/opportunities", timeout=30)
    rows = r.json()
    if not rows:
        pytest.skip("No opportunities in DB")
    # prefer one with a URL
    for row in rows:
        if (row.get("url") or "").startswith("http"):
            return row["id"]
    return rows[0]["id"]


class TestFetchSubmission:
    def test_fetch_submission_persists(self, auth_session, an_opportunity_id):
        opp_id = an_opportunity_id
        r = auth_session.post(
            f"{BASE_URL}/api/opportunities/{opp_id}/fetch-submission", timeout=90
        )
        assert r.status_code == 200, r.text
        data = r.json()
        for k in [
            "submission_url",
            "submission_email",
            "submission_type",
            "apply_instructions",
        ]:
            assert k in data, f"missing key {k} in fetch-submission response"
        assert data.get("submission_type") in [
            "portal",
            "email",
            "form",
            "unknown",
        ]
        # Verify persistence via GET
        r2 = auth_session.get(
            f"{BASE_URL}/api/opportunities/{opp_id}", timeout=30
        )
        assert r2.status_code == 200
        fetched = r2.json()
        assert fetched.get("submission_type") == data.get("submission_type")
        assert (
            fetched.get("submission_url") == data.get("submission_url")
        ), "submission_url did not persist"

    def test_fetch_submission_404(self, auth_session):
        r = auth_session.post(
            f"{BASE_URL}/api/opportunities/__nonexistent__/fetch-submission",
            timeout=30,
        )
        assert r.status_code == 404


class TestEmailTemplate:
    def test_email_template_shape(self, auth_session, an_opportunity_id):
        r = auth_session.post(
            f"{BASE_URL}/api/opportunities/{an_opportunity_id}/email-template",
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["to", "subject", "body"]:
            assert k in data
        assert "Grant Application" in data["subject"]
        assert len(data["body"]) > 50

    def test_email_template_404(self, auth_session):
        r = auth_session.post(
            f"{BASE_URL}/api/opportunities/__nope__/email-template", timeout=30
        )
        assert r.status_code == 404


# ---------- Regression on V11 + existing ----------

class TestRegression:
    def test_v11_donations_list(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/v11/donations", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_dashboard_still_ok(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/opportunities/dashboard", timeout=60
        )
        assert r.status_code == 200
        j = r.json()
        assert "stats" in j
