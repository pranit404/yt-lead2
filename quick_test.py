#!/usr/bin/env python3
"""
Quick Backend Testing for YouTube Login Automation System
Focus: Core API endpoints without heavy operations
"""

import requests
import json
import sys
import time

BACKEND_URL = "http://localhost:8001/api"

def test_endpoint(name, method, url, data=None, timeout=10):
    """Test a single endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data or {}, timeout=timeout)
        
        status = "✅ PASS" if response.status_code == 200 else "❌ FAIL"
        print(f"{status} {name}: HTTP {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"    Response keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"    Response: List with {len(data)} items")
                else:
                    print(f"    Response type: {type(data)}")
            except:
                print(f"    Response: {response.text[:100]}...")
        else:
            print(f"    Error: {response.text[:200]}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ FAIL {name}: {str(e)}")
        return False

def main():
    """Run quick tests"""
    print("🚀 Quick YouTube Login Automation Tests")
    print("=" * 50)
    
    results = []
    
    # Test 1: Backend connectivity
    results.append(test_endpoint("Backend Connectivity", "GET", f"{BACKEND_URL}/"))
    
    # Test 2: Account initialization
    results.append(test_endpoint("Initialize Real Accounts", "POST", f"{BACKEND_URL}/accounts/initialize-real-accounts"))
    
    # Test 3: List accounts
    results.append(test_endpoint("List Accounts", "GET", f"{BACKEND_URL}/accounts"))
    
    # Test 4: Session status
    results.append(test_endpoint("Session Status", "GET", f"{BACKEND_URL}/accounts/session/status"))
    
    # Test 5: Try login with first account (get account ID first)
    try:
        accounts_response = requests.get(f"{BACKEND_URL}/accounts", timeout=10)
        if accounts_response.status_code == 200:
            accounts = accounts_response.json()
            if accounts and len(accounts) > 0:
                account_id = accounts[0]["id"]
                print(f"\n🔐 Testing login with account: {accounts[0]['email']}")
                results.append(test_endpoint("Login Automation", "POST", f"{BACKEND_URL}/accounts/{account_id}/login", timeout=30))
                
                # Test session validation
                results.append(test_endpoint("Session Validation", "GET", f"{BACKEND_URL}/accounts/{account_id}/session/validate", timeout=15))
            else:
                print("❌ FAIL No accounts available for login testing")
                results.append(False)
        else:
            print("❌ FAIL Could not retrieve accounts for login testing")
            results.append(False)
    except Exception as e:
        print(f"❌ FAIL Login test setup error: {e}")
        results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("✅ All core YouTube Login Automation endpoints working!")
    elif passed >= total * 0.8:
        print("⚠️ Most endpoints working, minor issues detected")
    else:
        print("❌ Multiple critical issues found")
    
    return passed >= total * 0.8

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)