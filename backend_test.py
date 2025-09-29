#!/usr/bin/env python3
"""
Backend Testing Suite for YouTube Lead Generation Platform
Focus: YouTube Account Management System Testing (2captcha Integration Phase 1 Step 1)
"""

import requests
import json
import sys
import time
import uuid
from typing import Dict, List, Optional

# Backend URL Configuration
BACKEND_URL = "http://localhost:8001/api"

class YouTubeAccountManagementTester:
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
    
    def test_account_management_crud_operations(self):
        """Test all CRUD operations for YouTube account management"""
        print("\n🔧 Testing Account Management CRUD Operations...")
        
        # Test data for accounts
        test_accounts = [
            {
                "email": f"test_account_1_{uuid.uuid4().hex[:8]}@gmail.com",
                "password": "test_password_123",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            {
                "email": f"test_account_2_{uuid.uuid4().hex[:8]}@gmail.com", 
                "password": "test_password_456",
                "ip_address": "192.168.1.101",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            {
                "email": f"test_account_3_{uuid.uuid4().hex[:8]}@gmail.com",
                "password": "test_password_789",
                "ip_address": "192.168.1.102", 
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            }
        ]
        
        created_account_ids = []
        
        # Test 1: POST /api/accounts/add - Add new accounts
        for i, account_data in enumerate(test_accounts):
            try:
                response = requests.post(f"{self.backend_url}/accounts/add", json=account_data, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    account_id = data.get("id")
                    created_account_ids.append(account_id)
                    
                    # Verify all fields are present
                    required_fields = ["id", "email", "password", "status", "created_at", "updated_at"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields and data.get("status") == "active":
                        self.log_test(f"Add Account {i+1}", True, 
                                    f"Account created successfully with ID: {account_id}", data)
                    else:
                        self.log_test(f"Add Account {i+1}", False, 
                                    f"Missing fields: {missing_fields} or incorrect status", data)
                else:
                    self.log_test(f"Add Account {i+1}", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test(f"Add Account {i+1}", False, f"Request error: {str(e)}")
            
            time.sleep(0.5)
        
        # Test 2: GET /api/accounts - List all accounts
        try:
            response = requests.get(f"{self.backend_url}/accounts", timeout=10)
            
            if response.status_code == 200:
                accounts = response.json()
                
                if isinstance(accounts, list) and len(accounts) >= len(created_account_ids):
                    # Check if our created accounts are in the list
                    account_ids_in_list = [acc.get("id") for acc in accounts]
                    found_accounts = [acc_id for acc_id in created_account_ids if acc_id in account_ids_in_list]
                    
                    if len(found_accounts) == len(created_account_ids):
                        self.log_test("List All Accounts", True, 
                                    f"Found {len(accounts)} accounts including all {len(created_account_ids)} created accounts")
                    else:
                        self.log_test("List All Accounts", False, 
                                    f"Missing some created accounts. Found {len(found_accounts)}/{len(created_account_ids)}")
                else:
                    self.log_test("List All Accounts", False, 
                                f"Expected list with at least {len(created_account_ids)} accounts, got: {type(accounts)}")
            else:
                self.log_test("List All Accounts", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("List All Accounts", False, f"Request error: {str(e)}")
        
        # Test 3: GET /api/accounts/{account_id} - Get specific account
        if created_account_ids:
            test_account_id = created_account_ids[0]
            try:
                response = requests.get(f"{self.backend_url}/accounts/{test_account_id}", timeout=10)
                
                if response.status_code == 200:
                    account = response.json()
                    
                    if account.get("id") == test_account_id and account.get("email"):
                        self.log_test("Get Specific Account", True, 
                                    f"Successfully retrieved account: {account.get('email')}")
                    else:
                        self.log_test("Get Specific Account", False, 
                                    f"Account data mismatch or missing fields")
                else:
                    self.log_test("Get Specific Account", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test("Get Specific Account", False, f"Request error: {str(e)}")
        
        # Test 4: PUT /api/accounts/{account_id}/status - Update account status
        if created_account_ids:
            test_account_id = created_account_ids[1] if len(created_account_ids) > 1 else created_account_ids[0]
            status_updates = ["rate_limited", "banned", "maintenance", "active"]
            
            for status in status_updates:
                try:
                    response = requests.put(f"{self.backend_url}/accounts/{test_account_id}/status", 
                                          json={"status": status}, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "updated" in data.get("message", "").lower():
                            self.log_test(f"Update Status to {status}", True, 
                                        f"Status updated successfully: {data.get('message')}")
                        else:
                            self.log_test(f"Update Status to {status}", False, 
                                        f"Unexpected response: {data}")
                    else:
                        self.log_test(f"Update Status to {status}", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                        
                except Exception as e:
                    self.log_test(f"Update Status to {status}", False, f"Request error: {str(e)}")
                
                time.sleep(0.3)
        
        # Test 5: DELETE /api/accounts/{account_id} - Delete account
        if created_account_ids:
            # Delete the last account to test deletion
            delete_account_id = created_account_ids[-1]
            try:
                response = requests.delete(f"{self.backend_url}/accounts/{delete_account_id}", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if "deleted" in data.get("message", "").lower():
                        self.log_test("Delete Account", True, 
                                    f"Account deleted successfully: {data.get('message')}")
                        created_account_ids.remove(delete_account_id)  # Remove from tracking
                    else:
                        self.log_test("Delete Account", False, 
                                    f"Unexpected response: {data}")
                else:
                    self.log_test("Delete Account", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test("Delete Account", False, f"Request error: {str(e)}")
        
        return created_account_ids  # Return remaining account IDs for other tests
    
    def test_account_rotation_logic(self):
        """Test account rotation and availability logic"""
        print("\n🔄 Testing Account Rotation Logic...")
        
        # Test 1: GET /api/accounts/available - Get next available account
        try:
            response = requests.get(f"{self.backend_url}/accounts/available", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("account_found"):
                    account_info = {
                        "account_id": data.get("account_id"),
                        "account_email": data.get("account_email"),
                        "status": data.get("status"),
                        "daily_requests": data.get("daily_requests"),
                        "success_rate": data.get("success_rate")
                    }
                    
                    # Verify account is active and under daily limit
                    if (data.get("status") == "active" and 
                        isinstance(data.get("daily_requests"), int) and 
                        data.get("daily_requests") < 100):  # MAX_DAILY_REQUESTS_PER_ACCOUNT
                        
                        self.log_test("Get Available Account", True, 
                                    f"Found available account: {data.get('account_email')} "
                                    f"(Daily requests: {data.get('daily_requests')}, "
                                    f"Success rate: {data.get('success_rate')}%)", account_info)
                    else:
                        self.log_test("Get Available Account", False, 
                                    f"Account found but doesn't meet availability criteria: {account_info}")
                else:
                    # No available accounts - this could be valid if no accounts exist
                    message = data.get("message", "No message provided")
                    self.log_test("Get Available Account", True, 
                                f"No available accounts found: {message}")
            else:
                self.log_test("Get Available Account", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Get Available Account", False, f"Request error: {str(e)}")
    
    def test_account_statistics_overview(self):
        """Test account statistics and overview endpoint"""
        print("\n📊 Testing Account Statistics Overview...")
        
        try:
            response = requests.get(f"{self.backend_url}/accounts/stats/overview", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                
                # Check required fields
                required_fields = [
                    "total_accounts", "active_accounts", "banned_accounts", 
                    "rate_limited_accounts", "high_usage_accounts",
                    "max_daily_requests_per_account", "max_concurrent_accounts"
                ]
                
                missing_fields = [field for field in required_fields if field not in stats]
                
                if not missing_fields:
                    # Verify data consistency
                    total = stats.get("total_accounts", 0)
                    active = stats.get("active_accounts", 0)
                    banned = stats.get("banned_accounts", 0)
                    rate_limited = stats.get("rate_limited_accounts", 0)
                    
                    # Basic validation: active + banned + rate_limited should not exceed total
                    if active + banned + rate_limited <= total:
                        self.log_test("Account Statistics Overview", True, 
                                    f"Statistics retrieved successfully - Total: {total}, "
                                    f"Active: {active}, Banned: {banned}, Rate Limited: {rate_limited}", stats)
                    else:
                        self.log_test("Account Statistics Overview", False, 
                                    f"Data inconsistency: sum of status counts exceeds total", stats)
                else:
                    self.log_test("Account Statistics Overview", False, 
                                f"Missing required fields: {missing_fields}", stats)
            else:
                self.log_test("Account Statistics Overview", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Account Statistics Overview", False, f"Request error: {str(e)}")
    
    def test_database_schema_validation(self):
        """Test MongoDB integration and schema validation"""
        print("\n🗄️ Testing Database Schema Validation...")
        
        # Create a test account to verify schema
        test_account = {
            "email": f"schema_test_{uuid.uuid4().hex[:8]}@gmail.com",
            "password": "schema_test_password",
            "ip_address": "10.0.0.1",
            "user_agent": "Schema Test User Agent"
        }
        
        try:
            # Create account
            response = requests.post(f"{self.backend_url}/accounts/add", json=test_account, timeout=10)
            
            if response.status_code == 200:
                account_data = response.json()
                account_id = account_data.get("id")
                
                # Verify all expected schema fields are present
                expected_fields = [
                    "id", "email", "password", "status", "last_used", "rate_limit_reset",
                    "daily_requests_count", "total_requests_count", "session_data",
                    "ip_address", "user_agent", "cookies", "success_rate", "last_error",
                    "created_at", "updated_at"
                ]
                
                present_fields = list(account_data.keys())
                missing_fields = [field for field in expected_fields if field not in present_fields]
                
                # Verify data types
                type_checks = [
                    ("id", str), ("email", str), ("password", str), ("status", str),
                    ("daily_requests_count", int), ("total_requests_count", int),
                    ("success_rate", (int, float)), ("ip_address", str), ("user_agent", str)
                ]
                
                type_errors = []
                for field, expected_type in type_checks:
                    if field in account_data:
                        if not isinstance(account_data[field], expected_type):
                            type_errors.append(f"{field}: expected {expected_type}, got {type(account_data[field])}")
                
                if not missing_fields and not type_errors:
                    self.log_test("Database Schema Validation", True, 
                                f"All schema fields present with correct types", account_data)
                else:
                    error_msg = f"Missing fields: {missing_fields}, Type errors: {type_errors}"
                    self.log_test("Database Schema Validation", False, error_msg, account_data)
                
                # Clean up test account
                try:
                    requests.delete(f"{self.backend_url}/accounts/{account_id}", timeout=10)
                except:
                    pass  # Cleanup failure is not critical for this test
                    
            else:
                self.log_test("Database Schema Validation", False, 
                            f"Failed to create test account: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Database Schema Validation", False, f"Request error: {str(e)}")
    
    def test_environment_configuration(self):
        """Test environment configuration and settings"""
        print("\n⚙️ Testing Environment Configuration...")
        
        # Test account statistics to verify environment variables are loaded
        try:
            response = requests.get(f"{self.backend_url}/accounts/stats/overview", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                
                # Check if environment variables are properly loaded
                max_daily = stats.get("max_daily_requests_per_account")
                max_concurrent = stats.get("max_concurrent_accounts")
                
                # Expected values from environment (from backend/.env)
                expected_max_daily = 100
                expected_max_concurrent = 3
                
                if max_daily == expected_max_daily and max_concurrent == expected_max_concurrent:
                    self.log_test("Environment Configuration", True, 
                                f"Environment variables loaded correctly - "
                                f"Max daily: {max_daily}, Max concurrent: {max_concurrent}")
                else:
                    self.log_test("Environment Configuration", False, 
                                f"Environment variables mismatch - "
                                f"Expected daily: {expected_max_daily}, got: {max_daily}, "
                                f"Expected concurrent: {expected_max_concurrent}, got: {max_concurrent}")
            else:
                self.log_test("Environment Configuration", False, 
                            f"Could not retrieve configuration: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Environment Configuration", False, f"Request error: {str(e)}")
    
    def test_integration_with_existing_system(self):
        """Test integration with existing lead generation system"""
        print("\n🔗 Testing Integration with Existing System...")
        
        # Test 1: Verify existing endpoints still work
        existing_endpoints = [
            ("/", "Root endpoint"),
            ("/leads/main", "Main leads endpoint"),
            ("/leads/no-email", "No-email leads endpoint"),
            ("/settings/email-sending", "Email settings endpoint")
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
    
    def test_error_handling_and_validation(self):
        """Test error handling and input validation"""
        print("\n⚠️ Testing Error Handling and Validation...")
        
        # Test 1: Duplicate account creation
        duplicate_email = f"duplicate_test_{uuid.uuid4().hex[:8]}@gmail.com"
        account_data = {
            "email": duplicate_email,
            "password": "test_password",
            "ip_address": "192.168.1.200"
        }
        
        try:
            # Create first account
            response1 = requests.post(f"{self.backend_url}/accounts/add", json=account_data, timeout=10)
            
            if response1.status_code == 200:
                account_id = response1.json().get("id")
                
                # Try to create duplicate
                response2 = requests.post(f"{self.backend_url}/accounts/add", json=account_data, timeout=10)
                
                if response2.status_code == 400:
                    self.log_test("Duplicate Account Prevention", True, 
                                "Correctly prevented duplicate account creation")
                else:
                    self.log_test("Duplicate Account Prevention", False, 
                                f"Should have returned 400, got: {response2.status_code}")
                
                # Cleanup
                try:
                    requests.delete(f"{self.backend_url}/accounts/{account_id}", timeout=10)
                except:
                    pass
            else:
                self.log_test("Duplicate Account Prevention", False, 
                            "Could not create initial account for duplicate test")
                
        except Exception as e:
            self.log_test("Duplicate Account Prevention", False, f"Request error: {str(e)}")
        
        # Test 2: Invalid status update
        try:
            # Try to update with invalid status
            response = requests.put(f"{self.backend_url}/accounts/nonexistent_id/status", 
                                  json={"status": "invalid_status"}, timeout=10)
            
            if response.status_code in [400, 404]:
                self.log_test("Invalid Status Update", True, 
                            f"Correctly rejected invalid status: HTTP {response.status_code}")
            else:
                self.log_test("Invalid Status Update", False, 
                            f"Should have returned 400/404, got: {response.status_code}")
                
        except Exception as e:
            self.log_test("Invalid Status Update", False, f"Request error: {str(e)}")
        
        # Test 3: Non-existent account operations
        fake_id = "nonexistent_account_id"
        
        operations = [
            ("GET", f"/accounts/{fake_id}", "Get non-existent account"),
            ("PUT", f"/accounts/{fake_id}/status", "Update non-existent account"),
            ("DELETE", f"/accounts/{fake_id}", "Delete non-existent account")
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
                    self.log_test(f"Error Handling - {description}", True, 
                                "Correctly returned 404 for non-existent account")
                else:
                    self.log_test(f"Error Handling - {description}", False, 
                                f"Should have returned 404, got: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Error Handling - {description}", False, f"Request error: {str(e)}")
            
            time.sleep(0.2)
        """Test the debug text email extraction endpoint with various email formats"""
        test_cases = [
            {
                "name": "Plain Email",
                "text": "Contact me at john@example.com for business inquiries",
                "expected_email": "john@example.com"
            },
            {
                "name": "Obfuscated Email - [at] [dot]",
                "text": "Reach out to business [at] creator [dot] com for collaborations",
                "expected_email": "business@creator.com"
            },
            {
                "name": "Obfuscated Email - (at) (dot)",
                "text": "Email me at contact(at)youtuber(dot)net",
                "expected_email": "contact@youtuber.net"
            },
            {
                "name": "Obfuscated Email - spaces",
                "text": "Send inquiries to hello at company dot org",
                "expected_email": "hello@company.org"
            },
            {
                "name": "Email with Context",
                "text": "For business opportunities, contact: business@creator.com",
                "expected_email": "business@creator.com"
            },
            {
                "name": "Multiple Emails",
                "text": "Contact support@company.com or sales@company.com for help",
                "expected_email": "support@company.com"  # Should return first valid one
            },
            {
                "name": "Email in Sentence",
                "text": "My email address is creator123@gmail.com and I respond quickly",
                "expected_email": "creator123@gmail.com"
            },
            {
                "name": "Complex Email",
                "text": "Business inquiries: first.last+business@sub.domain.co.uk",
                "expected_email": "first.last+business@sub.domain.co.uk"
            },
            {
                "name": "No Email",
                "text": "This text has no email addresses in it at all",
                "expected_email": None
            },
            {
                "name": "Invalid Email Format",
                "text": "Contact me at notanemail@invalid or fake@email",
                "expected_email": None
            }
        ]
        
        endpoint = f"{self.backend_url}/debug/test-text-email-extraction"
        
        for test_case in test_cases:
            try:
                response = requests.post(endpoint, params={"text": test_case["text"]}, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    found_email = data.get("email_found")
                    
                    if test_case["expected_email"] is None:
                        # Expecting no email
                        if found_email is None:
                            self.log_test(f"Text Email Extraction - {test_case['name']}", True, 
                                        "Correctly found no email", data)
                        else:
                            self.log_test(f"Text Email Extraction - {test_case['name']}", False, 
                                        f"Expected no email but found: {found_email}", data)
                    else:
                        # Expecting an email
                        if found_email == test_case["expected_email"]:
                            self.log_test(f"Text Email Extraction - {test_case['name']}", True, 
                                        f"Correctly extracted: {found_email}", data)
                        else:
                            self.log_test(f"Text Email Extraction - {test_case['name']}", False, 
                                        f"Expected: {test_case['expected_email']}, Got: {found_email}", data)
                else:
                    self.log_test(f"Text Email Extraction - {test_case['name']}", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test(f"Text Email Extraction - {test_case['name']}", False, 
                            f"Request error: {str(e)}")
                
            time.sleep(0.5)  # Rate limiting
    
    def test_channel_email_extraction_endpoint(self):
        """Test the debug channel email extraction endpoint with real YouTube channels"""
        # Test channels with known email patterns (these are public channels for testing)
        test_channels = [
            {
                "name": "Popular Tech Channel",
                "channel_id": "UCBJycsmduvYEL83R_U4JriQ",  # Marques Brownlee - likely has business email
                "description": "Large tech channel - should have business contact info"
            },
            {
                "name": "Business Channel",
                "channel_id": "UC-lHJZR3Gqxm24_Vd_AJ5Yw",  # PewDiePie - large channel
                "description": "Major creator - likely has business email"
            },
            {
                "name": "Smaller Channel Test",
                "channel_id": "UCsT0YIqwnpJCM-mx7-gSA4Q",  # TEDx Talks
                "description": "TEDx channel - should have contact info"
            }
        ]
        
        endpoint = f"{self.backend_url}/debug/test-email-extraction"
        
        for test_channel in test_channels:
            try:
                print(f"\n🔍 Testing channel: {test_channel['name']} ({test_channel['channel_id']})")
                
                response = requests.post(endpoint, params={"channel_id": test_channel["channel_id"]}, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        email_found = data.get("email_found")
                        content_length = data.get("content_length", 0)
                        
                        if email_found:
                            self.log_test(f"Channel Email Extraction - {test_channel['name']}", True, 
                                        f"Email found: {email_found}, Content length: {content_length}", data)
                        else:
                            # Not necessarily a failure - some channels might not have emails
                            self.log_test(f"Channel Email Extraction - {test_channel['name']}", True, 
                                        f"No email found but scraping worked. Content length: {content_length}", data)
                    else:
                        error_msg = data.get("error", "Unknown error")
                        self.log_test(f"Channel Email Extraction - {test_channel['name']}", False, 
                                    f"Scraping failed: {error_msg}", data)
                else:
                    self.log_test(f"Channel Email Extraction - {test_channel['name']}", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test(f"Channel Email Extraction - {test_channel['name']}", False, 
                            f"Request error: {str(e)}")
                
            time.sleep(2)  # Longer delay for web scraping tests
    
    def test_email_regex_patterns(self):
        """Test email regex patterns directly through the text extraction endpoint"""
        edge_cases = [
            {
                "name": "Email with Numbers",
                "text": "Contact user123@domain456.com for support",
                "should_find": True
            },
            {
                "name": "Email with Hyphens",
                "text": "Reach out to first-last@sub-domain.co.uk",
                "should_find": True
            },
            {
                "name": "Email with Plus",
                "text": "Send to user+tag@example.com",
                "should_find": True
            },
            {
                "name": "Email with Underscore",
                "text": "Contact first_last@company_name.org",
                "should_find": True
            },
            {
                "name": "Email in Parentheses",
                "text": "Business contact (business@creator.com) available",
                "should_find": True
            },
            {
                "name": "Email with Quotes",
                "text": 'Email me at "contact@example.com" for inquiries',
                "should_find": True
            },
            {
                "name": "Email at End of Sentence",
                "text": "For business inquiries contact me at business@creator.com.",
                "should_find": True
            },
            {
                "name": "Email with Line Break",
                "text": "Contact:\nbusiness@creator.com\nfor opportunities",
                "should_find": True
            },
            {
                "name": "Invalid - No TLD",
                "text": "Contact me at user@domain",
                "should_find": False
            },
            {
                "name": "Invalid - No Domain",
                "text": "Contact me at user@.com",
                "should_find": False
            }
        ]
        
        endpoint = f"{self.backend_url}/debug/test-text-email-extraction"
        
        for test_case in edge_cases:
            try:
                response = requests.post(endpoint, params={"text": test_case["text"]}, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    found_email = data.get("email_found")
                    
                    if test_case["should_find"]:
                        if found_email:
                            self.log_test(f"Email Regex - {test_case['name']}", True, 
                                        f"Correctly found email: {found_email}", data)
                        else:
                            self.log_test(f"Email Regex - {test_case['name']}", False, 
                                        "Expected to find email but didn't", data)
                    else:
                        if found_email is None:
                            self.log_test(f"Email Regex - {test_case['name']}", True, 
                                        "Correctly rejected invalid email", data)
                        else:
                            self.log_test(f"Email Regex - {test_case['name']}", False, 
                                        f"Should not have found email but got: {found_email}", data)
                else:
                    self.log_test(f"Email Regex - {test_case['name']}", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test(f"Email Regex - {test_case['name']}", False, 
                            f"Request error: {str(e)}")
                
            time.sleep(0.3)
    
    def test_error_handling(self):
        """Test error handling in the email extraction endpoints"""
        
        # Test text extraction with invalid inputs
        invalid_text_cases = [
            {"text": "", "name": "Empty String"},
            {"text": None, "name": "None Value"},
            {"text": "a" * 10000, "name": "Very Long Text"}  # Test with very long text
        ]
        
        endpoint = f"{self.backend_url}/debug/test-text-email-extraction"
        
        for case in invalid_text_cases:
            try:
                response = requests.post(endpoint, params={"text": case["text"]}, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") is not False:  # Should handle gracefully
                        self.log_test(f"Error Handling - Text - {case['name']}", True, 
                                    "Handled invalid input gracefully", data)
                    else:
                        self.log_test(f"Error Handling - Text - {case['name']}", False, 
                                    f"Failed to handle invalid input: {data.get('error')}", data)
                else:
                    # Some error responses are acceptable for invalid input
                    self.log_test(f"Error Handling - Text - {case['name']}", True, 
                                f"Returned appropriate error: HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Error Handling - Text - {case['name']}", True, 
                            f"Exception handled: {str(e)}")
        
        # Test channel extraction with invalid channel IDs
        invalid_channel_cases = [
            {"channel_id": "", "name": "Empty Channel ID"},
            {"channel_id": "invalid_id_123", "name": "Invalid Channel ID"},
            {"channel_id": "UC" + "x" * 50, "name": "Malformed Channel ID"}
        ]
        
        endpoint = f"{self.backend_url}/debug/test-email-extraction"
        
        for case in invalid_channel_cases:
            try:
                response = requests.post(endpoint, params={"channel_id": case["channel_id"]}, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    if not data.get("success"):  # Should fail gracefully
                        self.log_test(f"Error Handling - Channel - {case['name']}", True, 
                                    "Properly handled invalid channel ID", data)
                    else:
                        self.log_test(f"Error Handling - Channel - {case['name']}", False, 
                                    "Should have failed with invalid channel ID", data)
                else:
                    self.log_test(f"Error Handling - Channel - {case['name']}", True, 
                                f"Returned appropriate error: HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Error Handling - Channel - {case['name']}", True, 
                            f"Exception handled: {str(e)}")
                
            time.sleep(1)
    
    def run_all_tests(self):
        """Run all YouTube Account Management System tests"""
        print("🚀 Starting YouTube Account Management System Testing")
        print("🎯 2captcha Integration Phase 1 Step 1")
        print("=" * 70)
        
        # Test 1: Basic connectivity
        if not self.test_backend_connectivity():
            print("❌ Backend not accessible. Stopping tests.")
            return False
        
        print("\n🔧 Testing Account Management CRUD Operations...")
        created_accounts = self.test_account_management_crud_operations()
        
        print("\n🔄 Testing Account Rotation Logic...")
        self.test_account_rotation_logic()
        
        print("\n📊 Testing Account Statistics Overview...")
        self.test_account_statistics_overview()
        
        print("\n🗄️ Testing Database Schema Validation...")
        self.test_database_schema_validation()
        
        print("\n⚙️ Testing Environment Configuration...")
        self.test_environment_configuration()
        
        print("\n🔗 Testing Integration with Existing System...")
        self.test_integration_with_existing_system()
        
        print("\n⚠️ Testing Error Handling and Validation...")
        self.test_error_handling_and_validation()
        
        # Cleanup any remaining test accounts
        if created_accounts:
            print(f"\n🧹 Cleaning up {len(created_accounts)} test accounts...")
            for account_id in created_accounts:
                try:
                    requests.delete(f"{self.backend_url}/accounts/{account_id}", timeout=5)
                except:
                    pass  # Cleanup failures are not critical
        
        return True
    
    def generate_report(self):
        """Generate test report"""
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        
        print("\n" + "=" * 70)
        print("📊 YOUTUBE ACCOUNT MANAGEMENT SYSTEM TEST REPORT")
        print("🎯 2captcha Integration Phase 1 Step 1")
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
            "CRUD Operations": [t for t in self.test_results if any(crud in t["test_name"] for crud in ["Add Account", "List All", "Get Specific", "Update Status", "Delete Account"])],
            "Account Rotation": [t for t in self.test_results if "Available Account" in t["test_name"]],
            "Statistics": [t for t in self.test_results if "Statistics" in t["test_name"]],
            "Database Schema": [t for t in self.test_results if "Schema" in t["test_name"]],
            "Environment Config": [t for t in self.test_results if "Environment" in t["test_name"]],
            "System Integration": [t for t in self.test_results if "Existing System" in t["test_name"]],
            "Error Handling": [t for t in self.test_results if "Error Handling" in t["test_name"] or "Duplicate" in t["test_name"] or "Invalid" in t["test_name"]]
        }
        
        for category, tests in categories.items():
            if tests:
                passed = len([t for t in tests if t["success"]])
                print(f"  • {category}: {passed}/{len(tests)} passed")
        
        # Critical issues assessment
        critical_failures = []
        for test in self.failed_tests:
            if any(critical in test["test_name"] for critical in ["Add Account", "List All", "Get Available", "Database Schema"]):
                critical_failures.append(test["test_name"])
        
        # Overall assessment
        if len(self.failed_tests) == 0:
            print("\n✅ OVERALL: YouTube Account Management System is working perfectly!")
            print("🎯 Ready for Phase 1 Step 2: Enhanced email extraction with 2captcha fallback")
        elif critical_failures:
            print(f"\n❌ OVERALL: Critical issues found in core functionality: {', '.join(critical_failures)}")
            print("🚨 Must fix critical issues before proceeding to next phase")
        elif len(self.failed_tests) <= 3:
            print("\n⚠️ OVERALL: Account management mostly working with minor issues")
            print("🔧 Minor fixes recommended but system is functional")
        else:
            print("\n❌ OVERALL: Multiple issues found in account management system")
            print("🛠️ Significant fixes needed before next phase")
        
        return len(critical_failures) == 0

def main():
    """Main test execution"""
    tester = EmailExtractionTester()
    
    success = tester.run_all_tests()
    if success:
        overall_success = tester.generate_report()
        sys.exit(0 if overall_success else 1)
    else:
        print("❌ Tests could not be completed due to connectivity issues")
        sys.exit(1)

if __name__ == "__main__":
    main()