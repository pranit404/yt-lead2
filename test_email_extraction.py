#!/usr/bin/env python3
"""
Test script to debug email extraction issues
"""

import re
from typing import Optional

def extract_email_from_text(text: str) -> Optional[str]:
    """Current email extraction function from the app"""
    if not text:
        return None
        
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    
    if matches:
        return matches[0].lower()
    return None

def improved_extract_email_from_text(text: str) -> Optional[str]:
    """Improved email extraction with better regex"""
    if not text:
        return None
    
    # More comprehensive email regex pattern
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(email_pattern, text)
    
    if matches:
        return matches[0].lower()
    return None

# Test cases
test_cases = [
    "Contact me at john@example.com for business inquiries",
    "Email: support@company.co.uk",
    "business@test-domain.com",
    "user.name+tag@example-site.org",
    "Contact: info@123company.com",
    "Reach out to hello@startup.io",
    "My email is: contact@my-website.net",
    "For collaborations: partnerships@content-creator.com",
    "Business inquiries: business@youtuber.tv"
]

print("Testing Current Email Extraction:")
print("=" * 50)

for i, test_text in enumerate(test_cases, 1):
    current_result = extract_email_from_text(test_text)
    improved_result = improved_extract_email_from_text(test_text)
    
    print(f"Test {i}: {test_text}")
    print(f"  Current: {current_result}")
    print(f"  Improved: {improved_result}")
    print()

# Test with sample YouTube about page content
youtube_about_sample = """
Channel About Section:

Welcome to my channel! I create amazing content about technology and programming.

For business inquiries, please contact me at: creator@example.com

Subscribe for more awesome videos!

Links:
- Website: https://mywebsite.com
- Twitter: @myhandle
- Business email: partnerships@creator.net

Thanks for watching!
"""

print("YouTube About Page Sample Test:")
print("=" * 50)
print("Sample text:")
print(youtube_about_sample)
print()
print(f"Current extraction: {extract_email_from_text(youtube_about_sample)}")
print(f"Improved extraction: {improved_extract_email_from_text(youtube_about_sample)}")