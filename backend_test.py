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

class EmailExtractionTester:
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
    
    def test_text_email_extraction_endpoint(self):
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
        """Run all email extraction tests"""
        print("🚀 Starting Email Extraction Bug Fix Testing")
        print("=" * 60)
        
        # Test 1: Basic connectivity
        if not self.test_backend_connectivity():
            print("❌ Backend not accessible. Stopping tests.")
            return False
        
        print("\n📧 Testing Text Email Extraction Endpoint...")
        self.test_text_email_extraction_endpoint()
        
        print("\n🔍 Testing Channel Email Extraction Endpoint...")
        self.test_channel_email_extraction_endpoint()
        
        print("\n🧪 Testing Email Regex Patterns...")
        self.test_email_regex_patterns()
        
        print("\n⚠️ Testing Error Handling...")
        self.test_error_handling()
        
        return True
    
    def generate_report(self):
        """Generate test report"""
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        
        print("\n" + "=" * 60)
        print("📊 EMAIL EXTRACTION BUG FIX TEST REPORT")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  • {test['test_name']}: {test['details']}")
        
        print("\n🔍 KEY FINDINGS:")
        
        # Analyze results for key insights
        text_extraction_tests = [t for t in self.test_results if "Text Email Extraction" in t["test_name"]]
        text_passed = len([t for t in text_extraction_tests if t["success"]])
        
        channel_extraction_tests = [t for t in self.test_results if "Channel Email Extraction" in t["test_name"]]
        channel_passed = len([t for t in channel_extraction_tests if t["success"]])
        
        regex_tests = [t for t in self.test_results if "Email Regex" in t["test_name"]]
        regex_passed = len([t for t in regex_tests if t["success"]])
        
        print(f"  • Text Email Extraction: {text_passed}/{len(text_extraction_tests)} passed")
        print(f"  • Channel Email Extraction: {channel_passed}/{len(channel_extraction_tests)} passed")
        print(f"  • Email Regex Patterns: {regex_passed}/{len(regex_tests)} passed")
        
        # Overall assessment
        if len(self.failed_tests) == 0:
            print("\n✅ OVERALL: Email extraction bug fix appears to be working correctly!")
        elif len(self.failed_tests) <= 2:
            print("\n⚠️ OVERALL: Email extraction mostly working with minor issues")
        else:
            print("\n❌ OVERALL: Email extraction still has significant issues")
        
        return len(self.failed_tests) == 0

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