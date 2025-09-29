#!/usr/bin/env python3
"""
Focused Email Extraction Testing - Testing the core email regex patterns
"""

import requests
import json

BACKEND_URL = "http://localhost:8001/api"

def test_email_patterns():
    """Test specific email extraction patterns that were reported as failing"""
    
    print("🧪 Testing Email Extraction Patterns")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Obfuscated [at] [dot]",
            "text": "business [at] creator [dot] com",
            "expected": "business@creator.com",
            "critical": True
        },
        {
            "name": "Underscore in domain",
            "text": "Contact first_last@company_name.org",
            "expected": "first_last@company_name.org", 
            "critical": True
        },
        {
            "name": "Plain email",
            "text": "Contact me at john@example.com",
            "expected": "john@example.com",
            "critical": False
        },
        {
            "name": "Email with context",
            "text": "For business: business@creator.com",
            "expected": "business@creator.com",
            "critical": False
        }
    ]
    
    failed_critical = []
    
    for test in test_cases:
        try:
            response = requests.post(f"{BACKEND_URL}/debug/test-text-email-extraction", 
                                   params={"text": test["text"]}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                found = data.get("email_found")
                
                if found == test["expected"]:
                    print(f"✅ {test['name']}: PASS - Found {found}")
                else:
                    print(f"❌ {test['name']}: FAIL - Expected {test['expected']}, got {found}")
                    if test["critical"]:
                        failed_critical.append(test)
            else:
                print(f"❌ {test['name']}: HTTP Error {response.status_code}")
                if test["critical"]:
                    failed_critical.append(test)
                    
        except Exception as e:
            print(f"❌ {test['name']}: Exception - {e}")
            if test["critical"]:
                failed_critical.append(test)
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    if failed_critical:
        print("❌ CRITICAL ISSUES FOUND:")
        for test in failed_critical:
            print(f"  • {test['name']}: {test['text']}")
        print(f"\n🔧 The email extraction regex needs fixes for {len(failed_critical)} critical patterns")
        return False
    else:
        print("✅ All critical email extraction patterns working!")
        return True

def test_basic_functionality():
    """Test basic API functionality"""
    print("\n🔌 Testing Basic API Functionality")
    print("=" * 50)
    
    try:
        # Test root endpoint
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ Backend API accessible")
        else:
            print(f"❌ Backend API error: {response.status_code}")
            return False
            
        # Test text extraction endpoint exists
        response = requests.post(f"{BACKEND_URL}/debug/test-text-email-extraction", 
                               params={"text": "test@example.com"}, timeout=5)
        if response.status_code == 200:
            print("✅ Text email extraction endpoint working")
        else:
            print(f"❌ Text extraction endpoint error: {response.status_code}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Focused Email Extraction Bug Fix Testing")
    print("=" * 60)
    
    if not test_basic_functionality():
        print("❌ Basic functionality failed. Cannot proceed.")
        exit(1)
    
    success = test_email_patterns()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ RESULT: Email extraction core functionality is working!")
        print("📝 NOTE: Web scraping tests skipped due to Playwright environment issues")
    else:
        print("❌ RESULT: Email extraction has critical issues that need fixing")
    print("=" * 60)