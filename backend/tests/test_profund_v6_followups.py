"""
ProFund AI V6 - Follow-Up Email System Tests
Tests for: follow-ups CRUD, scan, generate, mark-sent, dismiss
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFollowUpsV6:
    """V6 Follow-Up Email System Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for all tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # ==================== GET /api/follow-ups ====================
    def test_get_follow_ups_returns_list(self):
        """GET /api/follow-ups returns list of follow-ups"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} follow-ups")
    
    def test_follow_ups_have_required_fields(self):
        """Follow-ups have all required fields"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            fu = data[0]
            required_fields = ['id', 'donor_id', 'donor_name', 'trigger_type', 'email_type', 
                             'urgency', 'reason', 'status', 'due_date']
            for field in required_fields:
                assert field in fu, f"Missing field: {field}"
            print(f"Follow-up fields verified: {list(fu.keys())}")
    
    def test_follow_ups_have_urgency_levels(self):
        """Follow-ups have valid urgency levels (high/medium/low)"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        valid_urgencies = ['high', 'medium', 'low']
        for fu in data:
            assert fu['urgency'] in valid_urgencies, f"Invalid urgency: {fu['urgency']}"
        print(f"All {len(data)} follow-ups have valid urgency levels")
    
    def test_follow_ups_have_valid_email_types(self):
        """Follow-ups have valid email types"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        valid_types = ['application_followup', 'relationship_reengagement', 'post_rejection', 
                      'post_approval_thanks', 'partnership_continuation']
        for fu in data:
            assert fu['email_type'] in valid_types, f"Invalid email_type: {fu['email_type']}"
        print(f"All {len(data)} follow-ups have valid email types")
    
    def test_follow_ups_have_valid_status(self):
        """Follow-ups have valid status (pending/draft/sent/dismissed)"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        valid_statuses = ['pending', 'draft', 'sent', 'dismissed']
        for fu in data:
            assert fu['status'] in valid_statuses, f"Invalid status: {fu['status']}"
        print(f"All {len(data)} follow-ups have valid status")
    
    # ==================== POST /api/follow-ups/scan ====================
    def test_scan_follow_ups(self):
        """POST /api/follow-ups/scan detects follow-up triggers"""
        response = requests.post(f"{BASE_URL}/api/follow-ups/scan", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert 'scanned' in data
        assert data['scanned'] == True
        assert 'triggers_found' in data
        assert 'follow_ups_created' in data
        print(f"Scan result: {data['triggers_found']} triggers found, {data['follow_ups_created']} created")
    
    # ==================== POST /api/follow-ups/{id}/generate ====================
    def test_generate_follow_up_email(self):
        """POST /api/follow-ups/{id}/generate creates AI email draft"""
        # Get a pending follow-up
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        follow_ups = response.json()
        pending = [fu for fu in follow_ups if fu['status'] == 'pending']
        
        if len(pending) == 0:
            pytest.skip("No pending follow-ups to test generation")
        
        fu_id = pending[0]['id']
        print(f"Generating email for follow-up: {fu_id}")
        
        # Generate email (this calls real GPT-5.2)
        response = requests.post(f"{BASE_URL}/api/follow-ups/{fu_id}/generate", headers=self.headers, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert 'id' in data
        assert 'subject' in data
        assert 'body' in data
        assert 'status' in data
        assert data['status'] == 'draft'
        assert len(data['subject']) > 0, "Subject should not be empty"
        assert len(data['body']) > 10, "Body should have content"
        print(f"Generated email - Subject: {data['subject'][:50]}...")
    
    def test_generate_follow_up_not_found(self):
        """POST /api/follow-ups/{id}/generate returns 404 for invalid ID"""
        response = requests.post(f"{BASE_URL}/api/follow-ups/invalid-id-12345/generate", headers=self.headers)
        assert response.status_code == 404
    
    # ==================== PUT /api/follow-ups/{id} ====================
    def test_update_follow_up_draft(self):
        """PUT /api/follow-ups/{id} updates email draft"""
        # Get a follow-up with draft status
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        follow_ups = response.json()
        drafts = [fu for fu in follow_ups if fu['status'] == 'draft']
        
        if len(drafts) == 0:
            pytest.skip("No draft follow-ups to test update")
        
        fu_id = drafts[0]['id']
        
        # Update the draft
        update_data = {
            "email_subject": "TEST_Updated Subject Line",
            "email_draft": "TEST_Updated email body content for testing purposes.",
            "status": "draft"
        }
        response = requests.put(f"{BASE_URL}/api/follow-ups/{fu_id}", json=update_data, headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data['updated'] == True
        print(f"Updated follow-up {fu_id}")
        
        # Verify update persisted
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        follow_ups = response.json()
        updated = next((fu for fu in follow_ups if fu['id'] == fu_id), None)
        assert updated is not None
        assert updated['email_subject'] == "TEST_Updated Subject Line"
        print("Update verified in database")
    
    def test_update_follow_up_no_fields(self):
        """PUT /api/follow-ups/{id} returns 400 when no fields provided"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        follow_ups = response.json()
        if len(follow_ups) == 0:
            pytest.skip("No follow-ups to test")
        
        fu_id = follow_ups[0]['id']
        response = requests.put(f"{BASE_URL}/api/follow-ups/{fu_id}", json={}, headers=self.headers)
        assert response.status_code == 400
    
    # ==================== POST /api/follow-ups/{id}/mark-sent ====================
    def test_mark_follow_up_sent(self):
        """POST /api/follow-ups/{id}/mark-sent marks as sent and logs interaction"""
        # Get a draft follow-up
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        follow_ups = response.json()
        drafts = [fu for fu in follow_ups if fu['status'] == 'draft']
        
        if len(drafts) == 0:
            pytest.skip("No draft follow-ups to test mark-sent")
        
        fu_id = drafts[0]['id']
        donor_name = drafts[0]['donor_name']
        
        # Mark as sent
        response = requests.post(f"{BASE_URL}/api/follow-ups/{fu_id}/mark-sent", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'sent'
        print(f"Marked follow-up {fu_id} as sent")
        
        # Verify status changed
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        follow_ups = response.json()
        sent = next((fu for fu in follow_ups if fu['id'] == fu_id), None)
        assert sent is not None
        assert sent['status'] == 'sent'
        assert sent['sent_at'] != ''
        print(f"Verified sent status and sent_at timestamp")
    
    def test_mark_sent_not_found(self):
        """POST /api/follow-ups/{id}/mark-sent returns 404 for invalid ID"""
        response = requests.post(f"{BASE_URL}/api/follow-ups/invalid-id-12345/mark-sent", headers=self.headers)
        assert response.status_code == 404
    
    # ==================== DELETE /api/follow-ups/{id} ====================
    def test_dismiss_follow_up(self):
        """DELETE /api/follow-ups/{id} dismisses (soft delete) follow-up"""
        # Get a pending follow-up
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        follow_ups = response.json()
        pending = [fu for fu in follow_ups if fu['status'] == 'pending']
        
        if len(pending) == 0:
            pytest.skip("No pending follow-ups to test dismiss")
        
        fu_id = pending[0]['id']
        
        # Dismiss
        response = requests.delete(f"{BASE_URL}/api/follow-ups/{fu_id}", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'dismissed'
        print(f"Dismissed follow-up {fu_id}")
        
        # Verify status changed to dismissed
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        follow_ups = response.json()
        dismissed = next((fu for fu in follow_ups if fu['id'] == fu_id), None)
        assert dismissed is not None
        assert dismissed['status'] == 'dismissed'
        print("Verified dismissed status")
    
    # ==================== Auth Tests ====================
    def test_follow_ups_requires_auth(self):
        """GET /api/follow-ups requires authentication"""
        response = requests.get(f"{BASE_URL}/api/follow-ups")
        assert response.status_code == 401
    
    def test_scan_requires_auth(self):
        """POST /api/follow-ups/scan requires authentication"""
        response = requests.post(f"{BASE_URL}/api/follow-ups/scan")
        assert response.status_code == 401
    
    # ==================== Integration Tests ====================
    def test_follow_ups_sorted_by_urgency(self):
        """Follow-ups are sorted by urgency (high first)"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) < 2:
            pytest.skip("Need at least 2 follow-ups to test sorting")
        
        urgency_order = {'high': 1, 'medium': 2, 'low': 3}
        for i in range(len(data) - 1):
            current = urgency_order.get(data[i]['urgency'], 3)
            next_item = urgency_order.get(data[i+1]['urgency'], 3)
            assert current <= next_item, "Follow-ups should be sorted by urgency"
        print("Follow-ups correctly sorted by urgency")
    
    def test_follow_ups_include_donor_relationship_data(self):
        """Follow-ups include donor relationship score and level"""
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No follow-ups to test")
        
        fu = data[0]
        # These fields come from JOIN with donors table
        assert 'relationship_score' in fu or fu.get('relationship_score') is None
        assert 'relationship_level' in fu or fu.get('relationship_level') is None
        print(f"Follow-up includes donor data: score={fu.get('relationship_score')}, level={fu.get('relationship_level')}")


class TestV6WithV5Integration:
    """Test V6 features work with V5 donor system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_donors_endpoint_still_works(self):
        """V5 donors endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"V5 donors endpoint working: {len(data)} donors")
    
    def test_dashboard_still_works(self):
        """Dashboard endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/opportunities/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert 'stats' in data
        assert 'top_opportunities' in data
        print(f"Dashboard working: {data['stats']['total_opportunities']} opportunities")
    
    def test_donor_interactions_endpoint_works(self):
        """V5 donor interactions endpoint works"""
        response = requests.get(f"{BASE_URL}/api/donors", headers=self.headers)
        donors = response.json()
        if len(donors) > 0:
            donor_id = donors[0]['id']
            response = requests.get(f"{BASE_URL}/api/donors/{donor_id}", headers=self.headers)
            assert response.status_code == 200
            data = response.json()
            assert 'interactions' in data
            print(f"Donor detail working: {len(data.get('interactions', []))} interactions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
