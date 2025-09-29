#!/usr/bin/env python3
"""
Debug script to test YouTube about page scraping
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
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

async def debug_scrape_channel_about_page(channel_id: str):
    """Debug version of scraping function with detailed logging"""
    try:
        urls_to_try = [
            f"https://www.youtube.com/channel/{channel_id}/about",
            f"https://www.youtube.com/@{channel_id}/about"
        ]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Set to False to see browser
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            for about_url in urls_to_try:
                try:
                    print(f"Trying to scrape: {about_url}")
                    
                    await page.goto(about_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(5000)  # Wait longer for content to load
                    
                    # Try to find and click any "Show more" buttons
                    try:
                        show_more_button = await page.query_selector("button[aria-label*='more']")
                        if show_more_button:
                            await show_more_button.click()
                            await page.wait_for_timeout(2000)
                            print("Clicked 'Show more' button")
                    except:
                        pass
                    
                    content = await page.content()
                    print(f"Page content length: {len(content)}")
                    
                    # Save raw HTML for inspection
                    with open(f"/app/debug_page_content_{channel_id}.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    soup = BeautifulSoup(content, 'html.parser')
                    text_content = soup.get_text()
                    
                    print(f"Extracted text length: {len(text_content)}")
                    print("First 1000 characters of extracted text:")
                    print("=" * 50)
                    print(text_content[:1000])
                    print("=" * 50)
                    
                    # Look for specific YouTube about page elements
                    about_sections = soup.find_all(['div', 'span', 'p'], string=re.compile(r'@|email|contact', re.IGNORECASE))
                    print(f"Found {len(about_sections)} potential about sections")
                    
                    for section in about_sections[:5]:  # Show first 5
                        print(f"About section: {section.get_text()[:200]}")
                    
                    email = extract_email_from_text(text_content)
                    print(f"Email found: {email}")
                    
                    await browser.close()
                    return email, text_content[:2000]
                        
                except Exception as url_error:
                    print(f"Failed to scrape {about_url}: {url_error}")
                    continue
            
            await browser.close()
            
    except Exception as e:
        print(f"Error scraping about page for channel {channel_id}: {e}")
    
    return None, None

# Test with a well-known YouTube channel (using a placeholder)
async def main():
    # We need a real channel ID to test - let's use a popular one
    # For testing, let's use a channel ID format
    test_channel_id = "UCBJycsmduvYEL83R_U4JriQ"  # Example: Marques Brownlee's channel
    
    print(f"Testing scraping for channel: {test_channel_id}")
    email, content = await debug_scrape_channel_about_page(test_channel_id)
    
    print(f"\nFinal result:")
    print(f"Email: {email}")
    print(f"Content preview: {content[:500] if content else 'None'}")

if __name__ == "__main__":
    # First, let's check if Playwright is installed
    try:
        asyncio.run(main())
    except ImportError as e:
        print(f"Import error: {e}")
        print("Installing playwright...")