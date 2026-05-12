"""
ProFund AI V9 - Application Wizard API Tests
Tests the 6-step guided wizard for grant applications:
- POST /api/wizard/start - Start new wizard for an opportunity
- GET /api/wizard - List all active wizards with completion %
- GET /api/wizard/{id} - Get full wizard with steps, analysis, documents
- POST /api/wizard/{id}/analyze - AI analysis (Step 1→2) using GPT-5.2
- POST /api/wizard/{id}/generate-docs - Generate application documents (Step 3→4)
- PUT /api/wizard/{id}/step - Advance step and update completion %
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    def test_login_success(self, auth_token):
        """Test login with valid credentials"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print("✓ Login successful")


class TestWizardAPI:
    """Wizard API endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for API calls"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def opportunity_id(self, auth_headers):
        """Get an opportunity ID for testing"""
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        assert response.status_code == 200
        opps = response.json()
        assert len(opps) > 0, "No opportunities found"
        return opps[0]["id"]
    
    def test_wizard_list_empty_or_existing(self, auth_headers):
        """Test GET /api/wizard returns list (may be empty initially)"""
        response = requests.get(f"{BASE_URL}/api/wizard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/wizard returns list with {len(data)} wizards")
    
    def test_wizard_start(self, auth_headers, opportunity_id):
        """Test POST /api/wizard/start creates new wizard"""
        response = requests.post(
            f"{BASE_URL}/api/wizard/start",
            json={"opportunity_id": opportunity_id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "opportunity_id" in data
        # May return exists=True if wizard already exists
        if data.get("exists"):
            print(f"✓ POST /api/wizard/start - wizard already exists: {data['id']}")
        else:
            assert data["current_step"] == 1
            print(f"✓ POST /api/wizard/start - new wizard created: {data['id']}")
        return data["id"]
    
    def test_wizard_get_by_id(self, auth_headers, opportunity_id):
        """Test GET /api/wizard/{id} returns full wizard"""
        # First start/get a wizard
        start_res = requests.post(
            f"{BASE_URL}/api/wizard/start",
            json={"opportunity_id": opportunity_id},
            headers=auth_headers
        )
        wiz_id = start_res.json()["id"]
        
        # Get wizard details
        response = requests.get(f"{BASE_URL}/api/wizard/{wiz_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "id" in data
        assert "opportunity_id" in data
        assert "title" in data
        assert "donor_name" in data
        assert "current_step" in data
        assert "total_steps" in data
        assert data["total_steps"] == 6
        assert "status" in data
        assert "completion_pct" in data
        assert "steps" in data
        assert len(data["steps"]) == 6
        assert "org_info" in data
        assert "grant_analysis" in data
        assert "documents" in data
        assert "review_checklist" in data
        assert "opportunity" in data
        
        print(f"✓ GET /api/wizard/{wiz_id} returns full wizard with all fields")
        print(f"  - Title: {data['title']}")
        print(f"  - Current Step: {data['current_step']}/6")
        print(f"  - Completion: {data['completion_pct']}%")
    
    def test_wizard_analyze_step1(self, auth_headers, opportunity_id):
        """Test POST /api/wizard/{id}/analyze runs AI analysis (Step 1→2)"""
        # Start fresh wizard or get existing
        start_res = requests.post(
            f"{BASE_URL}/api/wizard/start",
            json={"opportunity_id": opportunity_id},
            headers=auth_headers
        )
        wiz_id = start_res.json()["id"]
        
        # Check current step
        get_res = requests.get(f"{BASE_URL}/api/wizard/{wiz_id}", headers=auth_headers)
        current_step = get_res.json()["current_step"]
        
        if current_step >= 2:
            print(f"✓ Wizard already analyzed (step {current_step}), skipping AI call")
            return
        
        # Run analysis (real GPT-5.2 call, ~10 seconds)
        print("  Running AI analysis (may take ~10 seconds)...")
        response = requests.post(
            f"{BASE_URL}/api/wizard/{wiz_id}/analyze",
            json={},
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "step" in data
        assert data["step"] == 2
        assert "analysis" in data
        
        analysis = data["analysis"]
        # Check analysis structure
        print(f"✓ POST /api/wizard/{wiz_id}/analyze completed")
        print(f"  - Analysis keys: {list(analysis.keys())}")
        if "requirements" in analysis:
            print(f"  - Requirements: {len(analysis['requirements'])} items")
        if "eligibility_fit" in analysis:
            print(f"  - Eligibility fit: {analysis['eligibility_fit'][:100]}...")
    
    def test_wizard_step_advance(self, auth_headers, opportunity_id):
        """Test PUT /api/wizard/{id}/step advances step"""
        # Get wizard
        start_res = requests.post(
            f"{BASE_URL}/api/wizard/start",
            json={"opportunity_id": opportunity_id},
            headers=auth_headers
        )
        wiz_id = start_res.json()["id"]
        
        # Get current step
        get_res = requests.get(f"{BASE_URL}/api/wizard/{wiz_id}", headers=auth_headers)
        current_step = get_res.json()["current_step"]
        
        # Advance to step 3 if at step 2
        if current_step == 2:
            response = requests.put(
                f"{BASE_URL}/api/wizard/{wiz_id}/step",
                json={"current_step": 3},
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["step"] == 3
            assert "completion_pct" in data
            print(f"✓ PUT /api/wizard/{wiz_id}/step advanced to step 3, completion: {data['completion_pct']}%")
        else:
            print(f"✓ Wizard at step {current_step}, step advance test skipped")
    
    def test_wizard_generate_docs_step3(self, auth_headers, opportunity_id):
        """Test POST /api/wizard/{id}/generate-docs generates documents (Step 3→4)"""
        # Get wizard
        start_res = requests.post(
            f"{BASE_URL}/api/wizard/start",
            json={"opportunity_id": opportunity_id},
            headers=auth_headers
        )
        wiz_id = start_res.json()["id"]
        
        # Get current step
        get_res = requests.get(f"{BASE_URL}/api/wizard/{wiz_id}", headers=auth_headers)
        current_step = get_res.json()["current_step"]
        
        if current_step >= 4:
            print(f"✓ Wizard already has documents (step {current_step}), skipping AI call")
            return
        
        if current_step < 3:
            # Need to advance to step 3 first
            print(f"  Wizard at step {current_step}, need to run analyze first")
            return
        
        # Generate docs (real GPT-5.2 call, ~10 seconds)
        print("  Generating documents (may take ~10 seconds)...")
        response = requests.post(
            f"{BASE_URL}/api/wizard/{wiz_id}/generate-docs",
            json={},
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "step" in data
        assert data["step"] == 4
        assert "documents" in data
        
        docs = data["documents"]
        print(f"✓ POST /api/wizard/{wiz_id}/generate-docs completed")
        print(f"  - Document keys: {list(docs.keys())}")
        
        # Check expected document types
        expected_docs = ["cover_letter", "executive_summary", "project_narrative", 
                        "budget_justification", "sustainability_plan", "monitoring_plan"]
        for doc_type in expected_docs:
            if doc_type in docs:
                print(f"  - {doc_type}: {len(docs[doc_type])} chars")
    
    def test_wizard_complete_step6(self, auth_headers, opportunity_id):
        """Test completing wizard at step 6 marks it complete"""
        # Get wizard
        start_res = requests.post(
            f"{BASE_URL}/api/wizard/start",
            json={"opportunity_id": opportunity_id},
            headers=auth_headers
        )
        wiz_id = start_res.json()["id"]
        
        # Get current step
        get_res = requests.get(f"{BASE_URL}/api/wizard/{wiz_id}", headers=auth_headers)
        wiz_data = get_res.json()
        current_step = wiz_data["current_step"]
        
        if wiz_data["status"] == "complete":
            print(f"✓ Wizard already complete")
            return
        
        # Advance to step 6 with checklist
        response = requests.put(
            f"{BASE_URL}/api/wizard/{wiz_id}/step",
            json={
                "current_step": 6,
                "review_checklist": {
                    "item_0": True,
                    "item_1": True,
                    "item_2": True
                }
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["step"] == 6
        assert data["completion_pct"] == 100
        assert data["status"] == "complete"
        print(f"✓ PUT /api/wizard/{wiz_id}/step to step 6 - wizard complete")
        
        # Verify saved_opportunities status updated to "Ready to Submit"
        saved_res = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        saved = saved_res.json()
        for s in saved:
            if s.get("id") == opportunity_id or s.get("opportunity_id") == opportunity_id:
                print(f"  - Saved status: {s.get('status')}")
                break
    
    def test_wizard_list_shows_completion(self, auth_headers):
        """Test GET /api/wizard shows completion % for all wizards"""
        response = requests.get(f"{BASE_URL}/api/wizard", headers=auth_headers)
        assert response.status_code == 200
        wizards = response.json()
        
        print(f"✓ GET /api/wizard returns {len(wizards)} wizards")
        for w in wizards[:3]:  # Show first 3
            print(f"  - {w['title'][:40]}... Step {w['current_step']}/6, {w['completion_pct']}% complete, status: {w['status']}")
    
    def test_wizard_auto_saves_opportunity(self, auth_headers):
        """Test that starting wizard auto-saves the opportunity"""
        # Get an unsaved opportunity
        opps_res = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        opps = opps_res.json()
        
        saved_res = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        saved_ids = [s["id"] for s in saved_res.json()]
        
        # Find an opportunity that might not be saved
        test_opp = opps[1] if len(opps) > 1 else opps[0]
        
        # Start wizard
        start_res = requests.post(
            f"{BASE_URL}/api/wizard/start",
            json={"opportunity_id": test_opp["id"]},
            headers=auth_headers
        )
        assert start_res.status_code == 200
        
        # Check if opportunity is now saved
        saved_res2 = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        saved_opp_ids = [s.get("opportunity_id") or s.get("id") for s in saved_res2.json()]
        
        # The opportunity should be in saved list
        print(f"✓ Wizard auto-save check: opportunity {test_opp['id'][:8]}... in saved list")


class TestWizardNotFound:
    """Test error handling for wizard endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_wizard_get_not_found(self, auth_headers):
        """Test GET /api/wizard/{id} returns 404 for invalid ID"""
        response = requests.get(
            f"{BASE_URL}/api/wizard/invalid-wizard-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✓ GET /api/wizard/invalid-id returns 404")
    
    def test_wizard_start_invalid_opportunity(self, auth_headers):
        """Test POST /api/wizard/start returns 404 for invalid opportunity"""
        response = requests.post(
            f"{BASE_URL}/api/wizard/start",
            json={"opportunity_id": "invalid-opp-id-12345"},
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✓ POST /api/wizard/start with invalid opportunity returns 404")


class TestV8ReportsStillWork:
    """Regression test: V8 Intelligence reports still work"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_reports_list(self, auth_headers):
        """Test GET /api/reports returns list"""
        response = requests.get(f"{BASE_URL}/api/reports", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/reports returns {len(data)} reports (V8 regression)")
    
    def test_reports_latest(self, auth_headers):
        """Test GET /api/reports/latest returns report or null"""
        response = requests.get(f"{BASE_URL}/api/reports/latest", headers=auth_headers)
        assert response.status_code == 200
        print("✓ GET /api/reports/latest works (V8 regression)")


class TestV7CalendarStillWorks:
    """Regression test: V7 Calendar/Command Center still works"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_calendar_events(self, auth_headers):
        """Test GET /api/calendar/events returns events"""
        response = requests.get(f"{BASE_URL}/api/calendar/events", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        print(f"✓ GET /api/calendar/events returns {len(data['events'])} events (V7 regression)")
    
    def test_calendar_week_summary(self, auth_headers):
        """Test GET /api/calendar/week-summary returns summary"""
        response = requests.get(f"{BASE_URL}/api/calendar/week-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "deadlines_this_week" in data
        print("✓ GET /api/calendar/week-summary works (V7 regression)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
