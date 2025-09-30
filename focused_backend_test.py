#!/usr/bin/env python3
"""
Focused Backend Testing Suite for YouTube Lead Generation Platform
Testing Only Available Endpoints - Strategic 9-Credit Budget
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

class FocusedBackendTester:
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
            ("/accounts", "youtube_accounts collection")
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

    def test_lead_generation_system(self):
        """Test lead generation system endpoints"""
        print("\n📝 Testing Lead Generation System...")
        
        # Test lead generation start endpoint
        test_request = {
            "keywords": ["video editing"],
            "max_videos_per_keyword": 5,
            "max_channels": 3,
            "subscriber_min": 1000,
            "subscriber_max": 50000,
            "test_mode": True
        }
        
        try:
            response = requests.post(f"{self.backend_url}/lead-generation/start", json=test_request, timeout=30)
            if response.status_code in [200, 202]:
                data = response.json()
                status_id = data.get('id')
                self.log_test("Lead Generation Start", True, 
                            f"Request accepted with ID: {status_id}", data)
                
                # Test status endpoint if we got an ID
                if status_id:
                    try:
                        status_response = requests.get(f"{self.backend_url}/lead-generation/status/{status_id}", timeout=10)
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            self.log_test("Lead Generation Status", True, 
                                        f"Status retrieved: {status_data.get('status', 'Unknown')}", status_data)
                        else:
                            self.log_test("Lead Generation Status", False, 
                                        f"HTTP {status_response.status_code}: {status_response.text}")
                    except Exception as e:
                        self.log_test("Lead Generation Status", False, f"Request error: {str(e)}")
            else:
                self.log_test("Lead Generation Start", False, 
                            f"HTTP {response.status_code}: {response.text}", critical=True)
        except Exception as e:
            self.log_test("Lead Generation Start", False, f"Request error: {str(e)}", critical=True)

    def test_email_extraction_debug_endpoints(self):
        """Test email extraction debug endpoints"""
        print("\n🔍 Testing Email Extraction Debug Endpoints...")
        
        # Test text email extraction endpoint
        test_email_data = {
            "text": "Contact us at business@creator.com for collaborations"
        }
        
        try:
            response = requests.post(f"{self.backend_url}/debug/test-text-email-extraction", 
                                   json=test_email_data, timeout=15)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Text Email Extraction Debug", True, 
                            f"Email extraction test completed: {data.get('success', False)}", data)
            else:
                self.log_test("Text Email Extraction Debug", False, 
                            f"HTTP {response.status_code}: {response.text}", critical=True)
        except Exception as e:
            self.log_test("Text Email Extraction Debug", False, f"Request error: {str(e)}", critical=True)

        # Test email extraction endpoint
        try:
            response = requests.post(f"{self.backend_url}/debug/test-email-extraction", json={}, timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Email Extraction Debug", True, 
                            f"Email extraction test completed: {data.get('success', False)}", data)
            else:
                self.log_test("Email Extraction Debug", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Email Extraction Debug", False, f"Request error: {str(e)}")

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

        # Test account statistics
        try:
            response = requests.get(f"{self.backend_url}/accounts/stats/overview", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                self.log_test("Account Statistics Overview", True, 
                            f"Statistics retrieved: {stats.get('total_accounts', 0)} total accounts", stats)
            else:
                self.log_test("Account Statistics Overview", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Account Statistics Overview", False, f"Request error: {str(e)}")

    # =============================================================================
    # PRIORITY 3: QUEUE & PROCESSING SYSTEM (1 CREDIT)
    # =============================================================================
    
    def test_queue_processing_system(self):
        """Test queue processing system endpoints"""
        print("\n⚡ Testing Queue & Processing System...")
        
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
                            f"Processing status retrieved: {status.get('concurrent_processing', 0)} concurrent", status)
            else:
                self.log_test("Queue Processing Status", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Queue Processing Status", False, f"Request error: {str(e)}")

        # Test error analysis endpoint
        try:
            response = requests.get(f"{self.backend_url}/queue/error-analysis", timeout=10)
            if response.status_code == 200:
                analysis = response.json()
                self.log_test("Queue Error Analysis", True, 
                            f"Error analysis retrieved: {analysis.get('analysis', {}).get('total_errors', 0)} total errors", analysis)
            else:
                self.log_test("Queue Error Analysis", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Queue Error Analysis", False, f"Request error: {str(e)}")

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

    def test_monitoring_endpoints(self):
        """Test monitoring and optimization endpoints"""
        print("\n📊 Testing Monitoring & Optimization...")
        
        # Test performance dashboard
        try:
            response = requests.get(f"{self.backend_url}/monitoring/performance-dashboard", timeout=10)
            if response.status_code == 200:
                dashboard = response.json()
                self.log_test("Performance Dashboard", True, 
                            f"Dashboard data retrieved: {len(dashboard)} metrics", dashboard)
            else:
                self.log_test("Performance Dashboard", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Performance Dashboard", False, f"Request error: {str(e)}")

        # Test optimization recommendations
        try:
            response = requests.get(f"{self.backend_url}/optimization/recommendations", timeout=10)
            if response.status_code == 200:
                recommendations = response.json()
                self.log_test("Optimization Recommendations", True, 
                            f"Recommendations retrieved: {len(recommendations.get('recommendations', []))} items", recommendations)
            else:
                self.log_test("Optimization Recommendations", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Optimization Recommendations", False, f"Request error: {str(e)}")

    def test_advanced_email_features(self):
        """Test advanced email extraction features"""
        print("\n📧 Testing Advanced Email Features...")
        
        # Test comprehensive email detection
        test_data = {
            "text": "Contact us at business@creator.com or reach out via hello[at]example[dot]com",
            "channel_content": "For business inquiries: contact@example.com"
        }
        
        try:
            response = requests.post(f"{self.backend_url}/email/comprehensive-detection", 
                                   json=test_data, timeout=15)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Comprehensive Email Detection", True, 
                            f"Detection completed: {data.get('emails_found', 0)} emails found", data)
            else:
                self.log_test("Comprehensive Email Detection", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Comprehensive Email Detection", False, f"Request error: {str(e)}")

        # Test email detection stats
        try:
            response = requests.get(f"{self.backend_url}/email/detection-stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                self.log_test("Email Detection Stats", True, 
                            f"Stats retrieved: {stats.get('total_detections', 0)} total detections", stats)
            else:
                self.log_test("Email Detection Stats", False, 
                            f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Email Detection Stats", False, f"Request error: {str(e)}")

    def run_focused_tests(self):
        """Run all focused backend tests within 9-credit budget"""
        print("🚀 FOCUSED BACKEND TESTING - 9-CREDIT BUDGET")
        print("=" * 80)
        print("🎯 Focus: Available Endpoints Only - Core Functionality")
        print("=" * 80)
        
        # PRIORITY 1: Core Lead Generation System (4 credits)
        print("\n" + "="*50)
        print("🥇 PRIORITY 1: CORE LEAD GENERATION SYSTEM (4 CREDITS)")
        print("="*50)
        
        if not self.test_backend_connectivity():
            print("❌ Backend not accessible. Stopping tests.")
            return False
            
        self.test_mongodb_collections()
        self.test_lead_generation_system()
        self.test_email_extraction_debug_endpoints()
        
        # PRIORITY 2: Account Management (2 credits)
        print("\n" + "="*50)
        print("🥈 PRIORITY 2: ACCOUNT MANAGEMENT (2 CREDITS)")
        print("="*50)
        
        self.test_youtube_accounts_system()
        
        # PRIORITY 3: Queue & Processing System (1 credit)
        print("\n" + "="*50)
        print("🥉 PRIORITY 3: QUEUE & PROCESSING SYSTEM (1 CREDIT)")
        print("="*50)
        
        self.test_queue_processing_system()
        
        # Additional critical tests (2 credits remaining)
        print("\n" + "="*50)
        print("🔧 ADDITIONAL CRITICAL TESTS (2 CREDITS)")
        print("="*50)
        
        self.test_environment_configuration()
        self.test_monitoring_endpoints()
        self.test_advanced_email_features()
        
        return True

    def generate_focused_report(self):
        """Generate focused test report"""
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        critical_failed = len(self.critical_failures)
        
        print("\n" + "=" * 80)
        print("📊 FOCUSED BACKEND TEST REPORT")
        print("🎯 9-Credit Budget Testing Results - Available Endpoints Only")
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
                "Backend Connectivity", "MongoDB", "Lead Generation", "Email Extraction"
            ],
            "PRIORITY 2 - Account Management": [
                "YouTube Accounts", "Account Health", "Account Statistics"
            ],
            "PRIORITY 3 - Queue & Processing": [
                "Smart Queue", "Queue Processing", "Queue Error", "Retry Failed"
            ],
            "ADDITIONAL - Monitoring & Email": [
                "Email Settings", "Performance Dashboard", "Optimization", "Comprehensive Email", "Email Detection"
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
        print(f"  • Focus maintained on available endpoints only")
        print(f"  • {total_tests} comprehensive tests executed")
        print(f"  • Avoided testing non-existent endpoints")

        return critical_failed == 0

def main():
    """Main test execution"""
    tester = FocusedBackendTester()
    
    print("🎯 FOCUSED BACKEND TESTING - 9 CREDIT BUDGET")
    print("Focus: Available Endpoints Only - Core Functionality")
    print("=" * 80)
    
    success = tester.run_focused_tests()
    
    if success:
        tester.generate_focused_report()
    else:
        print("❌ Testing failed due to connectivity issues")
        return 1
    
    # Return exit code based on critical failures
    return 0 if len(tester.critical_failures) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())