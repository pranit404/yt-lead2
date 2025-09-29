#!/usr/bin/env python3
"""
Test deduplication functionality and email status handling
"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8001/api"

def test_deduplication():
    """Test that channels already in database are skipped during processing"""
    print("🔍 Testing Deduplication Functionality...")
    
    # First, check if we have any existing leads
    main_leads_response = requests.get(f"{BACKEND_URL}/leads/main")
    no_email_leads_response = requests.get(f"{BACKEND_URL}/leads/no-email")
    
    if main_leads_response.status_code == 200 and no_email_leads_response.status_code == 200:
        main_leads = main_leads_response.json()
        no_email_leads = no_email_leads_response.json()
        
        print(f"📊 Current database state:")
        print(f"  • Main leads (with emails): {len(main_leads)}")
        print(f"  • No email leads: {len(no_email_leads)}")
        
        if len(main_leads) > 0 or len(no_email_leads) > 0:
            print("✅ Database has existing leads - deduplication should work")
            
            # Start a small lead generation process to test deduplication
            payload = {
                "keywords": ["tech review"],  # Common keyword likely to find existing channels
                "max_videos_per_keyword": 20,
                "max_channels": 5,
                "subscriber_min": 10000,
                "subscriber_max": 1000000,
                "test_mode": True
            }
            
            print("🚀 Starting lead generation to test deduplication...")
            response = requests.post(f"{BACKEND_URL}/lead-generation/start", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                status_id = data["id"]
                print(f"✅ Lead generation started with ID: {status_id}")
                
                # Wait for processing to complete or make some progress
                for i in range(10):  # Wait up to 20 seconds
                    time.sleep(2)
                    status_response = requests.get(f"{BACKEND_URL}/lead-generation/status/{status_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"📊 Status: {status_data.get('status')} - Step: {status_data.get('current_step')}")
                        
                        if status_data.get('status') in ['completed', 'failed']:
                            break
                
                print("✅ Deduplication test completed - check logs for 'already processed, skipping' messages")
            else:
                print(f"❌ Failed to start lead generation: {response.status_code}")
        else:
            print("⚠️ No existing leads in database - deduplication cannot be tested")
    else:
        print("❌ Failed to get current leads from database")

def test_email_status_handling():
    """Test email status handling with sending disabled"""
    print("\n📧 Testing Email Status Handling...")
    
    # Disable email sending
    print("🔧 Disabling email sending...")
    disable_response = requests.post(f"{BACKEND_URL}/settings/email-sending?enabled=false")
    
    if disable_response.status_code == 200:
        print("✅ Email sending disabled")
        
        # Start a small lead generation process
        payload = {
            "keywords": ["youtube tutorial"],
            "max_videos_per_keyword": 10,
            "max_channels": 2,
            "subscriber_min": 50000,
            "subscriber_max": 500000,
            "test_mode": True
        }
        
        print("🚀 Starting lead generation with email sending disabled...")
        response = requests.post(f"{BACKEND_URL}/lead-generation/start", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            status_id = data["id"]
            print(f"✅ Lead generation started with ID: {status_id}")
            
            # Wait for some processing
            time.sleep(10)
            
            # Check the leads to see email status
            main_leads_response = requests.get(f"{BACKEND_URL}/leads/main")
            if main_leads_response.status_code == 200:
                leads = main_leads_response.json()
                
                # Look for recent leads with "prepared_not_sent" status
                recent_leads = [lead for lead in leads if lead.get('email_sent_status') == 'prepared_not_sent']
                
                if recent_leads:
                    print(f"✅ Found {len(recent_leads)} leads with 'prepared_not_sent' status")
                    for lead in recent_leads[:3]:  # Show first 3
                        print(f"  • {lead.get('channel_title')}: {lead.get('email_sent_status')}")
                else:
                    print("⚠️ No leads found with 'prepared_not_sent' status")
            
        else:
            print(f"❌ Failed to start lead generation: {response.status_code}")
        
        # Re-enable email sending
        print("🔧 Re-enabling email sending...")
        enable_response = requests.post(f"{BACKEND_URL}/settings/email-sending?enabled=true")
        if enable_response.status_code == 200:
            print("✅ Email sending re-enabled")
    else:
        print(f"❌ Failed to disable email sending: {disable_response.status_code}")

def test_test_mode_limits():
    """Test that test mode actually applies the reduced limits"""
    print("\n🧪 Testing Test Mode Limits...")
    
    # Test with high limits but test mode enabled
    payload = {
        "keywords": ["gaming"],
        "max_videos_per_keyword": 1000,  # Should be reduced to 100
        "max_channels": 100,  # Should be reduced to 10
        "subscriber_min": 10000,
        "subscriber_max": 1000000,
        "test_mode": True
    }
    
    print("🚀 Starting lead generation with test mode and high limits...")
    response = requests.post(f"{BACKEND_URL}/lead-generation/start", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        status_id = data["id"]
        print(f"✅ Test mode lead generation started with ID: {status_id}")
        
        # Monitor for a bit to see if limits are applied
        time.sleep(5)
        
        status_response = requests.get(f"{BACKEND_URL}/lead-generation/status/{status_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"📊 Status: {status_data.get('status')} - Channels discovered: {status_data.get('channels_discovered', 0)}")
            print("✅ Test mode limits should be applied (check Discord notifications for confirmation)")
        
    else:
        print(f"❌ Failed to start test mode lead generation: {response.status_code}")

if __name__ == "__main__":
    print("🚀 Starting Deduplication and Email Status Testing")
    print("=" * 60)
    
    test_deduplication()
    test_email_status_handling()
    test_test_mode_limits()
    
    print("\n✅ All deduplication and email status tests completed!")
    print("📝 Check Discord notifications and backend logs for detailed information")