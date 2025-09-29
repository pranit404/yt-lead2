from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import json
import aiohttp
import re
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dateutil import parser
import requests
from urllib.parse import urlparse, parse_qs
import html2text
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import bcrypt
import jwt
from passlib.context import CryptContext

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="YouTube Lead Generation Platform")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# YouTube API Configuration
YOUTUBE_API_KEYS = [
    "AIzaSyDyM6MKF0tJyLsCl4bhXg-w7See_S1Y4yA",
    "AIzaSyAaAH54IWe7JZkAklJfdpFPmFNim7rBtOA", 
    "AIzaSyCkm2lb0wSKtujS60keW_VdGrYEh7_OQBs",
    "AIzaSyCkMuE7FZ3NaTmNevVndHbF-2dLVL1JTnk",
    "AIzaSyAmNLv0XYiuJX6UCRPvJ2369kBMp19yEXw",
    "AIzaSyAWbnMs2HSq8mcC9ec2x8x55kiPEIZh6iw",
    "AIzaSyAk96LI5E7VXjZU7q58TOcEEROv6qDMKVo",
    "AIzaSyCprVXfw5jzudCPQKej0vSW26F3PoF6MSI"
]

current_key_index = 0

# Email Configuration  
SMTP_EMAIL = "nighthawks848@gmail.com"
SMTP_PASSWORD = "nbhp idgp gsdo iuhx"

# Global Settings
SEND_EMAILS_ENABLED = os.environ.get('SEND_EMAILS_ENABLED', 'true').lower() == 'true'

# Discord Configuration
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1417915138400587909/B9_tEDQKMZfemFvu0z2vy3z7HjVyCZf5PCAj6DmDuOdPira5wwvH_QJpZRjKTUPbzP3c"

# Gemini Configuration
GEMINI_API_KEY = "AIzaSyDO7g9pBST5_856x6PkXilLVhMqYtCK2J0"

# Authentication Configuration
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256" 
ACCESS_TOKEN_EXPIRE_MINUTES = 30
RECAPTCHA_SECRET_KEY = ""

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# Pydantic Models
class LeadGenerationRequest(BaseModel):
    keywords: List[str]
    max_videos_per_keyword: int = 2000
    max_channels: int = 1000
    subscriber_min: int = 10000
    subscriber_max: int = 1000000
    content_frequency_min: float = 0.14
    content_frequency_max: Optional[float] = 2.0
    test_mode: bool = False  # Reduces limits for faster testing

class Channel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    channel_title: str
    creator_name: str
    channel_url: str
    email: Optional[str] = None
    email_status: str = "not_found"
    subscriber_count: int = 0
    video_count: int = 0
    discovery_score: float = 0.0
    discovery_method: str = "keyword_search"
    keywords_found_in: List[str] = []
    latest_video_title: Optional[str] = None
    latest_video_date: Optional[str] = None
    top_content_terms: List[str] = []
    activity_level: str = "unknown"
    quality_score: float = 0.0
    content_consistency: str = "unknown"
    content_frequency_weekly: float = 0.0
    about_page_content: Optional[str] = None
    comments_analyzed: int = 0
    top_comment: Optional[str] = None
    comment_author: Optional[str] = None
    email_subject: Optional[str] = None
    email_body_preview: Optional[str] = None
    personalization_method: str = "ai_generated"
    email_sent_status: str = "not_sent"
    processing_priority: str = "medium"
    validation_reasons: List[str] = []
    discovery_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_timestamp: Optional[datetime] = None
    error_messages: List[str] = []

class ProcessingStatus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str
    current_step: str
    channels_discovered: int = 0
    channels_processed: int = 0
    emails_found: int = 0
    emails_sent: int = 0
    errors: List[str] = []
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Utility Functions
async def send_discord_notification(message: str):
    """Send notification to Discord webhook"""
    try:
        if DISCORD_WEBHOOK:
            async with aiohttp.ClientSession() as session:
                await session.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")

def get_youtube_service():
    """Get YouTube API service with key rotation"""
    global current_key_index
    try:
        api_key = YOUTUBE_API_KEYS[current_key_index]
        youtube = build('youtube', 'v3', developerKey=api_key)
        return youtube
    except Exception as e:
        logger.error(f"Error with YouTube API key {current_key_index}: {e}")
        current_key_index = (current_key_index + 1) % len(YOUTUBE_API_KEYS)
        if current_key_index == 0:
            raise HTTPException(status_code=429, detail="All YouTube API keys exhausted")
        return get_youtube_service()

async def search_youtube_videos(keyword: str, max_results: int = 50):
    """Search YouTube videos by keyword"""
    try:
        youtube = get_youtube_service()
        videos = []
        next_page_token = None
        
        logger.info(f"Starting YouTube search for keyword: '{keyword}', max_results: {max_results}")
        
        while len(videos) < max_results:
            try:
                request = youtube.search().list(
                    part="snippet",
                    q=keyword,
                    type="video",
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token,
                    order="relevance",
                    publishedAfter="2022-01-01T00:00:00Z"
                )
                
                response = request.execute()
                logger.info(f"YouTube API response: {len(response.get('items', []))} videos found")
                
                for item in response.get('items', []):
                    video_data = {
                        'videoId': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'channelId': item['snippet']['channelId'],
                        'channelTitle': item['snippet']['channelTitle'],
                        'publishedAt': item['snippet']['publishedAt'],
                        'description': item['snippet']['description'][:500],
                        'keyword': keyword
                    }
                    videos.append(video_data)
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
            except Exception as api_error:
                logger.error(f"YouTube API error for '{keyword}': {api_error}")
                global current_key_index
                current_key_index = (current_key_index + 1) % len(YOUTUBE_API_KEYS)
                logger.info(f"Switched to API key index: {current_key_index}")
                
                if current_key_index == 0:
                    logger.error("All YouTube API keys exhausted")
                    break
                    
                youtube = get_youtube_service()
                continue
                
        logger.info(f"Final result: {len(videos)} videos found for keyword '{keyword}'")
        return videos
        
    except Exception as e:
        logger.error(f"Error searching YouTube videos for '{keyword}': {e}")
        return []

def extract_email_from_text(text: str) -> Optional[str]:
    """Extract email address from text using improved regex patterns with proper obfuscation handling"""
    if not text:
        return None
    
    # Clean up common obfuscations with proper space handling
    # Use regex to handle spaces around obfuscated parts properly
    cleaned_text = re.sub(r'\s*\[\s*at\s*\]\s*', '@', text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*\[\s*dot\s*\]\s*', '.', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*\(\s*at\s*\)\s*', '@', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*\(\s*dot\s*\)\s*', '.', cleaned_text, flags=re.IGNORECASE)
    
    # Also handle common text obfuscations
    cleaned_text = re.sub(r'\s+at\s+', '@', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s+dot\s+', '.', cleaned_text, flags=re.IGNORECASE)
    
    # Multiple regex patterns with underscore support for domains
    email_patterns = [
        # Standard email pattern with underscore support in domain
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}',
        # Pattern for context-based emails  
        r'(?:contact|email|reach|business|inquiries?)[\s:]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]{2,})',
        # Pattern with word boundaries
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}\b',
    ]
    
    all_matches = []
    
    for pattern in email_patterns:
        matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
        all_matches.extend(matches)
    
    # Filter and validate matches
    for match in all_matches:
        # Handle tuple matches from capture groups
        email = match if isinstance(match, str) else match[0] if match else ""
        email = email.strip().lower()
        
        # Enhanced validation
        if email and '@' in email and '.' in email and 5 <= len(email) <= 254:
            if email.count('@') == 1:
                local, domain = email.split('@')
                if local and domain and '.' in domain:
                    # Additional check: ensure TLD is reasonable
                    domain_parts = domain.split('.')
                    if len(domain_parts) >= 2 and len(domain_parts[-1]) >= 2:
                        return email
    
    return None

async def scrape_channel_about_page(channel_id: str) -> tuple[Optional[str], Optional[str]]:
    """Scrape channel about page for email and content using Playwright with improved targeting"""
    try:
        urls_to_try = [
            f"https://www.youtube.com/channel/{channel_id}/about",
            f"https://www.youtube.com/@{channel_id}/about"
        ]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            for about_url in urls_to_try:
                try:
                    logger.info(f"Trying to scrape: {about_url}")
                    
                    await page.goto(about_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(5000)  # Increased wait time
                    
                    # Try to expand "Show more" buttons to reveal full content
                    try:
                        # Look for various "show more" button selectors
                        show_more_selectors = [
                            "button[aria-label*='more']",
                            "button[aria-label*='Show more']",
                            "button[aria-label*='Show less']",
                            "tp-yt-paper-button#expand",
                            "yt-button-shape[aria-label*='more']",
                            "#expand-button",
                            "[aria-label*='more']"
                        ]
                        
                        for selector in show_more_selectors:
                            try:
                                show_more_button = await page.wait_for_selector(selector, timeout=2000)
                                if show_more_button:
                                    await show_more_button.click()
                                    await page.wait_for_timeout(2000)
                                    logger.info(f"Successfully clicked show more button with selector: {selector}")
                                    break
                            except:
                                continue
                                
                    except Exception as expand_error:
                        logger.debug(f"Could not expand content: {expand_error}")
                    
                    # Wait a bit more after potential expansion
                    await page.wait_for_timeout(3000)
                    
                    # Get page content
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Target specific YouTube about page elements
                    about_text_elements = []
                    
                    # Try to find description/about content in specific containers
                    description_selectors = [
                        "yt-formatted-string#description-text",
                        "#description-text",
                        "[id*='description']",
                        "[class*='description']",
                        "yt-formatted-string.ytd-channel-about-metadata-renderer",
                        ".ytd-channel-about-metadata-renderer",
                        "#about-description",
                        "yt-formatted-string.content"
                    ]
                    
                    for selector in description_selectors:
                        elements = soup.select(selector)
                        for element in elements:
                            text = element.get_text().strip()
                            if text and len(text) > 10:  # Only meaningful text
                                about_text_elements.append(text)
                    
                    # Combine all found text
                    combined_text = "\n".join(about_text_elements)
                    
                    # Fallback to general text extraction if specific selectors didn't work
                    if not combined_text.strip():
                        logger.info("Fallback to general text extraction")
                        combined_text = soup.get_text()
                    
                    logger.info(f"Extracted text length: {len(combined_text)}")
                    logger.debug(f"First 500 chars: {combined_text[:500]}")
                    
                    # Extract email from the text
                    email = extract_email_from_text(combined_text)
                    
                    if email:
                        logger.info(f"Found email: {email}")
                        await browser.close()
                        return email, combined_text[:1000]
                    elif "About" in content or combined_text.strip():
                        logger.info("No email found but content retrieved")
                        await browser.close()
                        return None, combined_text[:1000]
                        
                except Exception as url_error:
                    logger.warning(f"Failed to scrape {about_url}: {url_error}")
                    continue
            
            await browser.close()
            
    except Exception as e:
        logger.error(f"Error scraping about page for channel {channel_id}: {e}")
    
    return None, None

async def get_channel_details(channel_id: str):
    """Get detailed channel information"""
    try:
        youtube = get_youtube_service()
        
        request = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            id=channel_id
        )
        
        response = request.execute()
        items = response.get('items', [])
        
        if not items:
            return None
            
        channel = items[0]
        snippet = channel.get('snippet', {})
        statistics = channel.get('statistics', {})
        
        return {
            'channel_title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'custom_url': snippet.get('customUrl', ''),
            'subscriber_count': int(statistics.get('subscriberCount', 0)),
            'video_count': int(statistics.get('videoCount', 0)),
            'view_count': int(statistics.get('viewCount', 0)),
            'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
            'published_at': snippet.get('publishedAt', '')
        }
        
    except Exception as e:
        logger.error(f"Error getting channel details for {channel_id}: {e}")
        return None

async def get_channel_videos(channel_id: str, max_results: int = 3):
    """Get recent videos from a channel"""
    try:
        youtube = get_youtube_service()
        
        request = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        )
        
        response = request.execute()
        items = response.get('items', [])
        
        if not items:
            return []
            
        uploads_playlist = items[0]['contentDetails']['relatedPlaylists']['uploads']
        
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist,
            maxResults=max_results
        )
        
        response = request.execute()
        
        videos = []
        for item in response.get('items', []):
            snippet = item.get('snippet', {})
            videos.append({
                'videoId': snippet.get('resourceId', {}).get('videoId', ''),
                'title': snippet.get('title', ''),
                'publishedAt': snippet.get('publishedAt', ''),
                'description': snippet.get('description', '')[:200]
            })
            
        return videos
        
    except Exception as e:
        logger.error(f"Error getting videos for channel {channel_id}: {e}")
        return []

async def calculate_content_frequency(channel_id: str) -> float:
    """Calculate content frequency in videos per week based on recent uploads"""
    try:
        youtube = get_youtube_service()
        
        request = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        )
        
        response = request.execute()
        items = response.get('items', [])
        
        if not items:
            return 0.0
            
        uploads_playlist = items[0]['contentDetails']['relatedPlaylists']['uploads']
        
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist,
            maxResults=50
        )
        
        response = request.execute()
        videos = response.get('items', [])
        
        if len(videos) < 2:
            return 0.0
        
        publish_dates = []
        
        for video in videos:
            pub_date_str = video.get('snippet', {}).get('publishedAt', '')
            if pub_date_str:
                try:
                    pub_date = parser.parse(pub_date_str)
                    publish_dates.append(pub_date)
                except:
                    continue
        
        if len(publish_dates) < 2:
            return 0.0
        
        publish_dates.sort(reverse=True)
        
        total_days = 0
        intervals = 0
        
        for i in range(len(publish_dates) - 1):
            time_diff = publish_dates[i] - publish_dates[i + 1]
            total_days += time_diff.total_seconds() / (24 * 3600)
            intervals += 1
        
        if intervals == 0:
            return 0.0
        
        avg_days_between_uploads = total_days / intervals
        
        if avg_days_between_uploads > 0:
            videos_per_week = 7.0 / avg_days_between_uploads
            return round(videos_per_week, 2)
        
        return 0.0
        
    except Exception as e:
        logger.error(f"Error calculating content frequency for channel {channel_id}: {e}")
        return 0.0

async def get_video_comments(video_id: str, max_results: int = 100):
    """Get comments for a video"""
    try:
        youtube = get_youtube_service()
        
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_id,
            maxResults=max_results,
            order="relevance"
        )
        
        response = request.execute()
        
        comments = []
        for item in response.get('items', []):
            comment = item['snippet']['topLevelComment']['snippet']
            comments.append({
                'author': comment.get('authorDisplayName', ''),
                'text': comment.get('textDisplay', ''),
                'likes': comment.get('likeCount', 0),
                'published': comment.get('publishedAt', '')
            })
            
        return comments
        
    except Exception as e:
        logger.error(f"Error getting comments for video {video_id}: {e}")
        return []

def analyze_comments_for_editing(comments: List[Dict]) -> Dict:
    """Analyze comments for editing-related feedback"""
    editing_terms = [
        'edit', 'editing', 'transition', 'cut', 'audio', 'sound', 'music', 
        'video quality', 'graphics', 'effects', 'slow', 'fast', 'pace',
        'boring', 'engaging', 'flow', 'smooth', 'jarring', 'sharp'
    ]
    
    relevant_comments = []
    editing_score = 5.0
    
    for comment in comments:
        text_lower = comment['text'].lower()
        
        for term in editing_terms:
            if term in text_lower:
                relevant_comments.append(comment)
                
                if any(word in text_lower for word in ['good', 'great', 'nice', 'love', 'perfect']):
                    editing_score += 0.5
                elif any(word in text_lower for word in ['bad', 'poor', 'hate', 'awful', 'terrible']):
                    editing_score -= 0.5
                break
    
    top_comment = None
    if relevant_comments:
        top_comment = max(relevant_comments, key=lambda x: x['likes'])
    elif comments:
        top_comment = max(comments, key=lambda x: x['likes'])
    
    return {
        'editing_score': max(1.0, min(10.0, editing_score)),
        'relevant_comments': len(relevant_comments),
        'top_comment': top_comment
    }

async def generate_client_outreach_email(channel_data: Dict, video_data: Dict, comment_data: Dict) -> Dict:
    """Generate personalized client outreach email using Gemini"""
    try:
        ai_input = {
            "creatorName": channel_data.get('creator_name', channel_data.get('channel_title', '')),
            "channelName": channel_data.get('channel_title', ''),
            "channelUrl": f"https://youtube.com/channel/{channel_data.get('channel_id', '')}",
            "niche": "content creation",
            "subscribers": channel_data.get('subscriber_count', 0),
            "lastVideoTitle": video_data.get('title', ''),
            "videoUrl": f"https://youtube.com/watch?v={video_data.get('videoId', '')}",
            "topCommentAuthor": comment_data.get('author', ''),
            "topCommentText": comment_data.get('text', ''),
            "commentCount": len(channel_data.get('comments_analyzed', []))
        }
        
        # CLIENT OUTREACH TEMPLATE (not collaboration)
        prompt = f"""Generate a personalized client outreach email for a video editing service. This is for acquiring the creator as a CLIENT for our video editing services, not for collaboration. Use the following data:

- Creator Name: {ai_input['creatorName']}
- Channel Name: {ai_input['channelName']}  
- Channel URL: {ai_input['channelUrl']}
- Subscriber Count: {ai_input['subscribers']}
- Recent Video Title: {ai_input['lastVideoTitle']}
- Recent Video URL: {ai_input['videoUrl']}
- Top Viewer Comment by {ai_input['topCommentAuthor']}: "{ai_input['topCommentText']}"

Requirements:
- Position our video editing services as a solution for their channel growth
- Reference their content specifically and show we've researched their channel
- Focus on how professional editing can increase their revenue and audience
- Include a clear call-to-action to book a consultation or get a quote
- Keep tone professional but approachable
- Output ONLY valid JSON with keys: subject, plain, html
- Make it clear we're offering our services TO them, not asking for collaboration

Subject should be about offering video editing services that will grow their channel.

Template structure:
- Hook: Mention specific video or achievement
- Problem identification: Subtle mention of editing improvements that could boost performance  
- Solution: Our video editing services
- Social proof: Brief mention of results we've achieved for other creators
- Call-to-action: Book consultation or get quote

Output as JSON with subject, plain, and html keys."""

        if GEMINI_API_KEY:
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
                    "maxOutputTokens": 2048
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        generated_text = result['candidates'][0]['content']['parts'][0]['text']
                        
                        try:
                            json_start = generated_text.find('{')
                            json_end = generated_text.rfind('}') + 1
                            if json_start != -1 and json_end != -1:
                                json_text = generated_text[json_start:json_end]
                                return json.loads(json_text)
                        except:
                            pass
                        
                        return {
                            "subject": "Professional Video Editing Services - Grow Your Channel Revenue",
                            "plain": generated_text,
                            "html": generated_text.replace('\n', '<br>')
                        }
                    
    except Exception as e:
        logger.error(f"Error generating AI email: {e}")
    
    # Fallback client outreach email
    return {
        "subject": f"Professional Video Editing Services for {channel_data.get('channel_title', '')}",
        "plain": f"""Hi {ai_input['creatorName']},

I came across your YouTube channel "{ai_input['channelName']}" and was impressed by your content, especially your recent video "{ai_input['lastVideoTitle']}".

With {ai_input['subscribers']:,} subscribers, you're at a great stage where professional video editing could significantly boost your channel's growth and revenue potential.

Our video editing team specializes in helping content creators like you:
• Increase average view duration by 30-50%
• Improve audience retention and engagement
• Create more consistent, professional content
• Save 10-15 hours per week on editing

We've helped creators grow from 50K to 500K+ subscribers through strategic editing improvements.

Would you be interested in a free consultation to discuss how we can help accelerate your channel's growth?

Best regards,
Professional Video Editing Team

P.S. I noticed the engagement on your videos - with the right editing enhancements, we could help you monetize that audience even more effectively.""",
        "html": f"""<p>Hi {ai_input['creatorName']},</p>
<p>I came across your YouTube channel "<strong>{ai_input['channelName']}</strong>" and was impressed by your content, especially your recent video "<em>{ai_input['lastVideoTitle']}</em>".</p>
<p>With <strong>{ai_input['subscribers']:,} subscribers</strong>, you're at a great stage where professional video editing could significantly boost your channel's growth and revenue potential.</p>
<p>Our video editing team specializes in helping content creators like you:</p>
<ul>
<li>Increase average view duration by 30-50%</li>
<li>Improve audience retention and engagement</li>
<li>Create more consistent, professional content</li>
<li>Save 10-15 hours per week on editing</li>
</ul>
<p>We've helped creators grow from 50K to 500K+ subscribers through strategic editing improvements.</p>
<p>Would you be interested in a <strong>free consultation</strong> to discuss how we can help accelerate your channel's growth?</p>
<p>Best regards,<br>Professional Video Editing Team</p>
<p><em>P.S. I noticed the engagement on your videos - with the right editing enhancements, we could help you monetize that audience even more effectively.</em></p>"""
    }

async def send_email(to_email: str, subject: str, html_body: str, plain_body: str):
    """Send email via SMTP"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Bcc'] = SMTP_EMAIL
        
        part1 = MIMEText(plain_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False

# API Routes
@api_router.post("/lead-generation/start", response_model=ProcessingStatus)
async def start_lead_generation(request: LeadGenerationRequest, background_tasks: BackgroundTasks):
    """Start the lead generation process"""
    status = ProcessingStatus(
        status="started",
        current_step="initializing"
    )
    
    await db.processing_status.insert_one(status.dict())
    background_tasks.add_task(process_lead_generation, status.id, request)
    
    await send_discord_notification(f"🚀 **Lead Generation Started!**\n📋 Keywords: {', '.join(request.keywords)}\n👥 Subscriber Range: {request.subscriber_min:,} - {request.subscriber_max:,}\n🎯 Max Channels: {request.max_channels}")
    
    return status

async def process_lead_generation(status_id: str, request: LeadGenerationRequest):
    """Background task to process lead generation"""
    try:
        await db.processing_status.update_one(
            {"id": status_id},
            {"$set": {"current_step": "discovering_videos", "updated_at": datetime.now(timezone.utc)}}
        )
        
        all_videos = []
        
        for keyword in request.keywords:
            await send_discord_notification(f"🔍 Searching videos for keyword: **{keyword}**")
            logger.info(f"Processing keyword: '{keyword}' with max {request.max_videos_per_keyword} videos")
            
            videos = await search_youtube_videos(keyword, request.max_videos_per_keyword)
            logger.info(f"Found {len(videos)} videos for keyword '{keyword}'")
            all_videos.extend(videos)
            
            await asyncio.sleep(1)
        
        logger.info(f"Total videos discovered across all keywords: {len(all_videos)}")
        
        channels_dict = {}
        for video in all_videos:
            channel_id = video['channelId']
            if channel_id not in channels_dict:
                channels_dict[channel_id] = {
                    'channel_id': channel_id,
                    'channel_title': video['channelTitle'],
                    'videos': []
                }
            channels_dict[channel_id]['videos'].append(video)
        
        channels_discovered = len(channels_dict)
        await db.processing_status.update_one(
            {"id": status_id},
            {"$set": {"channels_discovered": channels_discovered, "updated_at": datetime.now(timezone.utc)}}
        )
        
        await send_discord_notification(f"📊 Discovered **{channels_discovered}** unique channels")
        
        channels_processed = 0
        emails_found = 0
        emails_sent = 0
        
        for channel_id, channel_info in list(channels_dict.items())[:request.max_channels]:
            try:
                await db.processing_status.update_one(
                    {"id": status_id},
                    {"$set": {"current_step": f"processing_channel_{channels_processed + 1}", "updated_at": datetime.now(timezone.utc)}}
                )
                
                channel_details = await get_channel_details(channel_id)
                if not channel_details:
                    continue
                
                subscriber_count = channel_details['subscriber_count']
                if subscriber_count < request.subscriber_min or subscriber_count > request.subscriber_max:
                    logger.info(f"Channel {channel_details['channel_title']} filtered out by subscriber count: {subscriber_count}")
                    continue
                
                content_frequency = await calculate_content_frequency(channel_id)
                if content_frequency < request.content_frequency_min:
                    logger.info(f"Channel {channel_details['channel_title']} filtered out by low content frequency: {content_frequency}")
                    continue
                
                if request.content_frequency_max and content_frequency > request.content_frequency_max:
                    logger.info(f"Channel {channel_details['channel_title']} filtered out by high content frequency: {content_frequency}")
                    continue
                
                logger.info(f"Channel {channel_details['channel_title']} passed filters - Subscribers: {subscriber_count}, Frequency: {content_frequency}")
                
                channel = Channel(
                    channel_id=channel_id,
                    channel_title=channel_details['channel_title'],
                    creator_name=channel_details['channel_title'],
                    channel_url=f"https://youtube.com/channel/{channel_id}",
                    subscriber_count=channel_details['subscriber_count'],
                    video_count=channel_details['video_count'],
                    content_frequency_weekly=content_frequency,
                    keywords_found_in=[video['keyword'] for video in channel_info['videos']],
                    processing_timestamp=datetime.now(timezone.utc)
                )
                
                # Email extraction
                email, about_content = await scrape_channel_about_page(channel_id)
                if email:
                    channel.email = email
                    channel.email_status = "found"
                    channel.about_page_content = about_content
                    emails_found += 1
                    
                    # Send notification for each email found
                    await send_discord_notification(f"📧 **Email Found!** \n🎯 Channel: **{channel.channel_title}**\n📧 Email: `{email}`\n👥 Subscribers: {subscriber_count:,}")
                    
                    await process_channel_with_email(channel)
                    
                    if channel.email_subject and channel.email_body_preview:
                        email_sent = await send_email(
                            email, 
                            channel.email_subject, 
                            channel.email_body_preview,
                            channel.email_body_preview
                        )
                        
                        if email_sent:
                            channel.email_sent_status = "sent"
                            emails_sent += 1
                            await send_discord_notification(f"✉️ **Email Sent!** Client outreach sent to **{channel.channel_title}**")
                        else:
                            channel.email_sent_status = "failed"
                    
                    await db.main_leads.insert_one(channel.dict())
                    
                else:
                    channel.email_status = "not_found"
                    await db.no_email_leads.insert_one(channel.dict())
                    
                    # Send notification for each email not found
                    await send_discord_notification(f"❌ **No Email Found** \n🎯 Channel: **{channel.channel_title}**\n👥 Subscribers: {subscriber_count:,}")
                
                channels_processed += 1
                
                await db.processing_status.update_one(
                    {"id": status_id},
                    {"$set": {
                        "channels_processed": channels_processed,
                        "emails_found": emails_found,
                        "emails_sent": emails_sent,
                        "updated_at": datetime.now(timezone.utc)
                    }}
                )
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing channel {channel_id}: {e}")
                await db.processing_status.update_one(
                    {"id": status_id},
                    {"$push": {"errors": f"Channel {channel_id}: {str(e)}"}}
                )
        
        await db.processing_status.update_one(
            {"id": status_id},
            {"$set": {
                "status": "completed",
                "current_step": "finished",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        await send_discord_notification(f"✅ **Lead Generation Completed!**\n📊 **Final Results:**\n🎯 Channels Processed: **{channels_processed}**\n📧 Emails Found: **{emails_found}**\n✉️ Client Outreach Sent: **{emails_sent}**")
        
    except Exception as e:
        logger.error(f"Error in lead generation process: {e}")
        await db.processing_status.update_one(
            {"id": status_id},
            {"$set": {
                "status": "failed",
                "current_step": "error",
                "updated_at": datetime.now(timezone.utc)
            },
            "$push": {"errors": str(e)}}
        )
        
        await send_discord_notification(f"❌ **Lead Generation Failed:** {str(e)}")

async def process_channel_with_email(channel: Channel):
    """Process channel that has email - full analysis"""
    try:
        videos = await get_channel_videos(channel.channel_id, 3)
        if videos:
            latest_video = videos[0]
            channel.latest_video_title = latest_video['title']
            channel.latest_video_date = latest_video['publishedAt']
            
            comments = await get_video_comments(latest_video['videoId'], 100)
            channel.comments_analyzed = len(comments)
            
            if comments:
                comment_analysis = analyze_comments_for_editing(comments)
                top_comment = comment_analysis['top_comment']
                
                if top_comment:
                    channel.top_comment = top_comment['text']
                    channel.comment_author = top_comment['author']
                
                email_content = await generate_client_outreach_email(
                    channel.dict(),
                    latest_video,
                    top_comment or {}
                )
                
                channel.email_subject = email_content.get('subject', '')
                channel.email_body_preview = email_content.get('html', '')
                
    except Exception as e:
        logger.error(f"Error processing channel with email {channel.channel_id}: {e}")
        channel.error_messages.append(str(e))

@api_router.get("/lead-generation/status/{status_id}", response_model=ProcessingStatus)
async def get_processing_status(status_id: str):
    """Get processing status"""
    status = await db.processing_status.find_one({"id": status_id})
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    return ProcessingStatus(**status)

@api_router.get("/leads/main", response_model=List[Channel])
async def get_main_leads():
    """Get all main leads (with emails)"""
    leads = await db.main_leads.find().to_list(1000)
    return [Channel(**lead) for lead in leads]

@api_router.get("/leads/no-email", response_model=List[Channel])
async def get_no_email_leads():
    """Get all leads without emails"""
    leads = await db.no_email_leads.find().to_list(1000)
    return [Channel(**lead) for lead in leads]

@api_router.post("/leads/add-email/{channel_id}")
async def add_email_to_channel(channel_id: str, email: str):
    """Add email to a channel and move from no-email to main leads"""
    try:
        channel_doc = await db.no_email_leads.find_one({"channel_id": channel_id})
        if not channel_doc:
            raise HTTPException(status_code=404, detail="Channel not found in no-email leads")
        
        channel_doc['email'] = email
        channel_doc['email_status'] = "manually_added"
        channel_doc['processing_timestamp'] = datetime.now(timezone.utc)
        
        channel = Channel(**channel_doc)
        await process_channel_with_email(channel)
        
        if channel.email_subject and channel.email_body_preview:
            email_sent = await send_email(
                email,
                channel.email_subject,
                channel.email_body_preview,
                channel.email_body_preview
            )
            
            if email_sent:
                channel.email_sent_status = "sent"
                await send_discord_notification(f"✉️ **Manual Email Sent!** Client outreach sent to **{channel.channel_title}** (manual email)")
        
        await db.main_leads.insert_one(channel.dict())
        await db.no_email_leads.delete_one({"channel_id": channel_id})
        
        return {"message": "Email added and channel processed successfully"}
        
    except Exception as e:
        logger.error(f"Error adding email to channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/")
async def root():
    return {"message": "YouTube Lead Generation Platform API"}

@api_router.post("/debug/test-email-extraction")
async def test_email_extraction(channel_id: str):
    """Debug endpoint to test email extraction for a specific channel"""
    try:
        logger.info(f"Testing email extraction for channel: {channel_id}")
        
        # Test the scraping function
        email, content = await scrape_channel_about_page(channel_id)
        
        return {
            "channel_id": channel_id,
            "email_found": email,
            "content_preview": content[:500] if content else None,
            "content_length": len(content) if content else 0,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error testing email extraction: {e}")
        return {
            "channel_id": channel_id,
            "email_found": None,
            "content_preview": None,
            "content_length": 0,
            "error": str(e),
            "success": False
        }

@api_router.post("/debug/test-text-email-extraction") 
async def test_text_email_extraction(text: str):
    """Debug endpoint to test email extraction from raw text"""
    try:
        email = extract_email_from_text(text)
        return {
            "input_text": text,
            "email_found": email,
            "success": True
        }
    except Exception as e:
        return {
            "input_text": text,
            "email_found": None,
            "error": str(e),
            "success": False
        }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
