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

# Discord Configuration
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1417915138400587909/B9_tEDQKMZfemFvu0z2vy3z7HjVyCZf5PCAj6DmDuOdPira5wwvH_QJpZRjKTUPbzP3c"

# Gemini Configuration
GEMINI_API_KEY = "AIzaSyDO7g9pBST5_856x6PkXilLVhMqYtCK2J0"

# Google Sheets Configuration
GOOGLE_CLIENT_ID = "304595221220-rj66fpkfj3n4ptvneq7pnmg9va7bo3q7.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

# Authentication Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY", "")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# Pydantic Models
class LeadGenerationRequest(BaseModel):
    keywords: List[str]
    max_videos_per_keyword: int = 2000
    max_channels: int = 1000
    # Subscriber range filtering (default: Small 10K-100K + Medium 100K-1M)
    subscriber_min: int = 10000  # 10K subscribers minimum
    subscriber_max: int = 1000000  # 1M subscribers maximum
    # Content frequency filtering (videos per week)
    content_frequency_min: float = 0.14  # ~1 video per week minimum (1/7 days)
    content_frequency_max: Optional[float] = 2.0  # 2 videos per week maximum

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
    content_frequency_weekly: float = 0.0  # Videos per week
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

# Authentication Models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Token(BaseModel):
    access_token: str
    token_type: str

class EmailExtractionRequest(BaseModel):
    channel_id: str
    recaptcha_response: str

# Utility Functions
async def send_discord_notification(message: str):
    """Send notification to Discord webhook"""
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")

# Authentication Utility Functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Simple SHA256 hashing for now (in production, use proper bcrypt)
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_password_hash(password: str) -> str:
    # Simple SHA256 hashing for now (in production, use proper bcrypt)
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_username(username: str):
    user_doc = await db.users.find_one({"username": username})
    return user_doc

async def get_user_by_email(email: str):
    user_doc = await db.users.find_one({"email": email})
    return user_doc

async def create_user(user_data: UserCreate):
    hashed_password = get_password_hash(user_data.password)
    new_user = {
        "id": str(uuid.uuid4()),
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "full_name": user_data.full_name,
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.users.insert_one(new_user)
    return new_user

async def authenticate_user(username: str, password: str):
    user = await get_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if not current_user["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def verify_recaptcha(recaptcha_response: str) -> bool:
    """Verify reCAPTCHA v2 response"""
    if not RECAPTCHA_SECRET_KEY:
        logger.warning("reCAPTCHA secret key not configured, skipping verification")
        return True  # Skip verification if not configured
    
    try:
        data = {
            'secret': RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post('https://www.google.com/recaptcha/api/siteverify', data=data) as response:
                result = await response.json()
                return result.get('success', False)
    except Exception as e:
        logger.error(f"reCAPTCHA verification failed: {e}")
        return False

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
                    publishedAfter="2022-01-01T00:00:00Z"  # Extended date range
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
                # Try next API key
                global current_key_index
                current_key_index = (current_key_index + 1) % len(YOUTUBE_API_KEYS)
                logger.info(f"Switched to API key index: {current_key_index}")
                
                if current_key_index == 0:  # All keys tried
                    logger.error("All YouTube API keys exhausted")
                    break
                    
                # Retry with new key
                youtube = get_youtube_service()
                continue
                
        logger.info(f"Final result: {len(videos)} videos found for keyword '{keyword}'")
        return videos
        
    except Exception as e:
        logger.error(f"Error searching YouTube videos for '{keyword}': {e}")
        return []

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
    """Scrape channel about page for email and content using Playwright"""
    try:
        # Try both URL formats for YouTube channels
        urls_to_try = [
            f"https://www.youtube.com/channel/{channel_id}/about",
            f"https://www.youtube.com/@{channel_id}/about"  # Handle format
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
                    
                    # Navigate to the about page
                    await page.goto(about_url, wait_until="networkidle", timeout=30000)
                    
                    # Wait for content to load
                    await page.wait_for_timeout(3000)
                    
                    # Get page content
                    content = await page.content()
                    
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    text_content = soup.get_text()
                    
                    # Look for email in the page content
                    email = extract_email_from_text(text_content)
                    
                    if email or "About" in content:
                        # Success - found either email or valid about page
                        await browser.close()
                        return email, text_content[:1000]
                        
                except Exception as url_error:
                    logger.warning(f"Failed to scrape {about_url}: {url_error}")
                    continue
            
            await browser.close()
            
    except Exception as e:
        logger.error(f"Error scraping about page for channel {channel_id}: {e}")
    
    # Fallback: Try to get channel details from YouTube API for custom URL
    try:
        youtube = get_youtube_service()
        request = youtube.channels().list(
            part="snippet",
            id=channel_id
        )
        response = request.execute()
        items = response.get('items', [])
        
        if items:
            snippet = items[0].get('snippet', {})
            description = snippet.get('description', '')
            custom_url = snippet.get('customUrl', '')
            
            # Try to extract email from description
            email = extract_email_from_text(description)
            
            if email:
                logger.info(f"Found email in channel description: {email}")
                return email, description[:1000]
                
            # If no email but has custom URL, try that format
            if custom_url:
                custom_handle = custom_url.replace('/', '').replace('@', '')
                try:
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        context = await browser.new_context()
                        page = await context.new_page()
                        
                        about_url = f"https://www.youtube.com/@{custom_handle}/about"
                        await page.goto(about_url, wait_until="networkidle", timeout=30000)
                        await page.wait_for_timeout(3000)
                        
                        content = await page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        text_content = soup.get_text()
                        
                        email = extract_email_from_text(text_content)
                        
                        await browser.close()
                        
                        if email:
                            return email, text_content[:1000]
                            
                except Exception as custom_error:
                    logger.warning(f"Failed to scrape custom URL {custom_handle}: {custom_error}")
            
            return None, description[:1000]
            
    except Exception as api_error:
        logger.error(f"Error getting channel details from API: {api_error}")
    
    return None, None

async def enhanced_email_extraction(channel_url: str, channel_title: str) -> Optional[str]:
    """Enhanced email extraction using multiple strategies"""
    try:
        # Strategy 1: Try scraping the channel about page with different approaches
        channel_id = channel_url.split('/')[-1] if '/' in channel_url else channel_url
        
        # Use the existing scrape_channel_about_page function
        email, _ = await scrape_channel_about_page(channel_id)
        if email:
            return email
        
        # Strategy 2: Try alternative URL formats and social media links
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            # Try different URL variations
            urls_to_try = [
                f"https://www.youtube.com/c/{channel_title.replace(' ', '')}/about",
                f"https://www.youtube.com/{channel_title.replace(' ', '')}/about",
                channel_url + "/about" if not channel_url.endswith("/about") else channel_url
            ]
            
            for url in urls_to_try:
                try:
                    await page.goto(url, wait_until="networkidle", timeout=20000)
                    await page.wait_for_timeout(2000)
                    
                    # Look for email patterns in page content
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    text_content = soup.get_text()
                    
                    # Extract email from text
                    email = extract_email_from_text(text_content)
                    if email:
                        await browser.close()
                        return email
                        
                    # Look for social media links that might contain emails
                    links = soup.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        if any(domain in href for domain in ['instagram.com', 'twitter.com', 'facebook.com']):
                            # Could potentially scrape these for contact info, but for now skip
                            pass
                            
                except Exception as url_error:
                    logger.debug(f"Failed to scrape {url}: {url_error}")
                    continue
            
            await browser.close()
        
        return None
        
    except Exception as e:
        logger.error(f"Enhanced email extraction error for {channel_title}: {e}")
        return None

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
        
        # Get uploads playlist
        request = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        )
        
        response = request.execute()
        items = response.get('items', [])
        
        if not items:
            return []
            
        uploads_playlist = items[0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get videos from uploads playlist
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
        
        # Get uploads playlist
        request = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        )
        
        response = request.execute()
        items = response.get('items', [])
        
        if not items:
            return 0.0
            
        uploads_playlist = items[0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get recent videos (up to 50 for analysis)
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist,
            maxResults=50
        )
        
        response = request.execute()
        videos = response.get('items', [])
        
        if len(videos) < 2:
            return 0.0
        
        # Parse publication dates and calculate frequency
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
        
        # Sort dates (newest first)
        publish_dates.sort(reverse=True)
        
        # Calculate average time between uploads (in days)
        total_days = 0
        intervals = 0
        
        for i in range(len(publish_dates) - 1):
            time_diff = publish_dates[i] - publish_dates[i + 1]
            total_days += time_diff.total_seconds() / (24 * 3600)
            intervals += 1
        
        if intervals == 0:
            return 0.0
        
        avg_days_between_uploads = total_days / intervals
        
        # Convert to videos per week
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
    editing_score = 5.0  # Default score
    
    for comment in comments:
        text_lower = comment['text'].lower()
        
        # Check if comment mentions editing terms
        for term in editing_terms:
            if term in text_lower:
                relevant_comments.append(comment)
                
                # Simple sentiment analysis for editing score
                if any(word in text_lower for word in ['good', 'great', 'nice', 'love', 'perfect']):
                    editing_score += 0.5
                elif any(word in text_lower for word in ['bad', 'poor', 'hate', 'awful', 'terrible']):
                    editing_score -= 0.5
                break
    
    # Find top comment (most liked relevant comment or most liked overall)
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

async def generate_ai_outreach_email(channel_data: Dict, video_data: Dict, comment_data: Dict) -> Dict:
    """Generate personalized outreach email using Gemini"""
    try:
        # Prepare AI input
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
        
        # Construct the prompt with the user's specific video editing template
        prompt = f"""Using the following data about a YouTube creator's channel, generate a personalized outreach email from the template given at last. Fill the blanks like creator name etc., and change the lines of the email as per the details for personalization. Make sure to change the P.S. sentence according to the comments. Send the subject line separately. Send HTML and text forms of the copy. Base the email on these details:

- Creator Name: {ai_input['creatorName']}
- Channel Name: {ai_input['channelName']}  
- Channel URL: {ai_input['channelUrl']}
- Niche: {ai_input['niche']}
- Subscriber Count: {ai_input['subscribers']}
- Recent Video Title: {ai_input['lastVideoTitle']}
- Recent Video URL: {ai_input['videoUrl']}
- Top Viewer Comment by {ai_input['topCommentAuthor']}: "{ai_input['topCommentText']}"
- Comment Count: {ai_input['commentCount']}

Editing/SFX/Graphics micro‑audit (latest video):
- If tooling allows accessing the Recent Video URL, analyze it directly for editing, sound, pacing, motion/graphics, text readability, color/LUT consistency, transitions, and export settings. If access isn't possible, infer only from provided metadata/comments and clearly state that a quick 5‑minute audit can confirm specifics.
- Identify up to 3 concrete issues or hypotheses with 1 actionable fix each (e.g., "dialogue compression ~3:1 with soft knee," "reduce music ducking threshold by ~2dB," "increase lower‑third contrast to meet WCAG AA, add subtle drop shadow," "smooth keyframe easing on zooms," "standardize white balance around 5600K," "export at 1080p, 16–20 Mbps").
- Do NOT fabricate details you cannot verify from the inputs or from the video if you can open the URL.

Requirements:
- Use their actual name and recent video details.
- Reference the top viewer comment naturally.
- Keep the tone professional yet warm.
- Include a clear call-to-action for collaboration.
- Output ONLY valid JSON with keys: subject, plain, html.
- Avoid fabricating any data not provided.
- Change the P.S..... line with the error you found.
- Its optional to write about the fix for that problem, if you doubt or fabricated the fix out of nothing DO NOT write about the fix in body

subject: I spent 3 hours analyzing your editing patterns - found something that could 10x your retention

Template to adapt (fill placeholders with provided data and weave in the micro‑audit):

Hey {ai_input['creatorName']},

I know this might sound crazy, but I just spent the last 3 hours diving deep into your recent videos, and I discovered something that made me pause my Netflix show at 2 AM.

You're 1 of only 3 YouTubers whose channel I've analyzed this month that has the perfect storm for explosive growth — and honestly, I couldn't sleep without reaching out to you.

Here's what caught my attention:

Your content quality is solid (seriously, the way you handle {ai_input['lastVideoTitle']} is refreshing), but I noticed something in your comment section that most creators miss entirely.

For example, {ai_input['topCommentAuthor']} said: "{ai_input['topCommentText']}".

You're sitting at what I call the "retention goldmine" — you have the technical skills (evidenced by viewer comments), but your current editing score suggests you're tapping into about 50% of your potential.

Quick micro-audit on your latest video:
- [Bullet 1: concise issue/hypothesis + actionable fix]
- [Bullet 2: concise issue/hypothesis + actionable fix]
- [Optional Bullet 3: concise issue/hypothesis + actionable fix]

The gap I identified: Your audio optimization and modern pacing techniques could increase your average view duration by 40–60%. I've seen this exact pattern with 2 other channels I've worked with — one went from 45K to 180K subs in 4 months after we fixed these specific elements.

I specialize in bridging this exact gap — taking technically proficient creators like you and optimizing the retention psychology behind the scenes.

What I'm proposing:
- Free analysis of your top 3 performing videos
- Custom editing strategy tailored to your audience's behavior patterns
- Implementation that maintains your authentic style while maximizing watch time

I only take on 3–4 creators per quarter (quality over quantity), and your channel profile fits exactly what I'm looking for in a collaboration partner.

Interested in seeing what those specific optimizations could look like for your content?

Best regards,
Video Editing Specialist

P.S. If you want, I can share a 30‑second fix that addresses the feedback in that top comment — happy to send it over regardless of whether we work together.

Output as JSON with subject, plain, and html keys."""

        # Make request to Gemini API
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
                    
                    # Try to parse as JSON
                    try:
                        # Clean the response to extract JSON
                        json_start = generated_text.find('{')
                        json_end = generated_text.rfind('}') + 1
                        if json_start != -1 and json_end != -1:
                            json_text = generated_text[json_start:json_end]
                            return json.loads(json_text)
                    except:
                        pass
                    
                    # Fallback: create structured response
                    return {
                        "subject": "I spent 3 hours analyzing your editing patterns - found something that could 10x your retention",
                        "plain": generated_text,
                        "html": generated_text.replace('\n', '<br>')
                    }
                else:
                    logger.error(f"Gemini API error: {response.status}")
                    
    except Exception as e:
        logger.error(f"Error generating AI email: {e}")
    
    # Fallback email
    return {
        "subject": "Collaboration Opportunity - Content Creator Partnership",
        "plain": f"Hi {channel_data.get('channel_title', '')},\n\nI came across your channel and was impressed by your content quality. I'd love to discuss potential collaboration opportunities.\n\nBest regards,\nLead Generation Team",
        "html": f"<p>Hi {channel_data.get('channel_title', '')},</p><p>I came across your channel and was impressed by your content quality. I'd love to discuss potential collaboration opportunities.</p><p>Best regards,<br>Lead Generation Team</p>"
    }

async def send_email(to_email: str, subject: str, html_body: str, plain_body: str):
    """Send email via SMTP"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Bcc'] = SMTP_EMAIL  # BCC for tracking
        
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
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False

# API Routes

# Authentication Routes
@api_router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    # Check if username already exists
    if await get_user_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if await get_user_by_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    new_user = await create_user(user)
    
    return UserResponse(
        id=new_user["id"],
        username=new_user["username"],
        email=new_user["email"],
        full_name=new_user["full_name"],
        is_active=new_user["is_active"],
        created_at=new_user["created_at"]
    )

@api_router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"]
    )

# Enhanced Email Extraction Route (Protected with Auth + reCAPTCHA)
@api_router.post("/extract-email")
async def extract_email_address(
    request: EmailExtractionRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Extract email address with reCAPTCHA verification (requires authentication)"""
    
    # Verify reCAPTCHA
    if not await verify_recaptcha(request.recaptcha_response):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reCAPTCHA verification failed"
        )
    
    try:
        # Find the channel
        channel_doc = await db.main_leads.find_one({"channel_id": request.channel_id})
        if not channel_doc:
            channel_doc = await db.no_email_leads.find_one({"channel_id": request.channel_id})
        
        if not channel_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        
        # If email already exists, return it
        if channel_doc.get("email"):
            return {
                "email": channel_doc["email"],
                "extraction_method": "cached",
                "message": "Email already available"
            }
        
        # Attempt enhanced email extraction using Playwright
        extracted_email = await enhanced_email_extraction(
            channel_doc["channel_url"], 
            channel_doc["channel_title"]
        )
        
        if extracted_email:
            # Update the channel with the extracted email
            update_data = {
                "email": extracted_email,
                "email_status": "extracted_enhanced",
                "processing_timestamp": datetime.now(timezone.utc)
            }
            
            # Move to main_leads if it was in no_email_leads
            if channel_doc.get("email_status") == "not_found":
                await db.no_email_leads.delete_one({"channel_id": request.channel_id})
                channel_doc.update(update_data)
                await db.main_leads.insert_one(channel_doc)
            else:
                await db.main_leads.update_one(
                    {"channel_id": request.channel_id},
                    {"$set": update_data}
                )
            
            return {
                "email": extracted_email,
                "extraction_method": "enhanced_playwright",
                "message": "Email successfully extracted"
            }
        else:
            return {
                "email": None,
                "extraction_method": "enhanced_playwright",
                "message": "No email found despite enhanced extraction"
            }
            
    except Exception as e:
        logger.error(f"Enhanced email extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email extraction failed"
        )

@api_router.post("/lead-generation/start", response_model=ProcessingStatus)
async def start_lead_generation(request: LeadGenerationRequest, background_tasks: BackgroundTasks):
    """Start the lead generation process"""
    
    # Create processing status
    status = ProcessingStatus(
        status="started",
        current_step="initializing"
    )
    
    # Save initial status
    await db.processing_status.insert_one(status.dict())
    
    # Start background processing
    background_tasks.add_task(process_lead_generation, status.id, request)
    
    await send_discord_notification(f"🚀 Lead generation started with keywords: {', '.join(request.keywords)}")
    
    return status

async def process_lead_generation(status_id: str, request: LeadGenerationRequest):
    """Background task to process lead generation"""
    try:
        # Update status
        await db.processing_status.update_one(
            {"id": status_id},
            {"$set": {"current_step": "discovering_videos", "updated_at": datetime.now(timezone.utc)}}
        )
        
        all_videos = []
        
        # Discover videos for each keyword
        for keyword in request.keywords:
            await send_discord_notification(f"🔍 Searching videos for keyword: {keyword}")
            logger.info(f"Processing keyword: '{keyword}' with max {request.max_videos_per_keyword} videos")
            
            videos = await search_youtube_videos(keyword, request.max_videos_per_keyword)
            logger.info(f"Found {len(videos)} videos for keyword '{keyword}'")
            all_videos.extend(videos)
            
            await asyncio.sleep(1)  # Rate limiting
        
        logger.info(f"Total videos discovered across all keywords: {len(all_videos)}")
        
        # Extract unique channels
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
        
        await send_discord_notification(f"📊 Discovered {channels_discovered} unique channels")
        
        # Process each channel
        channels_processed = 0
        emails_found = 0
        emails_sent = 0
        
        for channel_id, channel_info in list(channels_dict.items())[:request.max_channels]:
            try:
                await db.processing_status.update_one(
                    {"id": status_id},
                    {"$set": {"current_step": f"processing_channel_{channels_processed + 1}", "updated_at": datetime.now(timezone.utc)}}
                )
                
                # Get channel details
                channel_details = await get_channel_details(channel_id)
                if not channel_details:
                    continue
                
                # Apply subscriber range filter
                subscriber_count = channel_details['subscriber_count']
                if subscriber_count < request.subscriber_min or subscriber_count > request.subscriber_max:
                    logger.info(f"Channel {channel_details['channel_title']} filtered out by subscriber count: {subscriber_count} (range: {request.subscriber_min}-{request.subscriber_max})")
                    continue
                
                # Calculate and apply content frequency filter
                content_frequency = await calculate_content_frequency(channel_id)
                if content_frequency < request.content_frequency_min:
                    logger.info(f"Channel {channel_details['channel_title']} filtered out by low content frequency: {content_frequency} videos/week (minimum: {request.content_frequency_min})")
                    continue
                
                if request.content_frequency_max and content_frequency > request.content_frequency_max:
                    logger.info(f"Channel {channel_details['channel_title']} filtered out by high content frequency: {content_frequency} videos/week (maximum: {request.content_frequency_max})")
                    continue
                
                logger.info(f"Channel {channel_details['channel_title']} passed filters - Subscribers: {subscriber_count}, Frequency: {content_frequency} videos/week")
                
                # Create channel object
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
                
                # Email extraction (FIRST PRIORITY)
                email, about_content = await scrape_channel_about_page(channel_id)
                if email:
                    channel.email = email
                    channel.email_status = "found"
                    channel.about_page_content = about_content
                    emails_found += 1
                    
                    # Continue with full processing for channels with emails
                    await process_channel_with_email(channel)
                    
                    # Send outreach email
                    if channel.email_subject and channel.email_body_preview:
                        email_sent = await send_email(
                            email, 
                            channel.email_subject, 
                            channel.email_body_preview,
                            channel.email_body_preview  # Using same for both for now
                        )
                        
                        if email_sent:
                            channel.email_sent_status = "sent"
                            emails_sent += 1
                            await send_discord_notification(f"✉️ Email sent to {channel.channel_title}")
                        else:
                            channel.email_sent_status = "failed"
                    
                    # Store in main leads collection
                    await db.main_leads.insert_one(channel.dict())
                    
                else:
                    channel.email_status = "not_found"
                    # Store in no-email leads collection
                    await db.no_email_leads.insert_one(channel.dict())
                
                channels_processed += 1
                
                # Update progress
                await db.processing_status.update_one(
                    {"id": status_id},
                    {"$set": {
                        "channels_processed": channels_processed,
                        "emails_found": emails_found,
                        "emails_sent": emails_sent,
                        "updated_at": datetime.now(timezone.utc)
                    }}
                )
                
                await asyncio.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error processing channel {channel_id}: {e}")
                await db.processing_status.update_one(
                    {"id": status_id},
                    {"$push": {"errors": f"Channel {channel_id}: {str(e)}"}}
                )
        
        # Final status update
        await db.processing_status.update_one(
            {"id": status_id},
            {"$set": {
                "status": "completed",
                "current_step": "finished",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        await send_discord_notification(f"✅ Lead generation completed!\n📊 Stats:\n- Channels: {channels_processed}\n- Emails found: {emails_found}\n- Emails sent: {emails_sent}")
        
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
        
        await send_discord_notification(f"❌ Lead generation failed: {str(e)}")

async def process_channel_with_email(channel: Channel):
    """Process channel that has email - full analysis"""
    try:
        # Get recent videos
        videos = await get_channel_videos(channel.channel_id, 3)
        if videos:
            latest_video = videos[0]
            channel.latest_video_title = latest_video['title']
            channel.latest_video_date = latest_video['publishedAt']
            
            # Analyze comments from latest video
            comments = await get_video_comments(latest_video['videoId'], 100)
            channel.comments_analyzed = len(comments)
            
            if comments:
                comment_analysis = analyze_comments_for_editing(comments)
                top_comment = comment_analysis['top_comment']
                
                if top_comment:
                    channel.top_comment = top_comment['text']
                    channel.comment_author = top_comment['author']
                
                # Generate AI outreach email
                email_content = await generate_ai_outreach_email(
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
        # Find channel in no-email collection
        channel_doc = await db.no_email_leads.find_one({"channel_id": channel_id})
        if not channel_doc:
            raise HTTPException(status_code=404, detail="Channel not found in no-email leads")
        
        # Update with email
        channel_doc['email'] = email
        channel_doc['email_status'] = "manually_added"
        channel_doc['processing_timestamp'] = datetime.now(timezone.utc)
        
        # Process with full analysis
        channel = Channel(**channel_doc)
        await process_channel_with_email(channel)
        
        # Generate and send email
        if channel.email_subject and channel.email_body_preview:
            email_sent = await send_email(
                email,
                channel.email_subject,
                channel.email_body_preview,
                channel.email_body_preview
            )
            
            if email_sent:
                channel.email_sent_status = "sent"
                await send_discord_notification(f"✉️ Email sent to {channel.channel_title} (manual email)")
        
        # Move to main leads
        await db.main_leads.insert_one(channel.dict())
        await db.no_email_leads.delete_one({"channel_id": channel_id})
        
        return {"message": "Email added and channel processed successfully"}
        
    except Exception as e:
        logger.error(f"Error adding email to channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/")
async def root():
    return {"message": "YouTube Lead Generation Platform API"}

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