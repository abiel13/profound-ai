"""
ProFund AI V7 - Command Center Calendar API Tests
Tests calendar events aggregation, week summary, and V1-V6 feature regression
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "admin@profund.ai"
        print(f"✓ Login successful - user: {data['user']['name']}")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for all tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@profund.ai",
        "password": "ProFund2024!"
    })
    if response.status_code != 200:
        pytest.skip("Authentication failed")
    return response.json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    """Get auth headers"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestCalendarEventsAPI:
    """V7 Calendar Events API Tests"""
    
    def test_get_calendar_events(self, auth_headers):
        """GET /api/calendar/events returns events list"""
        response = requests.get(f"{BASE_URL}/api/calendar/events", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "events" in data
        assert "range" in data
        print(f"✓ Calendar events returned: {len(data['events'])} events")
    
    def test_calendar_events_count(self, auth_headers):
        """Verify 21 events (19 deadlines + 2 interactions)"""
        response = requests.get(f"{BASE_URL}/api/calendar/events", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        events = data["events"]
        assert len(events) == 21, f"Expected 21 events, got {len(events)}"
        
        # Count by type
        deadlines = [e for e in events if e["type"] == "deadline"]
        interactions = [e for e in events if e["type"] == "interaction"]
        
        assert len(deadlines) == 19, f"Expected 19 deadlines, got {len(deadlines)}"
        assert len(interactions) == 2, f"Expected 2 interactions, got {len(interactions)}"
        print(f"✓ Event counts correct: {len(deadlines)} deadlines, {len(interactions)} interactions")
    
    def test_calendar_event_structure(self, auth_headers):
        """Verify event structure has required fields"""
        response = requests.get(f"{BASE_URL}/api/calendar/events", headers=auth_headers)
        assert response.status_code == 200
        events = response.json()["events"]
        
        for event in events[:5]:  # Check first 5
            assert "id" in event
            assert "date" in event
            assert "type" in event
            assert "title" in event
            assert "urgency" in event
            assert "meta" in event
            assert "link" in event
        print("✓ Event structure validated")
    
    def test_calendar_event_types(self, auth_headers):
        """Verify event types are valid"""
        response = requests.get(f"{BASE_URL}/api/calendar/events", headers=auth_headers)
        assert response.status_code == 200
        events = response.json()["events"]
        
        valid_types = {"deadline", "follow_up", "submission", "decision", "interaction"}
        for event in events:
            assert event["type"] in valid_types, f"Invalid type: {event['type']}"
        print("✓ All event types valid")
    
    def test_calendar_events_sorted_by_date(self, auth_headers):
        """Verify events are sorted by date"""
        response = requests.get(f"{BASE_URL}/api/calendar/events", headers=auth_headers)
        assert response.status_code == 200
        events = response.json()["events"]
        
        dates = [e["date"] for e in events]
        assert dates == sorted(dates), "Events not sorted by date"
        print("✓ Events sorted by date")
    
    def test_calendar_deadline_urgency(self, auth_headers):
        """Verify deadline urgency levels"""
        response = requests.get(f"{BASE_URL}/api/calendar/events", headers=auth_headers)
        assert response.status_code == 200
        events = response.json()["events"]
        
        deadlines = [e for e in events if e["type"] == "deadline"]
        valid_urgencies = {"critical", "high", "medium"}
        for d in deadlines:
            assert d["urgency"] in valid_urgencies, f"Invalid urgency: {d['urgency']}"
        print("✓ Deadline urgency levels valid")
    
    def test_calendar_events_with_month_filter(self, auth_headers):
        """Test month filter parameter"""
        response = requests.get(f"{BASE_URL}/api/calendar/events?month=2026-05", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        # May 2026 should have some deadlines
        print(f"✓ Month filter works: {len(data['events'])} events in May 2026")


class TestWeekSummaryAPI:
    """V7 Week Summary API Tests"""
    
    def test_get_week_summary(self, auth_headers):
        """GET /api/calendar/week-summary returns summary"""
        response = requests.get(f"{BASE_URL}/api/calendar/week-summary", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "deadlines_this_week" in data
        assert "deadlines_next_week" in data
        assert "pending_followups" in data
        assert "in_progress" in data
        print(f"✓ Week summary returned: {data}")
    
    def test_week_summary_in_progress_count(self, auth_headers):
        """Verify in_progress count is 11"""
        response = requests.get(f"{BASE_URL}/api/calendar/week-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["in_progress"] == 11, f"Expected 11 in progress, got {data['in_progress']}"
        print(f"✓ In progress count correct: {data['in_progress']}")
    
    def test_week_summary_data_types(self, auth_headers):
        """Verify data types in week summary"""
        response = requests.get(f"{BASE_URL}/api/calendar/week-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["deadlines_this_week"], int)
        assert isinstance(data["deadlines_next_week"], int)
        assert isinstance(data["pending_followups"], int)
        assert isinstance(data["in_progress"], int)
        print("✓ Week summary data types correct")


class TestV6FollowUpsRegression:
    """V6 Follow-Ups feature regression tests"""
    
    def test_get_follow_ups(self, auth_headers):
        """GET /api/follow-ups still works"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=auth_headers)
        assert response.status_code == 200
        print(f"✓ Follow-ups endpoint works: {len(response.json())} follow-ups")


class TestV5DonorsRegression:
    """V5 Donors feature regression tests"""
    
    def test_get_donors(self, auth_headers):
        """GET /api/donors still works"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        assert response.status_code == 200
        donors = response.json()
        assert len(donors) > 0, "No donors found"
        print(f"✓ Donors endpoint works: {len(donors)} donors")
    
    def test_donor_structure(self, auth_headers):
        """Verify donor has relationship_score"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=auth_headers)
        assert response.status_code == 200
        donors = response.json()
        
        for donor in donors[:3]:
            assert "relationship_score" in donor
        print("✓ Donor structure includes relationship_score")


class TestV4AnalyticsRegression:
    """V4 Analytics feature regression tests"""
    
    def test_get_performance_analytics(self, auth_headers):
        """GET /api/analytics/performance still works"""
        response = requests.get(f"{BASE_URL}/api/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Data is nested in 'summary' object
        assert "summary" in data
        summary = data["summary"]
        assert "approved_count" in summary
        assert "total_secured" in summary
        print(f"✓ Analytics endpoint works: {summary['approved_count']} approved, ${summary['total_secured']} secured")


class TestV3WorkspaceRegression:
    """V3 Workspace feature regression tests"""
    
    def test_get_smart_queue(self, auth_headers):
        """GET /api/queue still works"""
        response = requests.get(f"{BASE_URL}/api/queue", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ Smart queue endpoint works: {len(data['items'])} items")


class TestV2DashboardRegression:
    """V2 Dashboard feature regression tests"""
    
    def test_get_dashboard(self, auth_headers):
        """GET /api/opportunities/dashboard still works"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "top_opportunities" in data
        print(f"✓ Dashboard endpoint works: {data['stats']['total_opportunities']} opportunities")


class TestV1OpportunitiesRegression:
    """V1 Opportunities feature regression tests"""
    
    def test_get_opportunities(self, auth_headers):
        """GET /api/opportunities still works"""
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=auth_headers)
        assert response.status_code == 200
        opps = response.json()
        assert len(opps) > 0, "No opportunities found"
        print(f"✓ Opportunities endpoint works: {len(opps)} opportunities")
    
    def test_get_saved(self, auth_headers):
        """GET /api/saved still works"""
        response = requests.get(f"{BASE_URL}/api/saved", headers=auth_headers)
        assert response.status_code == 200
        print(f"✓ Saved endpoint works: {len(response.json())} saved")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
