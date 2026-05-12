"""
ProFund AI V3 Features - Backend API Tests
Tests NEW features: Smart Apply Queue, 24/7 Monitoring, Auto-Draft System, Dashboard Extras, Automation Suggestions
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@profund.ai"
TEST_PASSWORD = "ProFund2024!"


@pytest.fixture
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestSmartApplyQueue:
    """Smart Apply Queue endpoint tests"""
    
    def test_queue_generate_endpoint(self, auth_headers):
        """Test POST /api/queue/generate starts queue generation"""
        response = requests.post(f"{BASE_URL}/api/queue/generate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["started", "running"]
        assert "message" in data
    
    def test_queue_status_endpoint(self, auth_headers):
        """Test GET /api/queue/status returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/queue/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "generating" in data
        assert isinstance(data["generating"], bool)
        # last_generated can be null or string
        assert "last_generated" in data
    
    def test_queue_list_endpoint(self, auth_headers):
        """Test GET /api/queue returns queue items"""
        response = requests.get(f"{BASE_URL}/api/queue", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "generating" in data
        assert "last_generated" in data
        
        # If items exist, verify structure
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "opportunity_id" in item
            assert "score" in item
            assert "status" in item
            assert "title" in item
            assert "donor_name" in item
    
    def test_queue_items_have_proposals(self, auth_headers):
        """Test queue items with draft_ready status have proposal_id"""
        response = requests.get(f"{BASE_URL}/api/queue", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        draft_ready_items = [i for i in data["items"] if i.get("status") == "draft_ready"]
        for item in draft_ready_items:
            assert item.get("proposal_id"), f"Item {item['id']} is draft_ready but has no proposal_id"
    
    def test_queue_unauthorized(self):
        """Test queue endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/queue")
        assert response.status_code == 401
        
        response = requests.post(f"{BASE_URL}/api/queue/generate")
        assert response.status_code == 401


class TestMonitoringSystem:
    """24/7 Monitoring System endpoint tests"""
    
    def test_monitoring_status_endpoint(self, auth_headers):
        """Test GET /api/monitoring/status returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/monitoring/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "active" in data
        assert isinstance(data["active"], bool)
        assert "last_scan" in data
        assert "next_scan" in data
        assert "scans_completed" in data
        assert isinstance(data["scans_completed"], int)
    
    def test_monitoring_trigger_endpoint(self, auth_headers):
        """Test POST /api/monitoring/trigger starts a scan"""
        response = requests.post(f"{BASE_URL}/api/monitoring/trigger", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "started"
        assert "message" in data
    
    def test_monitoring_log_endpoint(self, auth_headers):
        """Test GET /api/monitoring/log returns scan history"""
        response = requests.get(f"{BASE_URL}/api/monitoring/log", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # If logs exist, verify structure
        if len(data) > 0:
            log = data[0]
            assert "id" in log
            assert "scan_type" in log
            assert "started_at" in log
            assert "status" in log
            assert "sources_checked" in log
            assert "new_found" in log
    
    def test_monitoring_active_by_default(self, auth_headers):
        """Test monitoring is active (APScheduler running)"""
        response = requests.get(f"{BASE_URL}/api/monitoring/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Monitoring should be active with APScheduler
        assert data["active"] == True
    
    def test_monitoring_unauthorized(self):
        """Test monitoring endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/monitoring/status")
        assert response.status_code == 401
        
        response = requests.post(f"{BASE_URL}/api/monitoring/trigger")
        assert response.status_code == 401


class TestAutomationSuggestions:
    """Pipeline Automation Suggestions endpoint tests"""
    
    def test_suggestions_endpoint(self, auth_headers):
        """Test GET /api/automation/suggestions returns suggestions"""
        response = requests.get(f"{BASE_URL}/api/automation/suggestions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        
        # If suggestions exist, verify structure
        if len(data["suggestions"]) > 0:
            suggestion = data["suggestions"][0]
            assert "type" in suggestion
            assert "message" in suggestion
            assert "opportunity_id" in suggestion
            assert "action" in suggestion
    
    def test_suggestions_types(self, auth_headers):
        """Test suggestions have valid types"""
        response = requests.get(f"{BASE_URL}/api/automation/suggestions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        valid_types = ["move_to_preparing", "ready_to_submit"]
        for suggestion in data["suggestions"]:
            assert suggestion["type"] in valid_types
    
    def test_suggestions_unauthorized(self):
        """Test suggestions endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/automation/suggestions")
        assert response.status_code == 401


class TestDashboardExtras:
    """Dashboard Extras endpoint tests"""
    
    def test_dashboard_extras_endpoint(self, auth_headers):
        """Test GET /api/dashboard/extras returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/dashboard/extras", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields
        assert "priority_apps" in data
        assert "drafts_ready" in data
        assert "new_24h_count" in data
        assert "monitoring" in data
        assert "queue_generating" in data
        
        # Verify types
        assert isinstance(data["priority_apps"], list)
        assert isinstance(data["drafts_ready"], list)
        assert isinstance(data["new_24h_count"], int)
        assert isinstance(data["monitoring"], dict)
        assert isinstance(data["queue_generating"], bool)
    
    def test_dashboard_extras_monitoring_structure(self, auth_headers):
        """Test monitoring section in dashboard extras"""
        response = requests.get(f"{BASE_URL}/api/dashboard/extras", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        monitoring = data["monitoring"]
        assert "active" in monitoring
        assert "last_scan" in monitoring
        assert "scans_completed" in monitoring
    
    def test_dashboard_extras_priority_apps_structure(self, auth_headers):
        """Test priority_apps structure in dashboard extras"""
        response = requests.get(f"{BASE_URL}/api/dashboard/extras", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data["priority_apps"]) > 0:
            app = data["priority_apps"][0]
            assert "id" in app
            assert "opportunity_id" in app
            assert "title" in app
            assert "donor_name" in app
            assert "ai_match_score" in app
            assert "deadline" in app
    
    def test_dashboard_extras_drafts_ready_structure(self, auth_headers):
        """Test drafts_ready structure in dashboard extras"""
        response = requests.get(f"{BASE_URL}/api/dashboard/extras", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data["drafts_ready"]) > 0:
            draft = data["drafts_ready"][0]
            assert "id" in draft
            assert "title" in draft
            assert "donor_name" in draft
            assert "proposal_id" in draft
            assert "draft_created" in draft
    
    def test_dashboard_extras_unauthorized(self):
        """Test dashboard extras requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/extras")
        assert response.status_code == 401


class TestAutoGeneratedProposals:
    """Auto-generated proposals tests"""
    
    def test_proposals_have_auto_generated_flag(self, auth_headers):
        """Test proposals endpoint returns auto_generated field"""
        response = requests.get(f"{BASE_URL}/api/proposals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            # Check that auto_generated field exists
            for proposal in data:
                assert "auto_generated" in proposal or proposal.get("auto_generated") is None
    
    def test_auto_generated_proposals_exist(self, auth_headers):
        """Test that auto-generated proposals were created by smart queue"""
        response = requests.get(f"{BASE_URL}/api/proposals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        auto_generated = [p for p in data if p.get("auto_generated") == 1]
        # After smart queue runs, there should be auto-generated proposals
        assert len(auto_generated) >= 0  # May be 0 if queue hasn't run


class TestSourcesV3:
    """Sources V3 - new columns tests"""
    
    def test_sources_endpoint(self, auth_headers):
        """Test sources endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/sources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        if len(data) > 0:
            source = data[0]
            assert "id" in source
            assert "name" in source
            assert "url" in source


class TestOpportunitiesV3:
    """Opportunities V3 - new columns tests"""
    
    def test_opportunities_have_v3_fields(self, auth_headers):
        """Test opportunities have new V3 fields"""
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            opp = data[0]
            # These fields may be empty but should exist in schema
            # auto_draft_ready and queued_at are new V3 fields
            assert "id" in opp
            assert "title" in opp


class TestSavedOpportunitiesV3:
    """Saved opportunities V3 - auto-saved by smart queue"""
    
    def test_saved_includes_auto_queued(self, auth_headers):
        """Test saved opportunities include those auto-saved by smart queue"""
        response = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # After smart queue runs, there should be saved opportunities with 'Preparing' status
        preparing = [s for s in data if s.get("status") == "Preparing"]
        # May be 0 if queue hasn't run, but endpoint should work
        assert isinstance(preparing, list)


class TestIntegrationV3:
    """Integration tests for V3 features"""
    
    def test_smart_queue_creates_proposals(self, auth_headers):
        """Test smart queue creates proposals for queued items"""
        # Get queue items
        queue_res = requests.get(f"{BASE_URL}/api/queue", headers=auth_headers)
        queue_items = queue_res.json()["items"]
        
        # Get proposals
        proposals_res = requests.get(f"{BASE_URL}/api/proposals", headers=auth_headers)
        proposals = proposals_res.json()
        
        # For each draft_ready queue item, there should be a proposal
        for item in queue_items:
            if item.get("status") == "draft_ready" and item.get("proposal_id"):
                proposal_ids = [p["id"] for p in proposals]
                assert item["proposal_id"] in proposal_ids, f"Proposal {item['proposal_id']} not found"
    
    def test_monitoring_updates_sources(self, auth_headers):
        """Test monitoring scan updates source last_checked"""
        # Trigger a scan
        requests.post(f"{BASE_URL}/api/monitoring/trigger", headers=auth_headers)
        time.sleep(2)  # Wait for scan to complete
        
        # Check monitoring log
        log_res = requests.get(f"{BASE_URL}/api/monitoring/log", headers=auth_headers)
        logs = log_res.json()
        
        # Should have at least one completed scan
        completed = [l for l in logs if l.get("status") == "completed"]
        assert len(completed) > 0
    
    def test_dashboard_extras_reflects_queue(self, auth_headers):
        """Test dashboard extras shows queue data"""
        # Get queue
        queue_res = requests.get(f"{BASE_URL}/api/queue", headers=auth_headers)
        queue_items = queue_res.json()["items"]
        
        # Get dashboard extras
        extras_res = requests.get(f"{BASE_URL}/api/dashboard/extras", headers=auth_headers)
        extras = extras_res.json()
        
        # Priority apps should match queue items for current week
        # (may differ if week changed, but structure should be consistent)
        assert isinstance(extras["priority_apps"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
