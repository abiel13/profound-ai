"""
ProFund AI V8 - Weekly Intelligence Reports API Tests
Tests: Report generation, listing, retrieval, PDF export
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://worldwide-grants-1.preview.emergentagent.com').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "admin@profund.ai"
        print(f"✓ Login successful - user: {data['user']['email']}")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@profund.ai",
        "password": "ProFund2024!"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get auth headers"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestReportsAPI:
    """V8 Weekly Intelligence Reports API tests"""
    
    def test_reports_list_empty_or_populated(self, auth_headers):
        """Test GET /api/reports returns list"""
        response = requests.get(f"{BASE_URL}/api/reports", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/reports - {len(data)} reports found")
    
    def test_reports_latest_returns_null_or_report(self, auth_headers):
        """Test GET /api/reports/latest returns null or report"""
        response = requests.get(f"{BASE_URL}/api/reports/latest", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Can be null (no reports) or a report object
        if data is not None:
            assert "id" in data
            assert "week_label" in data
            assert "executive_summary" in data
            print(f"✓ GET /api/reports/latest - report found: {data['week_label']}")
        else:
            print("✓ GET /api/reports/latest - no reports yet (null)")
    
    def test_report_generate(self, auth_headers):
        """Test POST /api/reports/generate creates AI-powered report with all 7 sections"""
        response = requests.post(f"{BASE_URL}/api/reports/generate", headers=auth_headers, timeout=120)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields
        assert "id" in data
        assert "week_label" in data
        assert "created_at" in data
        
        # Verify all 7 sections exist
        required_sections = [
            "executive_summary",
            "top_opportunities", 
            "urgent_actions",
            "relationship_health",
            "pipeline_overview",
            "performance_insights",
            "ai_recommendations"
        ]
        for section in required_sections:
            assert section in data, f"Missing section: {section}"
            assert data[section], f"Section {section} is empty"
        
        print(f"✓ POST /api/reports/generate - report created: {data['id'][:8]}...")
        print(f"  Week: {data['week_label']}")
        print(f"  Sections: {', '.join(required_sections)}")
        
        # Store report ID for subsequent tests
        pytest.report_id = data['id']
        return data['id']
    
    def test_report_get_by_id(self, auth_headers):
        """Test GET /api/reports/{id} returns full report"""
        # Get latest report ID
        list_response = requests.get(f"{BASE_URL}/api/reports", headers=auth_headers)
        reports = list_response.json()
        if not reports:
            pytest.skip("No reports to test")
        
        report_id = reports[0]['id']
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all 7 sections
        assert "executive_summary" in data
        assert "top_opportunities" in data
        assert "urgent_actions" in data
        assert "relationship_health" in data
        assert "pipeline_overview" in data
        assert "performance_insights" in data
        assert "ai_recommendations" in data
        assert "raw_data" in data
        
        # Verify raw_data contains metrics
        raw_data = data.get('raw_data', {})
        assert "pipeline_total" in raw_data
        assert "total_secured" in raw_data
        assert "approval_rate" in raw_data
        
        print(f"✓ GET /api/reports/{report_id[:8]}... - all 7 sections present")
        print(f"  Pipeline: ${raw_data.get('pipeline_total', 0):,.0f}")
        print(f"  Secured: ${raw_data.get('total_secured', 0):,.0f}")
        print(f"  Rate: {raw_data.get('approval_rate', 0)}%")
    
    def test_report_pdf_export(self, auth_headers):
        """Test GET /api/reports/{id}/pdf returns valid PDF"""
        # Get latest report ID
        list_response = requests.get(f"{BASE_URL}/api/reports", headers=auth_headers)
        reports = list_response.json()
        if not reports:
            pytest.skip("No reports to test")
        
        report_id = reports[0]['id']
        response = requests.get(f"{BASE_URL}/api/reports/{report_id}/pdf", headers=auth_headers)
        assert response.status_code == 200
        assert response.headers.get('content-type') == 'application/pdf'
        
        # Verify PDF content starts with %PDF
        content = response.content
        assert content[:4] == b'%PDF', "Response is not a valid PDF"
        assert len(content) > 1000, "PDF seems too small"
        
        print(f"✓ GET /api/reports/{report_id[:8]}../pdf - valid PDF ({len(content)} bytes)")
    
    def test_report_not_found(self, auth_headers):
        """Test GET /api/reports/{id} returns 404 for invalid ID"""
        response = requests.get(f"{BASE_URL}/api/reports/invalid-id-12345", headers=auth_headers)
        assert response.status_code == 404
        print("✓ GET /api/reports/invalid-id - returns 404")


class TestV7Regression:
    """V7 Command Center regression tests"""
    
    def test_calendar_events(self, auth_headers):
        """Test calendar events API still works"""
        response = requests.get(f"{BASE_URL}/api/calendar/events", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # API returns {events: [], range: {}}
        assert "events" in data
        assert isinstance(data["events"], list)
        print(f"✓ GET /api/calendar/events - {len(data['events'])} events")
    
    def test_week_summary(self, auth_headers):
        """Test week summary API still works"""
        response = requests.get(f"{BASE_URL}/api/calendar/week-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "deadlines_this_week" in data
        assert "in_progress" in data
        print(f"✓ GET /api/calendar/week-summary - in_progress: {data['in_progress']}")


class TestV6Regression:
    """V6 Follow-ups and Donors regression tests"""
    
    def test_follow_ups(self, auth_headers):
        """Test follow-ups API still works"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/follow-ups - {len(data)} follow-ups")
    
    def test_donors(self, auth_headers):
        """Test donors API still works"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/donors - {len(data)} donors")


class TestV5Regression:
    """V5 Performance Analytics regression tests"""
    
    def test_analytics_performance(self, auth_headers):
        """Test analytics performance API still works"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # API returns {summary: {approval_rate, ...}, ...}
        assert "summary" in data
        assert "approval_rate" in data["summary"]
        print(f"✓ GET /api/analytics/performance - rate: {data['summary']['approval_rate']}%")


class TestV4Regression:
    """V4 Workspace regression tests"""
    
    def test_queue(self, auth_headers):
        """Test smart queue API still works"""
        response = requests.get(f"{BASE_URL}/api/queue", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ GET /api/queue - {len(data['items'])} items")


class TestV1V3Regression:
    """V1-V3 Core features regression tests"""
    
    def test_dashboard(self, auth_headers):
        """Test dashboard API still works"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "top_opportunities" in data
        print(f"✓ GET /api/opportunities/dashboard - {data['stats']['total_opportunities']} opportunities")
    
    def test_opportunities(self, auth_headers):
        """Test opportunities API still works"""
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/opportunities - {len(data)} opportunities")
    
    def test_saved(self, auth_headers):
        """Test saved API still works"""
        response = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/saved - {len(data)} saved")
    
    def test_proposals(self, auth_headers):
        """Test proposals API still works"""
        response = requests.get(f"{BASE_URL}/api/proposals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/proposals - {len(data)} proposals")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
