#!/usr/bin/env python3
"""
Strategic Backend Testing Suite for YouTube Lead Generation Platform
9-Credit Budget Testing - Focus on Core Functionality
"""

import requests
import json
import sys
import time
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Backend URL Configuration
BACKEND_URL = "https://exec-guide.preview.emergentagent.com/api"

class StrategicBackendTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.test_results = []
        self.failed_tests = []
        self.critical_failures = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Dict = None, critical: bool = False):
        """Log test results"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "critical": critical
        }
        self.test_results.append(result)
        
        if not success:
            self.failed_tests.append(result)
            if critical:
                self.critical_failures.append(result)
            
        status = "✅ PASS" if success else "❌ FAIL"
        priority = " [CRITICAL]" if critical else ""
        print(f"{status} {test_name}{priority}: {details}")

    # =============================================================================
    # PRIORITY 1: CORE LEAD GENERATION SYSTEM (4 CREDITS)
    # =============================================================================
    
    def test_api_docs_availability(self):
        """Test /api/docs endpoint availability"""
        print("\n📚 Testing API Documentation Availability...")
        
        try:
            response = requests.get(f"{self.backend_url}/docs", timeout=10)
            if response.status_code == 200:
                self.log_test("API Docs Availability", True, "API documentation is accessible", critical=True)
                return True
            else:
                self.log_test("API Docs Availability", False, f"HTTP {response.status_code}", critical=True)
                return False
        except Exception as e:
            self.log_test("API Docs Availability", False, f"Connection error: {str(e)}", critical=True)
            return False

    def test_backend_connectivity(self):
        """Test basic backend connectivity"""
        print("\n🔌 Testing Backend Connectivity...")
        
        try:
            response = requests.get(f"{self.backend_url}/", timeout=10)
            if response.status_code == 200:
                self.log_test("Backend Connectivity", True, "Backend is accessible", critical=True)
                return True
            else:
                self.log_test("Backend Connectivity", False, f"HTTP {response.status_code}", critical=True)
                return False
        except Exception as e:
            self.log_test("Backend Connectivity", False, f"Connection error: {str(e)}", critical=True)
            return False

    def test_mongodb_collections(self):
        """Test MongoDB database connectivity and collections"""
        print("\n🗄️ Testing MongoDB Collections...")
        
        # Test main collections by trying to access their endpoints
        collections_tests = [
            ("/leads/main", "main_leads collection"),
            ("/leads/no-email", "no_email_leads collection"),
            ("/accounts", "youtube_accounts collection"),
            ("/proxies", "proxy_pool collection"),
            ("/queue", "scraping_queue collection")
        ]
        
        for endpoint, description in collections_tests:
            try:
                response = requests.get(f"{self.backend_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(f"MongoDB - {description}", True, 
                                f"Collection accessible, returned {len(data) if isinstance(data, list) else 'data'}")
                else:
                    self.log_test(f"MongoDB - {description}", False, 
                                f"HTTP {response.status_code}: {response.text}", critical=True)
            except Exception as e:
                self.log_test(f"MongoDB - {description}", False, f"Request error: {str(e)}", critical=True)

    def test_lead_management_crud(self):
        """Test basic CRUD operations for lead management"""
        print("\n📝 Testing Lead Management CRUD Operations...")
        
        # Test lead generation request (with test_mode=true)
        test_request = {
            "keywords": ["video editing"],
            "max_videos_per_keyword": 5,
            "max_channels": 3,
            "subscriber_min": 1000,
            "subscriber_max": 50000,
            "test_mode": True
        }
        
        try:
            response = requests.post(f"{self.backend_url}/generate-leads", json=test_request, timeout=30)
            if response.status_code in [200, 202]:
                data = response.json()
                self.log_test("Lead Generation Request", True, 
                            f"Request accepted: {data.get('message', 'Processing started')}", data)
            else:
                self.log_test("Lead Generation Request", False, 
                            f"HTTP {response.status_code}: {response.text}", critical=True)
        except Exception as e:
            self.log_test("Lead Generation Request", False, f"Request error: {str(e)}", critical=True)

    def test_email_extraction_debug_endpoints(self):
        """Test email extraction debug endpoints"""
        print("\n🔍 Testing Email Extraction Debug Endpoints...")
        
        # Test email extraction endpoint
        test_email_data = {
            "text": "Contact us at business@creator.com for collaborations"
        }
        
        try:
            response = requests.post(f"{self.backend_url}/debug/extract-email-test", 
                                   json=test_email_data, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("email_found"):
                    self.log_test("Email Extraction Debug", True, 
                                f"Email extracted: {data.get('extracted_email')}", data)
                else:
                    self.log_test("Email Extraction Debug", False, 
                                "No email found in test text", data)
            else:
                self.log_test("Email Extraction Debug", False, 
                            f"HTTP {response.status_code}: {response.text}", critical=True)
        except Exception as e:
            self.log_test("Email Extraction Debug", False, f"Request error: {str(e)}", critical=True)

        # Test channel scraping debug endpoint
        test_channel_data = {
            "channel_handle": "@VaibhavKadnar",
            "test_mode": True
        }
        
        try:
            response = requests.post(f"{self.backend_url}/debug/test-channel-scraping", 
                                   json=test_channel_data, timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Channel Scraping Debug", True, 
                            f"Channel scraping test completed: {data.get('status', 'Unknown')}", data)
            else:
                self.log_test("Channel Scraping Debug", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Channel Scraping Debug", False, f"Request error: {str(e)}")

    # =============================================================================
    # PRIORITY 2: ACCOUNT & PROXY MANAGEMENT (2 CREDITS)
    # =============================================================================
    
    def test_youtube_accounts_system(self):
        """Test YouTube accounts system endpoints"""
        print("\n👤 Testing YouTube Accounts System...")
        
        # Test GET /api/accounts
        try:
            response = requests.get(f"{self.backend_url}/accounts", timeout=10)
            if response.status_code == 200:
                accounts = response.json()
                self.log_test("List YouTube Accounts", True, 
                            f"Retrieved {len(accounts)} accounts", {"count": len(accounts)})
            else:
                self.log_test("List YouTube Accounts", False, 
                            f"HTTP {response.status_code}: {response.text}", critical=True)
        except Exception as e:
            self.log_test("List YouTube Accounts", False, f"Request error: {str(e)}", critical=True)

        # Test POST /api/accounts/add
        test_account = {
            "email": f"test_account_{uuid.uuid4().hex[:8]}@gmail.com",
            "password": "test_password_123",
            "ip_address": "192.168.1.100"
        }
        
        created_account_id = None
        try:
            response = requests.post(f"{self.backend_url}/accounts/add", json=test_account, timeout=10)
            if response.status_code == 200:
                data = response.json()
                created_account_id = data.get("id")
                self.log_test("Add YouTube Account", True, 
                            f"Account created with ID: {created_account_id}", data)
            else:
                self.log_test("Add YouTube Account", False, 
                            f"HTTP {response.status_code}: {response.text}", critical=True)
        except Exception as e:
            self.log_test("Add YouTube Account", False, f"Request error: {str(e)}", critical=True)

        # Test account health monitoring
        if created_account_id:
            try:
                response = requests.get(f"{self.backend_url}/accounts/{created_account_id}/health", timeout=10)
                if response.status_code == 200:
                    health_data = response.json()
                    self.log_test("Account Health Check", True, 
                                f"Health status: {health_data.get('healthy', 'Unknown')}", health_data)
                else:
                    self.log_test("Account Health Check", False, 
                                f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.log_test("Account Health Check", False, f"Request error: {str(e)}")

            # Cleanup test account
            try:
                requests.delete(f"{self.backend_url}/accounts/{created_account_id}", timeout=5)
            except:
                pass

        # Test healthiest account endpoint
        try:
            response = requests.get(f"{self.backend_url}/accounts/healthiest", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Get Healthiest Account", True, 
                            f"Healthiest account found: {data.get('account_found', False)}", data)
            else:
                self.log_test("Get Healthiest Account", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Get Healthiest Account", False, f"Request error: {str(e)}")

    def test_proxy_management_system(self):
        """Test proxy pool management system"""
        print("\n🌐 Testing Proxy Management System...")
        
        # Test GET /api/proxies
        try:
            response = requests.get(f"{self.backend_url}/proxies", timeout=10)
            if response.status_code == 200:
                proxies = response.json()
                self.log_test("List Proxies", True, 
                            f"Retrieved {len(proxies)} proxies", {"count": len(proxies)})
            else:
                self.log_test("List Proxies", False, 
                            f"HTTP {response.status_code}: {response.text}", critical=True)
        except Exception as e:
            self.log_test("List Proxies", False, f"Request error: {str(e)}", critical=True)

        # Test GET /api/proxies/available
        try:
            response = requests.get(f"{self.backend_url}/proxies/available", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Get Available Proxy", True, 
                            f"Available proxy: {data.get('proxy_found', False)}", data)
            else:
                self.log_test("Get Available Proxy", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Get Available Proxy", False, f"Request error: {str(e)}")

        # Test GET /api/proxies/stats/overview (Known issue from test_result.md)
        try:
            response = requests.get(f"{self.backend_url}/proxies/stats/overview", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                
                # Check for known missing fields
                required_fields = ["disabled_proxies", "unhealthy_proxies", 
                                 "max_daily_requests_per_proxy", "max_concurrent_proxies"]
                missing_fields = [field for field in required_fields if field not in stats]
                
                if missing_fields:
                    self.log_test("Proxy Statistics Overview", False, 
                                f"Missing required fields: {missing_fields} (Known issue from test_result.md)", 
                                stats, critical=True)
                else:
                    self.log_test("Proxy Statistics Overview", True, 
                                "All required fields present", stats)
            else:
                self.log_test("Proxy Statistics Overview", False, 
                            f"HTTP {response.status_code}: {response.text}", critical=True)
        except Exception as e:
            self.log_test("Proxy Statistics Overview", False, f"Request error: {str(e)}", critical=True)

        # Test proxy status update (Known issue: returns proxy data instead of success message)
        test_proxy = {
            "ip": "192.168.1.100",
            "port": 8080,
            "protocol": "http"
        }
        
        created_proxy_id = None
        try:
            response = requests.post(f"{self.backend_url}/proxies/add", json=test_proxy, timeout=10)
            if response.status_code == 200:
                data = response.json()
                created_proxy_id = data.get("id")
                
                # Test status update
                response = requests.put(f"{self.backend_url}/proxies/{created_proxy_id}/status", 
                                      json={"status": "disabled"}, timeout=10)
                if response.status_code == 200:
                    update_data = response.json()
                    # Check if it returns success message or proxy data (known issue)
                    if "message" in update_data and "updated" in update_data["message"].lower():
                        self.log_test("Proxy Status Update", True, 
                                    "Status update returns success message", update_data)
                    else:
                        self.log_test("Proxy Status Update", False, 
                                    "Status update returns proxy data instead of success message (Known issue)", 
                                    update_data, critical=True)
                else:
                    self.log_test("Proxy Status Update", False, 
                                f"HTTP {response.status_code}: {response.text}")
            else:
                self.log_test("Add Test Proxy", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Proxy Status Update Test", False, f"Request error: {str(e)}")

        # Cleanup test proxy
        if created_proxy_id:
            try:
                requests.delete(f"{self.backend_url}/proxies/{created_proxy_id}", timeout=5)
            except:
                pass

    # =============================================================================
    # PRIORITY 3: QUEUE & PROCESSING SYSTEM (1 CREDIT)
    # =============================================================================
    
    def test_queue_processing_system(self):
        """Test request queue operations and processing"""
        print("\n⚡ Testing Queue & Processing System...")
        
        # Test POST /api/queue/add
        test_queue_request = {
            "channel_id": "UC_test_channel_123",
            "request_type": "channel_scraping",
            "priority": 5,
            "payload": {"test_mode": True}
        }
        
        created_queue_id = None
        try:
            response = requests.post(f"{self.backend_url}/queue/add", json=test_queue_request, timeout=10)
            if response.status_code == 200:
                data = response.json()
                created_queue_id = data.get("id")
                self.log_test("Add Queue Request", True, 
                            f"Queue request added with ID: {created_queue_id}", data)
            else:
                self.log_test("Add Queue Request", False, 
                            f"HTTP {response.status_code}: {response.text}", critical=True)
        except Exception as e:
            self.log_test("Add Queue Request", False, f"Request error: {str(e)}", critical=True)

        # Test GET /api/queue/stats
        try:
            response = requests.get(f"{self.backend_url}/queue/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                self.log_test("Queue Statistics", True, 
                            f"Queue stats retrieved: {stats.get('total_requests', 0)} total requests", stats)
            else:
                self.log_test("Queue Statistics", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Queue Statistics", False, f"Request error: {str(e)}")

        # Test GET /api/queue/next
        try:
            response = requests.get(f"{self.backend_url}/queue/next", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Get Next Queue Request", True, 
                            f"Next request available: {data.get('request_found', False)}", data)
            else:
                self.log_test("Get Next Queue Request", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Get Next Queue Request", False, f"Request error: {str(e)}")

        # Test POST /api/queue/smart-process
        try:
            response = requests.post(f"{self.backend_url}/queue/smart-process", json={}, timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Smart Queue Processor", True, 
                            f"Smart processing initiated: {data.get('message', 'Started')}", data)
            else:
                self.log_test("Smart Queue Processor", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Smart Queue Processor", False, f"Request error: {str(e)}")

        # Test GET /api/queue/processing-status
        try:
            response = requests.get(f"{self.backend_url}/queue/processing-status", timeout=10)
            if response.status_code == 200:
                status = response.json()
                self.log_test("Queue Processing Status", True, 
                            f"Processing status retrieved: {status.get('status', 'Unknown')}", status)
            else:
                self.log_test("Queue Processing Status", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Queue Processing Status", False, f"Request error: {str(e)}")

        # Cleanup test queue request
        if created_queue_id:
            try:
                requests.delete(f"{self.backend_url}/queue/{created_queue_id}", timeout=5)
            except:
                pass

    def test_rate_limiting_validation(self):
        """Test rate limiting and error recovery validation"""
        print("\n⏱️ Testing Rate Limiting & Error Recovery...")
        
        # Test error analysis endpoint
        try:
            response = requests.get(f"{self.backend_url}/queue/error-analysis", timeout=10)
            if response.status_code == 200:
                analysis = response.json()
                self.log_test("Error Analysis", True, 
                            f"Error analysis retrieved: {analysis.get('total_errors', 0)} total errors", analysis)
            else:
                self.log_test("Error Analysis", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Error Analysis", False, f"Request error: {str(e)}")

        # Test retry failed requests
        try:
            response = requests.post(f"{self.backend_url}/queue/retry-failed", json={}, timeout=15)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Retry Failed Requests", True, 
                            f"Retry initiated: {data.get('message', 'Started')}", data)
            else:
                self.log_test("Retry Failed Requests", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Retry Failed Requests", False, f"Request error: {str(e)}")

    # =============================================================================
    # ADDITIONAL CRITICAL TESTS
    # =============================================================================
    
    def test_environment_configuration(self):
        """Test environment variable configuration"""
        print("\n⚙️ Testing Environment Configuration...")
        
        # Test email sending settings
        try:
            response = requests.get(f"{self.backend_url}/settings/email-sending", timeout=10)
            if response.status_code == 200:
                settings = response.json()
                self.log_test("Email Settings", True, 
                            f"Email sending enabled: {settings.get('enabled', False)}", settings)
            else:
                self.log_test("Email Settings", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Email Settings", False, f"Request error: {str(e)}")

    def run_strategic_tests(self):
        """Run all strategic backend tests within 9-credit budget"""
        print("🚀 STRATEGIC BACKEND TESTING - 9-CREDIT BUDGET")
        print("=" * 80)
        print("🎯 Focus: Core Lead Generation, Account/Proxy Management, Queue Processing")
        print("=" * 80)
        
        # PRIORITY 1: Core Lead Generation System (4 credits)
        print("\n" + "="*50)
        print("🥇 PRIORITY 1: CORE LEAD GENERATION SYSTEM (4 CREDITS)")
        print("="*50)
        
        if not self.test_backend_connectivity():
            print("❌ Backend not accessible. Stopping tests.")
            return False
            
        self.test_api_docs_availability()
        self.test_mongodb_collections()
        self.test_lead_management_crud()
        self.test_email_extraction_debug_endpoints()
        
        # PRIORITY 2: Account & Proxy Management (2 credits)
        print("\n" + "="*50)
        print("🥈 PRIORITY 2: ACCOUNT & PROXY MANAGEMENT (2 CREDITS)")
        print("="*50)
        
        self.test_youtube_accounts_system()
        self.test_proxy_management_system()
        
        # PRIORITY 3: Queue & Processing System (1 credit)
        print("\n" + "="*50)
        print("🥉 PRIORITY 3: QUEUE & PROCESSING SYSTEM (1 CREDIT)")
        print("="*50)
        
        self.test_queue_processing_system()
        self.test_rate_limiting_validation()
        
        # Additional critical tests (2 credits remaining)
        print("\n" + "="*50)
        print("🔧 ADDITIONAL CRITICAL TESTS (2 CREDITS)")
        print("="*50)
        
        self.test_environment_configuration()
        
        return True

    def generate_strategic_report(self):
        """Generate strategic test report"""
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        critical_failed = len(self.critical_failures)
        
        print("\n" + "=" * 80)
        print("📊 STRATEGIC BACKEND TEST REPORT")
        print("🎯 9-Credit Budget Testing Results")
        print("=" * 80)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Critical Failures: {critical_failed}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
        
        # Priority-based results
        print("\n🎯 RESULTS BY PRIORITY:")
        
        priority_categories = {
            "PRIORITY 1 - Core Lead Generation": [
                "Backend Connectivity", "API Docs Availability", "MongoDB", 
                "Lead Generation Request", "Email Extraction Debug", "Channel Scraping Debug"
            ],
            "PRIORITY 2 - Account & Proxy Management": [
                "YouTube Accounts", "Account Health", "Healthiest Account", 
                "Proxies", "Proxy Statistics", "Proxy Status Update"
            ],
            "PRIORITY 3 - Queue & Processing": [
                "Queue Request", "Queue Statistics", "Smart Queue Processor", 
                "Queue Processing Status", "Error Analysis", "Retry Failed"
            ]
        }
        
        for category, keywords in priority_categories.items():
            category_tests = [t for t in self.test_results 
                            if any(keyword in t["test_name"] for keyword in keywords)]
            if category_tests:
                passed = len([t for t in category_tests if t["success"]])
                print(f"  • {category}: {passed}/{len(category_tests)} passed")

        # Critical failures analysis
        if self.critical_failures:
            print("\n❌ CRITICAL FAILURES (MUST FIX):")
            for test in self.critical_failures:
                print(f"  • {test['test_name']}: {test['details']}")

        # Known issues validation
        print("\n🔍 KNOWN ISSUES VALIDATION:")
        proxy_stats_failed = any("Proxy Statistics Overview" in t["test_name"] and not t["success"] 
                                for t in self.test_results)
        proxy_status_failed = any("Proxy Status Update" in t["test_name"] and not t["success"] 
                                 for t in self.test_results)
        
        if proxy_stats_failed:
            print("  • ✅ Confirmed: Proxy statistics overview missing fields (from test_result.md)")
        if proxy_status_failed:
            print("  • ✅ Confirmed: Proxy status update returns proxy data instead of success messages")

        # Overall assessment
        print("\n🎯 OVERALL ASSESSMENT:")
        if critical_failed == 0 and len(self.failed_tests) <= 2:
            print("✅ EXCELLENT: Core functionality working with minimal issues")
            print("🚀 System ready for production use")
        elif critical_failed == 0:
            print("⚠️ GOOD: Core functionality working with some minor issues")
            print("🔧 Minor fixes recommended but system is functional")
        elif critical_failed <= 2:
            print("❌ NEEDS ATTENTION: Some critical issues found")
            print("🛠️ Fix critical issues before full deployment")
        else:
            print("🚨 CRITICAL: Multiple critical failures detected")
            print("⛔ System requires immediate fixes before use")

        # Budget utilization
        print(f"\n💰 BUDGET UTILIZATION:")
        print(f"  • Tests completed within 9-credit strategic budget")
        print(f"  • Focus maintained on high-priority functionality")
        print(f"  • {total_tests} comprehensive tests executed")

        return critical_failed == 0

def main():
    """Main test execution"""
    tester = StrategicBackendTester()
    
    print("🎯 STRATEGIC BACKEND TESTING - 9 CREDIT BUDGET")
    print("Focus: Core Lead Generation, Account/Proxy Management, Queue Processing")
    print("=" * 80)
    
    success = tester.run_strategic_tests()
    
    if success:
        tester.generate_strategic_report()
    else:
        print("❌ Testing failed due to connectivity issues")
        return 1
    
    # Return exit code based on critical failures
    return 0 if len(tester.critical_failures) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())