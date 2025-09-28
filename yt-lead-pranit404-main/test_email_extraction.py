#!/usr/bin/env python3
"""
Test email extraction functionality directly
"""

import asyncio
import aiohttp
import re
import html2text
from typing import Optional

def extract_email_from_text(text: str) -> Optional[str]:
    """Extract email address from text using regex"""
    if not text:
        return None
        
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    
    if matches:
        return matches[0].lower()
    return None

async def scrape_channel_about_page(channel_id: str) -> tuple[Optional[str], Optional[str]]:
    """Scrape channel about page for email and content"""
    try:
        about_url = f"https://www.youtube.com/channel/{channel_id}/about"
        print(f"🔍 Scraping: {about_url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(about_url) as response:
                print(f"Response status: {response.status}")
                
                if response.status == 200:
                    html_content = await response.text()
                    print(f"HTML content length: {len(html_content)}")
                    
                    # Convert HTML to plain text
                    h = html2text.HTML2Text()
                    h.ignore_links = True
                    text_content = h.handle(html_content)
                    
                    print(f"Text content length: {len(text_content)}")
                    print(f"First 500 chars: {text_content[:500]}")
                    
                    # Extract email
                    email = extract_email_from_text(text_content)
                    print(f"Extracted email: {email}")
                    
                    return email, text_content[:1000]  # Return first 1000 chars
                else:
                    print(f"Failed to fetch page: {response.status}")
                    
    except Exception as e:
        print(f"Error scraping about page for channel {channel_id}: {e}")
    
    return None, None

async def test_email_extraction():
    """Test email extraction with real channel IDs"""
    test_channels = [
        "UCCs2yAPn3mE3_ix2kjGBnKw",  # Mak Crypto Signals
        "UCTR1Tk8SaMO9qw930kIOMHQ",  # Sagar Sinha
        "UCL-QLzGmf468WAL1U-9g0qA"   # Craig Percoco
    ]
    
    for channel_id in test_channels:
        print(f"\n{'='*60}")
        print(f"Testing channel: {channel_id}")
        print('='*60)
        
        email, content = await scrape_channel_about_page(channel_id)
        
        print(f"Result - Email: {email}")
        print(f"Result - Content preview: {content[:200] if content else 'None'}")
        
        await asyncio.sleep(2)  # Rate limiting

if __name__ == "__main__":
    asyncio.run(test_email_extraction())