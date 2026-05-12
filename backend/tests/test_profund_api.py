"""
ProFund AI Backend API Tests
Tests all API endpoints: auth, opportunities, saved, profile, sources, deadlines, proposals, filters
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@profund.ai"
TEST_PASSWORD = "ProFund2024!"


class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["email"] == TEST_EMAIL
        assert data["user"]["role"] == "admin"
        assert len(data["token"]) > 0
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_auth_me_with_token(self):
        """Test /auth/me endpoint with valid token"""
        # First login
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = login_res.json()["token"]
        
        # Get current user
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_EMAIL
    
    def test_auth_me_without_token(self):
        """Test /auth/me endpoint without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
    
    def test_logout(self):
        """Test logout endpoint"""
        response = requests.post(f"{BASE_URL}/api/auth/logout")
        assert response.status_code == 200


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


class TestDashboard:
    """Dashboard endpoint tests"""
    
    def test_dashboard_data(self, auth_headers):
        """Test dashboard returns all required sections"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check all required sections exist
        assert "high_match" in data, "high_match section missing"
        assert "expiring_soon" in data, "expiring_soon section missing"
        assert "recently_added" in data, "recently_added section missing"
        assert "saved" in data, "saved section missing"
        assert "stats" in data, "stats section missing"
        
        # Check stats structure
        stats = data["stats"]
        assert "total_opportunities" in stats
        assert "saved_count" in stats
        assert "expiring_soon_count" in stats
        
        # Verify we have 20 opportunities seeded
        assert stats["total_opportunities"] == 20, f"Expected 20 opportunities, got {stats['total_opportunities']}"
    
    def test_dashboard_unauthorized(self):
        """Test dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard")
        assert response.status_code == 401


class TestOpportunities:
    """Opportunities CRUD tests"""
    
    def test_list_opportunities(self, auth_headers):
        """Test listing all opportunities"""
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 20, f"Expected 20 opportunities, got {len(data)}"
        
        # Check opportunity structure
        opp = data[0]
        assert "id" in opp
        assert "title" in opp
        assert "donor_name" in opp
        assert "funding_min" in opp
        assert "funding_max" in opp
        assert "deadline" in opp
    
    def test_search_opportunities(self, auth_headers):
        """Test searching opportunities"""
        response = requests.get(f"{BASE_URL}/api/opportunities?search=youth", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should find opportunities with "youth" in title/description
        assert len(data) > 0, "Search should return results for 'youth'"
    
    def test_filter_by_sector(self, auth_headers):
        """Test filtering by sector"""
        response = requests.get(f"{BASE_URL}/api/opportunities?sector=Education", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for opp in data:
            assert opp["sector"] == "Education"
    
    def test_filter_by_donor_type(self, auth_headers):
        """Test filtering by donor type"""
        response = requests.get(f"{BASE_URL}/api/opportunities?donor_type=Foundation", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for opp in data:
            assert opp["donor_type"] == "Foundation"
    
    def test_sort_by_deadline(self, auth_headers):
        """Test sorting by deadline"""
        response = requests.get(f"{BASE_URL}/api/opportunities?sort_by=deadline", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Verify sorted by deadline ascending
        for i in range(len(data) - 1):
            assert data[i]["deadline"] <= data[i+1]["deadline"]
    
    def test_sort_by_funding(self, auth_headers):
        """Test sorting by funding"""
        response = requests.get(f"{BASE_URL}/api/opportunities?sort_by=funding", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Verify sorted by funding_max descending
        for i in range(len(data) - 1):
            assert data[i]["funding_max"] >= data[i+1]["funding_max"]
    
    def test_get_single_opportunity(self, auth_headers):
        """Test getting a single opportunity"""
        # First get list to get an ID
        list_res = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        opp_id = list_res.json()[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/opportunities/{opp_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == opp_id
        assert "is_saved" in data
    
    def test_get_nonexistent_opportunity(self, auth_headers):
        """Test getting a non-existent opportunity"""
        response = requests.get(f"{BASE_URL}/api/opportunities/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404


class TestSavedOpportunities:
    """Saved opportunities CRUD tests"""
    
    def test_save_and_list_opportunity(self, auth_headers):
        """Test saving an opportunity and verifying it appears in saved list"""
        # Get an opportunity to save
        list_res = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        opp_id = list_res.json()[0]["id"]
        
        # Save it
        save_res = requests.post(f"{BASE_URL}/api/saved", json={
            "opportunity_id": opp_id
        }, headers=auth_headers)
        
        # May already be saved from previous test runs
        if save_res.status_code == 400:
            # Already saved, just verify it's in the list
            pass
        else:
            assert save_res.status_code == 200
            save_data = save_res.json()
            assert save_data["opportunity_id"] == opp_id
            assert save_data["status"] == "New"
        
        # Verify it appears in saved list
        saved_res = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        assert saved_res.status_code == 200
        saved_list = saved_res.json()
        assert any(s["id"] == opp_id for s in saved_list), "Saved opportunity not in list"
    
    def test_update_saved_status(self, auth_headers):
        """Test updating saved opportunity status"""
        # Get saved list
        saved_res = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        saved_list = saved_res.json()
        
        if len(saved_list) == 0:
            pytest.skip("No saved opportunities to update")
        
        saved_id = saved_list[0]["saved_id"]
        
        # Update status
        update_res = requests.put(f"{BASE_URL}/api/saved/{saved_id}", json={
            "status": "Reviewing"
        }, headers=auth_headers)
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "Reviewing"
        
        # Verify persistence
        saved_res2 = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        updated = next((s for s in saved_res2.json() if s["saved_id"] == saved_id), None)
        assert updated is not None
        assert updated["status"] == "Reviewing"
    
    def test_update_invalid_status(self, auth_headers):
        """Test updating with invalid status"""
        saved_res = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        saved_list = saved_res.json()
        
        if len(saved_list) == 0:
            pytest.skip("No saved opportunities to update")
        
        saved_id = saved_list[0]["saved_id"]
        
        update_res = requests.put(f"{BASE_URL}/api/saved/{saved_id}", json={
            "status": "InvalidStatus"
        }, headers=auth_headers)
        assert update_res.status_code == 400


class TestProfile:
    """Organization profile tests"""
    
    def test_get_profile(self, auth_headers):
        """Test getting organization profile"""
        response = requests.get(f"{BASE_URL}/api/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check default profile data
        assert data["name"] == "Pro Youth Foundation"
        assert data["country"] == "Namibia"
        assert "mission" in data
        assert "focus_sectors" in data
        assert "beneficiaries" in data
        assert isinstance(data["focus_sectors"], list)
        assert isinstance(data["beneficiaries"], list)
    
    def test_update_profile(self, auth_headers):
        """Test updating organization profile"""
        # Update profile
        update_res = requests.put(f"{BASE_URL}/api/profile", json={
            "name": "Pro Youth Foundation Updated",
            "country": "Namibia"
        }, headers=auth_headers)
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Pro Youth Foundation Updated"
        
        # Verify persistence
        get_res = requests.get(f"{BASE_URL}/api/profile", headers=auth_headers)
        assert get_res.json()["name"] == "Pro Youth Foundation Updated"
        
        # Restore original
        requests.put(f"{BASE_URL}/api/profile", json={
            "name": "Pro Youth Foundation"
        }, headers=auth_headers)


class TestSources:
    """Sources CRUD tests"""
    
    def test_list_sources(self, auth_headers):
        """Test listing sources"""
        response = requests.get(f"{BASE_URL}/api/sources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 10, f"Expected 10 pre-loaded sources, got {len(data)}"
    
    def test_create_source(self, auth_headers):
        """Test creating a new source"""
        response = requests.post(f"{BASE_URL}/api/sources", json={
            "name": "TEST_New Source",
            "url": "https://test.example.com",
            "type": "Foundation",
            "description": "Test source description"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_New Source"
        assert "id" in data
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/sources/{data['id']}", headers=auth_headers)
    
    def test_update_source(self, auth_headers):
        """Test updating a source"""
        # Create a source first
        create_res = requests.post(f"{BASE_URL}/api/sources", json={
            "name": "TEST_Source to Update",
            "type": "Government"
        }, headers=auth_headers)
        source_id = create_res.json()["id"]
        
        # Update it
        update_res = requests.put(f"{BASE_URL}/api/sources/{source_id}", json={
            "name": "TEST_Updated Source Name"
        }, headers=auth_headers)
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "TEST_Updated Source Name"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/sources/{source_id}", headers=auth_headers)
    
    def test_delete_source(self, auth_headers):
        """Test deleting a source"""
        # Create a source first
        create_res = requests.post(f"{BASE_URL}/api/sources", json={
            "name": "TEST_Source to Delete"
        }, headers=auth_headers)
        source_id = create_res.json()["id"]
        
        # Delete it
        delete_res = requests.delete(f"{BASE_URL}/api/sources/{source_id}", headers=auth_headers)
        assert delete_res.status_code == 200
        
        # Verify it's gone
        list_res = requests.get(f"{BASE_URL}/api/sources", headers=auth_headers)
        assert not any(s["id"] == source_id for s in list_res.json())


class TestDeadlines:
    """Deadlines endpoint tests"""
    
    def test_get_deadlines(self, auth_headers):
        """Test getting deadlines"""
        response = requests.get(f"{BASE_URL}/api/deadlines", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Should return opportunities with future deadlines, sorted by deadline
        if len(data) > 1:
            for i in range(len(data) - 1):
                assert data[i]["deadline"] <= data[i+1]["deadline"]


class TestFilters:
    """Filters endpoint tests"""
    
    def test_get_filters(self, auth_headers):
        """Test getting filter options"""
        response = requests.get(f"{BASE_URL}/api/filters", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "sectors" in data
        assert "donor_types" in data
        assert isinstance(data["sectors"], list)
        assert isinstance(data["donor_types"], list)
        
        # Should have multiple sectors and donor types from seeded data
        assert len(data["sectors"]) > 0, "No sectors found"
        assert len(data["donor_types"]) > 0, "No donor types found"


class TestProposals:
    """Proposals endpoint tests"""
    
    def test_list_proposals(self, auth_headers):
        """Test listing proposals"""
        response = requests.get(f"{BASE_URL}/api/proposals", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_delete_nonexistent_proposal(self, auth_headers):
        """Test deleting non-existent proposal"""
        response = requests.delete(f"{BASE_URL}/api/proposals/nonexistent-id", headers=auth_headers)
        # Should return 200 even if not found (idempotent delete)
        assert response.status_code == 200


class TestAIEndpoints:
    """AI endpoint tests - just verify endpoints respond (actual AI calls may take time)"""
    
    def test_ai_summarize_endpoint_exists(self, auth_headers):
        """Test AI summarize endpoint exists and validates input"""
        response = requests.post(f"{BASE_URL}/api/ai/summarize", json={
            "opportunity_id": "nonexistent"
        }, headers=auth_headers)
        # Should return 404 for non-existent opportunity
        assert response.status_code == 404
    
    def test_ai_match_endpoint_exists(self, auth_headers):
        """Test AI match score endpoint exists and validates input"""
        response = requests.post(f"{BASE_URL}/api/ai/match-score", json={
            "opportunity_id": "nonexistent"
        }, headers=auth_headers)
        assert response.status_code == 404
    
    def test_ai_fit_endpoint_exists(self, auth_headers):
        """Test AI fit explanation endpoint exists and validates input"""
        response = requests.post(f"{BASE_URL}/api/ai/fit-explanation", json={
            "opportunity_id": "nonexistent"
        }, headers=auth_headers)
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
