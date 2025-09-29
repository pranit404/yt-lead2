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
import ipaddress
from urllib.parse import urlparse, parse_qs
import html2text
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import bcrypt
import jwt
from passlib.context import CryptContext
from twocaptcha import TwoCaptcha

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

# 2captcha Configuration  
TWOCAPTCHA_API_KEY = "1f2a3d913a5e81af32e4014d5f9afbdb"

# Account Rotation Settings
MAX_ACCOUNTS_CONCURRENT = int(os.environ.get('MAX_ACCOUNTS_CONCURRENT', '3'))
ACCOUNT_COOLDOWN_MINUTES = int(os.environ.get('ACCOUNT_COOLDOWN_MINUTES', '30'))
MAX_DAILY_REQUESTS_PER_ACCOUNT = int(os.environ.get('MAX_DAILY_REQUESTS_PER_ACCOUNT', '100'))

# Proxy Management Settings
MAX_PROXIES_CONCURRENT = int(os.environ.get('MAX_PROXIES_CONCURRENT', '5'))
PROXY_COOLDOWN_MINUTES = int(os.environ.get('PROXY_COOLDOWN_MINUTES', '15'))
MAX_DAILY_REQUESTS_PER_PROXY = int(os.environ.get('MAX_DAILY_REQUESTS_PER_PROXY', '200'))
PROXY_HEALTH_CHECK_TIMEOUT = int(os.environ.get('PROXY_HEALTH_CHECK_TIMEOUT', '10'))

# Queue & Rate Limiting Settings
MAX_REQUESTS_PER_HOUR_PER_ACCOUNT = int(os.environ.get('MAX_REQUESTS_PER_HOUR_PER_ACCOUNT', '15'))
MAX_CONCURRENT_PROCESSING = int(os.environ.get('MAX_CONCURRENT_PROCESSING', '5'))
QUEUE_RETRY_ATTEMPTS = int(os.environ.get('QUEUE_RETRY_ATTEMPTS', '3'))
QUEUE_RETRY_DELAY_MINUTES = int(os.environ.get('QUEUE_RETRY_DELAY_MINUTES', '10'))

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

class YouTubeAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password: str
    status: str = "active"  # active, banned, rate_limited, maintenance
    last_used: Optional[datetime] = None
    rate_limit_reset: Optional[datetime] = None
    daily_requests_count: int = 0
    total_requests_count: int = 0
    session_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    cookies: Optional[Dict[str, Any]] = None
    success_rate: float = 100.0
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class AccountRotationRequest(BaseModel):
    force_new: bool = False
    preferred_account_id: Optional[str] = None

class AccountAddRequest(BaseModel):
    email: str
    password: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class AccountStatusUpdate(BaseModel):
    status: str

# Proxy Management Models
class ProxyConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ip: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks4, socks5
    status: str = "active"  # active, disabled, banned, maintenance
    last_used: Optional[datetime] = None
    daily_requests_count: int = 0
    total_requests_count: int = 0
    success_rate: float = 100.0
    response_time_avg: float = 0.0  # Average response time in seconds
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"  # healthy, unhealthy, unknown
    last_error: Optional[str] = None
    location: Optional[str] = None  # Geographic location
    provider: Optional[str] = None  # Proxy provider name
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProxyAddRequest(BaseModel):
    ip: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    location: Optional[str] = None
    provider: Optional[str] = None

class ProxyStatusUpdate(BaseModel):
    status: str

class ProxyHealthCheckRequest(BaseModel):
    proxy_id: Optional[str] = None  # If None, check all proxies

# Queue Management Models
class QueueRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    request_type: str = "channel_scraping"  # Types: channel_scraping, email_extraction, 2captcha_fallback
    priority: int = 5  # Priority 1-10 (1 = highest)
    attempts: int = 0
    max_attempts: int = 3
    status: str = "pending"  # pending, processing, completed, failed, retry_scheduled
    account_id: Optional[str] = None  # Assigned account for processing
    proxy_id: Optional[str] = None  # Assigned proxy for processing
    scheduled_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = {}  # Additional request-specific data
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AddToQueueRequest(BaseModel):
    channel_id: str
    request_type: str = "channel_scraping"
    priority: int = 5
    payload: Optional[Dict[str, Any]] = {}

class QueueStatusUpdate(BaseModel):
    status: str
    error_message: Optional[str] = None

class QueueBatchRequest(BaseModel):
    channel_ids: List[str]
    request_type: str = "channel_scraping"
    priority: int = 5
    payload: Optional[Dict[str, Any]] = {}

# Utility Functions
async def send_discord_notification(message: str):
    """Send notification to Discord webhook"""
    try:
        if DISCORD_WEBHOOK:
            async with aiohttp.ClientSession() as session:
                await session.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")

# Validation Functions
def validate_ip_address(ip: str) -> bool:
    """Validate if IP address is valid"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def validate_port(port: int) -> bool:
    """Validate if port number is valid (1-65535)"""
    return 1 <= port <= 65535

def validate_protocol(protocol: str) -> bool:
    """Validate if protocol is supported"""
    valid_protocols = ["http", "https", "socks4", "socks5"]
    return protocol.lower() in valid_protocols

# Account Management Functions
async def get_available_account() -> Optional[YouTubeAccount]:
    """Get an available YouTube account for scraping"""
    try:
        now = datetime.now(timezone.utc)
        
        # Find accounts that are active and not rate limited
        accounts_cursor = db.youtube_accounts.find({
            "status": "active",
            "$or": [
                {"rate_limit_reset": {"$lt": now}},
                {"rate_limit_reset": None}
            ],
            "daily_requests_count": {"$lt": MAX_DAILY_REQUESTS_PER_ACCOUNT}
        }).sort("last_used", 1).limit(1)
        
        accounts = await accounts_cursor.to_list(1)
        
        if accounts:
            account_doc = accounts[0]
            # Reset daily count if it's a new day
            if account_doc.get('last_used'):
                last_used = account_doc['last_used']
                if isinstance(last_used, str):
                    last_used = parser.parse(last_used)
                if now.date() > last_used.date():
                    account_doc['daily_requests_count'] = 0
            
            return YouTubeAccount(**account_doc)
        
        return None
    except Exception as e:
        logger.error(f"Error getting available account: {e}")
        return None

async def update_account_usage(account_id: str, success: bool = True, error_message: str = None):
    """Update account usage statistics"""
    try:
        now = datetime.now(timezone.utc)
        update_data = {
            "last_used": now,
            "updated_at": now,
            "$inc": {
                "daily_requests_count": 1,
                "total_requests_count": 1
            }
        }
        
        if error_message:
            update_data["last_error"] = error_message
            
        # Update success rate (simple moving average)
        account_doc = await db.youtube_accounts.find_one({"id": account_id})
        if account_doc:
            current_rate = account_doc.get('success_rate', 100.0)
            total_requests = account_doc.get('total_requests_count', 0)
            
            # Simple weighted average (give more weight to recent results)
            if total_requests > 0:
                weight = min(0.1, 1.0 / total_requests)  # 10% max weight for new result
                new_rate = current_rate * (1 - weight) + (100.0 if success else 0.0) * weight
                update_data["success_rate"] = round(new_rate, 2)
        
        await db.youtube_accounts.update_one(
            {"id": account_id},
            {"$set": update_data}
        )
        
        logger.info(f"Updated account {account_id} usage. Success: {success}")
        
    except Exception as e:
        logger.error(f"Error updating account usage for {account_id}: {e}")

async def mark_account_banned(account_id: str, reason: str = "Detected as banned"):
    """Mark an account as banned"""
    try:
        await db.youtube_accounts.update_one(
            {"id": account_id},
            {
                "$set": {
                    "status": "banned",
                    "last_error": reason,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        await send_discord_notification(f"🚫 **Account Banned** \n📧 Account: {account_id}\n💬 Reason: {reason}")
        logger.warning(f"Marked account {account_id} as banned: {reason}")
        
    except Exception as e:
        logger.error(f"Error marking account as banned {account_id}: {e}")

async def reset_daily_limits():
    """Reset daily request counts for all accounts (should be called daily)"""
    try:
        await db.youtube_accounts.update_many(
            {},
            {
                "$set": {
                    "daily_requests_count": 0,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        logger.info("Daily limits reset for all accounts")
    except Exception as e:
        logger.error(f"Error resetting daily limits: {e}")

# Proxy Management Functions
async def get_available_proxy() -> Optional[ProxyConfig]:
    """Get an available proxy for scraping"""
    try:
        now = datetime.now(timezone.utc)
        
        # Find proxies that are active and not overloaded
        proxies_cursor = db.proxy_pool.find({
            "status": "active",
            "health_status": {"$in": ["healthy", "unknown"]},
            "daily_requests_count": {"$lt": MAX_DAILY_REQUESTS_PER_PROXY},
            "$or": [
                {"last_used": None},
                {"last_used": {"$lt": now - timedelta(minutes=PROXY_COOLDOWN_MINUTES)}}
            ]
        }).sort([("success_rate", -1), ("last_used", 1)]).limit(1)
        
        proxies = await proxies_cursor.to_list(1)
        
        if proxies:
            proxy_doc = proxies[0]
            # Reset daily count if it's a new day
            if proxy_doc.get('last_used'):
                last_used = proxy_doc['last_used']
                if isinstance(last_used, str):
                    last_used = parser.parse(last_used)
                if now.date() > last_used.date():
                    proxy_doc['daily_requests_count'] = 0
            
            return ProxyConfig(**proxy_doc)
        
        return None
    except Exception as e:
        logger.error(f"Error getting available proxy: {e}")
        return None

async def update_proxy_usage(proxy_id: str, success: bool = True, response_time: float = 0.0, error_message: str = None):
    """Update proxy usage statistics"""
    try:
        now = datetime.now(timezone.utc)
        update_data = {
            "last_used": now,
            "updated_at": now,
            "$inc": {
                "daily_requests_count": 1,
                "total_requests_count": 1
            }
        }
        
        if error_message:
            update_data["last_error"] = error_message
            
        # Update success rate and average response time
        proxy_doc = await db.proxy_pool.find_one({"id": proxy_id})
        if proxy_doc:
            current_rate = proxy_doc.get('success_rate', 100.0)
            current_response_time = proxy_doc.get('response_time_avg', 0.0)
            total_requests = proxy_doc.get('total_requests_count', 0)
            
            # Simple weighted average for success rate
            if total_requests > 0:
                weight = min(0.1, 1.0 / total_requests)  # 10% max weight for new result
                new_rate = current_rate * (1 - weight) + (100.0 if success else 0.0) * weight
                update_data["success_rate"] = round(new_rate, 2)
            
            # Update average response time
            if response_time > 0:
                if total_requests > 0:
                    new_response_time = (current_response_time * total_requests + response_time) / (total_requests + 1)
                    update_data["response_time_avg"] = round(new_response_time, 3)
                else:
                    update_data["response_time_avg"] = response_time
        
        await db.proxy_pool.update_one(
            {"id": proxy_id},
            {"$set": update_data}
        )
        
        logger.info(f"Updated proxy {proxy_id} usage. Success: {success}, Response time: {response_time}s")
        
    except Exception as e:
        logger.error(f"Error updating proxy usage for {proxy_id}: {e}")

async def check_proxy_health(proxy: ProxyConfig) -> bool:
    """Check if a proxy is healthy by making a test request"""
    try:
        proxy_url = f"{proxy.protocol}://"
        if proxy.username and proxy.password:
            proxy_url += f"{proxy.username}:{proxy.password}@"
        proxy_url += f"{proxy.ip}:{proxy.port}"
        
        # Test the proxy with a simple HTTP request
        start_time = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://httpbin.org/ip",
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=PROXY_HEALTH_CHECK_TIMEOUT)
            ) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                if response.status == 200:
                    # Update proxy health status
                    await db.proxy_pool.update_one(
                        {"id": proxy.id},
                        {
                            "$set": {
                                "health_status": "healthy",
                                "last_health_check": datetime.now(timezone.utc),
                                "response_time_avg": response_time,
                                "last_error": None,
                                "updated_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                    logger.info(f"Proxy {proxy.id} health check passed. Response time: {response_time}s")
                    return True
                else:
                    raise Exception(f"HTTP {response.status}")
    
    except Exception as e:
        error_message = f"Health check failed: {str(e)}"
        # Mark proxy as unhealthy
        await db.proxy_pool.update_one(
            {"id": proxy.id},
            {
                "$set": {
                    "health_status": "unhealthy",
                    "last_health_check": datetime.now(timezone.utc),
                    "last_error": error_message,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        logger.warning(f"Proxy {proxy.id} health check failed: {error_message}")
        return False

async def mark_proxy_banned(proxy_id: str, reason: str = "Detected as banned"):
    """Mark a proxy as banned"""
    try:
        await db.proxy_pool.update_one(
            {"id": proxy_id},
            {
                "$set": {
                    "status": "banned",
                    "health_status": "unhealthy",
                    "last_error": reason,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        await send_discord_notification(f"🚫 **Proxy Banned** \n🔗 Proxy: {proxy_id}\n💬 Reason: {reason}")
        logger.warning(f"Marked proxy {proxy_id} as banned: {reason}")
        
    except Exception as e:
        logger.error(f"Error marking proxy as banned {proxy_id}: {e}")

async def reset_proxy_daily_limits():
    """Reset daily request counts for all proxies (should be called daily)"""
    try:
        await db.proxy_pool.update_many(
            {},
            {
                "$set": {
                    "daily_requests_count": 0,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        logger.info("Daily limits reset for all proxies")
    except Exception as e:
        logger.error(f"Error resetting proxy daily limits: {e}")

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
        # Handle different channel ID formats
        if channel_id.startswith('@'):
            urls_to_try = [
                f"https://www.youtube.com/{channel_id}/about",  # @username format
            ]
        elif channel_id.startswith('UC') and len(channel_id) == 24:
            urls_to_try = [
                f"https://www.youtube.com/channel/{channel_id}/about",  # UCxxxxx format
            ]
        else:
            urls_to_try = [
                f"https://www.youtube.com/@{channel_id}/about",  # assume username without @
                f"https://www.youtube.com/channel/{channel_id}/about"  # fallback
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

# Queue Management Functions
async def add_to_queue(channel_id: str, request_type: str = "channel_scraping", priority: int = 5, payload: Optional[Dict[str, Any]] = None) -> str:
    """Add a request to the scraping queue"""
    try:
        # Check if request already exists in queue
        existing = await db.scraping_queue.find_one({
            "channel_id": channel_id,
            "status": {"$in": ["pending", "processing", "retry_scheduled"]}
        })
        
        if existing:
            logger.info(f"Request for channel {channel_id} already exists in queue with status {existing['status']}")
            return existing["id"]
        
        queue_request = QueueRequest(
            channel_id=channel_id,
            request_type=request_type,
            priority=priority,
            payload=payload or {}
        )
        
        await db.scraping_queue.insert_one(queue_request.dict())
        
        # Send Discord notification
        await send_discord_notification(f"📝 **New Queue Request**\n🆔 Channel: {channel_id}\n📊 Type: {request_type}\n⭐ Priority: {priority}")
        
        logger.info(f"Added request {queue_request.id} to queue for channel {channel_id}")
        return queue_request.id
        
    except Exception as e:
        logger.error(f"Error adding request to queue: {e}")
        raise

async def get_next_queue_request(account_id: Optional[str] = None) -> Optional[QueueRequest]:
    """Get the next available request from the queue with rate limiting"""
    try:
        now = datetime.now(timezone.utc)
        
        # If specific account provided, check its rate limits
        if account_id:
            account = await db.youtube_accounts.find_one({"id": account_id})
            if not account:
                return None
                
            # Check rate limits for this account
            if await is_account_rate_limited(account_id):
                logger.info(f"Account {account_id} is rate limited, skipping queue processing")
                return None
        
        # Find pending requests, prioritizing by priority then by scheduled time
        query = {
            "status": "pending",
            "scheduled_time": {"$lte": now},
            "attempts": {"$lt": QUEUE_RETRY_ATTEMPTS}
        }
        
        # Get highest priority request first
        requests_cursor = db.scraping_queue.find(query).sort([
            ("priority", 1),  # Lower number = higher priority
            ("scheduled_time", 1)  # Earlier first
        ]).limit(1)
        
        requests = await requests_cursor.to_list(1)
        
        if requests:
            request_data = requests[0]
            request = QueueRequest(**request_data)
            
            # Mark as processing
            await db.scraping_queue.update_one(
                {"id": request.id},
                {
                    "$set": {
                        "status": "processing",
                        "processing_started_at": now,
                        "account_id": account_id,
                        "updated_at": now
                    }
                }
            )
            
            logger.info(f"Assigned queue request {request.id} for processing by account {account_id}")
            return request
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting next queue request: {e}")
        return None

async def is_account_rate_limited(account_id: str) -> bool:
    """Check if account has exceeded hourly rate limits"""
    try:
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        
        # Count requests in the last hour for this account
        requests_in_last_hour = await db.scraping_queue.count_documents({
            "account_id": account_id,
            "processing_started_at": {"$gte": one_hour_ago},
            "status": {"$in": ["processing", "completed"]}
        })
        
        return requests_in_last_hour >= MAX_REQUESTS_PER_HOUR_PER_ACCOUNT
        
    except Exception as e:
        logger.error(f"Error checking rate limits for account {account_id}: {e}")
        return True  # Err on the side of caution

async def complete_queue_request(request_id: str, success: bool = True, error_message: Optional[str] = None):
    """Mark a queue request as completed or failed"""
    try:
        now = datetime.now(timezone.utc)
        
        if success:
            status = "completed"
            update_data = {
                "$set": {
                    "status": status,
                    "completed_at": now,
                    "updated_at": now
                }
            }
        else:
            # Increment attempts
            request_data = await db.scraping_queue.find_one({"id": request_id})
            if not request_data:
                logger.error(f"Queue request {request_id} not found")
                return
            
            attempts = request_data.get("attempts", 0) + 1
            
            if attempts >= QUEUE_RETRY_ATTEMPTS:
                status = "failed"
                update_data = {
                    "$set": {
                        "status": status,
                        "attempts": attempts,
                        "error_message": error_message,
                        "completed_at": now,
                        "updated_at": now
                    }
                }
            else:
                # Schedule retry
                status = "retry_scheduled"
                retry_time = now + timedelta(minutes=QUEUE_RETRY_DELAY_MINUTES)
                update_data = {
                    "$set": {
                        "status": status,
                        "attempts": attempts,
                        "error_message": error_message,
                        "scheduled_time": retry_time,
                        "processing_started_at": None,
                        "account_id": None,
                        "updated_at": now
                    }
                }
        
        await db.scraping_queue.update_one({"id": request_id}, update_data)
        
        # Send Discord notification
        if success:
            await send_discord_notification(f"✅ **Queue Request Completed**\n🆔 Request ID: {request_id}")
        else:
            await send_discord_notification(f"❌ **Queue Request Failed**\n🆔 Request ID: {request_id}\n📝 Error: {error_message[:100] if error_message else 'Unknown error'}")
        
        logger.info(f"Queue request {request_id} marked as {status}")
        
    except Exception as e:
        logger.error(f"Error completing queue request {request_id}: {e}")

async def get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics"""
    try:
        stats = {}
        
        # Count requests by status
        for status in ["pending", "processing", "completed", "failed", "retry_scheduled"]:
            count = await db.scraping_queue.count_documents({"status": status})
            stats[f"{status}_requests"] = count
        
        # Total requests
        total_requests = await db.scraping_queue.count_documents({})
        stats["total_requests"] = total_requests
        
        # Rate limiting stats
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        
        requests_last_hour = await db.scraping_queue.count_documents({
            "processing_started_at": {"$gte": one_hour_ago}
        })
        stats["requests_last_hour"] = requests_last_hour
        
        # Processing capacity
        concurrent_processing = await db.scraping_queue.count_documents({"status": "processing"})
        stats["concurrent_processing"] = concurrent_processing
        stats["max_concurrent_processing"] = MAX_CONCURRENT_PROCESSING
        stats["max_requests_per_hour_per_account"] = MAX_REQUESTS_PER_HOUR_PER_ACCOUNT
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return {}

async def cleanup_old_queue_requests():
    """Clean up completed requests older than 7 days"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        result = await db.scraping_queue.delete_many({
            "status": {"$in": ["completed", "failed"]},
            "completed_at": {"$lt": cutoff_date}
        })
        
        if result.deleted_count > 0:
            logger.info(f"Cleaned up {result.deleted_count} old queue requests")
            await send_discord_notification(f"🧹 **Queue Cleanup**\n🗑️ Removed {result.deleted_count} old requests")
        
    except Exception as e:
        logger.error(f"Error cleaning up old queue requests: {e}")

async def process_queue_batch():
    """Process multiple queue requests in batch (basic processor structure)"""
    try:
        logger.info("Starting batch queue processing...")
        
        # Get available accounts
        available_accounts = []
        accounts_cursor = db.youtube_accounts.find({"status": "active"})
        async for account in accounts_cursor:
            if not await is_account_rate_limited(account["id"]):
                available_accounts.append(account["id"])
        
        if not available_accounts:
            logger.info("No available accounts for queue processing")
            return
        
        # Process requests up to concurrent limit
        concurrent_processing = await db.scraping_queue.count_documents({"status": "processing"})
        available_slots = MAX_CONCURRENT_PROCESSING - concurrent_processing
        
        if available_slots <= 0:
            logger.info("Maximum concurrent processing limit reached")
            return
        
        processed_count = 0
        for account_id in available_accounts[:available_slots]:
            request = await get_next_queue_request(account_id)
            if request:
                logger.info(f"Processing queue request {request.id} with account {account_id}")
                # TODO: Implement actual processing logic here
                # This is a placeholder for the actual scraping/extraction logic
                processed_count += 1
        
        if processed_count > 0:
            logger.info(f"Started processing {processed_count} queue requests")
            await send_discord_notification(f"🔄 **Queue Processing Started**\n📊 Processing {processed_count} requests")
        
    except Exception as e:
        logger.error(f"Error in batch queue processing: {e}")

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
    
    test_mode_str = " 🧪 (Test Mode)" if request.test_mode else ""
    email_status_str = "✅ Enabled" if SEND_EMAILS_ENABLED else "❌ Disabled (Extract only)"
    
    await send_discord_notification(f"🚀 **Lead Generation Started!{test_mode_str}**\n📋 Keywords: {', '.join(request.keywords)}\n👥 Subscriber Range: {request.subscriber_min:,} - {request.subscriber_max:,}\n🎯 Max Channels: {request.max_channels}\n✉️ Email Sending: {email_status_str}")
    
    return status

async def process_lead_generation(status_id: str, request: LeadGenerationRequest):
    """Background task to process lead generation"""
    try:
        # Apply test mode limits if enabled
        if request.test_mode:
            request.max_videos_per_keyword = min(request.max_videos_per_keyword, 100)
            request.max_channels = min(request.max_channels, 10)
            await send_discord_notification(f"🧪 **Test Mode Enabled!** Limits reduced for faster testing")
        
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
                # Check for deduplication - skip if channel already exists in database
                existing_main_lead = await db.main_leads.find_one({"channel_id": channel_id})
                existing_no_email_lead = await db.no_email_leads.find_one({"channel_id": channel_id})
                
                if existing_main_lead or existing_no_email_lead:
                    logger.info(f"Channel {channel_id} already processed, skipping for deduplication")
                    continue
                
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
                    
                    # Check global email sending setting
                    if SEND_EMAILS_ENABLED and channel.email_subject and channel.email_body_preview:
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
                    elif not SEND_EMAILS_ENABLED and channel.email_subject and channel.email_body_preview:
                        # Email sending disabled, but still store as prepared
                        channel.email_sent_status = "prepared_not_sent"
                        await send_discord_notification(f"📋 **Email Prepared!** (Sending disabled) Client outreach prepared for **{channel.channel_title}**")
                    
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
        
        # Check global email sending setting
        if SEND_EMAILS_ENABLED and channel.email_subject and channel.email_body_preview:
            email_sent = await send_email(
                email,
                channel.email_subject,
                channel.email_body_preview,
                channel.email_body_preview
            )
            
            if email_sent:
                channel.email_sent_status = "sent"
                await send_discord_notification(f"✉️ **Manual Email Sent!** Client outreach sent to **{channel.channel_title}** (manual email)")
            else:
                channel.email_sent_status = "failed"
        elif not SEND_EMAILS_ENABLED and channel.email_subject and channel.email_body_preview:
            # Email sending disabled, but still store as prepared
            channel.email_sent_status = "prepared_not_sent"
            await send_discord_notification(f"📋 **Manual Email Prepared!** (Sending disabled) Client outreach prepared for **{channel.channel_title}**")
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

@api_router.get("/settings/email-sending")
async def get_email_sending_status():
    """Get current email sending status"""
    return {
        "email_sending_enabled": SEND_EMAILS_ENABLED,
        "status": "enabled" if SEND_EMAILS_ENABLED else "disabled"
    }

@api_router.post("/settings/email-sending")
async def toggle_email_sending(enabled: bool):
    """Toggle email sending on/off"""
    global SEND_EMAILS_ENABLED
    SEND_EMAILS_ENABLED = enabled
    os.environ['SEND_EMAILS_ENABLED'] = str(enabled).lower()
    
    return {
        "email_sending_enabled": SEND_EMAILS_ENABLED,
        "status": "enabled" if SEND_EMAILS_ENABLED else "disabled",
        "message": f"Email sending {'enabled' if enabled else 'disabled'} successfully"
    }

# YouTube Account Management API Routes
@api_router.post("/accounts/add", response_model=YouTubeAccount)
async def add_youtube_account(request: AccountAddRequest):
    """Add a new YouTube account for scraping"""
    try:
        # Check if account already exists
        existing = await db.youtube_accounts.find_one({"email": request.email})
        if existing:
            raise HTTPException(status_code=400, detail="Account with this email already exists")
        
        account = YouTubeAccount(
            email=request.email,
            password=request.password,
            ip_address=request.ip_address,
            user_agent=request.user_agent
        )
        
        await db.youtube_accounts.insert_one(account.dict())
        
        await send_discord_notification(f"✅ **New YouTube Account Added** \n📧 Email: {account.email}\n🆔 ID: {account.id}")
        
        logger.info(f"Added new YouTube account: {account.email}")
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding YouTube account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/accounts", response_model=List[YouTubeAccount])
async def get_youtube_accounts():
    """Get all YouTube accounts"""
    try:
        accounts = await db.youtube_accounts.find().to_list(1000)
        return [YouTubeAccount(**account) for account in accounts]
    except Exception as e:
        logger.error(f"Error getting YouTube accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/accounts/available")
async def get_next_available_account():
    """Get the next available account for testing"""
    try:
        account = await get_available_account()
        if account:
            return {
                "account_found": True,
                "account_id": account.id,
                "account_email": account.email,
                "status": account.status,
                "daily_requests": account.daily_requests_count,
                "success_rate": account.success_rate
            }
        else:
            return {
                "account_found": False,
                "message": "No available accounts found"
            }
    except Exception as e:
        logger.error(f"Error getting available account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/accounts/stats/overview")
async def get_accounts_overview():
    """Get overview statistics of all accounts"""
    try:
        total_accounts = await db.youtube_accounts.count_documents({})
        active_accounts = await db.youtube_accounts.count_documents({"status": "active"})
        banned_accounts = await db.youtube_accounts.count_documents({"status": "banned"})
        rate_limited = await db.youtube_accounts.count_documents({"status": "rate_limited"})
        
        # Get accounts with high usage today
        today = datetime.now(timezone.utc).date()
        high_usage = await db.youtube_accounts.count_documents({
            "daily_requests_count": {"$gte": MAX_DAILY_REQUESTS_PER_ACCOUNT * 0.8}
        })
        
        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "banned_accounts": banned_accounts,
            "rate_limited_accounts": rate_limited,
            "high_usage_accounts": high_usage,
            "max_daily_requests_per_account": MAX_DAILY_REQUESTS_PER_ACCOUNT,
            "max_concurrent_accounts": MAX_ACCOUNTS_CONCURRENT
        }
    except Exception as e:
        logger.error(f"Error getting accounts overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/accounts/{account_id}", response_model=YouTubeAccount)
async def get_youtube_account(account_id: str):
    """Get a specific YouTube account"""
    try:
        account = await db.youtube_accounts.find_one({"id": account_id})
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return YouTubeAccount(**account)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting YouTube account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/accounts/{account_id}/status")
async def update_account_status(account_id: str, request: AccountStatusUpdate):
    """Update account status (active, banned, rate_limited, maintenance)"""
    try:
        valid_statuses = ["active", "banned", "rate_limited", "maintenance"]
        if request.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        result = await db.youtube_accounts.update_one(
            {"id": account_id},
            {
                "$set": {
                    "status": request.status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Account not found")
        
        await send_discord_notification(f"🔄 **Account Status Updated** \n🆔 ID: {account_id}\n📊 Status: {request.status}")
        
        return {"message": f"Account status updated to {request.status}", "account_id": account_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account status {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/accounts/{account_id}")
async def delete_youtube_account(account_id: str):
    """Delete a YouTube account"""
    try:
        result = await db.youtube_accounts.delete_one({"id": account_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Account not found")
        
        await send_discord_notification(f"🗑️ **Account Deleted** \n🆔 ID: {account_id}")
        
        return {"message": "Account deleted successfully", "account_id": account_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Proxy Management API Routes
@api_router.post("/proxies/add", response_model=ProxyConfig)
async def add_proxy(request: ProxyAddRequest):
    """Add a new proxy to the proxy pool"""
    try:
        # Validate input data
        if not validate_ip_address(request.ip):
            raise HTTPException(status_code=400, detail=f"Invalid IP address: {request.ip}")
        
        if not validate_port(request.port):
            raise HTTPException(status_code=400, detail=f"Invalid port number: {request.port}. Must be between 1 and 65535")
        
        if not validate_protocol(request.protocol):
            raise HTTPException(status_code=400, detail=f"Invalid protocol: {request.protocol}. Must be one of: http, https, socks4, socks5")
        
        # Create new proxy configuration
        proxy = ProxyConfig(
            ip=request.ip,
            port=request.port,
            username=request.username,
            password=request.password,
            protocol=request.protocol.lower(),
            location=request.location,
            provider=request.provider
        )
        
        # Check if proxy already exists
        existing = await db.proxy_pool.find_one({
            "ip": request.ip,
            "port": request.port
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Proxy with this IP and port already exists")
        
        # Insert proxy into database
        await db.proxy_pool.insert_one(proxy.dict())
        
        await send_discord_notification(f"🔗 **New Proxy Added** \n🌐 IP: {proxy.ip}:{proxy.port}\n📍 Location: {proxy.location or 'Unknown'}")
        
        return proxy
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/proxies", response_model=List[ProxyConfig])
async def get_proxies():
    """Get all proxies in the pool"""
    try:
        proxies = await db.proxy_pool.find().to_list(1000)
        return [ProxyConfig(**proxy) for proxy in proxies]
    except Exception as e:
        logger.error(f"Error getting proxies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/proxies/available")
async def get_next_available_proxy():
    """Get the next available proxy for testing"""
    try:
        proxy = await get_available_proxy()
        
        if not proxy:
            return {
                "message": "No available proxies found",
                "available": False,
                "proxy": None
            }
        
        return {
            "message": "Available proxy found",
            "available": True,
            "proxy": proxy.dict(),
            "ready_for_use": True
        }
        
    except Exception as e:
        logger.error(f"Error getting available proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/proxies/stats/overview")
async def get_proxies_overview():
    """Get overview statistics of all proxies"""
    try:
        total = await db.proxy_pool.count_documents({})
        active = await db.proxy_pool.count_documents({"status": "active"})
        disabled = await db.proxy_pool.count_documents({"status": "disabled"})
        healthy = await db.proxy_pool.count_documents({"health_status": "healthy"})
        unhealthy = await db.proxy_pool.count_documents({"health_status": "unhealthy"})
        banned = await db.proxy_pool.count_documents({"status": "banned"})
        
        # Get average success rate
        pipeline = [
            {"$group": {
                "_id": None,
                "avg_success_rate": {"$avg": "$success_rate"},
                "avg_response_time": {"$avg": "$response_time_avg"}
            }}
        ]
        
        averages = await db.proxy_pool.aggregate(pipeline).to_list(1)
        avg_success = averages[0]["avg_success_rate"] if averages else 0
        avg_response = averages[0]["avg_response_time"] if averages else 0
        
        return {
            "total_proxies": total,
            "active_proxies": active,
            "disabled_proxies": disabled,
            "healthy_proxies": healthy,
            "unhealthy_proxies": unhealthy,
            "banned_proxies": banned,
            "average_success_rate": round(avg_success, 2),
            "average_response_time": round(avg_response, 3),
            "max_daily_requests_per_proxy": MAX_DAILY_REQUESTS_PER_PROXY,
            "max_concurrent_proxies": MAX_PROXIES_CONCURRENT,
            "pool_health": "good" if (healthy / max(active, 1)) > 0.7 else "needs_attention"
        }
        
    except Exception as e:
        logger.error(f"Error getting proxies overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/proxies/{proxy_id}", response_model=ProxyConfig)
async def get_proxy(proxy_id: str):
    """Get a specific proxy"""
    try:
        proxy = await db.proxy_pool.find_one({"id": proxy_id})
        
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")
        
        return ProxyConfig(**proxy)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting proxy {proxy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/proxies/{proxy_id}/status")
async def update_proxy_status(proxy_id: str, request: ProxyStatusUpdate):
    """Update proxy status (active, disabled, banned, maintenance)"""
    try:
        # Validate status
        valid_statuses = ["active", "disabled", "banned", "maintenance"]
        if request.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        # Update proxy status
        result = await db.proxy_pool.update_one(
            {"id": proxy_id},
            {
                "$set": {
                    "status": request.status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Proxy not found")
        
        # Get updated proxy for notification
        updated_proxy = await db.proxy_pool.find_one({"id": proxy_id})
        
        await send_discord_notification(f"🔄 **Proxy Status Updated** \n🌐 IP: {updated_proxy['ip']}:{updated_proxy['port']}\n📊 Status: {request.status}")
        
        return {"message": "Proxy status updated successfully", "proxy_id": proxy_id, "new_status": request.status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating proxy status {proxy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/proxies/health-check")
async def run_proxy_health_check(request: ProxyHealthCheckRequest = ProxyHealthCheckRequest()):
    """Run health check on proxies"""
    try:
        checked_proxies = []
        failed_proxies = []
        
        if request.proxy_id:
            # Check specific proxy
            proxy_doc = await db.proxy_pool.find_one({"id": request.proxy_id})
            if not proxy_doc:
                raise HTTPException(status_code=404, detail="Proxy not found")
            
            proxy = ProxyConfig(**proxy_doc)
            is_healthy = await check_proxy_health(proxy)
            
            checked_proxies.append({
                "proxy_id": proxy.id,
                "ip": f"{proxy.ip}:{proxy.port}",
                "healthy": is_healthy
            })
            
            if not is_healthy:
                failed_proxies.append(proxy.id)
        else:
            # Check all active proxies
            active_proxies = await db.proxy_pool.find({"status": "active"}).to_list(100)
            
            for proxy_doc in active_proxies:
                proxy = ProxyConfig(**proxy_doc)
                is_healthy = await check_proxy_health(proxy)
                
                checked_proxies.append({
                    "proxy_id": proxy.id,
                    "ip": f"{proxy.ip}:{proxy.port}",
                    "healthy": is_healthy
                })
                
                if not is_healthy:
                    failed_proxies.append(proxy.id)
        
        health_summary = {
            "message": f"Health check completed. Checked {len(checked_proxies)} proxies.",
            "total_checked": len(checked_proxies),
            "healthy_count": len([p for p in checked_proxies if p["healthy"]]),
            "unhealthy_count": len(failed_proxies),
            "checked": checked_proxies,
            "failed_proxy_ids": failed_proxies
        }
        
        if failed_proxies:
            await send_discord_notification(f"⚠️ **Proxy Health Check** \n❌ Failed: {len(failed_proxies)}/{len(checked_proxies)} proxies\n🔧 Action needed for unhealthy proxies")
        
        return health_summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running proxy health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/proxies/{proxy_id}")
async def delete_proxy(proxy_id: str):
    """Delete a proxy from the pool"""
    try:
        result = await db.proxy_pool.delete_one({"id": proxy_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Proxy not found")
        
        await send_discord_notification(f"🗑️ **Proxy Deleted** \n🆔 ID: {proxy_id}")
        
        return {"message": "Proxy deleted successfully", "proxy_id": proxy_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting proxy {proxy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Queue Management API Routes
@api_router.post("/queue/add", response_model=dict)
async def add_request_to_queue(request: AddToQueueRequest):
    """Add a new request to the scraping queue"""
    try:
        request_id = await add_to_queue(
            channel_id=request.channel_id,
            request_type=request.request_type,
            priority=request.priority,
            payload=request.payload
        )
        
        return {
            "message": "Request added to queue successfully",
            "request_id": request_id,
            "channel_id": request.channel_id,
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Error adding request to queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/queue/batch", response_model=dict)
async def add_batch_to_queue(request: QueueBatchRequest):
    """Add multiple requests to the scraping queue"""
    try:
        request_ids = []
        
        for channel_id in request.channel_ids:
            request_id = await add_to_queue(
                channel_id=channel_id,
                request_type=request.request_type,
                priority=request.priority,
                payload=request.payload
            )
            request_ids.append({"channel_id": channel_id, "request_id": request_id})
        
        return {
            "message": f"Added {len(request_ids)} requests to queue successfully",
            "requests": request_ids,
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Error adding batch to queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/queue/next")
async def get_next_request():
    """Get the next available request from queue for processing"""
    try:
        # Get available account
        account = await get_available_account()
        if not account:
            return {
                "message": "No available accounts for processing",
                "request": None,
                "account": None
            }
        
        # Get next request
        request = await get_next_queue_request(account.id)
        if not request:
            return {
                "message": "No pending requests in queue",
                "request": None,
                "account": account.dict()
            }
        
        return {
            "message": "Request assigned for processing",
            "request": request.dict(),
            "account": account.dict()
        }
        
    except Exception as e:
        logger.error(f"Error getting next request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/queue/stats")
async def get_queue_statistics():
    """Get queue statistics and overview"""
    try:
        stats = await get_queue_stats()
        return {
            "message": "Queue statistics retrieved successfully",
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting queue statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/queue", response_model=List[QueueRequest])
async def get_queue_requests(
    status: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    """Get queue requests with optional filtering"""
    try:
        query = {}
        if status:
            query["status"] = status
        
        requests_cursor = db.scraping_queue.find(query).sort("created_at", -1).skip(skip).limit(limit)
        requests = await requests_cursor.to_list(limit)
        
        return [QueueRequest(**req) for req in requests]
        
    except Exception as e:
        logger.error(f"Error getting queue requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/queue/{request_id}", response_model=QueueRequest)
async def get_queue_request(request_id: str):
    """Get a specific queue request by ID"""
    try:
        request_data = await db.scraping_queue.find_one({"id": request_id})
        if not request_data:
            raise HTTPException(status_code=404, detail="Queue request not found")
        
        return QueueRequest(**request_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting queue request {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/queue/{request_id}/status")
async def update_queue_request_status(request_id: str, request: QueueStatusUpdate):
    """Update queue request status (for manual management)"""
    try:
        if request.status == "completed":
            await complete_queue_request(request_id, success=True)
        elif request.status == "failed":
            await complete_queue_request(request_id, success=False, error_message=request.error_message)
        else:
            # Direct status update
            await db.scraping_queue.update_one(
                {"id": request_id},
                {
                    "$set": {
                        "status": request.status,
                        "error_message": request.error_message,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        
        updated_request = await db.scraping_queue.find_one({"id": request_id})
        if not updated_request:
            raise HTTPException(status_code=404, detail="Queue request not found")
        
        return {
            "message": "Queue request status updated successfully",
            "request": QueueRequest(**updated_request).dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating queue request status {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/queue/process")
async def process_queue_manually():
    """Manually trigger queue processing"""
    try:
        await process_queue_batch()
        
        return {
            "message": "Queue processing triggered successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing queue manually: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/queue/{request_id}")
async def delete_queue_request(request_id: str):
    """Delete a specific queue request"""
    try:
        result = await db.scraping_queue.delete_one({"id": request_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Queue request not found")
        
        await send_discord_notification(f"🗑️ **Queue Request Deleted** \n🆔 Request ID: {request_id}")
        
        return {
            "message": "Queue request deleted successfully",
            "request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting queue request {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/queue/cleanup")
async def cleanup_queue():
    """Clean up old completed/failed requests"""
    try:
        await cleanup_old_queue_requests()
        
        return {
            "message": "Queue cleanup completed successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
