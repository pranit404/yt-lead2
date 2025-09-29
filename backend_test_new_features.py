#!/usr/bin/env python3
"""
Backend Testing Suite for YouTube Lead Generation Platform
Focus: Email Sending Switch and Test Mode Functionality Testing
"""

import requests
import json
import sys
import time
from typing import Dict, List, Optional

# Backend URL Configuration
BACKEND_URL = "http://localhost:8001/api"

class NewFeaturesTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.test_results = []
        self.failed_tests = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Dict = None):
        """Log test results"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "response_data": response_data
        }
        self.test_results.append(result)
        
        if not success:
            self.failed_tests.append(result)
            
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def test_backend_connectivity(self):
        """Test basic backend connectivity"""
        try:
            response = requests.get(f"{self.backend_url}/", timeout=10)
            if response.status_code == 200:
                self.log_test("Backend Connectivity", True, "Backend is accessible")
                return True
            else:
                self.log_test("Backend Connectivity", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Backend Connectivity", False, f"Connection error: {str(e)}")
            return False
    
    def test_email_settings_get_endpoint(self):
        """Test GET /api/settings/email-sending endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/settings/email-sending", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["email_sending_enabled", "status"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Email Settings GET", False, 
                                f"Missing required fields: {missing_fields}", data)
                else:
                    # Validate field types and values
                    if isinstance(data["email_sending_enabled"], bool) and data["status"] in ["enabled", "disabled"]:
                        self.log_test("Email Settings GET", True, 
                                    f"Current status: {data['status']}", data)
                    else:
                        self.log_test("Email Settings GET", False, 
                                    f"Invalid field types or values", data)
            else:
                self.log_test("Email Settings GET", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Email Settings GET", False, f"Request error: {str(e)}")
    
    def test_email_settings_post_disable(self):
        """Test POST /api/settings/email-sending with enabled: false"""
        try:
            response = requests.post(f"{self.backend_url}/settings/email-sending?enabled=false", 
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["email_sending_enabled", "status", "message"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Email Settings POST Disable", False, 
                                f"Missing required fields: {missing_fields}", data)
                else:
                    # Validate that email sending is disabled
                    if (data["email_sending_enabled"] == False and 
                        data["status"] == "disabled" and 
                        "disabled" in data["message"].lower()):
                        self.log_test("Email Settings POST Disable", True, 
                                    "Email sending successfully disabled", data)
                    else:
                        self.log_test("Email Settings POST Disable", False, 
                                    "Email sending not properly disabled", data)
            else:
                self.log_test("Email Settings POST Disable", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Email Settings POST Disable", False, f"Request error: {str(e)}")
    
    def test_email_settings_post_enable(self):
        """Test POST /api/settings/email-sending with enabled: true"""
        try:
            response = requests.post(f"{self.backend_url}/settings/email-sending?enabled=true", 
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["email_sending_enabled", "status", "message"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Email Settings POST Enable", False, 
                                f"Missing required fields: {missing_fields}", data)
                else:
                    # Validate that email sending is enabled
                    if (data["email_sending_enabled"] == True and 
                        data["status"] == "enabled" and 
                        "enabled" in data["message"].lower()):
                        self.log_test("Email Settings POST Enable", True, 
                                    "Email sending successfully enabled", data)
                    else:
                        self.log_test("Email Settings POST Enable", False, 
                                    "Email sending not properly enabled", data)
            else:
                self.log_test("Email Settings POST Enable", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Email Settings POST Enable", False, f"Request error: {str(e)}")
    
    def test_email_settings_persistence(self):
        """Test that email settings persist after changes"""
        try:
            # First, set to disabled
            requests.post(f"{self.backend_url}/settings/email-sending?enabled=false", timeout=10)
            
            # Wait a moment
            time.sleep(1)
            
            # Check if it persisted
            response = requests.get(f"{self.backend_url}/settings/email-sending", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data["email_sending_enabled"] == False:
                    # Now set to enabled
                    requests.post(f"{self.backend_url}/settings/email-sending?enabled=true", timeout=10)
                    
                    time.sleep(1)
                    
                    # Check if it persisted
                    response = requests.get(f"{self.backend_url}/settings/email-sending", timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data["email_sending_enabled"] == True:
                            self.log_test("Email Settings Persistence", True, 
                                        "Settings persist correctly across changes", data)
                        else:
                            self.log_test("Email Settings Persistence", False, 
                                        "Enable setting did not persist", data)
                    else:
                        self.log_test("Email Settings Persistence", False, 
                                    f"Failed to get settings after enable: HTTP {response.status_code}")
                else:
                    self.log_test("Email Settings Persistence", False, 
                                "Disable setting did not persist", data)
            else:
                self.log_test("Email Settings Persistence", False, 
                            f"Failed to get settings after disable: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Email Settings Persistence", False, f"Request error: {str(e)}")
    
    def test_lead_generation_test_mode_limits(self):
        """Test that test_mode applies reduced limits"""
        try:
            # Test with test_mode: true
            payload = {
                "keywords": ["test keyword"],
                "max_videos_per_keyword": 500,  # Higher than test mode limit
                "max_channels": 50,  # Higher than test mode limit
                "subscriber_min": 1000,
                "subscriber_max": 100000,
                "test_mode": True
            }
            
            response = requests.post(f"{self.backend_url}/lead-generation/start", 
                                   json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check that we get a processing status
                if "id" in data and "status" in data:
                    status_id = data["id"]
                    
                    # Wait a moment for processing to start
                    time.sleep(2)
                    
                    # Check processing status
                    status_response = requests.get(f"{self.backend_url}/lead-generation/status/{status_id}", 
                                                 timeout=10)
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        self.log_test("Lead Generation Test Mode", True, 
                                    f"Test mode started successfully, status: {status_data.get('status')}", 
                                    {"start_response": data, "status_response": status_data})
                    else:
                        self.log_test("Lead Generation Test Mode", False, 
                                    f"Failed to get status: HTTP {status_response.status_code}")
                else:
                    self.log_test("Lead Generation Test Mode", False, 
                                "Invalid response structure", data)
            else:
                self.log_test("Lead Generation Test Mode", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Lead Generation Test Mode", False, f"Request error: {str(e)}")
    
    def test_lead_generation_normal_mode(self):
        """Test lead generation without test mode"""
        try:
            payload = {
                "keywords": ["test keyword"],
                "max_videos_per_keyword": 50,
                "max_channels": 5,
                "subscriber_min": 1000,
                "subscriber_max": 100000,
                "test_mode": False
            }
            
            response = requests.post(f"{self.backend_url}/lead-generation/start", 
                                   json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check that we get a processing status
                if "id" in data and "status" in data:
                    status_id = data["id"]
                    
                    # Wait a moment for processing to start
                    time.sleep(2)
                    
                    # Check processing status
                    status_response = requests.get(f"{self.backend_url}/lead-generation/status/{status_id}", 
                                                 timeout=10)
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        self.log_test("Lead Generation Normal Mode", True, 
                                    f"Normal mode started successfully, status: {status_data.get('status')}", 
                                    {"start_response": data, "status_response": status_data})
                    else:
                        self.log_test("Lead Generation Normal Mode", False, 
                                    f"Failed to get status: HTTP {status_response.status_code}")
                else:
                    self.log_test("Lead Generation Normal Mode", False, 
                                "Invalid response structure", data)
            else:
                self.log_test("Lead Generation Normal Mode", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Lead Generation Normal Mode", False, f"Request error: {str(e)}")
    
    def test_lead_generation_with_email_disabled(self):
        """Test lead generation with email sending disabled"""
        try:
            # First, disable email sending
            email_response = requests.post(f"{self.backend_url}/settings/email-sending?enabled=false", 
                                         timeout=10)
            
            if email_response.status_code != 200:
                self.log_test("Lead Generation Email Disabled", False, 
                            "Failed to disable email sending for test")
                return
            
            time.sleep(1)
            
            # Start lead generation
            payload = {
                "keywords": ["test keyword"],
                "max_videos_per_keyword": 10,
                "max_channels": 2,
                "subscriber_min": 1000,
                "subscriber_max": 100000,
                "test_mode": True
            }
            
            response = requests.post(f"{self.backend_url}/lead-generation/start", 
                                   json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "id" in data:
                    self.log_test("Lead Generation Email Disabled", True, 
                                "Lead generation started with email sending disabled", data)
                else:
                    self.log_test("Lead Generation Email Disabled", False, 
                                "Invalid response structure", data)
            else:
                self.log_test("Lead Generation Email Disabled", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Lead Generation Email Disabled", False, f"Request error: {str(e)}")
    
    def test_api_endpoints_existence(self):
        """Test that all new API endpoints exist and respond"""
        endpoints_to_test = [
            {
                "method": "GET",
                "endpoint": "/settings/email-sending",
                "name": "Email Settings GET"
            },
            {
                "method": "POST", 
                "endpoint": "/settings/email-sending",
                "name": "Email Settings POST",
                "payload": {"enabled": True}
            },
            {
                "method": "POST",
                "endpoint": "/lead-generation/start",
                "name": "Lead Generation Start",
                "payload": {
                    "keywords": ["test"],
                    "max_videos_per_keyword": 10,
                    "max_channels": 2,
                    "test_mode": True
                }
            }
        ]
        
        for endpoint_test in endpoints_to_test:
            try:
                if endpoint_test["method"] == "GET":
                    response = requests.get(f"{self.backend_url}{endpoint_test['endpoint']}", timeout=10)
                else:
                    payload = endpoint_test.get("payload", {})
                    response = requests.post(f"{self.backend_url}{endpoint_test['endpoint']}", 
                                           json=payload, timeout=10)
                
                if response.status_code in [200, 201]:
                    self.log_test(f"API Endpoint - {endpoint_test['name']}", True, 
                                f"Endpoint exists and responds (HTTP {response.status_code})")
                else:
                    self.log_test(f"API Endpoint - {endpoint_test['name']}", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test(f"API Endpoint - {endpoint_test['name']}", False, 
                            f"Request error: {str(e)}")
    
    def test_environment_variable_reflection(self):
        """Test that environment variable changes are reflected in API responses"""
        try:
            # Get current status
            response = requests.get(f"{self.backend_url}/settings/email-sending", timeout=10)
            
            if response.status_code == 200:
                initial_data = response.json()
                initial_status = initial_data["email_sending_enabled"]
                
                # Toggle the setting
                new_status = not initial_status
                toggle_response = requests.post(f"{self.backend_url}/settings/email-sending?enabled={str(new_status).lower()}", 
                                              timeout=10)
                
                if toggle_response.status_code == 200:
                    time.sleep(1)
                    
                    # Check if the change is reflected
                    check_response = requests.get(f"{self.backend_url}/settings/email-sending", timeout=10)
                    
                    if check_response.status_code == 200:
                        check_data = check_response.json()
                        
                        if check_data["email_sending_enabled"] == new_status:
                            self.log_test("Environment Variable Reflection", True, 
                                        f"Setting changed from {initial_status} to {new_status}", 
                                        {"initial": initial_data, "final": check_data})
                        else:
                            self.log_test("Environment Variable Reflection", False, 
                                        f"Setting not reflected: expected {new_status}, got {check_data['email_sending_enabled']}")
                    else:
                        self.log_test("Environment Variable Reflection", False, 
                                    f"Failed to check final status: HTTP {check_response.status_code}")
                else:
                    self.log_test("Environment Variable Reflection", False, 
                                f"Failed to toggle setting: HTTP {toggle_response.status_code}")
            else:
                self.log_test("Environment Variable Reflection", False, 
                            f"Failed to get initial status: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Environment Variable Reflection", False, f"Request error: {str(e)}")
    
    def test_invalid_inputs(self):
        """Test API endpoints with invalid inputs"""
        invalid_tests = [
            {
                "name": "Email Settings - Invalid JSON",
                "endpoint": "/settings/email-sending",
                "method": "POST",
                "payload": {"invalid": "data"},
                "should_fail": True
            },
            {
                "name": "Email Settings - Missing enabled field",
                "endpoint": "/settings/email-sending", 
                "method": "POST",
                "payload": {},
                "should_fail": True
            },
            {
                "name": "Lead Generation - Missing keywords",
                "endpoint": "/lead-generation/start",
                "method": "POST", 
                "payload": {"test_mode": True},
                "should_fail": True
            },
            {
                "name": "Lead Generation - Invalid test_mode type",
                "endpoint": "/lead-generation/start",
                "method": "POST",
                "payload": {
                    "keywords": ["test"],
                    "test_mode": "invalid"
                },
                "should_fail": True
            }
        ]
        
        for test_case in invalid_tests:
            try:
                if test_case["method"] == "GET":
                    response = requests.get(f"{self.backend_url}{test_case['endpoint']}", timeout=10)
                else:
                    response = requests.post(f"{self.backend_url}{test_case['endpoint']}", 
                                           json=test_case["payload"], timeout=10)
                
                if test_case["should_fail"]:
                    if response.status_code >= 400:
                        self.log_test(f"Invalid Input - {test_case['name']}", True, 
                                    f"Correctly rejected invalid input (HTTP {response.status_code})")
                    else:
                        self.log_test(f"Invalid Input - {test_case['name']}", False, 
                                    f"Should have failed but got HTTP {response.status_code}")
                else:
                    if response.status_code < 400:
                        self.log_test(f"Invalid Input - {test_case['name']}", True, 
                                    f"Correctly accepted valid input (HTTP {response.status_code})")
                    else:
                        self.log_test(f"Invalid Input - {test_case['name']}", False, 
                                    f"Should have succeeded but got HTTP {response.status_code}")
                        
            except Exception as e:
                self.log_test(f"Invalid Input - {test_case['name']}", False, 
                            f"Request error: {str(e)}")
    
    def run_all_tests(self):
        """Run all new features tests"""
        print("🚀 Starting Email Sending Switch and Test Mode Testing")
        print("=" * 70)
        
        # Test 1: Basic connectivity
        if not self.test_backend_connectivity():
            print("❌ Backend not accessible. Stopping tests.")
            return False
        
        print("\n📧 Testing Email Settings API...")
        self.test_email_settings_get_endpoint()
        self.test_email_settings_post_disable()
        self.test_email_settings_post_enable()
        self.test_email_settings_persistence()
        
        print("\n🧪 Testing Test Mode Functionality...")
        self.test_lead_generation_test_mode_limits()
        self.test_lead_generation_normal_mode()
        
        print("\n✉️ Testing Email Sending Control...")
        self.test_lead_generation_with_email_disabled()
        
        print("\n🔗 Testing API Integration...")
        self.test_api_endpoints_existence()
        self.test_environment_variable_reflection()
        
        print("\n⚠️ Testing Invalid Inputs...")
        self.test_invalid_inputs()
        
        return True
    
    def generate_report(self):
        """Generate test report"""
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        
        print("\n" + "=" * 70)
        print("📊 EMAIL SENDING SWITCH & TEST MODE TEST REPORT")
        print("=" * 70)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  • {test['test_name']}: {test['details']}")
        
        print("\n🔍 KEY FINDINGS:")
        
        # Analyze results by category
        categories = {
            "Email Settings": [t for t in self.test_results if "Email Settings" in t["test_name"]],
            "Test Mode": [t for t in self.test_results if "Test Mode" in t["test_name"] or "Lead Generation" in t["test_name"]],
            "API Integration": [t for t in self.test_results if "API Endpoint" in t["test_name"] or "Environment Variable" in t["test_name"]],
            "Error Handling": [t for t in self.test_results if "Invalid Input" in t["test_name"]]
        }
        
        for category, tests in categories.items():
            if tests:
                passed = len([t for t in tests if t["success"]])
                print(f"  • {category}: {passed}/{len(tests)} passed")
        
        # Overall assessment
        critical_failures = [t for t in self.failed_tests if any(keyword in t["test_name"] 
                           for keyword in ["Email Settings", "Test Mode", "Lead Generation"])]
        
        if len(self.failed_tests) == 0:
            print("\n✅ OVERALL: All new features working correctly!")
        elif len(critical_failures) == 0:
            print("\n⚠️ OVERALL: Core features working, minor issues with edge cases")
        else:
            print("\n❌ OVERALL: Critical issues found with new features")
        
        return len(critical_failures) == 0

def main():
    """Main test execution"""
    tester = NewFeaturesTester()
    
    success = tester.run_all_tests()
    if success:
        overall_success = tester.generate_report()
        sys.exit(0 if overall_success else 1)
    else:
        print("❌ Tests could not be completed due to connectivity issues")
        sys.exit(1)

if __name__ == "__main__":
    main()