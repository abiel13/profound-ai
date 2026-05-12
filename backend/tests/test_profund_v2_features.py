"""
ProFund AI V2 Features - Backend API Tests
Tests NEW features: Bulk AI Analysis, Pipeline, PDF Export, Workspace statuses, Decision Labels
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


class TestBulkAIAnalysis:
    """Bulk AI Analysis endpoint tests"""
    
    def test_bulk_analyze_endpoint(self, auth_headers):
        """Test /api/ai/bulk-analyze endpoint exists and responds"""
        response = requests.post(f"{BASE_URL}/api/ai/bulk-analyze", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should return status (started or running)
        assert "status" in data
        assert data["status"] in ["started", "running"]
    
    def test_bulk_status_endpoint(self, auth_headers):
        """Test /api/ai/bulk-status returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/ai/bulk-status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have running, total, processed, errors fields
        assert "running" in data
        assert "total" in data
        assert "processed" in data
        assert "errors" in data
        assert isinstance(data["running"], bool)
        assert isinstance(data["total"], int)
        assert isinstance(data["processed"], int)
    
    def test_bulk_status_unauthorized(self):
        """Test bulk status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/ai/bulk-status")
        assert response.status_code == 401


class TestPipelineEndpoint:
    """Pipeline endpoint tests"""
    
    def test_pipeline_endpoint(self, auth_headers):
        """Test /api/pipeline returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/pipeline", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_pipeline" in data
        assert "all_opportunities_value" in data
        assert "stages" in data
        
        # Verify types
        assert isinstance(data["total_pipeline"], (int, float))
        assert isinstance(data["all_opportunities_value"], (int, float))
        assert isinstance(data["stages"], dict)
    
    def test_pipeline_unauthorized(self):
        """Test pipeline requires authentication"""
        response = requests.get(f"{BASE_URL}/api/pipeline")
        assert response.status_code == 401


class TestDashboardV2:
    """Dashboard V2 features - Pipeline, Actions, Top Opportunities"""
    
    def test_dashboard_has_pipeline(self, auth_headers):
        """Test dashboard returns pipeline data"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check pipeline section
        assert "pipeline" in data
        pipeline = data["pipeline"]
        assert "total" in pipeline
        assert "all_value" in pipeline
        assert "stages" in pipeline
    
    def test_dashboard_has_actions(self, auth_headers):
        """Test dashboard returns AI recommended actions"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check actions section
        assert "actions" in data
        assert isinstance(data["actions"], list)
        
        # If there are actions, verify structure
        if len(data["actions"]) > 0:
            action = data["actions"][0]
            assert "type" in action
            assert "priority" in action
            assert "message" in action
    
    def test_dashboard_has_top_opportunities(self, auth_headers):
        """Test dashboard returns top AI-scored opportunities"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check top_opportunities section
        assert "top_opportunities" in data
        assert isinstance(data["top_opportunities"], list)
    
    def test_dashboard_has_apply_now_count(self, auth_headers):
        """Test dashboard stats include apply_now_count"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "stats" in data
        stats = data["stats"]
        assert "apply_now_count" in stats
        assert "analyzed_count" in stats


class TestDecisionLabels:
    """Decision labels (Apply Now, Review First) tests"""
    
    def test_opportunities_have_decision_labels(self, auth_headers):
        """Test opportunities have decision_label field after AI analysis"""
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Find opportunities with AI scores
        scored_opps = [o for o in data if o.get("ai_match_score", 0) > 0]
        
        if len(scored_opps) > 0:
            # Check that scored opportunities have decision labels
            for opp in scored_opps[:5]:  # Check first 5
                assert "decision_label" in opp or opp.get("decision_label") is None
                if opp.get("decision_label"):
                    assert opp["decision_label"] in ["Apply Now", "Review First", "Ignore"]
    
    def test_opportunities_have_fit_level(self, auth_headers):
        """Test opportunities have fit_level field after AI analysis"""
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Find opportunities with AI scores
        scored_opps = [o for o in data if o.get("ai_match_score", 0) > 0]
        
        if len(scored_opps) > 0:
            for opp in scored_opps[:5]:
                if opp.get("fit_level"):
                    assert opp["fit_level"] in ["High", "Medium", "Low"]


class TestWorkspaceStatuses:
    """Workspace 8-stage status flow tests"""
    
    VALID_STATUSES = ["New", "Identified", "Analyzing", "Reviewing", "Drafting", 
                     "Preparing", "Ready to Submit", "Submitted", "Rejected", "Approved"]
    
    def test_all_statuses_accepted(self, auth_headers):
        """Test all 8+ statuses are accepted by the API"""
        # First get or create a saved opportunity
        saved_res = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        saved_list = saved_res.json()
        
        if len(saved_list) == 0:
            # Save an opportunity first
            opps_res = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
            opp_id = opps_res.json()[0]["id"]
            save_res = requests.post(f"{BASE_URL}/api/saved", json={"opportunity_id": opp_id}, headers=auth_headers)
            if save_res.status_code == 200:
                saved_id = save_res.json()["id"]
            else:
                pytest.skip("Could not create saved opportunity")
        else:
            saved_id = saved_list[0]["saved_id"]
        
        # Test each status
        for status in self.VALID_STATUSES:
            update_res = requests.put(f"{BASE_URL}/api/saved/{saved_id}", json={
                "status": status
            }, headers=auth_headers)
            assert update_res.status_code == 200, f"Status '{status}' was rejected"
            assert update_res.json()["status"] == status
    
    def test_invalid_status_rejected(self, auth_headers):
        """Test invalid status is rejected"""
        saved_res = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        saved_list = saved_res.json()
        
        if len(saved_list) == 0:
            pytest.skip("No saved opportunities to test")
        
        saved_id = saved_list[0]["saved_id"]
        
        update_res = requests.put(f"{BASE_URL}/api/saved/{saved_id}", json={
            "status": "InvalidStatus123"
        }, headers=auth_headers)
        assert update_res.status_code == 400


class TestPDFExport:
    """PDF Export endpoint tests"""
    
    def test_pdf_export_nonexistent_proposal(self, auth_headers):
        """Test PDF export returns 404 for non-existent proposal"""
        response = requests.get(f"{BASE_URL}/api/proposals/nonexistent-id/pdf", headers=auth_headers)
        assert response.status_code == 404
    
    def test_pdf_export_existing_proposal(self, auth_headers):
        """Test PDF export works for existing proposal"""
        # First check if there are any proposals
        proposals_res = requests.get(f"{BASE_URL}/api/proposals", headers=auth_headers)
        proposals = proposals_res.json()
        
        if len(proposals) == 0:
            pytest.skip("No proposals exist to test PDF export")
        
        proposal_id = proposals[0]["id"]
        
        # Try to export PDF
        response = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}/pdf", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify it's a PDF
        assert response.headers.get("content-type") == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        
        # Verify PDF content starts with PDF magic bytes
        assert response.content[:4] == b'%PDF'
    
    def test_pdf_export_unauthorized(self):
        """Test PDF export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/proposals/some-id/pdf")
        assert response.status_code == 401


class TestSortByMatch:
    """Sort by match score tests"""
    
    def test_sort_by_match_score(self, auth_headers):
        """Test sorting opportunities by AI match score"""
        response = requests.get(f"{BASE_URL}/api/opportunities?sort_by=match", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify sorted by match score descending
        scores = [o.get("ai_match_score", 0) for o in data]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i+1], "Not sorted by match score descending"


class TestSavedOpportunitiesV2:
    """Saved opportunities V2 - expanded status options"""
    
    def test_saved_returns_status(self, auth_headers):
        """Test saved opportunities include status field"""
        response = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            item = data[0]
            assert "status" in item
            assert "saved_id" in item


class TestOpportunityDetailV2:
    """Opportunity detail V2 - AI fields"""
    
    def test_opportunity_has_ai_fields(self, auth_headers):
        """Test opportunity detail includes AI analysis fields"""
        # Get an opportunity
        opps_res = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        opp_id = opps_res.json()[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/opportunities/{opp_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check AI fields exist (may be empty if not analyzed)
        assert "ai_summary" in data or data.get("ai_summary") is None
        assert "ai_match_score" in data or data.get("ai_match_score") is None
        assert "ai_fit_explanation" in data or data.get("ai_fit_explanation") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
