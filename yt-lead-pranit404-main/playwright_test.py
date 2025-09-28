#!/usr/bin/env python3
"""
Focused test for Playwright email extraction functionality
"""

import asyncio
import aiohttp
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://email-extract-tool.preview.emergentagent.com/api"

async def test_playwright_email_extraction():
    """Test Playwright email extraction with small focused test"""
    try:
        async with aiohttp.ClientSession() as session:
            # Start a small lead generation test
            payload = {
                "keywords": ["investment tips"],
                "max_videos_per_keyword": 10,
                "max_channels": 3
            }
            
            logger.info("🚀 Starting focused Playwright email extraction test...")
            
            async with session.post(
                f"{BASE_URL}/lead-generation/start",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    status_id = data.get("id")
                    logger.info(f"✅ Test started. Status ID: {status_id}")
                    
                    # Monitor progress
                    max_attempts = 20
                    attempt = 0
                    
                    while attempt < max_attempts:
                        async with session.get(f"{BASE_URL}/lead-generation/status/{status_id}") as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                status = status_data.get("status", "unknown")
                                current_step = status_data.get("current_step", "unknown")
                                channels_discovered = status_data.get("channels_discovered", 0)
                                channels_processed = status_data.get("channels_processed", 0)
                                emails_found = status_data.get("emails_found", 0)
                                
                                logger.info(f"Status: {status}, Step: {current_step}, Channels: {channels_discovered}/{channels_processed}, Emails: {emails_found}")
                                
                                if status == "completed":
                                    logger.info("✅ Test completed successfully")
                                    
                                    # Check results
                                    async with session.get(f"{BASE_URL}/leads/main") as leads_response:
                                        if leads_response.status == 200:
                                            main_leads = await leads_response.json()
                                            logger.info(f"📊 Main leads with emails: {len(main_leads)}")
                                            
                                            for lead in main_leads:
                                                email = lead.get("email", "N/A")
                                                channel_title = lead.get("channel_title", "Unknown")
                                                about_content = lead.get("about_page_content", "")
                                                logger.info(f"✅ Found: {channel_title} - {email}")
                                                if about_content:
                                                    logger.info(f"   📄 About page content extracted: {len(about_content)} chars")
                                                else:
                                                    logger.info(f"   📄 Email found via API fallback")
                                    
                                    return True
                                elif status == "failed":
                                    logger.error("❌ Test failed")
                                    return False
                                
                                await asyncio.sleep(5)
                                attempt += 1
                            else:
                                logger.error(f"❌ Status check failed: {status_response.status}")
                                return False
                    
                    logger.warning("⚠️ Test timeout")
                    return False
                else:
                    logger.error(f"❌ Failed to start test: {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_playwright_email_extraction())
    logger.info(f"🎯 Playwright test result: {'SUCCESS' if success else 'FAILED'}")