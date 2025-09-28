#!/usr/bin/env python3
"""
Debug script to examine lead data and understand email extraction issues
"""

import asyncio
import aiohttp
import json
from typing import Dict, List

BASE_URL = "https://email-extract-tool.preview.emergentagent.com/api"

async def debug_leads():
    """Debug lead data to understand email extraction issues"""
    async with aiohttp.ClientSession() as session:
        print("🔍 Debugging lead data...")
        
        # Get main leads
        async with session.get(f"{BASE_URL}/leads/main") as response:
            main_leads = await response.json()
            print(f"\n📊 Main Leads (with emails): {len(main_leads)}")
            
            if main_leads:
                for i, lead in enumerate(main_leads[:3]):  # Show first 3
                    print(f"\nLead {i+1}:")
                    print(f"  Channel: {lead.get('channel_title', 'N/A')}")
                    print(f"  Email: {lead.get('email', 'N/A')}")
                    print(f"  Email Status: {lead.get('email_status', 'N/A')}")
                    print(f"  Email Subject: {lead.get('email_subject', 'N/A')[:100] if lead.get('email_subject') else 'N/A'}")
                    print(f"  Email Sent Status: {lead.get('email_sent_status', 'N/A')}")
                    print(f"  Comments Analyzed: {lead.get('comments_analyzed', 0)}")
                    print(f"  Top Comment: {lead.get('top_comment', 'N/A')[:100] if lead.get('top_comment') else 'N/A'}")
        
        # Get no-email leads
        async with session.get(f"{BASE_URL}/leads/no-email") as response:
            no_email_leads = await response.json()
            print(f"\n📊 No-Email Leads: {len(no_email_leads)}")
            
            if no_email_leads:
                for i, lead in enumerate(no_email_leads[:3]):  # Show first 3
                    print(f"\nNo-Email Lead {i+1}:")
                    print(f"  Channel: {lead.get('channel_title', 'N/A')}")
                    print(f"  Channel ID: {lead.get('channel_id', 'N/A')}")
                    print(f"  Email Status: {lead.get('email_status', 'N/A')}")
                    print(f"  Subscriber Count: {lead.get('subscriber_count', 0)}")
                    print(f"  About Page Content: {lead.get('about_page_content', 'N/A')[:200] if lead.get('about_page_content') else 'N/A'}")
                    print(f"  Error Messages: {lead.get('error_messages', [])}")

if __name__ == "__main__":
    asyncio.run(debug_leads())