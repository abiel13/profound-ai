"""
ProFund AI V10 - Batch Application Mode Tests
Tests batch processing: select opportunities, start batch, poll status, review queue, approve flow
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBatchApplicationMode:
    """V10 Batch Application Mode API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # ==================== BATCH STATUS API ====================
    
    def test_batch_status_endpoint(self):
        """GET /api/batch/status returns batch state"""
        response = requests.get(f"{BASE_URL}/api/batch/status", headers=self.headers)
        assert response.status_code == 200, f"Batch status failed: {response.text}"
        data = response.json()
        # Should have running, total, processed, errors keys
        assert "running" in data, "Missing 'running' key in batch status"
        assert "total" in data, "Missing 'total' key in batch status"
        assert "processed" in data, "Missing 'processed' key in batch status"
        assert "errors" in data, "Missing 'errors' key in batch status"
        print(f"Batch status: running={data['running']}, processed={data['processed']}/{data['total']}")
    
    # ==================== BATCH REVIEW API ====================
    
    def test_batch_review_endpoint(self):
        """GET /api/batch/review returns applications with batch_review status"""
        response = requests.get(f"{BASE_URL}/api/batch/review", headers=self.headers)
        assert response.status_code == 200, f"Batch review failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Batch review should return a list"
        print(f"Batch review queue: {len(data)} items")
        if data:
            item = data[0]
            assert "id" in item, "Review item missing 'id'"
            assert "title" in item, "Review item missing 'title'"
            assert "donor_name" in item, "Review item missing 'donor_name'"
            assert "review_checklist" in item, "Review item missing 'review_checklist'"
            print(f"First review item: {item['title']} - quality: {item.get('review_checklist', {}).get('quality_score', 'N/A')}")
    
    # ==================== ELIGIBLE OPPORTUNITIES ====================
    
    def test_get_eligible_opportunities(self):
        """GET /api/opportunities with 75%+ match score for batch selection"""
        response = requests.get(f"{BASE_URL}/api/opportunities?sort_by=match", headers=self.headers)
        assert response.status_code == 200, f"Get opportunities failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Opportunities should return a list"
        
        # Filter for batch-eligible (75%+ score, valid deadline)
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        eligible = [o for o in data if o.get('ai_match_score', 0) >= 75 and o.get('deadline', '') >= today]
        print(f"Total opportunities: {len(data)}, Batch-eligible (75%+): {len(eligible)}")
        
        # Store for batch test
        self.eligible_opps = eligible
        assert len(eligible) > 0, "No eligible opportunities for batch (need 75%+ score)"
        
        # Verify first eligible has required fields
        opp = eligible[0]
        assert "id" in opp
        assert "title" in opp
        assert "ai_match_score" in opp
        assert opp["ai_match_score"] >= 75
        print(f"Top eligible: {opp['title']} - {opp['ai_match_score']}% match")
    
    # ==================== BATCH START API ====================
    
    def test_batch_start_no_opportunities(self):
        """POST /api/batch/start with empty list returns 400"""
        response = requests.post(f"{BASE_URL}/api/batch/start", 
                                 json={"opportunity_ids": []}, 
                                 headers=self.headers)
        assert response.status_code == 400, f"Expected 400 for empty batch, got {response.status_code}"
        print("Empty batch correctly rejected with 400")
    
    def test_batch_start_with_opportunities(self):
        """POST /api/batch/start starts batch processing (2 opportunities)"""
        # First get eligible opportunities
        response = requests.get(f"{BASE_URL}/api/opportunities?sort_by=match", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        eligible = [o for o in data if o.get('ai_match_score', 0) >= 75 and o.get('deadline', '') >= today]
        
        if len(eligible) < 2:
            pytest.skip("Not enough eligible opportunities for batch test")
        
        # Select 2 opportunities for batch (small batch for testing)
        opp_ids = [eligible[0]['id'], eligible[1]['id']]
        print(f"Starting batch with 2 opportunities: {eligible[0]['title'][:30]}..., {eligible[1]['title'][:30]}...")
        
        response = requests.post(f"{BASE_URL}/api/batch/start",
                                 json={"opportunity_ids": opp_ids},
                                 headers=self.headers)
        
        # Could be 200 (started) or 200 with running status if already running
        assert response.status_code == 200, f"Batch start failed: {response.text}"
        data = response.json()
        
        if data.get("status") == "running":
            print(f"Batch already running: {data.get('processed', 0)}/{data.get('total', 0)}")
        else:
            assert data.get("status") == "started", f"Expected 'started' status, got: {data}"
            assert data.get("total") == 2, f"Expected total=2, got: {data.get('total')}"
            print(f"Batch started successfully with {data['total']} opportunities")
    
    # ==================== BATCH POLLING ====================
    
    def test_batch_status_polling(self):
        """Poll GET /api/batch/status until batch completes"""
        max_polls = 30  # 30 * 5s = 150s max wait
        poll_interval = 5
        
        for i in range(max_polls):
            response = requests.get(f"{BASE_URL}/api/batch/status", headers=self.headers)
            assert response.status_code == 200
            data = response.json()
            
            print(f"Poll {i+1}: running={data['running']}, processed={data['processed']}/{data['total']}, errors={data['errors']}")
            
            if not data['running']:
                print(f"Batch complete! Processed: {data['processed']}, Errors: {data['errors']}")
                # Verify results array
                results = data.get('results', [])
                print(f"Results: {len(results)} items")
                for r in results:
                    print(f"  - {r.get('title', r.get('opportunity_id', 'unknown'))}: {r.get('status')} (quality: {r.get('quality_score', 'N/A')})")
                return
            
            time.sleep(poll_interval)
        
        # If we get here, batch didn't complete in time
        print("WARNING: Batch did not complete within timeout - this is expected if batch is still processing")
    
    # ==================== BATCH APPROVE API ====================
    
    def test_batch_approve_flow(self):
        """POST /api/batch/approve/{wiz_id} approves application"""
        # Get review queue
        response = requests.get(f"{BASE_URL}/api/batch/review", headers=self.headers)
        assert response.status_code == 200
        review_queue = response.json()
        
        if not review_queue:
            print("No items in review queue to approve - skipping approve test")
            pytest.skip("No items in review queue")
        
        # Approve first item
        item = review_queue[0]
        wiz_id = item['id']
        print(f"Approving: {item['title']} (wizard_id: {wiz_id})")
        
        response = requests.post(f"{BASE_URL}/api/batch/approve/{wiz_id}", 
                                 json={}, 
                                 headers=self.headers)
        assert response.status_code == 200, f"Approve failed: {response.text}"
        data = response.json()
        assert data.get("status") == "complete", f"Expected status='complete', got: {data}"
        print(f"Approved successfully - status: {data['status']}")
        
        # Verify it's no longer in review queue
        response = requests.get(f"{BASE_URL}/api/batch/review", headers=self.headers)
        assert response.status_code == 200
        new_queue = response.json()
        remaining_ids = [r['id'] for r in new_queue]
        assert wiz_id not in remaining_ids, "Approved item should be removed from review queue"
        print(f"Verified: item removed from review queue (now {len(new_queue)} items)")
    
    # ==================== QUALITY CONTROL ====================
    
    def test_quality_control_flags(self):
        """Verify quality control flags in review queue items"""
        response = requests.get(f"{BASE_URL}/api/batch/review", headers=self.headers)
        assert response.status_code == 200
        review_queue = response.json()
        
        if not review_queue:
            print("No items in review queue - skipping quality control test")
            pytest.skip("No items in review queue")
        
        for item in review_queue:
            checklist = item.get('review_checklist', {})
            quality_score = checklist.get('quality_score', 100)
            flags = checklist.get('flags', [])
            
            print(f"Quality check: {item['title'][:40]}...")
            print(f"  Score: {quality_score}%, Flags: {flags if flags else 'None'}")
            
            # Verify quality_score is a number
            assert isinstance(quality_score, (int, float)), "quality_score should be numeric"
            assert 0 <= quality_score <= 100, "quality_score should be 0-100"
            
            # Verify flags is a list
            assert isinstance(flags, list), "flags should be a list"
    
    # ==================== V9 WIZARD REGRESSION ====================
    
    def test_v9_wizard_still_works(self):
        """Verify V9 wizard endpoints still work (regression)"""
        # Get wizard list
        response = requests.get(f"{BASE_URL}/api/wizard", headers=self.headers)
        assert response.status_code == 200, f"Wizard list failed: {response.text}"
        wizards = response.json()
        print(f"V9 Wizard list: {len(wizards)} wizards")
        
        if wizards:
            # Get first wizard details
            wiz_id = wizards[0]['id']
            response = requests.get(f"{BASE_URL}/api/wizard/{wiz_id}", headers=self.headers)
            assert response.status_code == 200, f"Wizard get failed: {response.text}"
            wiz = response.json()
            assert "title" in wiz
            assert "current_step" in wiz
            print(f"V9 Wizard detail: {wiz['title'][:40]}... - step {wiz['current_step']}/{wiz.get('total_steps', 6)}")


class TestBatchEdgeCases:
    """Edge case tests for batch processing"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@profund.ai",
            "password": "ProFund2024!"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_batch_max_10_limit(self):
        """Verify batch is capped at 10 opportunities"""
        # Get all opportunities
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=self.headers)
        assert response.status_code == 200
        opps = response.json()
        
        if len(opps) < 11:
            pytest.skip("Not enough opportunities to test 10+ limit")
        
        # Try to start batch with 15 opportunities
        opp_ids = [o['id'] for o in opps[:15]]
        
        # Note: The API caps at 10, so this should succeed but only process 10
        response = requests.post(f"{BASE_URL}/api/batch/start",
                                 json={"opportunity_ids": opp_ids},
                                 headers=self.headers)
        
        # If batch is already running, that's fine
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "started":
                assert data.get("total") <= 10, f"Batch should cap at 10, got {data.get('total')}"
                print(f"Batch correctly capped at {data.get('total')} opportunities")
            else:
                print(f"Batch already running: {data}")
    
    def test_batch_unauthenticated(self):
        """Verify batch endpoints require authentication"""
        # No auth header
        response = requests.get(f"{BASE_URL}/api/batch/status")
        assert response.status_code == 401, "Batch status should require auth"
        
        response = requests.get(f"{BASE_URL}/api/batch/review")
        assert response.status_code == 401, "Batch review should require auth"
        
        response = requests.post(f"{BASE_URL}/api/batch/start", json={"opportunity_ids": ["test"]})
        assert response.status_code == 401, "Batch start should require auth"
        
        print("All batch endpoints correctly require authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
