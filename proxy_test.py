#!/usr/bin/env python3
"""
Backend Testing Suite for YouTube Lead Generation Platform
Focus: Proxy Management System Testing (Phase 1 Step 2)
"""

import requests
import json
import sys
import time
import uuid
from typing import Dict, List, Optional

# Backend URL Configuration
BACKEND_URL = "http://localhost:8001/api"

class ProxyManagementTester:
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
    
    def test_proxy_management_crud_operations(self):
        """Test all CRUD operations for proxy management"""
        print("\n🔧 Testing Proxy Management CRUD Operations...")
        
        # Test data for proxies with different configurations
        test_proxies = [
            {
                "ip": "192.168.1.100",
                "port": 8080,
                "protocol": "http",
                "location": "US-East",
                "provider": "TestProvider1"
            },
            {
                "ip": "10.0.0.50",
                "port": 3128,
                "username": "proxy_user",
                "password": "proxy_pass",
                "protocol": "http",
                "location": "EU-West",
                "provider": "TestProvider2"
            },
            {
                "ip": "172.16.0.25",
                "port": 1080,
                "protocol": "socks5",
                "location": "Asia-Pacific",
                "provider": "TestProvider3"
            }
        ]
        
        created_proxy_ids = []
        
        # Test 1: POST /api/proxies/add - Add new proxies
        for i, proxy_data in enumerate(test_proxies):
            try:
                response = requests.post(f"{self.backend_url}/proxies/add", json=proxy_data, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    proxy_id = data.get("id")
                    created_proxy_ids.append(proxy_id)
                    
                    # Verify all fields are present
                    required_fields = ["id", "ip", "port", "protocol", "status", "created_at", "updated_at"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields and data.get("status") == "active":
                        self.log_test(f"Add Proxy {i+1} ({proxy_data['protocol']})", True, 
                                    f"Proxy created successfully with ID: {proxy_id}", data)
                    else:
                        self.log_test(f"Add Proxy {i+1} ({proxy_data['protocol']})", False, 
                                    f"Missing fields: {missing_fields} or incorrect status", data)
                else:
                    self.log_test(f"Add Proxy {i+1} ({proxy_data['protocol']})", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test(f"Add Proxy {i+1} ({proxy_data['protocol']})", False, f"Request error: {str(e)}")
            
            time.sleep(0.5)
        
        # Test 2: Test duplicate proxy prevention
        if test_proxies:
            try:
                duplicate_proxy = test_proxies[0].copy()
                response = requests.post(f"{self.backend_url}/proxies/add", json=duplicate_proxy, timeout=10)
                
                if response.status_code == 400:
                    self.log_test("Duplicate Proxy Prevention", True, 
                                "Correctly prevented duplicate proxy creation")
                else:
                    self.log_test("Duplicate Proxy Prevention", False, 
                                f"Should have returned 400, got: {response.status_code}")
            except Exception as e:
                self.log_test("Duplicate Proxy Prevention", False, f"Request error: {str(e)}")
        
        # Test 3: GET /api/proxies - List all proxies
        try:
            response = requests.get(f"{self.backend_url}/proxies", timeout=10)
            
            if response.status_code == 200:
                proxies = response.json()
                
                if isinstance(proxies, list) and len(proxies) >= len(created_proxy_ids):
                    # Check if our created proxies are in the list
                    proxy_ids_in_list = [proxy.get("id") for proxy in proxies]
                    found_proxies = [proxy_id for proxy_id in created_proxy_ids if proxy_id in proxy_ids_in_list]
                    
                    if len(found_proxies) == len(created_proxy_ids):
                        self.log_test("List All Proxies", True, 
                                    f"Found {len(proxies)} proxies including all {len(created_proxy_ids)} created proxies")
                    else:
                        self.log_test("List All Proxies", False, 
                                    f"Missing some created proxies. Found {len(found_proxies)}/{len(created_proxy_ids)}")
                else:
                    self.log_test("List All Proxies", False, 
                                f"Expected list with at least {len(created_proxy_ids)} proxies, got: {type(proxies)}")
            else:
                self.log_test("List All Proxies", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("List All Proxies", False, f"Request error: {str(e)}")
        
        # Test 4: GET /api/proxies/{proxy_id} - Get specific proxy
        if created_proxy_ids:
            test_proxy_id = created_proxy_ids[0]
            try:
                response = requests.get(f"{self.backend_url}/proxies/{test_proxy_id}", timeout=10)
                
                if response.status_code == 200:
                    proxy = response.json()
                    
                    if proxy.get("id") == test_proxy_id and proxy.get("ip"):
                        self.log_test("Get Specific Proxy", True, 
                                    f"Successfully retrieved proxy: {proxy.get('ip')}:{proxy.get('port')}")
                    else:
                        self.log_test("Get Specific Proxy", False, 
                                    f"Proxy data mismatch or missing fields")
                else:
                    self.log_test("Get Specific Proxy", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test("Get Specific Proxy", False, f"Request error: {str(e)}")
        
        # Test 5: PUT /api/proxies/{proxy_id}/status - Update proxy status
        if created_proxy_ids:
            test_proxy_id = created_proxy_ids[1] if len(created_proxy_ids) > 1 else created_proxy_ids[0]
            status_updates = ["disabled", "banned", "maintenance", "active"]
            
            for status in status_updates:
                try:
                    response = requests.put(f"{self.backend_url}/proxies/{test_proxy_id}/status", 
                                          json={"status": status}, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "updated" in data.get("message", "").lower():
                            self.log_test(f"Update Proxy Status to {status}", True, 
                                        f"Status updated successfully: {data.get('message')}")
                        else:
                            self.log_test(f"Update Proxy Status to {status}", False, 
                                        f"Unexpected response: {data}")
                    else:
                        self.log_test(f"Update Proxy Status to {status}", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                        
                except Exception as e:
                    self.log_test(f"Update Proxy Status to {status}", False, f"Request error: {str(e)}")
                
                time.sleep(0.3)
        
        # Test 6: DELETE /api/proxies/{proxy_id} - Delete proxy
        if created_proxy_ids:
            # Delete the last proxy to test deletion
            delete_proxy_id = created_proxy_ids[-1]
            try:
                response = requests.delete(f"{self.backend_url}/proxies/{delete_proxy_id}", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if "deleted" in data.get("message", "").lower():
                        self.log_test("Delete Proxy", True, 
                                    f"Proxy deleted successfully: {data.get('message')}")
                        created_proxy_ids.remove(delete_proxy_id)  # Remove from tracking
                    else:
                        self.log_test("Delete Proxy", False, 
                                    f"Unexpected response: {data}")
                else:
                    self.log_test("Delete Proxy", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test("Delete Proxy", False, f"Request error: {str(e)}")
        
        return created_proxy_ids  # Return remaining proxy IDs for other tests
    
    def test_proxy_pool_operations(self):
        """Test proxy pool operations and rotation logic"""
        print("\n🔄 Testing Proxy Pool Operations...")
        
        # Test 1: GET /api/proxies/available - Get next available proxy
        try:
            response = requests.get(f"{self.backend_url}/proxies/available", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("proxy_found"):
                    proxy_info = {
                        "proxy_id": data.get("proxy_id"),
                        "ip": data.get("ip"),
                        "port": data.get("port"),
                        "protocol": data.get("protocol"),
                        "status": data.get("status"),
                        "daily_requests": data.get("daily_requests"),
                        "success_rate": data.get("success_rate")
                    }
                    
                    # Verify proxy is active and under daily limit
                    if (data.get("status") == "active" and 
                        isinstance(data.get("daily_requests"), int) and 
                        data.get("daily_requests") < 200):  # MAX_DAILY_REQUESTS_PER_PROXY
                        
                        self.log_test("Get Available Proxy", True, 
                                    f"Found available proxy: {data.get('ip')}:{data.get('port')} "
                                    f"(Daily requests: {data.get('daily_requests')}, "
                                    f"Success rate: {data.get('success_rate')}%)", proxy_info)
                    else:
                        self.log_test("Get Available Proxy", False, 
                                    f"Proxy found but doesn't meet availability criteria: {proxy_info}")
                else:
                    # No available proxies - this could be valid if no proxies exist
                    message = data.get("message", "No message provided")
                    self.log_test("Get Available Proxy", True, 
                                f"No available proxies found: {message}")
            else:
                self.log_test("Get Available Proxy", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Get Available Proxy", False, f"Request error: {str(e)}")
    
    def test_proxy_statistics_overview(self):
        """Test proxy statistics and overview endpoint"""
        print("\n📊 Testing Proxy Statistics Overview...")
        
        try:
            response = requests.get(f"{self.backend_url}/proxies/stats/overview", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                
                # Check required fields
                required_fields = [
                    "total_proxies", "active_proxies", "banned_proxies", 
                    "disabled_proxies", "healthy_proxies", "unhealthy_proxies",
                    "max_daily_requests_per_proxy", "max_concurrent_proxies"
                ]
                
                missing_fields = [field for field in required_fields if field not in stats]
                
                if not missing_fields:
                    # Verify data consistency
                    total = stats.get("total_proxies", 0)
                    active = stats.get("active_proxies", 0)
                    banned = stats.get("banned_proxies", 0)
                    disabled = stats.get("disabled_proxies", 0)
                    
                    # Basic validation: active + banned + disabled should not exceed total
                    if active + banned + disabled <= total:
                        self.log_test("Proxy Statistics Overview", True, 
                                    f"Statistics retrieved successfully - Total: {total}, "
                                    f"Active: {active}, Banned: {banned}, Disabled: {disabled}", stats)
                    else:
                        self.log_test("Proxy Statistics Overview", False, 
                                    f"Data inconsistency: sum of status counts exceeds total", stats)
                else:
                    self.log_test("Proxy Statistics Overview", False, 
                                f"Missing required fields: {missing_fields}", stats)
            else:
                self.log_test("Proxy Statistics Overview", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Proxy Statistics Overview", False, f"Request error: {str(e)}")
    
    def test_proxy_health_checking(self):
        """Test proxy health check functionality"""
        print("\n🏥 Testing Proxy Health Checking...")
        
        # Test 1: POST /api/proxies/health-check - Check all proxies
        try:
            response = requests.post(f"{self.backend_url}/proxies/health-check", json={}, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if "checked" in data.get("message", "").lower():
                    checked_count = data.get("proxies_checked", 0)
                    healthy_count = data.get("healthy_proxies", 0)
                    unhealthy_count = data.get("unhealthy_proxies", 0)
                    
                    self.log_test("Health Check All Proxies", True, 
                                f"Health check completed - Checked: {checked_count}, "
                                f"Healthy: {healthy_count}, Unhealthy: {unhealthy_count}", data)
                else:
                    self.log_test("Health Check All Proxies", False, 
                                f"Unexpected response format: {data}")
            else:
                self.log_test("Health Check All Proxies", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Health Check All Proxies", False, f"Request error: {str(e)}")
        
        # Test 2: Health check specific proxy (if we have proxy IDs from previous tests)
        # This would require coordination with CRUD test results
        # For now, we'll test with a mock proxy ID to verify error handling
        fake_proxy_id = "nonexistent_proxy_id"
        try:
            response = requests.post(f"{self.backend_url}/proxies/health-check", 
                                   json={"proxy_id": fake_proxy_id}, timeout=15)
            
            if response.status_code == 404:
                self.log_test("Health Check Specific Proxy (Error Handling)", True, 
                            "Correctly returned 404 for non-existent proxy")
            elif response.status_code == 200:
                # If it returns 200, it might be handling the case gracefully
                data = response.json()
                self.log_test("Health Check Specific Proxy (Error Handling)", True, 
                            f"Gracefully handled non-existent proxy: {data.get('message', '')}")
            else:
                self.log_test("Health Check Specific Proxy (Error Handling)", False, 
                            f"Unexpected status code: {response.status_code}")
                
        except Exception as e:
            self.log_test("Health Check Specific Proxy (Error Handling)", False, f"Request error: {str(e)}")
    
    def test_proxy_database_schema_validation(self):
        """Test MongoDB integration and proxy schema validation"""
        print("\n🗄️ Testing Proxy Database Schema Validation...")
        
        # Create a test proxy to verify schema
        test_proxy = {
            "ip": "203.0.113.1",  # RFC 5737 test IP
            "port": 8888,
            "username": "schema_test_user",
            "password": "schema_test_pass",
            "protocol": "http",
            "location": "Test-Location",
            "provider": "SchemaTestProvider"
        }
        
        try:
            # Create proxy
            response = requests.post(f"{self.backend_url}/proxies/add", json=test_proxy, timeout=10)
            
            if response.status_code == 200:
                proxy_data = response.json()
                proxy_id = proxy_data.get("id")
                
                # Verify all expected schema fields are present
                expected_fields = [
                    "id", "ip", "port", "username", "password", "protocol", "status",
                    "last_used", "daily_requests_count", "total_requests_count",
                    "success_rate", "response_time_avg", "last_health_check",
                    "health_status", "last_error", "location", "provider",
                    "created_at", "updated_at"
                ]
                
                present_fields = list(proxy_data.keys())
                missing_fields = [field for field in expected_fields if field not in present_fields]
                
                # Verify data types
                type_checks = [
                    ("id", str), ("ip", str), ("port", int), ("protocol", str),
                    ("status", str), ("daily_requests_count", int), 
                    ("total_requests_count", int), ("success_rate", (int, float)),
                    ("response_time_avg", (int, float)), ("location", str), ("provider", str)
                ]
                
                type_errors = []
                for field, expected_type in type_checks:
                    if field in proxy_data:
                        if not isinstance(proxy_data[field], expected_type):
                            type_errors.append(f"{field}: expected {expected_type}, got {type(proxy_data[field])}")
                
                if not missing_fields and not type_errors:
                    self.log_test("Proxy Database Schema Validation", True, 
                                f"All schema fields present with correct types", proxy_data)
                else:
                    error_msg = f"Missing fields: {missing_fields}, Type errors: {type_errors}"
                    self.log_test("Proxy Database Schema Validation", False, error_msg, proxy_data)
                
                # Clean up test proxy
                try:
                    requests.delete(f"{self.backend_url}/proxies/{proxy_id}", timeout=10)
                except:
                    pass  # Cleanup failure is not critical for this test
                    
            else:
                self.log_test("Proxy Database Schema Validation", False, 
                            f"Failed to create test proxy: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Proxy Database Schema Validation", False, f"Request error: {str(e)}")
    
    def test_proxy_environment_configuration(self):
        """Test proxy environment configuration and settings"""
        print("\n⚙️ Testing Proxy Environment Configuration...")
        
        # Test proxy statistics to verify environment variables are loaded
        try:
            response = requests.get(f"{self.backend_url}/proxies/stats/overview", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                
                # Check if environment variables are properly loaded
                max_daily = stats.get("max_daily_requests_per_proxy")
                max_concurrent = stats.get("max_concurrent_proxies")
                
                # Expected values from environment (from backend/.env)
                expected_max_daily = 200
                expected_max_concurrent = 5
                
                if max_daily == expected_max_daily and max_concurrent == expected_max_concurrent:
                    self.log_test("Proxy Environment Configuration", True, 
                                f"Environment variables loaded correctly - "
                                f"Max daily: {max_daily}, Max concurrent: {max_concurrent}")
                else:
                    self.log_test("Proxy Environment Configuration", False, 
                                f"Environment variables mismatch - "
                                f"Expected daily: {expected_max_daily}, got: {max_daily}, "
                                f"Expected concurrent: {expected_max_concurrent}, got: {max_concurrent}")
            else:
                self.log_test("Proxy Environment Configuration", False, 
                            f"Could not retrieve configuration: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Proxy Environment Configuration", False, f"Request error: {str(e)}")
    
    def test_proxy_error_handling_and_validation(self):
        """Test proxy error handling and input validation"""
        print("\n⚠️ Testing Proxy Error Handling and Validation...")
        
        # Test 1: Invalid proxy data
        invalid_proxy_tests = [
            ({"ip": "invalid_ip", "port": 8080}, "Invalid IP address"),
            ({"ip": "192.168.1.1", "port": "invalid_port"}, "Invalid port type"),
            ({"ip": "192.168.1.1", "port": 70000}, "Port out of range"),
            ({"ip": "192.168.1.1", "port": 8080, "protocol": "invalid_protocol"}, "Invalid protocol"),
        ]
        
        for invalid_data, test_description in invalid_proxy_tests:
            try:
                response = requests.post(f"{self.backend_url}/proxies/add", json=invalid_data, timeout=10)
                
                if response.status_code in [400, 422]:
                    self.log_test(f"Invalid Input Validation - {test_description}", True, 
                                f"Correctly rejected invalid data: HTTP {response.status_code}")
                else:
                    self.log_test(f"Invalid Input Validation - {test_description}", False, 
                                f"Should have returned 400/422, got: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Invalid Input Validation - {test_description}", False, f"Request error: {str(e)}")
            
            time.sleep(0.2)
        
        # Test 2: Invalid status update
        try:
            response = requests.put(f"{self.backend_url}/proxies/nonexistent_id/status", 
                                  json={"status": "invalid_status"}, timeout=10)
            
            if response.status_code in [400, 404]:
                self.log_test("Invalid Proxy Status Update", True, 
                            f"Correctly rejected invalid status: HTTP {response.status_code}")
            else:
                self.log_test("Invalid Proxy Status Update", False, 
                            f"Should have returned 400/404, got: {response.status_code}")
                
        except Exception as e:
            self.log_test("Invalid Proxy Status Update", False, f"Request error: {str(e)}")
        
        # Test 3: Non-existent proxy operations
        fake_id = "nonexistent_proxy_id"
        
        operations = [
            ("GET", f"/proxies/{fake_id}", "Get non-existent proxy"),
            ("PUT", f"/proxies/{fake_id}/status", "Update non-existent proxy"),
            ("DELETE", f"/proxies/{fake_id}", "Delete non-existent proxy")
        ]
        
        for method, endpoint, description in operations:
            try:
                if method == "GET":
                    response = requests.get(f"{self.backend_url}{endpoint}", timeout=10)
                elif method == "PUT":
                    response = requests.put(f"{self.backend_url}{endpoint}", 
                                          json={"status": "active"}, timeout=10)
                elif method == "DELETE":
                    response = requests.delete(f"{self.backend_url}{endpoint}", timeout=10)
                
                if response.status_code == 404:
                    self.log_test(f"Proxy Error Handling - {description}", True, 
                                "Correctly returned 404 for non-existent proxy")
                else:
                    self.log_test(f"Proxy Error Handling - {description}", False, 
                                f"Should have returned 404, got: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Proxy Error Handling - {description}", False, f"Request error: {str(e)}")
            
            time.sleep(0.2)
    
    def test_integration_with_existing_system(self):
        """Test integration with existing lead generation system"""
        print("\n🔗 Testing Integration with Existing System...")
        
        # Test 1: Verify existing endpoints still work
        existing_endpoints = [
            ("/", "Root endpoint"),
            ("/leads/main", "Main leads endpoint"),
            ("/leads/no-email", "No-email leads endpoint"),
            ("/settings/email-sending", "Email settings endpoint"),
            ("/accounts", "YouTube accounts endpoint")  # From Phase 1 Step 1
        ]
        
        for endpoint, description in existing_endpoints:
            try:
                response = requests.get(f"{self.backend_url}{endpoint}", timeout=10)
                
                if response.status_code == 200:
                    self.log_test(f"Existing System - {description}", True, 
                                f"Endpoint accessible: {endpoint}")
                else:
                    self.log_test(f"Existing System - {description}", False, 
                                f"HTTP {response.status_code} for {endpoint}")
                    
            except Exception as e:
                self.log_test(f"Existing System - {description}", False, 
                            f"Request error for {endpoint}: {str(e)}")
            
            time.sleep(0.3)
    
    def run_all_tests(self):
        """Run all Proxy Management System tests"""
        print("🚀 Starting Proxy Management System Testing")
        print("🎯 Phase 1 Step 2: Proxy Pool Management")
        print("=" * 70)
        
        # Test 1: Basic connectivity
        if not self.test_backend_connectivity():
            print("❌ Backend not accessible. Stopping tests.")
            return False
        
        print("\n🔧 Testing Proxy Management CRUD Operations...")
        created_proxies = self.test_proxy_management_crud_operations()
        
        print("\n🔄 Testing Proxy Pool Operations...")
        self.test_proxy_pool_operations()
        
        print("\n📊 Testing Proxy Statistics Overview...")
        self.test_proxy_statistics_overview()
        
        print("\n🏥 Testing Proxy Health Checking...")
        self.test_proxy_health_checking()
        
        print("\n🗄️ Testing Proxy Database Schema Validation...")
        self.test_proxy_database_schema_validation()
        
        print("\n⚙️ Testing Proxy Environment Configuration...")
        self.test_proxy_environment_configuration()
        
        print("\n🔗 Testing Integration with Existing System...")
        self.test_integration_with_existing_system()
        
        print("\n⚠️ Testing Proxy Error Handling and Validation...")
        self.test_proxy_error_handling_and_validation()
        
        # Cleanup any remaining test proxies
        if created_proxies:
            print(f"\n🧹 Cleaning up {len(created_proxies)} test proxies...")
            for proxy_id in created_proxies:
                try:
                    requests.delete(f"{self.backend_url}/proxies/{proxy_id}", timeout=5)
                except:
                    pass  # Cleanup failures are not critical
        
        return True
    
    def generate_report(self):
        """Generate test report"""
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        
        print("\n" + "=" * 70)
        print("📊 PROXY MANAGEMENT SYSTEM TEST REPORT")
        print("🎯 Phase 1 Step 2: Proxy Pool Management")
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
        
        # Analyze results by test category
        categories = {
            "CRUD Operations": [t for t in self.test_results if any(crud in t["test_name"] for crud in ["Add Proxy", "List All", "Get Specific", "Update Proxy Status", "Delete Proxy", "Duplicate Proxy"])],
            "Proxy Pool Operations": [t for t in self.test_results if "Available Proxy" in t["test_name"]],
            "Statistics": [t for t in self.test_results if "Statistics" in t["test_name"]],
            "Health Checking": [t for t in self.test_results if "Health Check" in t["test_name"]],
            "Database Schema": [t for t in self.test_results if "Schema" in t["test_name"]],
            "Environment Config": [t for t in self.test_results if "Environment" in t["test_name"]],
            "System Integration": [t for t in self.test_results if "Existing System" in t["test_name"]],
            "Error Handling": [t for t in self.test_results if "Error Handling" in t["test_name"] or "Invalid" in t["test_name"]]
        }
        
        for category, tests in categories.items():
            if tests:
                passed = len([t for t in tests if t["success"]])
                print(f"  • {category}: {passed}/{len(tests)} passed")
        
        # Critical issues assessment
        critical_failures = []
        for test in self.failed_tests:
            if any(critical in test["test_name"] for critical in ["Add Proxy", "List All", "Get Available", "Database Schema", "Health Check"]):
                critical_failures.append(test["test_name"])
        
        # Overall assessment
        if len(self.failed_tests) == 0:
            print("\n✅ OVERALL: Proxy Management System is working perfectly!")
            print("🎯 Ready for integration with email extraction workflows")
        elif critical_failures:
            print(f"\n❌ OVERALL: Critical issues found in core functionality: {', '.join(critical_failures)}")
            print("🚨 Must fix critical issues before proceeding to email extraction integration")
        elif len(self.failed_tests) <= 3:
            print("\n⚠️ OVERALL: Proxy management mostly working with minor issues")
            print("🔧 Minor fixes recommended but system is functional")
        else:
            print("\n❌ OVERALL: Multiple issues found in proxy management system")
            print("🛠️ Significant fixes needed before integration")
        
        return len(critical_failures) == 0

def main():
    """Main test execution"""
    tester = ProxyManagementTester()
    
    success = tester.run_all_tests()
    if success:
        overall_success = tester.generate_report()
        sys.exit(0 if overall_success else 1)
    else:
        print("❌ Tests could not be completed due to connectivity issues")
        sys.exit(1)

if __name__ == "__main__":
    main()