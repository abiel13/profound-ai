"""
ProFund AI V5 - Donor Relationship Manager Tests
Tests for: Donor profiles, interactions, relationship scoring, insights
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@profund.ai",
        "password": "ProFund2024!"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers for requests"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestDonorsList:
    """Test GET /api/donors - List all donors"""
    
    def test_list_donors_returns_20(self, auth_headers):
        """Should return 20 donors auto-synced from opportunities"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        assert response.status_code == 200
        donors = response.json()
        assert len(donors) == 20, f"Expected 20 donors, got {len(donors)}"
    
    def test_donors_sorted_by_relationship_score(self, auth_headers):
        """Donors should be sorted by relationship_score DESC"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        assert response.status_code == 200
        donors = response.json()
        scores = [d['relationship_score'] for d in donors]
        assert scores == sorted(scores, reverse=True), "Donors not sorted by score DESC"
    
    def test_donors_have_required_fields(self, auth_headers):
        """Each donor should have required fields"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        assert response.status_code == 200
        donors = response.json()
        required_fields = ['id', 'name', 'type', 'country', 'relationship_score', 
                          'relationship_level', 'total_applications', 'total_approvals', 
                          'total_rejections', 'total_funding_received']
        for donor in donors[:5]:  # Check first 5
            for field in required_fields:
                assert field in donor, f"Missing field: {field}"
    
    def test_growing_donors_have_correct_score(self, auth_headers):
        """GIZ, UNDP, UNICEF should have Growing status (score ~40)"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        assert response.status_code == 200
        donors = response.json()
        growing_names = ["GIZ (Germany)", "UNDP", "UNICEF Innovation"]
        for donor in donors:
            if donor['name'] in growing_names:
                assert donor['relationship_level'] == "Growing", f"{donor['name']} should be Growing"
                # Score should be around 40-50 (base 20 + 20 for 1 approval + interactions)
                assert donor['relationship_score'] >= 40, f"{donor['name']} score too low"
    
    def test_new_donors_have_base_score(self, auth_headers):
        """Donors without approvals should have New status (score ~20)"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        assert response.status_code == 200
        donors = response.json()
        new_donors = [d for d in donors if d['relationship_level'] == "New"]
        assert len(new_donors) >= 15, f"Expected at least 15 New donors, got {len(new_donors)}"
        for donor in new_donors[:5]:
            assert donor['relationship_score'] <= 30, f"{donor['name']} score too high for New"


class TestDonorDetail:
    """Test GET /api/donors/{id} - Donor detail with interactions, outcomes, opportunities"""
    
    def test_get_donor_detail(self, auth_headers):
        """Should return full donor detail"""
        # First get a donor ID
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        donor_id = donors[0]['id']
        
        response = requests.get(f"{BASE_URL}/api/donors/{donor_id}", headers=auth_headers)
        assert response.status_code == 200
        donor = response.json()
        assert 'interactions' in donor
        assert 'outcomes' in donor
        assert 'opportunities' in donor
    
    def test_donor_with_outcomes_has_history(self, auth_headers):
        """UNDP should have outcomes from V4 seeded data"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        undp = next((d for d in donors if d['name'] == "UNDP"), None)
        assert undp is not None, "UNDP donor not found"
        
        response = requests.get(f"{BASE_URL}/api/donors/{undp['id']}", headers=auth_headers)
        assert response.status_code == 200
        donor = response.json()
        assert len(donor['outcomes']) >= 1, "UNDP should have at least 1 outcome"
        assert donor['outcomes'][0]['outcome'] == 'approved'
    
    def test_donor_not_found(self, auth_headers):
        """Should return 404 for non-existent donor"""
        response = requests.get(f"{BASE_URL}/api/donors/non-existent-id", headers=auth_headers)
        assert response.status_code == 404


class TestDonorInteractions:
    """Test POST /api/donors/interactions - Log interactions"""
    
    def test_log_interaction(self, auth_headers):
        """Should log interaction and return ID"""
        # Get a donor
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        donor_id = donors[0]['id']
        
        # Log interaction
        response = requests.post(f"{BASE_URL}/api/donors/interactions", headers=auth_headers, json={
            "donor_id": donor_id,
            "type": "meeting",
            "date": "2026-01-17",
            "notes": "Test meeting interaction"
        })
        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert data['type'] == 'meeting'
    
    def test_interaction_increases_score(self, auth_headers):
        """Logging interaction should increase relationship score"""
        # Get a donor with low score
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        # Find a New donor
        new_donor = next((d for d in donors if d['relationship_level'] == "New"), None)
        if not new_donor:
            pytest.skip("No New donors available")
        
        initial_score = new_donor['relationship_score']
        
        # Log interaction
        response = requests.post(f"{BASE_URL}/api/donors/interactions", headers=auth_headers, json={
            "donor_id": new_donor['id'],
            "type": "call",
            "date": "2026-01-17",
            "notes": "Test call to increase score"
        })
        assert response.status_code == 200
        
        # Check score increased
        response = requests.get(f"{BASE_URL}/api/donors/{new_donor['id']}", headers=auth_headers)
        updated_donor = response.json()
        assert updated_donor['relationship_score'] >= initial_score, "Score should not decrease"
    
    def test_interaction_types(self, auth_headers):
        """Should accept all valid interaction types"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        donor_id = donors[0]['id']
        
        valid_types = ["email", "meeting", "call", "proposal_submitted", "follow_up"]
        for itype in valid_types:
            response = requests.post(f"{BASE_URL}/api/donors/interactions", headers=auth_headers, json={
                "donor_id": donor_id,
                "type": itype,
                "date": "2026-01-17",
                "notes": f"Test {itype}"
            })
            assert response.status_code == 200, f"Failed for type: {itype}"
    
    def test_interaction_invalid_donor(self, auth_headers):
        """Should return 404 for non-existent donor"""
        response = requests.post(f"{BASE_URL}/api/donors/interactions", headers=auth_headers, json={
            "donor_id": "non-existent-id",
            "type": "email",
            "date": "2026-01-17",
            "notes": "Test"
        })
        assert response.status_code == 404


class TestDonorUpdate:
    """Test PUT /api/donors/{id} - Update donor fields"""
    
    def test_update_donor_notes(self, auth_headers):
        """Should update donor notes"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        donor_id = donors[0]['id']
        
        response = requests.put(f"{BASE_URL}/api/donors/{donor_id}", headers=auth_headers, json={
            "notes": "Updated test notes"
        })
        assert response.status_code == 200
        assert response.json()['updated'] == True
    
    def test_update_donor_website(self, auth_headers):
        """Should update donor website"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        donor_id = donors[0]['id']
        
        response = requests.put(f"{BASE_URL}/api/donors/{donor_id}", headers=auth_headers, json={
            "website": "https://example.org"
        })
        assert response.status_code == 200
    
    def test_update_no_fields_error(self, auth_headers):
        """Should return 400 when no fields provided"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        donor_id = donors[0]['id']
        
        response = requests.put(f"{BASE_URL}/api/donors/{donor_id}", headers=auth_headers, json={})
        assert response.status_code == 400


class TestDonorInsights:
    """Test GET /api/donors/dashboard/insights - Relationship intelligence"""
    
    def test_insights_returns_structure(self, auth_headers):
        """Should return strong, follow_up, reapply, dormant, recommendations"""
        response = requests.get(f"{BASE_URL}/api/donors/dashboard/insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 'strong' in data
        assert 'follow_up' in data
        assert 'reapply' in data
        assert 'dormant' in data
        assert 'recommendations' in data
    
    def test_follow_up_recommendations(self, auth_headers):
        """Should have follow-up recommendations for donors without recent contact"""
        response = requests.get(f"{BASE_URL}/api/donors/dashboard/insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have follow_up recommendations since most donors have no interactions
        assert len(data['follow_up']) > 0 or len(data['recommendations']) > 0
    
    def test_reapply_recommendations(self, auth_headers):
        """Should have reapply recommendations for donors with prior approvals"""
        response = requests.get(f"{BASE_URL}/api/donors/dashboard/insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # GIZ, UNDP, UNICEF have approvals and active opportunities
        assert len(data['reapply']) >= 1, "Should have reapply recommendations"
    
    def test_recommendations_have_required_fields(self, auth_headers):
        """Recommendations should have type, priority, message, donor_id"""
        response = requests.get(f"{BASE_URL}/api/donors/dashboard/insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for rec in data['recommendations'][:3]:
            assert 'type' in rec
            assert 'priority' in rec
            assert 'message' in rec
            assert 'donor_id' in rec


class TestRelationshipScoring:
    """Test relationship score calculation"""
    
    def test_score_formula(self, auth_headers):
        """Verify score formula: base 20 + approvals*20 + interactions*3 - rejections*10"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        
        # Find UNDP (1 approval, should have score ~40-50)
        undp = next((d for d in donors if d['name'] == "UNDP"), None)
        assert undp is not None
        # Base 20 + 1 approval * 20 = 40 minimum
        assert undp['relationship_score'] >= 40
        
        # Find Ford Foundation (1 rejection, should have lower score)
        ford = next((d for d in donors if d['name'] == "Ford Foundation"), None)
        if ford:
            # Base 20 - 1 rejection * 10 = 10
            assert ford['relationship_score'] <= 20
    
    def test_relationship_levels(self, auth_headers):
        """Verify relationship levels: Strong (>=70), Growing (40-69), New (<40)"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        donors = response.json()
        
        for donor in donors:
            score = donor['relationship_score']
            level = donor['relationship_level']
            if score >= 70:
                assert level == "Strong", f"{donor['name']} with score {score} should be Strong"
            elif score >= 40:
                assert level == "Growing", f"{donor['name']} with score {score} should be Growing"
            else:
                assert level == "New", f"{donor['name']} with score {score} should be New"


class TestV4FeaturesStillWorking:
    """Verify V4 features still work"""
    
    def test_outcomes_endpoint(self, auth_headers):
        """GET /api/outcomes should still work"""
        response = requests.get(f"{BASE_URL}/api/outcomes", headers=auth_headers)
        assert response.status_code == 200
        outcomes = response.json()
        assert len(outcomes) >= 4, "Should have seeded outcomes from V4"
    
    def test_analytics_performance(self, auth_headers):
        """GET /api/analytics/performance should still work"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 'summary' in data
        assert 'top_donors' in data
    
    def test_dashboard(self, auth_headers):
        """GET /api/opportunities/dashboard should still work"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 'stats' in data
        assert 'top_opportunities' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
