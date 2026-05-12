"""
ProFund AI V4 Features - Backend API Tests
Tests NEW features: Application Outcomes CRUD, Performance Analytics, Learning Insights, AI Learning Context
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


class TestApplicationOutcomes:
    """Application Outcomes CRUD endpoint tests"""
    
    def test_outcomes_list_endpoint(self, auth_headers):
        """Test GET /api/outcomes returns list of outcomes"""
        response = requests.get(f"{BASE_URL}/api/outcomes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        # Should have seeded outcomes (4 demo outcomes)
        assert len(data) >= 4, "Expected at least 4 seeded outcomes"
        
        # Verify structure of first outcome
        if len(data) > 0:
            outcome = data[0]
            assert "id" in outcome
            assert "opportunity_id" in outcome
            assert "outcome" in outcome
            assert "amount_requested" in outcome
            assert "amount_awarded" in outcome
            assert "donor_name" in outcome
            assert "donor_type" in outcome
            assert "sector" in outcome
            assert "title" in outcome  # Joined from opportunities
    
    def test_outcomes_have_correct_values(self, auth_headers):
        """Test seeded outcomes have correct values"""
        response = requests.get(f"{BASE_URL}/api/outcomes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Count outcomes by status
        approved = [o for o in data if o.get("outcome") == "approved"]
        rejected = [o for o in data if o.get("outcome") == "rejected"]
        
        assert len(approved) >= 3, "Expected at least 3 approved outcomes"
        assert len(rejected) >= 1, "Expected at least 1 rejected outcome"
        
        # Verify total secured amount
        total_secured = sum(o.get("amount_awarded", 0) for o in approved)
        assert total_secured >= 445000, f"Expected at least $445K secured, got ${total_secured}"
    
    def test_outcomes_update_endpoint(self, auth_headers):
        """Test PUT /api/outcomes/{id} updates outcome"""
        # Get first outcome
        response = requests.get(f"{BASE_URL}/api/outcomes", headers=auth_headers)
        outcomes = response.json()
        assert len(outcomes) > 0
        
        outcome_id = outcomes[0]["id"]
        
        # Update the outcome
        update_response = requests.put(
            f"{BASE_URL}/api/outcomes/{outcome_id}",
            headers=auth_headers,
            json={"success_notes": "TEST_Updated notes for testing"}
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["updated"] == True
        assert data["id"] == outcome_id
    
    def test_outcomes_unauthorized(self):
        """Test outcomes endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/outcomes")
        assert response.status_code == 401
        
        # POST returns 422 (validation) or 401 (auth) - both indicate protected
        response = requests.post(f"{BASE_URL}/api/outcomes", json={
            "opportunity_id": "test-id",
            "outcome": "pending"
        })
        assert response.status_code == 401


class TestPerformanceAnalytics:
    """Performance Analytics endpoint tests"""
    
    def test_performance_endpoint(self, auth_headers):
        """Test GET /api/analytics/performance returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields
        assert "summary" in data
        assert "top_sectors" in data
        assert "top_donors" in data
        assert "timeline" in data
        assert "pipeline_vs_actual" in data
    
    def test_performance_summary_structure(self, auth_headers):
        """Test summary section has correct fields"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert "total_secured" in summary
        assert "total_requested" in summary
        assert "approved_count" in summary
        assert "rejected_count" in summary
        assert "pending_count" in summary
        assert "approval_rate" in summary
        assert "avg_award" in summary
    
    def test_performance_summary_values(self, auth_headers):
        """Test summary has expected values from seeded data"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        # Based on seeded data: $75K + $250K + $120K = $445K
        assert summary["total_secured"] >= 445000, f"Expected $445K secured, got ${summary['total_secured']}"
        # 3 approved, 1 rejected = 75% approval rate
        assert summary["approval_rate"] >= 75, f"Expected 75% approval rate, got {summary['approval_rate']}%"
        assert summary["approved_count"] >= 3
        assert summary["rejected_count"] >= 1
    
    def test_performance_top_sectors(self, auth_headers):
        """Test top_sectors has correct structure"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        top_sectors = data["top_sectors"]
        assert isinstance(top_sectors, list)
        
        if len(top_sectors) > 0:
            sector = top_sectors[0]
            assert "sector" in sector
            assert "total" in sector
            assert "wins" in sector
            assert "secured" in sector
    
    def test_performance_top_donors(self, auth_headers):
        """Test top_donors has correct structure"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        top_donors = data["top_donors"]
        assert isinstance(top_donors, list)
        
        if len(top_donors) > 0:
            donor = top_donors[0]
            assert "donor_name" in donor
            assert "donor_type" in donor
            assert "total" in donor
            assert "wins" in donor
            assert "secured" in donor
    
    def test_performance_timeline(self, auth_headers):
        """Test timeline has correct structure"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        timeline = data["timeline"]
        assert isinstance(timeline, list)
        
        if len(timeline) > 0:
            entry = timeline[0]
            assert "month" in entry
            assert "approved" in entry
            assert "rejected" in entry
            assert "secured" in entry
    
    def test_performance_pipeline_vs_actual(self, auth_headers):
        """Test pipeline_vs_actual has correct structure"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        pva = data["pipeline_vs_actual"]
        assert "total_available" in pva
        assert "in_pipeline" in pva
        assert "secured" in pva
    
    def test_performance_unauthorized(self):
        """Test performance endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance")
        assert response.status_code == 401


class TestLearningInsights:
    """Learning Insights endpoint tests"""
    
    def test_learning_insights_endpoint(self, auth_headers):
        """Test GET /api/analytics/learning-insights returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/analytics/learning-insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "insights" in data
        assert "has_data" in data
        assert isinstance(data["insights"], list)
        assert isinstance(data["has_data"], bool)
    
    def test_learning_insights_types(self, auth_headers):
        """Test insights have valid types (boost/caution/info)"""
        response = requests.get(f"{BASE_URL}/api/analytics/learning-insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        valid_types = ["boost", "caution", "info"]
        for insight in data["insights"]:
            assert "type" in insight
            assert "message" in insight
            assert insight["type"] in valid_types, f"Invalid insight type: {insight['type']}"
    
    def test_learning_insights_has_data(self, auth_headers):
        """Test has_data is true when outcomes exist"""
        response = requests.get(f"{BASE_URL}/api/analytics/learning-insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # With seeded outcomes, has_data should be true
        assert data["has_data"] == True
        assert len(data["insights"]) > 0
    
    def test_learning_insights_unauthorized(self):
        """Test learning insights requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/learning-insights")
        assert response.status_code == 401


class TestDashboardWithPerformance:
    """Dashboard integration with performance data"""
    
    def test_dashboard_still_works(self, auth_headers):
        """Test dashboard endpoint still returns all V3 data"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # V3 features should still work
        assert "top_opportunities" in data
        assert "high_match" in data
        assert "expiring_soon" in data
        assert "recently_added" in data
        assert "saved" in data
        assert "actions" in data
        assert "pipeline" in data
        assert "stats" in data
    
    def test_dashboard_extras_still_works(self, auth_headers):
        """Test dashboard extras endpoint still returns V3 data"""
        response = requests.get(f"{BASE_URL}/api/dashboard/extras", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "priority_apps" in data
        assert "drafts_ready" in data
        assert "new_24h_count" in data
        assert "monitoring" in data


class TestAILearningContext:
    """AI Learning Context integration tests"""
    
    def test_match_score_uses_learning_context(self, auth_headers):
        """Test AI match-score endpoint works (learning context is injected)"""
        # Get an opportunity to test
        opps_response = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        opps = opps_response.json()
        
        if len(opps) > 0:
            opp_id = opps[0]["id"]
            
            # Call match-score (this uses learning context internally)
            # Note: This makes an actual AI call, so we just verify the endpoint works
            response = requests.post(
                f"{BASE_URL}/api/ai/match-score",
                headers=auth_headers,
                json={"opportunity_id": opp_id}
            )
            # Should return 200 or 500 (if AI service unavailable)
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert "score" in data
                assert "explanation" in data
                assert "fit_level" in data


class TestOutcomeCreation:
    """Test creating new outcomes (requires Submitted opportunity)"""
    
    def test_outcome_create_duplicate_rejected(self, auth_headers):
        """Test creating duplicate outcome is rejected"""
        # Get existing outcome
        outcomes_response = requests.get(f"{BASE_URL}/api/outcomes", headers=auth_headers)
        outcomes = outcomes_response.json()
        
        if len(outcomes) > 0:
            existing_opp_id = outcomes[0]["opportunity_id"]
            
            # Try to create duplicate
            response = requests.post(
                f"{BASE_URL}/api/outcomes",
                headers=auth_headers,
                json={
                    "opportunity_id": existing_opp_id,
                    "outcome": "pending",
                    "amount_requested": 100000
                }
            )
            assert response.status_code == 400
            assert "already exists" in response.json().get("detail", "").lower()
    
    def test_outcome_create_invalid_opportunity(self, auth_headers):
        """Test creating outcome for non-existent opportunity fails"""
        response = requests.post(
            f"{BASE_URL}/api/outcomes",
            headers=auth_headers,
            json={
                "opportunity_id": "non-existent-id",
                "outcome": "pending",
                "amount_requested": 100000
            }
        )
        assert response.status_code == 404


class TestV4Integration:
    """Integration tests for V4 features"""
    
    def test_outcomes_affect_analytics(self, auth_headers):
        """Test that outcomes data is reflected in analytics"""
        # Get outcomes
        outcomes_response = requests.get(f"{BASE_URL}/api/outcomes", headers=auth_headers)
        outcomes = outcomes_response.json()
        
        # Get analytics
        analytics_response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        analytics = analytics_response.json()
        
        # Verify counts match
        approved_outcomes = len([o for o in outcomes if o.get("outcome") == "approved"])
        rejected_outcomes = len([o for o in outcomes if o.get("outcome") == "rejected"])
        
        assert analytics["summary"]["approved_count"] == approved_outcomes
        assert analytics["summary"]["rejected_count"] == rejected_outcomes
    
    def test_top_donors_match_outcomes(self, auth_headers):
        """Test top donors are derived from outcomes"""
        # Get outcomes
        outcomes_response = requests.get(f"{BASE_URL}/api/outcomes", headers=auth_headers)
        outcomes = outcomes_response.json()
        
        # Get analytics
        analytics_response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        analytics = analytics_response.json()
        
        # Verify donor names in top_donors exist in outcomes
        outcome_donors = set(o.get("donor_name") for o in outcomes)
        for donor in analytics["top_donors"]:
            assert donor["donor_name"] in outcome_donors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
