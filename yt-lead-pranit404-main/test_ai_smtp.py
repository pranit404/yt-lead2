#!/usr/bin/env python3
"""
Test AI email generation and SMTP functionality
"""

import asyncio
import aiohttp
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
GEMINI_API_KEY = "AIzaSyDO7g9pBST5_856x6PkXilLVhMqYtCK2J0"
SMTP_EMAIL = "nighthawks848@gmail.com"
SMTP_PASSWORD = "nbhp idgp gsdo iuhx"

async def test_gemini_api():
    """Test Google Gemini API for email generation"""
    try:
        print("🤖 Testing Gemini API...")
        
        # Sample data for testing
        test_data = {
            "creatorName": "Test Creator",
            "channelName": "Test Channel",
            "channelUrl": "https://youtube.com/channel/test",
            "niche": "content creation",
            "subscribers": 50000,
            "lastVideoTitle": "How to Create Amazing Content",
            "videoUrl": "https://youtube.com/watch?v=test",
            "topCommentAuthor": "TestViewer",
            "topCommentText": "Great video! Love your editing style.",
            "commentCount": 25
        }
        
        prompt = f"""Using the following data about a YouTube creator's channel, generate a personalized outreach email. Output ONLY valid JSON with keys: subject, plain, html.

Creator Name: {test_data['creatorName']}
Channel Name: {test_data['channelName']}
Subscriber Count: {test_data['subscribers']}
Recent Video Title: {test_data['lastVideoTitle']}
Top Viewer Comment by {test_data['topCommentAuthor']}: "{test_data['topCommentText']}"

Requirements:
- Professional yet warm tone
- Reference the comment naturally
- Include clear call-to-action
- Output ONLY valid JSON"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                print(f"Gemini API status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    generated_text = result['candidates'][0]['content']['parts'][0]['text']
                    print(f"✅ Gemini API working! Generated text length: {len(generated_text)}")
                    print(f"Generated content preview: {generated_text[:200]}...")
                    
                    # Try to parse as JSON
                    try:
                        json_start = generated_text.find('{')
                        json_end = generated_text.rfind('}') + 1
                        if json_start != -1 and json_end != -1:
                            json_text = generated_text[json_start:json_end]
                            parsed = json.loads(json_text)
                            print(f"✅ JSON parsing successful!")
                            print(f"Subject: {parsed.get('subject', 'N/A')}")
                            return parsed
                    except Exception as e:
                        print(f"⚠️ JSON parsing failed: {e}")
                        return {
                            "subject": "Test Subject",
                            "plain": generated_text,
                            "html": generated_text.replace('\n', '<br>')
                        }
                else:
                    error_text = await response.text()
                    print(f"❌ Gemini API failed: {response.status} - {error_text}")
                    return None
                    
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return None

def test_smtp():
    """Test SMTP email sending"""
    try:
        print("📧 Testing SMTP...")
        
        # Test email content
        subject = "Test Email from YouTube Lead Generation Platform"
        plain_body = "This is a test email to verify SMTP functionality."
        html_body = "<p>This is a <strong>test email</strong> to verify SMTP functionality.</p>"
        to_email = SMTP_EMAIL  # Send to self for testing
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        
        # Add plain text and HTML parts
        part1 = MIMEText(plain_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            
        print(f"✅ SMTP working! Test email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ SMTP error: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Testing AI Email Generation and SMTP Functionality")
    print("="*60)
    
    # Test Gemini API
    email_content = await test_gemini_api()
    
    print("\n" + "="*60)
    
    # Test SMTP
    smtp_success = test_smtp()
    
    print("\n" + "="*60)
    print("📊 Test Summary:")
    print(f"  Gemini API: {'✅ PASS' if email_content else '❌ FAIL'}")
    print(f"  SMTP: {'✅ PASS' if smtp_success else '❌ FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())