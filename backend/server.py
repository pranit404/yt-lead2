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
import random
import secrets

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

# YouTube Login Configuration
LOGIN_TIMEOUT = 30000  # 30 seconds
SESSION_EXPIRY_HOURS = 24  # Sessions expire after 24 hours
MAX_LOGIN_ATTEMPTS = 3
STEALTH_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

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

# =============================================================================
# STEP 5: ACCOUNT HEALTH MONITORING SYSTEM
# =============================================================================

# Account Health Status Constants
ACCOUNT_STATUS_ACTIVE = "active"
ACCOUNT_STATUS_BANNED = "banned"
ACCOUNT_STATUS_RATE_LIMITED = "rate_limited"
ACCOUNT_STATUS_NEEDS_VERIFICATION = "needs_verification"
ACCOUNT_STATUS_MAINTENANCE = "maintenance"
ACCOUNT_STATUS_COOLDOWN = "cooldown"

# Health Check Thresholds
HEALTH_CHECK_INTERVAL_MINUTES = 30
SUCCESS_RATE_THRESHOLD = 70.0  # Below this is considered unhealthy
MAX_CONSECUTIVE_FAILURES = 3
VERIFICATION_NEEDED_KEYWORDS = ["verify", "suspicious", "unusual activity", "phone number", "security"]

async def check_account_health(account_id: str) -> dict:
    """
    Perform comprehensive health check on a YouTube account
    Returns health status with detailed metrics
    """
    try:
        account_doc = await db.youtube_accounts.find_one({"id": account_id})
        if not account_doc:
            return {"healthy": False, "reason": "Account not found"}
        
        account = YouTubeAccount(**account_doc)
        now = datetime.now(timezone.utc)
        
        health_report = {
            "account_id": account_id,
            "email": account.email,
            "healthy": True,
            "status": account.status,
            "issues": [],
            "recommendations": [],
            "metrics": {},
            "last_check": now
        }
        
        # Check 1: Account Status
        if account.status in [ACCOUNT_STATUS_BANNED, ACCOUNT_STATUS_NEEDS_VERIFICATION]:
            health_report["healthy"] = False
            health_report["issues"].append(f"Account status is {account.status}")
        
        # Check 2: Success Rate
        if account.success_rate < SUCCESS_RATE_THRESHOLD:
            health_report["healthy"] = False
            health_report["issues"].append(f"Low success rate: {account.success_rate}%")
            health_report["recommendations"].append("Consider rotating this account less frequently")
        
        # Check 3: Rate Limiting Status
        if account.rate_limit_reset and account.rate_limit_reset > now:
            health_report["issues"].append("Account is currently rate limited")
            health_report["recommendations"].append(f"Wait until {account.rate_limit_reset} before using")
        
        # Check 4: Daily Request Limits
        daily_usage_percentage = (account.daily_requests_count / MAX_DAILY_REQUESTS_PER_ACCOUNT) * 100
        if daily_usage_percentage > 80:
            health_report["issues"].append(f"High daily usage: {daily_usage_percentage:.1f}%")
            health_report["recommendations"].append("Consider account rotation")
        
        # Check 5: Session Validity
        session_valid = False
        if account.session_data and account.cookies:
            session_valid = await validate_session(account)
            if not session_valid:
                health_report["issues"].append("Invalid or expired session")
                health_report["recommendations"].append("Re-authenticate account")
        
        # Check 6: Last Error Analysis
        if account.last_error:
            error_lower = account.last_error.lower()
            if any(keyword in error_lower for keyword in VERIFICATION_NEEDED_KEYWORDS):
                health_report["healthy"] = False
                health_report["issues"].append("Account may need verification")
                await db.youtube_accounts.update_one(
                    {"id": account_id},
                    {"$set": {"status": ACCOUNT_STATUS_NEEDS_VERIFICATION}}
                )
        
        # Populate metrics
        health_report["metrics"] = {
            "success_rate": account.success_rate,
            "daily_requests": account.daily_requests_count,
            "daily_limit": MAX_DAILY_REQUESTS_PER_ACCOUNT,
            "total_requests": account.total_requests_count,
            "session_valid": session_valid,
            "last_used": account.last_used.isoformat() if account.last_used else None,
            "account_age_days": (now - account.created_at).days if account.created_at else None
        }
        
        # Update health check timestamp
        await db.youtube_accounts.update_one(
            {"id": account_id},
            {
                "$set": {
                    "last_health_check": now,
                    "health_report": health_report
                }
            }
        )
        
        return health_report
        
    except Exception as e:
        logger.error(f"Error checking account health for {account_id}: {e}")
        return {"healthy": False, "reason": f"Health check failed: {str(e)}"}

async def monitor_all_accounts() -> dict:
    """
    Monitor health of all accounts and return summary
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Get all accounts
        accounts_cursor = db.youtube_accounts.find({})
        accounts = await accounts_cursor.to_list(None)
        
        monitoring_summary = {
            "total_accounts": len(accounts),
            "healthy_accounts": 0,
            "unhealthy_accounts": 0,
            "banned_accounts": 0,
            "rate_limited_accounts": 0,
            "needs_verification": 0,
            "accounts_needing_attention": [],
            "overall_health_score": 0.0,
            "recommendations": [],
            "timestamp": now
        }
        
        healthy_count = 0
        
        for account_doc in accounts:
            account = YouTubeAccount(**account_doc)
            
            # Perform health check
            health_report = await check_account_health(account.id)
            
            if health_report["healthy"]:
                healthy_count += 1
                monitoring_summary["healthy_accounts"] += 1
            else:
                monitoring_summary["unhealthy_accounts"] += 1
                monitoring_summary["accounts_needing_attention"].append({
                    "account_id": account.id,
                    "email": account.email,
                    "issues": health_report["issues"],
                    "recommendations": health_report["recommendations"]
                })
            
            # Count status types
            if account.status == ACCOUNT_STATUS_BANNED:
                monitoring_summary["banned_accounts"] += 1
            elif account.status == ACCOUNT_STATUS_RATE_LIMITED:
                monitoring_summary["rate_limited_accounts"] += 1
            elif account.status == ACCOUNT_STATUS_NEEDS_VERIFICATION:
                monitoring_summary["needs_verification"] += 1
        
        # Calculate overall health score
        if len(accounts) > 0:
            monitoring_summary["overall_health_score"] = (healthy_count / len(accounts)) * 100
        
        # Generate system-level recommendations
        if monitoring_summary["banned_accounts"] > len(accounts) * 0.2:  # More than 20% banned
            monitoring_summary["recommendations"].append("High ban rate detected - review automation patterns")
        
        if monitoring_summary["needs_verification"] > 0:
            monitoring_summary["recommendations"].append("Some accounts need manual verification")
        
        if monitoring_summary["overall_health_score"] < 60:
            monitoring_summary["recommendations"].append("System health below 60% - consider adding new accounts")
        
        # Send Discord notification if health is critical
        if monitoring_summary["overall_health_score"] < 30:
            await send_discord_notification(
                f"🚨 **CRITICAL ACCOUNT HEALTH ALERT**\n"
                f"📊 Overall Health: {monitoring_summary['overall_health_score']:.1f}%\n"
                f"🚫 Banned: {monitoring_summary['banned_accounts']}\n"
                f"⚠️ Unhealthy: {monitoring_summary['unhealthy_accounts']}\n"
                f"💡 Immediate attention required!"
            )
        
        return monitoring_summary
        
    except Exception as e:
        logger.error(f"Error monitoring all accounts: {e}")
        return {"error": str(e)}

async def auto_switch_account(current_account_id: str, reason: str = "automatic_rotation") -> Optional[YouTubeAccount]:
    """
    Automatically switch to a healthier account when current one is problematic
    """
    try:
        logger.info(f"Auto-switching from account {current_account_id}, reason: {reason}")
        
        # Mark current account for cooldown if it's problematic
        if reason in ["rate_limited", "banned", "verification_needed"]:
            cooldown_until = datetime.now(timezone.utc) + timedelta(
                minutes=ACCOUNT_COOLDOWN_MINUTES * 2
            )  # Double cooldown for problematic accounts
            
            await db.youtube_accounts.update_one(
                {"id": current_account_id},
                {
                    "$set": {
                        "status": ACCOUNT_STATUS_COOLDOWN,
                        "rate_limit_reset": cooldown_until,
                        "last_error": f"Auto-switched due to: {reason}",
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        
        # Find the healthiest available account
        next_account = await get_healthiest_available_account()
        
        if next_account:
            await send_discord_notification(
                f"🔄 **Account Auto-Switch**\n"
                f"📤 From: {current_account_id[:8]}...\n"
                f"📥 To: {next_account.email}\n"
                f"💬 Reason: {reason}"
            )
            
            return next_account
        else:
            await send_discord_notification(
                f"⚠️ **No Healthy Accounts Available**\n"
                f"📤 Tried to switch from: {current_account_id[:8]}...\n"
                f"💬 Reason: {reason}\n"
                f"🚨 Manual intervention required!"
            )
            
            return None
        
    except Exception as e:
        logger.error(f"Error auto-switching account: {e}")
        return None

async def get_healthiest_available_account() -> Optional[YouTubeAccount]:
    """
    Get the account with the best health metrics that's available for use
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Find accounts that are available (not in cooldown, not banned, etc.)
        accounts_cursor = db.youtube_accounts.find({
            "status": {"$in": [ACCOUNT_STATUS_ACTIVE]},
            "$or": [
                {"rate_limit_reset": {"$lt": now}},
                {"rate_limit_reset": None}
            ],
            "daily_requests_count": {"$lt": MAX_DAILY_REQUESTS_PER_ACCOUNT}
        }).sort([
            ("success_rate", -1),  # Highest success rate first
            ("daily_requests_count", 1),  # Lowest usage first
            ("last_used", 1)  # Least recently used first
        ])
        
        accounts = await accounts_cursor.to_list(None)
        
        # Score accounts based on health metrics
        best_account = None
        best_score = -1
        
        for account_doc in accounts:
            account = YouTubeAccount(**account_doc)
            
            # Calculate health score (0-100)
            score = 0
            
            # Success rate component (0-40 points)
            score += min(account.success_rate * 0.4, 40)
            
            # Usage component (0-30 points) - lower usage is better
            usage_ratio = account.daily_requests_count / MAX_DAILY_REQUESTS_PER_ACCOUNT
            score += max(30 - (usage_ratio * 30), 0)
            
            # Freshness component (0-20 points) - less recently used is better
            if account.last_used:
                hours_since_use = (now - account.last_used).total_seconds() / 3600
                score += min(hours_since_use * 2, 20)  # 2 points per hour, max 20
            else:
                score += 20  # Never used gets full points
            
            # Session validity component (0-10 points)
            if account.session_data and account.cookies:
                session_valid = await validate_session(account)
                if session_valid:
                    score += 10
            
            if score > best_score:
                best_score = score
                best_account = account
        
        if best_account:
            logger.info(f"Selected healthiest account: {best_account.email} (score: {best_score:.2f})")
        
        return best_account
        
    except Exception as e:
        logger.error(f"Error getting healthiest account: {e}")
        return None

async def apply_account_cooldown(account_id: str, cooldown_minutes: int = None):
    """
    Apply cooldown period to an account to prevent overuse
    """
    try:
        cooldown_minutes = cooldown_minutes or ACCOUNT_COOLDOWN_MINUTES
        cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=cooldown_minutes)
        
        await db.youtube_accounts.update_one(
            {"id": account_id},
            {
                "$set": {
                    "status": ACCOUNT_STATUS_COOLDOWN,
                    "rate_limit_reset": cooldown_until,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"Applied {cooldown_minutes}min cooldown to account {account_id}")
        
    except Exception as e:
        logger.error(f"Error applying cooldown to account {account_id}: {e}")

async def log_account_usage_pattern(account_id: str, action_type: str, success: bool, details: dict = None):
    """
    Log detailed account usage patterns for analysis
    """
    try:
        usage_log = {
            "account_id": account_id,
            "action_type": action_type,  # login, scraping, email_extraction, etc.
            "success": success,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc),
            "ip_address": details.get("ip_address") if details else None,
            "user_agent": details.get("user_agent") if details else None
        }
        
        # Store in usage_logs collection
        await db.account_usage_logs.insert_one(usage_log)
        
        # Update account statistics
        await update_account_usage(account_id, success, 
                                 details.get("error_message") if details else None)
        
    except Exception as e:
        logger.error(f"Error logging usage pattern for {account_id}: {e}")

# YouTube Login Automation Functions
async def validate_session(account: YouTubeAccount) -> bool:
    """Check if existing session is still valid"""
    try:
        if not account.session_data or not account.cookies:
            return False
            
        # Check if session has expired
        if account.last_used:
            session_age = datetime.now(timezone.utc) - account.last_used
            if session_age.total_seconds() > (SESSION_EXPIRY_HOURS * 3600):
                logger.info(f"Session expired for account {account.email}")
                return False
        
        # Test session validity with a simple YouTube request
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=account.user_agent or STEALTH_USER_AGENTS[0]
            )
            
            # Load cookies into context
            if account.cookies:
                try:
                    cookies_list = []
                    for cookie_data in account.cookies.values():
                        if isinstance(cookie_data, dict):
                            cookies_list.append(cookie_data)
                    
                    if cookies_list:
                        await context.add_cookies(cookies_list)
                except Exception as cookie_error:
                    logger.warning(f"Failed to load cookies for {account.email}: {cookie_error}")
                    await browser.close()
                    return False
            
            page = await context.new_page()
            
            try:
                # Try to access YouTube and check if we're logged in
                await page.goto("https://www.youtube.com", timeout=15000)
                await page.wait_for_timeout(3000)
                
                # Check for login indicators
                profile_button = await page.query_selector("button[aria-label*='Google Account']")
                avatar_button = await page.query_selector("img#avatar")
                
                await browser.close()
                
                if profile_button or avatar_button:
                    logger.info(f"Session valid for account {account.email}")
                    return True
                else:
                    logger.info(f"Session invalid for account {account.email} - not logged in")
                    return False
                    
            except Exception as e:
                logger.warning(f"Session validation failed for {account.email}: {e}")
                await browser.close()
                return False
                
    except Exception as e:
        logger.error(f"Error validating session for {account.email}: {e}")
        return False

async def save_session_data(account_id: str, cookies: list, session_data: dict, user_agent: str):
    """Save session data and cookies to MongoDB"""
    try:
        # Convert cookies list to dictionary for storage
        cookies_dict = {}
        for i, cookie in enumerate(cookies):
            cookies_dict[f"cookie_{i}"] = cookie
        
        await db.youtube_accounts.update_one(
            {"id": account_id},
            {
                "$set": {
                    "cookies": cookies_dict,
                    "session_data": session_data,
                    "user_agent": user_agent,
                    "last_used": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"Session data saved for account {account_id}")
        
    except Exception as e:
        logger.error(f"Error saving session data for {account_id}: {e}")

async def handle_captcha_with_2captcha(page, solver: TwoCaptcha) -> bool:
    """Handle CAPTCHA using 2captcha service"""
    try:
        logger.info("CAPTCHA detected, attempting to solve with 2captcha...")
        
        # Look for different CAPTCHA types
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "[data-sitekey]",
            "#captcha",
            ".captcha",
            "[aria-label*='captcha']"
        ]
        
        captcha_element = None
        for selector in captcha_selectors:
            captcha_element = await page.query_selector(selector)
            if captcha_element:
                break
        
        if not captcha_element:
            logger.warning("CAPTCHA detected but element not found")
            return False
        
        # Handle reCAPTCHA
        if "recaptcha" in (await captcha_element.get_attribute("src") or ""):
            try:
                # Get the site key
                site_key_element = await page.query_selector("[data-sitekey]")
                if not site_key_element:
                    logger.error("reCAPTCHA site key not found")
                    return False
                
                site_key = await site_key_element.get_attribute("data-sitekey")
                page_url = page.url
                
                logger.info(f"Solving reCAPTCHA with site key: {site_key}")
                
                # Solve CAPTCHA with 2captcha
                result = solver.recaptcha(sitekey=site_key, url=page_url)
                
                if result and result.get('code'):
                    # Inject the solution
                    await page.evaluate(f'''
                        document.getElementById('g-recaptcha-response').innerHTML = '{result["code"]}';
                        if (typeof ___grecaptcha_cfg !== 'undefined') {{
                            Object.entries(___grecaptcha_cfg.clients).forEach(([cid, client]) => {{
                                if (client && client.callback) {{
                                    client.callback('{result["code"]}');
                                }}
                            }});
                        }}
                    ''')
                    
                    # Submit the form or continue
                    submit_button = await page.query_selector("input[type='submit'], button[type='submit'], #submit")
                    if submit_button:
                        await submit_button.click()
                        await page.wait_for_timeout(3000)
                    
                    logger.info("reCAPTCHA solved successfully")
                    return True
                    
            except Exception as captcha_error:
                logger.error(f"Error solving reCAPTCHA: {captcha_error}")
                return False
        
        # Handle other CAPTCHA types
        logger.warning("Unsupported CAPTCHA type detected")
        return False
        
    except Exception as e:
        logger.error(f"Error handling CAPTCHA: {e}")
        return False

async def login_to_youtube(account: YouTubeAccount, use_proxy: bool = True) -> tuple[bool, str]:
    """
    Attempt to login to YouTube with given account
    Returns (success: bool, message: str)
    """
    try:
        logger.info(f"Attempting YouTube login for account: {account.email}")
        
        # Initialize 2captcha solver
        solver = TwoCaptcha(TWOCAPTCHA_API_KEY)
        
        # Get proxy if needed
        proxy = None
        if use_proxy:
            proxy = await get_available_proxy()
        
        # Select random user agent
        import random
        user_agent = random.choice(STEALTH_USER_AGENTS)
        
        async with async_playwright() as p:
            # Launch browser with stealth settings
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-first-run',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            # Create context with stealth settings
            context_options = {
                'user_agent': user_agent,
                'viewport': {'width': 1366, 'height': 768},
                'java_script_enabled': True,
                'accept_downloads': False,
            }
            
            # Add proxy if available
            if proxy and proxy.status == "active":
                proxy_url = f"{proxy.protocol}://"
                if proxy.username and proxy.password:
                    proxy_url += f"{proxy.username}:{proxy.password}@"
                proxy_url += f"{proxy.ip}:{proxy.port}"
                context_options['proxy'] = {'server': proxy_url}
                logger.info(f"Using proxy: {proxy.ip}:{proxy.port}")
            
            context = await browser.new_context(**context_options)
            
            # Add stealth script to avoid detection
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            """)
            
            page = await context.new_page()
            
            try:
                # Navigate to Google sign-in
                await page.goto("https://accounts.google.com/signin", timeout=LOGIN_TIMEOUT)
                await page.wait_for_timeout(3000)
                
                # Enter email
                email_input = await page.wait_for_selector("input[type='email']", timeout=10000)
                await email_input.fill(account.email)
                await page.wait_for_timeout(1000)
                
                # Click next
                next_button = await page.wait_for_selector("#identifierNext", timeout=5000)
                await next_button.click()
                await page.wait_for_timeout(3000)
                
                # Check for CAPTCHA after email
                captcha_detected = await page.query_selector("iframe[src*='recaptcha']")
                if captcha_detected:
                    captcha_solved = await handle_captcha_with_2captcha(page, solver)
                    if not captcha_solved:
                        await browser.close()
                        return False, "CAPTCHA solving failed after email entry"
                
                # Enter password
                password_input = await page.wait_for_selector("input[type='password']", timeout=10000)
                await password_input.fill(account.password)
                await page.wait_for_timeout(1000)
                
                # Click sign in
                signin_button = await page.wait_for_selector("#passwordNext", timeout=5000)
                await signin_button.click()
                await page.wait_for_timeout(5000)
                
                # Check for CAPTCHA after password
                captcha_detected = await page.query_selector("iframe[src*='recaptcha']")
                if captcha_detected:
                    captcha_solved = await handle_captcha_with_2captcha(page, solver)
                    if not captcha_solved:
                        await browser.close()
                        return False, "CAPTCHA solving failed after password entry"
                
                # Check for additional verification steps
                await page.wait_for_timeout(5000)
                
                # Handle 2FA or phone verification if present
                verification_selectors = [
                    "input[type='tel']",  # Phone verification
                    "input[aria-label*='code']",  # 2FA code
                    "[data-error-msg*='verify']"  # Generic verification
                ]
                
                verification_found = False
                for selector in verification_selectors:
                    element = await page.query_selector(selector)
                    if element:
                        verification_found = True
                        break
                
                if verification_found:
                    await browser.close()
                    return False, "Account requires additional verification (2FA/Phone)"
                
                # Navigate to YouTube to verify login
                await page.goto("https://www.youtube.com", timeout=LOGIN_TIMEOUT)
                await page.wait_for_timeout(5000)
                
                # Check if successfully logged in
                profile_indicators = [
                    "button[aria-label*='Google Account']",
                    "img#avatar",
                    "yt-img-shadow#avatar",
                    "[aria-label*='Account menu']"
                ]
                
                logged_in = False
                for selector in profile_indicators:
                    element = await page.query_selector(selector)
                    if element:
                        logged_in = True
                        break
                
                if logged_in:
                    # Save session data
                    cookies = await context.cookies()
                    session_data = {
                        'login_time': datetime.now(timezone.utc).isoformat(),
                        'proxy_used': f"{proxy.ip}:{proxy.port}" if proxy else None,
                        'user_agent': user_agent
                    }
                    
                    await save_session_data(account.id, cookies, session_data, user_agent)
                    
                    # Update account status
                    await update_account_usage(account.id, success=True)
                    
                    await browser.close()
                    
                    logger.info(f"Successfully logged in to YouTube: {account.email}")
                    await send_discord_notification(f"✅ **YouTube Login Success** \n📧 Account: {account.email}\n🌐 Proxy: {proxy.ip if proxy else 'None'}")
                    
                    return True, "Login successful"
                else:
                    await browser.close()
                    return False, "Login failed - account indicators not found"
                    
            except Exception as login_error:
                await browser.close()
                error_msg = f"Login process error: {login_error}"
                logger.error(f"Login failed for {account.email}: {error_msg}")
                
                # Update account with error
                await update_account_usage(account.id, success=False, error_message=error_msg)
                
                return False, error_msg
                
    except Exception as e:
        error_msg = f"Critical login error: {e}"
        logger.error(f"Critical error during login for {account.email}: {error_msg}")
        return False, error_msg

async def get_authenticated_session(account_id: Optional[str] = None) -> tuple[Optional[YouTubeAccount], Optional[dict]]:
    """
    Get an authenticated session for YouTube scraping
    Returns (account, session_context) where session_context contains browser setup info
    """
    try:
        # Get available account
        if account_id:
            account_doc = await db.youtube_accounts.find_one({"id": account_id, "status": "active"})
            if not account_doc:
                return None, None
            account = YouTubeAccount(**account_doc)
        else:
            account = await get_available_account()
            
        if not account:
            logger.warning("No available accounts for authentication")
            return None, None
        
        # Check if existing session is valid
        session_valid = await validate_session(account)
        
        if not session_valid:
            logger.info(f"Session invalid for {account.email}, attempting fresh login...")
            
            # Attempt login with retry logic
            login_attempts = 0
            login_success = False
            
            while login_attempts < MAX_LOGIN_ATTEMPTS and not login_success:
                login_attempts += 1
                success, message = await login_to_youtube(account)
                
                if success:
                    login_success = True
                    break
                else:
                    logger.warning(f"Login attempt {login_attempts} failed for {account.email}: {message}")
                    if "CAPTCHA" in message or "verification" in message:
                        # Don't retry for CAPTCHA or verification issues
                        break
                    
                    if login_attempts < MAX_LOGIN_ATTEMPTS:
                        await asyncio.sleep(5)  # Wait before retry
            
            if not login_success:
                # Mark account as having issues
                await update_account_usage(account.id, success=False, error_message="Failed to establish session")
                return None, None
        
        # Prepare session context for use
        session_context = {
            'user_agent': account.user_agent or STEALTH_USER_AGENTS[0],
            'cookies': account.cookies,
            'session_data': account.session_data,
            'account_id': account.id
        }
        
        logger.info(f"Authenticated session ready for account: {account.email}")
        return account, session_context
        
    except Exception as e:
        logger.error(f"Error getting authenticated session: {e}")
        return None, None

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

# =============================================================================
# STEP 6: ANTI-DETECTION BROWSER SETUP
# =============================================================================

# Browser fingerprinting and stealth configurations
BROWSER_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]

SCREEN_RESOLUTIONS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1680, "height": 1050},
    {"width": 1280, "height": 1024},
]

# Extended user agents for better rotation
EXTENDED_USER_AGENTS = [
    # Chrome Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    
    # Chrome macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    
    # Chrome Linux
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    
    # Firefox
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    
    # Safari
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
]

import random
import secrets

def get_random_fingerprint() -> dict:
    """Generate randomized browser fingerprint"""
    try:
        viewport = random.choice(BROWSER_VIEWPORTS)
        screen = random.choice(SCREEN_RESOLUTIONS)
        user_agent = random.choice(EXTENDED_USER_AGENTS)
        
        # Determine OS from user agent
        os_type = "Windows"
        if "Macintosh" in user_agent:
            os_type = "macOS"
        elif "X11" in user_agent or "Linux" in user_agent:
            os_type = "Linux"
        
        # Generate WebGL and Canvas fingerprints
        webgl_vendor = random.choice([
            "Google Inc. (Intel)",
            "Google Inc. (NVIDIA)",
            "Google Inc. (AMD)",
            "Mozilla",
            "WebKit WebGL"
        ])
        
        webgl_renderer = random.choice([
            "ANGLE (Intel, Intel(R) HD Graphics 620, OpenGL 4.1)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060, OpenGL 4.1)",
            "ANGLE (AMD, AMD Radeon Pro 560, OpenGL 4.1)",
            "Intel Iris OpenGL Engine",
            "AMD Radeon Pro 5500M OpenGL Engine"
        ])
        
        return {
            "user_agent": user_agent,
            "viewport": viewport,
            "screen": screen,
            "os_type": os_type,
            "timezone": random.choice([
                "America/New_York", "America/Chicago", "America/Denver", 
                "America/Los_Angeles", "Europe/London", "Europe/Berlin",
                "Asia/Tokyo", "Asia/Shanghai", "Australia/Sydney"
            ]),
            "language": random.choice(["en-US", "en-GB", "en-CA", "fr-FR", "de-DE"]),
            "languages": random.choice([
                ["en-US", "en"],
                ["en-GB", "en"],
                ["en-US", "en", "es"],
                ["fr-FR", "fr", "en"],
                ["de-DE", "de", "en"]
            ]),
            "webgl_vendor": webgl_vendor,
            "webgl_renderer": webgl_renderer,
            "hardware_concurrency": random.choice([4, 8, 12, 16]),
            "device_memory": random.choice([4, 8, 16, 32]),
            "platform": random.choice([
                "Win32", "MacIntel", "Linux x86_64"
            ]) if os_type != "macOS" else "MacIntel"
        }
    except Exception as e:
        logger.error(f"Error generating fingerprint: {e}")
        # Return fallback fingerprint
        return {
            "user_agent": EXTENDED_USER_AGENTS[0],
            "viewport": BROWSER_VIEWPORTS[0],
            "screen": SCREEN_RESOLUTIONS[0],
            "os_type": "Windows",
            "timezone": "America/New_York",
            "language": "en-US",
            "languages": ["en-US", "en"]
        }

async def create_stealth_browser_context(proxy_config: Optional[ProxyConfig] = None, 
                                       fingerprint: dict = None) -> tuple:
    """
    Create anti-detection browser context with stealth configurations
    Returns (browser, context, fingerprint_used)
    """
    try:
        if not fingerprint:
            fingerprint = get_random_fingerprint()
        
        # Launch browser with stealth args
        launch_options = {
            "headless": True,
            "args": [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Faster loading
                '--disable-javascript-harmony-shipping',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-sync',
                '--metrics-recording-only',
                '--no-default-browser-check',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--password-store=basic',
                '--use-mock-keychain',
                f'--user-agent={fingerprint["user_agent"]}'
            ]
        }
        
        # Add proxy configuration if provided
        if proxy_config:
            proxy_url = f"{proxy_config.protocol}://"
            if proxy_config.username and proxy_config.password:
                proxy_url += f"{proxy_config.username}:{proxy_config.password}@"
            proxy_url += f"{proxy_config.ip}:{proxy_config.port}"
            
            launch_options["proxy"] = {"server": proxy_url}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_options)
            
            # Create context with stealth settings
            context_options = {
                "user_agent": fingerprint["user_agent"],
                "viewport": fingerprint["viewport"],
                "screen": fingerprint["screen"],
                "locale": fingerprint["language"],
                "timezone_id": fingerprint["timezone"],
                "permissions": ["geolocation"],
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": f"{fingerprint['language']},en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-GPC": "1",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache"
                }
            }
            
            context = await browser.new_context(**context_options)
            
            # Add stealth scripts to hide automation
            await context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => """ + str(fingerprint["languages"]).replace("'", '"') + """,
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Mock hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => """ + str(fingerprint.get("hardware_concurrency", 4)) + """,
                });
                
                // Mock device memory  
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => """ + str(fingerprint.get("device_memory", 8)) + """,
                });
                
                // Mock platform
                Object.defineProperty(navigator, 'platform', {
                    get: () => '""" + fingerprint.get("platform", "Win32") + """',
                });
                
                // Remove automation indicators
                window.chrome = {
                    runtime: {},
                    loadTimes: function(){},
                    csi: function(){},
                    app: {}
                };
                
                // Mock WebGL
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return '""" + fingerprint.get("webgl_vendor", "Google Inc.") + """';
                    }
                    if (parameter === 37446) {
                        return '""" + fingerprint.get("webgl_renderer", "ANGLE (Intel)") + """';
                    }
                    return getParameter(parameter);
                };
                
                // Randomize canvas fingerprint
                const toDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(...args) {
                    const shift = Math.floor(Math.random() * 10) - 5;
                    const ctx = this.getContext('2d');
                    const originalData = ctx.getImageData(0, 0, this.width, this.height);
                    const data = originalData.data;
                    for (let i = 0; i < data.length; i += 4) {
                        data[i] = Math.min(255, Math.max(0, data[i] + shift));
                    }
                    ctx.putImageData(originalData, 0, 0);
                    return toDataURL.apply(this, args);
                };
            """)
            
            return browser, context, fingerprint
            
    except Exception as e:
        logger.error(f"Error creating stealth browser context: {e}")
        raise

async def simulate_human_behavior(page, action_delay_range: tuple = (1, 3)):
    """
    Simulate realistic human browsing behavior with random delays and movements
    """
    try:
        # Random delay before action
        delay = random.uniform(action_delay_range[0], action_delay_range[1])
        await asyncio.sleep(delay)
        
        # Random mouse movements
        for _ in range(random.randint(1, 3)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Occasional random scrolling
        if random.random() < 0.3:  # 30% chance to scroll
            scroll_delta = random.randint(-300, 300)
            await page.mouse.wheel(0, scroll_delta)
            await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Random typing delays if typing
        return random.uniform(0.05, 0.15)  # Per character delay
        
    except Exception as e:
        logger.error(f"Error simulating human behavior: {e}")
        return 0.1  # Default typing delay

async def rotate_user_agent_and_viewport(context, fingerprint: dict = None):
    """
    Rotate user agent and viewport for existing context
    """
    try:
        if not fingerprint:
            fingerprint = get_random_fingerprint()
        
        # Note: Playwright doesn't support changing user agent after context creation
        # This function documents the approach and can be used when creating new contexts
        logger.info(f"Using rotated fingerprint: {fingerprint['user_agent'][:50]}...")
        
        return fingerprint
        
    except Exception as e:
        logger.error(f"Error rotating user agent: {e}")
        return fingerprint

async def implement_residential_proxy_rotation(account_id: str) -> Optional[ProxyConfig]:
    """
    Get a residential proxy for the account with smart rotation
    """
    try:
        # Get available residential proxies (assuming they're marked with location)
        proxies_cursor = db.proxy_pool.find({
            "status": "active",
            "health_status": {"$in": ["healthy", "unknown"]},
            "location": {"$exists": True},  # Residential proxies should have location
            "daily_requests_count": {"$lt": MAX_DAILY_REQUESTS_PER_PROXY}
        }).sort([
            ("success_rate", -1),
            ("daily_requests_count", 1),
            ("last_used", 1)
        ])
        
        proxies = await proxies_cursor.to_list(None)
        
        if proxies:
            # Select proxy based on account's history to avoid pattern detection
            account_usage = await db.account_usage_logs.find({
                "account_id": account_id,
                "details.proxy_id": {"$exists": True}
            }).sort("timestamp", -1).limit(10).to_list(10)
            
            used_proxy_ids = [log["details"]["proxy_id"] for log in account_usage 
                            if log.get("details", {}).get("proxy_id")]
            
            # Prefer proxies not recently used by this account
            unused_proxies = [p for p in proxies if p["id"] not in used_proxy_ids]
            
            selected_proxy_data = unused_proxies[0] if unused_proxies else proxies[0]
            
            # Update proxy usage
            await db.proxy_pool.update_one(
                {"id": selected_proxy_data["id"]},
                {
                    "$set": {"last_used": datetime.now(timezone.utc)},
                    "$inc": {"daily_requests_count": 1}
                }
            )
            
            proxy_config = ProxyConfig(**selected_proxy_data)
            
            logger.info(f"Selected residential proxy: {proxy_config.location} for account {account_id}")
            
            return proxy_config
        
        return None
        
    except Exception as e:
        logger.error(f"Error implementing residential proxy rotation: {e}")
        return None

async def create_enhanced_stealth_session(account_id: str, 
                                        use_proxy: bool = True,
                                        session_type: str = "youtube_scraping") -> dict:
    """
    Create comprehensive anti-detection session with all stealth measures
    """
    try:
        logger.info(f"Creating enhanced stealth session for account {account_id}")
        
        # Get proxy if requested
        proxy_config = None
        if use_proxy:
            proxy_config = await implement_residential_proxy_rotation(account_id)
        
        # Generate fingerprint
        fingerprint = get_random_fingerprint()
        
        # Create stealth browser
        browser, context, used_fingerprint = await create_stealth_browser_context(
            proxy_config, fingerprint
        )
        
        # Create page with additional stealth measures
        page = await context.new_page()
        
        # Add extra stealth measures
        await page.set_extra_http_headers({
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": f'"{used_fingerprint.get("os_type", "Windows")}"',
            "sec-fetch-user": "?1"
        })
        
        # Log session creation
        await log_account_usage_pattern(
            account_id, 
            "stealth_session_created",
            True,
            {
                "session_type": session_type,
                "proxy_id": proxy_config.id if proxy_config else None,
                "proxy_location": proxy_config.location if proxy_config else None,
                "fingerprint": used_fingerprint,
                "user_agent": used_fingerprint["user_agent"][:100]
            }
        )
        
        session_info = {
            "browser": browser,
            "context": context,
            "page": page,
            "fingerprint": used_fingerprint,
            "proxy_config": proxy_config,
            "account_id": account_id,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc)
        }
        
        return session_info
        
    except Exception as e:
        logger.error(f"Error creating enhanced stealth session: {e}")
        raise

async def scrape_channel_about_page(channel_id: str, use_authenticated_session: bool = True) -> tuple[Optional[str], Optional[str]]:
    """Enhanced scrape channel about page with anti-detection browser and health monitoring"""
    try:
        logger.info(f"Starting enhanced scraping for channel: {channel_id}")
        
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
        
        account = None
        session_info = None
        
        if use_authenticated_session:
            # Get healthiest account for scraping
            account = await get_healthiest_available_account()
            if account:
                try:
                    # Create enhanced stealth session
                    session_info = await create_enhanced_stealth_session(
                        account.id, 
                        use_proxy=True, 
                        session_type="channel_scraping"
                    )
                    logger.info(f"Using authenticated session with account: {account.email}")
                except Exception as session_error:
                    logger.warning(f"Failed to create stealth session: {session_error}")
                    account = None
        
        # If no authenticated session, create anonymous stealth session
        if not session_info:
            logger.info("Using anonymous stealth scraping")
            # Create anonymous stealth session
            proxy_config = await implement_residential_proxy_rotation("anonymous")
            fingerprint = get_random_fingerprint()
            
            browser, context, used_fingerprint = await create_stealth_browser_context(
                proxy_config, fingerprint
            )
            
            session_info = {
                "browser": browser,
                "context": context,
                "page": await context.new_page(),
                "fingerprint": used_fingerprint,
                "proxy_config": proxy_config,
                "account_id": "anonymous"
            }
        
        page = session_info["page"]
        
        try:
            for about_url in urls_to_try:
                try:
                    logger.info(f"Trying to scrape: {about_url}")
                    
                    # Simulate human behavior before navigation
                    await simulate_human_behavior(page, (1, 2))
                    
                    await page.goto(about_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(random.randint(3000, 6000))  # Random wait
                    
                    # Check for bot detection or access denied
                    page_content = await page.content()
                    if any(indicator in page_content.lower() for indicator in 
                          ["access denied", "blocked", "captcha", "unusual traffic"]):
                        
                        # Handle potential bot detection
                        if account:
                            await log_account_usage_pattern(
                                account.id,
                                "bot_detection",
                                False,
                                {"error": "Possible bot detection on YouTube", "url": about_url}
                            )
                            
                            # Try to auto-switch account
                            new_account = await auto_switch_account(account.id, "bot_detection")
                            if new_account:
                                account = new_account
                                # Would need to recreate session here in production
                        
                        logger.warning("Possible bot detection, continuing with current session")
                    
                    # Try to expand "Show more" buttons with human-like behavior
                    try:
                        show_more_selectors = [
                            "button[aria-label*='more']",
                            "button[aria-label*='Show more']", 
                            "tp-yt-paper-button#expand",
                            "yt-button-shape[aria-label*='more']",
                            "#expand-button"
                        ]
                        
                        for selector in show_more_selectors:
                            try:
                                # Simulate human scrolling to find the button
                                await page.mouse.wheel(0, random.randint(100, 300))
                                await asyncio.sleep(random.uniform(0.5, 1.5))
                                
                                show_more_button = await page.wait_for_selector(selector, timeout=2000)
                                if show_more_button:
                                    # Human-like click with slight delay and randomization
                                    await simulate_human_behavior(page, (0.5, 1.0))
                                    await show_more_button.click()
                                    await page.wait_for_timeout(random.randint(2000, 4000))
                                    logger.info(f"Expanded content with selector: {selector}")
                                    break
                            except:
                                continue
                    except Exception as expand_error:
                        logger.debug(f"Could not expand show more: {expand_error}")
                    
                    # Extract page content with improved selectors
                    try:
                        # Multiple selector strategies for content extraction
                        content_selectors = [
                            "div#about-description",
                            "yt-formatted-string#description", 
                            "div.about-stats",
                            "div[id*='description']",
                            "div[class*='description']",
                            "span[class*='description']",
                            "#content-container",
                            "ytd-channel-about-metadata-renderer"
                        ]
                        
                        full_content = ""
                        
                        for selector in content_selectors:
                            try:
                                elements = await page.query_selector_all(selector)
                                for element in elements:
                                    element_text = await element.inner_text()
                                    if element_text and element_text not in full_content:
                                        full_content += f" {element_text}"
                            except:
                                continue
                        
                        # Also get general page text as fallback
                        if not full_content.strip():
                            full_content = await page.inner_text("body")
                        
                        # Clean and extract email
                        cleaned_content = full_content.strip()
                        logger.info(f"Extracted content length: {len(cleaned_content)} characters")
                        
                        if cleaned_content:
                            email = extract_email_from_text(cleaned_content)
                            
                            # Log successful scraping
                            if account:
                                await log_account_usage_pattern(
                                    account.id,
                                    "channel_scraping", 
                                    True,
                                    {
                                        "channel_id": channel_id,
                                        "url": about_url, 
                                        "content_length": len(cleaned_content),
                                        "email_found": bool(email),
                                        "proxy_used": bool(session_info.get("proxy_config"))
                                    }
                                )
                                
                                # Update account usage
                                await update_account_usage(account.id, True)
                            
                            return email, cleaned_content
                            
                    except Exception as extract_error:
                        logger.error(f"Content extraction error: {extract_error}")
                        if account:
                            await log_account_usage_pattern(
                                account.id,
                                "content_extraction_error",
                                False, 
                                {"error": str(extract_error), "url": about_url}
                            )
                    
                except Exception as url_error:
                    logger.warning(f"Error scraping {about_url}: {url_error}")
                    if account:
                        await log_account_usage_pattern(
                            account.id,
                            "scraping_error",
                            False,
                            {"error": str(url_error), "url": about_url}
                        )
                    continue
            
            # If we get here, all URLs failed
            logger.warning(f"All scraping attempts failed for channel: {channel_id}")
            if account:
                await update_account_usage(account.id, False, "All URLs failed")
            
            return None, None
            
        finally:
            # Always clean up browser resources
            try:
                await session_info["browser"].close()
            except:
                pass
    
    except Exception as e:
        logger.error(f"Critical error in enhanced scraping for {channel_id}: {e}")
        
        # Log critical error
        if account:
            await log_account_usage_pattern(
                account.id,
                "critical_scraping_error", 
                False,
                {"error": str(e), "channel_id": channel_id}
            )
            await update_account_usage(account.id, False, f"Critical error: {str(e)}")
        
        return None, None

# =============================================================================
# PHASE 3 STEP 7: AUTHENTICATED EMAIL EXTRACTION
# =============================================================================

import dns.resolver
import socket
from email_validator import validate_email, EmailNotValidError

async def check_email_deliverability(email: str) -> dict:
    """
    Check email deliverability with comprehensive validation
    Returns dict with validation status and confidence score
    """
    try:
        # Basic format validation first
        if not email or '@' not in email:
            return {"valid": False, "reason": "Invalid format", "confidence": 0}
        
        domain = email.split('@')[1]
        
        # Check if domain has MX record
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            has_mx = len(mx_records) > 0
        except:
            has_mx = False
        
        # Check if domain is reachable
        domain_reachable = False
        try:
            socket.gethostbyname(domain)
            domain_reachable = True
        except:
            pass
        
        # Use email-validator for additional validation
        try:
            validation_result = validate_email(email)
            format_valid = True
            normalized_email = validation_result.email
        except EmailNotValidError:
            format_valid = False
            normalized_email = email.lower()
        
        # Calculate confidence score
        confidence = 0
        if format_valid:
            confidence += 30
        if has_mx:
            confidence += 40
        if domain_reachable:
            confidence += 30
        
        return {
            "valid": format_valid and (has_mx or domain_reachable),
            "normalized_email": normalized_email,
            "has_mx_record": has_mx,
            "domain_reachable": domain_reachable,
            "confidence": confidence,
            "reason": "Valid" if confidence >= 70 else "Low deliverability"
        }
        
    except Exception as e:
        logger.error(f"Error checking email deliverability for {email}: {e}")
        return {"valid": False, "reason": f"Validation error: {str(e)}", "confidence": 0}

async def detect_contact_reveal_buttons(page) -> bool:
    """
    Detect and click YouTube 'View email address' or similar contact reveal buttons
    Returns True if button was found and clicked
    """
    try:
        # Common selectors for YouTube contact reveal buttons
        contact_button_selectors = [
            # Business email reveal buttons
            "button[aria-label*='email']",
            "button[aria-label*='contact']", 
            "button[aria-label*='View email']",
            "button[aria-label*='Show email']",
            "button[aria-label*='Business email']",
            "button[aria-label*='Show contact']",
            
            # Generic reveal buttons in about section
            "button[data-target*='email']",
            "button[onclick*='email']",
            "yt-button-shape[aria-label*='email']",
            "yt-button-shape[aria-label*='contact']",
            
            # Text-based buttons
            "button:has-text('View email address')",
            "button:has-text('Show email')",
            "button:has-text('Contact')",
            "button:has-text('Business email')",
            
            # Link-style contact buttons
            "a[href*='mailto']",
            "a[aria-label*='email']",
            "a[aria-label*='contact']"
        ]
        
        logger.info("Searching for contact reveal buttons...")
        
        for selector in contact_button_selectors:
            try:
                # Wait briefly for dynamic content
                await page.wait_for_timeout(1000)
                
                # Check if button exists and is visible
                button = await page.query_selector(selector)
                if button:
                    # Check if button is visible and enabled
                    is_visible = await button.is_visible()
                    is_enabled = await button.is_enabled()
                    
                    if is_visible and is_enabled:
                        logger.info(f"Found contact button with selector: {selector}")
                        
                        # Simulate human behavior before clicking
                        await simulate_human_behavior(page, (0.5, 1.5))
                        
                        # Scroll button into view
                        await button.scroll_into_view_if_needed()
                        await page.wait_for_timeout(random.randint(500, 1500))
                        
                        # Click the button
                        await button.click()
                        
                        # Wait for potential content reveal
                        await page.wait_for_timeout(random.randint(2000, 4000))
                        
                        logger.info("Successfully clicked contact reveal button")
                        return True
                        
            except Exception as selector_error:
                logger.debug(f"Selector {selector} failed: {selector_error}")
                continue
        
        logger.info("No contact reveal buttons found")
        return False
        
    except Exception as e:
        logger.error(f"Error detecting contact reveal buttons: {e}")
        return False

async def extract_emails_from_video_descriptions(channel_id: str, max_videos: int = 5) -> list:
    """
    Extract emails from recent video descriptions using authenticated session
    """
    try:
        logger.info(f"Extracting emails from video descriptions for channel: {channel_id}")
        
        # Get healthiest account for video scraping
        account = await get_healthiest_available_account()
        if not account:
            logger.warning("No healthy account available for video description extraction")
            return []
        
        session_info = await create_enhanced_stealth_session(
            account.id, 
            use_proxy=True, 
            session_type="video_description_scraping"
        )
        
        page = session_info["page"]
        found_emails = []
        
        # Get channel's recent videos
        videos = await get_channel_videos(channel_id, max_videos)
        
        if not videos:
            logger.warning(f"No videos found for channel: {channel_id}")
            return []
        
        for video in videos[:max_videos]:
            try:
                video_id = video.get('video_id')
                if not video_id:
                    continue
                    
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info(f"Scraping video description: {video_url}")
                
                await simulate_human_behavior(page, (1, 3))
                await page.goto(video_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(random.randint(2000, 4000))
                
                # Expand description if needed
                try:
                    expand_selectors = [
                        "button[aria-label*='Show more']",
                        "#expand-button",
                        "tp-yt-paper-button#expand",
                        "yt-button-shape[aria-label*='more']"
                    ]
                    
                    for selector in expand_selectors:
                        try:
                            expand_btn = await page.wait_for_selector(selector, timeout=2000)
                            if expand_btn:
                                await expand_btn.click()
                                await page.wait_for_timeout(random.randint(1500, 3000))
                                break
                        except:
                            continue
                            
                except Exception as expand_error:
                    logger.debug(f"Could not expand description: {expand_error}")
                
                # Extract description content
                description_selectors = [
                    "#description-text",
                    "#description",
                    "ytd-video-secondary-info-renderer #description",
                    "#meta-contents #description",
                    "yt-formatted-string#content",
                    "#description-inner"
                ]
                
                description_text = ""
                for selector in description_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            text = await element.inner_text()
                            if text and text not in description_text:
                                description_text += f" {text}"
                    except:
                        continue
                
                if description_text.strip():
                    # Extract emails from description
                    email = extract_email_from_text(description_text)
                    if email:
                        # Check email deliverability
                        deliverability = await check_email_deliverability(email)
                        
                        email_data = {
                            "email": email,
                            "source": "video_description",
                            "source_url": video_url,
                            "video_title": video.get('title', ''),
                            "context": description_text[:200],
                            "deliverability": deliverability,
                            "confidence": deliverability.get("confidence", 0) * 0.8  # 80% of deliverability confidence
                        }
                        
                        found_emails.append(email_data)
                        logger.info(f"Found email in video description: {email}")
                
                # Log usage
                await log_account_usage_pattern(
                    account.id,
                    "video_description_scraping",
                    True,
                    {
                        "video_id": video_id,
                        "channel_id": channel_id,
                        "description_length": len(description_text),
                        "email_found": bool(email) if 'email' in locals() else False
                    }
                )
                
            except Exception as video_error:
                logger.error(f"Error scraping video {video.get('video_id', 'unknown')}: {video_error}")
                await log_account_usage_pattern(
                    account.id,
                    "video_description_error",
                    False,
                    {"error": str(video_error), "video_id": video.get('video_id')}
                )
                continue
        
        # Clean up
        await session_info["browser"].close()
        
        # Remove duplicates
        unique_emails = []
        seen_emails = set()
        
        for email_data in found_emails:
            email = email_data["email"]
            if email not in seen_emails:
                seen_emails.add(email)
                unique_emails.append(email_data)
        
        logger.info(f"Extracted {len(unique_emails)} unique emails from video descriptions")
        return unique_emails
        
    except Exception as e:
        logger.error(f"Error extracting emails from video descriptions: {e}")
        return []

async def enhanced_authenticated_email_extraction(channel_id: str) -> dict:
    """
    Enhanced email extraction using authenticated sessions with contact button detection
    and video description extraction
    """
    try:
        logger.info(f"Starting enhanced authenticated email extraction for: {channel_id}")
        
        results = {
            "channel_id": channel_id,
            "emails_found": [],
            "sources_checked": [],
            "total_confidence": 0,
            "best_email": None,
            "extraction_summary": {}
        }
        
        # Step 1: Enhanced about page extraction with contact button detection
        about_email, about_content = await scrape_channel_about_page_with_contact_buttons(channel_id)
        
        if about_email:
            deliverability = await check_email_deliverability(about_email)
            email_data = {
                "email": about_email,
                "source": "about_page_authenticated",
                "context": about_content[:200] if about_content else "",
                "deliverability": deliverability,
                "confidence": deliverability.get("confidence", 0)  # Full confidence for about page
            }
            results["emails_found"].append(email_data)
            results["sources_checked"].append("about_page_authenticated")
        
        # Step 2: Video descriptions extraction
        video_emails = await extract_emails_from_video_descriptions(channel_id, max_videos=5)
        results["emails_found"].extend(video_emails)
        if video_emails:
            results["sources_checked"].append("video_descriptions")
        
        # Step 3: Calculate best email and overall confidence
        if results["emails_found"]:
            # Sort by confidence score
            results["emails_found"].sort(key=lambda x: x["confidence"], reverse=True)
            results["best_email"] = results["emails_found"][0]
            results["total_confidence"] = max([email["confidence"] for email in results["emails_found"]])
        
        # Step 4: Create extraction summary
        results["extraction_summary"] = {
            "total_emails_found": len(results["emails_found"]),
            "sources_checked": len(results["sources_checked"]),
            "highest_confidence": results["total_confidence"],
            "deliverable_emails": len([e for e in results["emails_found"] if e["deliverability"]["valid"]])
        }
        
        logger.info(f"Enhanced extraction complete: {results['extraction_summary']}")
        return results
        
    except Exception as e:
        logger.error(f"Error in enhanced authenticated email extraction: {e}")
        return {
            "channel_id": channel_id,
            "emails_found": [],
            "sources_checked": [],
            "total_confidence": 0,
            "best_email": None,
            "extraction_summary": {"error": str(e)},
            "error": str(e)
        }

async def scrape_channel_about_page_with_contact_buttons(channel_id: str) -> tuple[Optional[str], Optional[str]]:
    """
    Enhanced about page scraping with contact button detection and clicking
    """
    try:
        logger.info(f"Starting enhanced about page scraping with contact detection: {channel_id}")
        
        # Get healthiest account for scraping
        account = await get_healthiest_available_account()
        if not account:
            logger.warning("No healthy account available, falling back to anonymous scraping")
            return await scrape_channel_about_page(channel_id, use_authenticated_session=False)
        
        session_info = await create_enhanced_stealth_session(
            account.id, 
            use_proxy=True, 
            session_type="enhanced_about_scraping"
        )
        
        page = session_info["page"]
        
        # Handle different channel ID formats
        if channel_id.startswith('@'):
            urls_to_try = [f"https://www.youtube.com/{channel_id}/about"]
        elif channel_id.startswith('UC') and len(channel_id) == 24:
            urls_to_try = [f"https://www.youtube.com/channel/{channel_id}/about"]
        else:
            urls_to_try = [
                f"https://www.youtube.com/@{channel_id}/about",
                f"https://www.youtube.com/channel/{channel_id}/about"
            ]
        
        for about_url in urls_to_try:
            try:
                logger.info(f"Trying enhanced scraping: {about_url}")
                
                await simulate_human_behavior(page, (1, 2))
                await page.goto(about_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(random.randint(3000, 6000))
                
                # First, try to detect and click contact reveal buttons
                contact_button_clicked = await detect_contact_reveal_buttons(page)
                
                if contact_button_clicked:
                    logger.info("Contact button clicked, waiting for content reveal...")
                    await page.wait_for_timeout(random.randint(2000, 4000))
                
                # Expand "Show more" sections
                try:
                    show_more_selectors = [
                        "button[aria-label*='more']",
                        "button[aria-label*='Show more']", 
                        "tp-yt-paper-button#expand",
                        "yt-button-shape[aria-label*='more']",
                        "#expand-button"
                    ]
                    
                    for selector in show_more_selectors:
                        try:
                            await page.mouse.wheel(0, random.randint(100, 300))
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                            
                            show_more_button = await page.wait_for_selector(selector, timeout=2000)
                            if show_more_button:
                                await simulate_human_behavior(page, (0.5, 1.0))
                                await show_more_button.click()
                                await page.wait_for_timeout(random.randint(2000, 4000))
                                logger.info(f"Expanded content with selector: {selector}")
                                break
                        except:
                            continue
                except Exception as expand_error:
                    logger.debug(f"Could not expand show more: {expand_error}")
                
                # Extract content with enhanced selectors
                content_selectors = [
                    "div#about-description",
                    "yt-formatted-string#description", 
                    "div.about-stats",
                    "div[id*='description']",
                    "div[class*='description']",
                    "span[class*='description']",
                    "#content-container",
                    "ytd-channel-about-metadata-renderer",
                    # Enhanced selectors for contact info
                    "div[class*='contact']",
                    "div[class*='email']",
                    "span[class*='contact']",
                    "span[class*='email']",
                    "a[href*='mailto']"
                ]
                
                full_content = ""
                
                for selector in content_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            element_text = await element.inner_text()
                            if element_text and element_text not in full_content:
                                full_content += f" {element_text}"
                    except:
                        continue
                
                # Also check for mailto links specifically
                try:
                    mailto_links = await page.query_selector_all("a[href^='mailto:']")
                    for link in mailto_links:
                        href = await link.get_attribute("href")
                        if href:
                            email = href.replace("mailto:", "").split("?")[0]
                            full_content += f" {email}"
                except:
                    pass
                
                # Get general page text as fallback
                if not full_content.strip():
                    full_content = await page.inner_text("body")
                
                cleaned_content = full_content.strip()
                logger.info(f"Enhanced extraction - content length: {len(cleaned_content)} characters")
                
                if cleaned_content:
                    email = extract_email_from_text(cleaned_content)
                    
                    # Log successful scraping
                    await log_account_usage_pattern(
                        account.id,
                        "enhanced_about_scraping", 
                        True,
                        {
                            "channel_id": channel_id,
                            "url": about_url, 
                            "content_length": len(cleaned_content),
                            "email_found": bool(email),
                            "contact_button_clicked": contact_button_clicked
                        }
                    )
                    
                    await update_account_usage(account.id, True)
                    await session_info["browser"].close()
                    
                    return email, cleaned_content
                    
            except Exception as url_error:
                logger.warning(f"Error scraping {about_url}: {url_error}")
                continue
        
        # Clean up and return nothing if all failed
        await session_info["browser"].close()
        return None, None
        
    except Exception as e:
        logger.error(f"Critical error in enhanced about page scraping: {e}")
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

async def get_healthiest_account_for_queue():
    """Get the healthiest available account for queue processing using health scoring"""
    try:
        # Find accounts that are not banned, rate limited, or in cooldown
        current_time = datetime.now(timezone.utc)
        
        accounts_cursor = db.youtube_accounts.find({
            "status": {"$nin": ["banned", "rate_limited"]},
            "$or": [
                {"cooldown_until": {"$exists": False}},
                {"cooldown_until": {"$lte": current_time}}
            ]
        })
        
        available_accounts = []
        async for account in accounts_cursor:
            if not await is_account_rate_limited(account["id"]):
                # Calculate health score for account selection
                health_data = await get_account_health_score(account["id"])
                health_score = health_data.get("health_score", 0)
                
                available_accounts.append({
                    "id": account["id"],
                    "health_score": health_score,
                    "last_used": account.get("last_used"),
                    "success_rate": account.get("success_rate", 100)
                })
        
        if not available_accounts:
            return None
        
        # Sort by health score (highest first), then by least recently used
        available_accounts.sort(key=lambda x: (
            -x["health_score"],  # Highest health score first
            x["last_used"] or datetime.min.replace(tzinfo=timezone.utc)  # Least recently used
        ))
        
        return available_accounts[0]["id"]
        
    except Exception as e:
        logger.error(f"Error getting healthiest account: {e}")
        return None

async def smart_queue_processor():
    """Intelligent queue processor with account selection, proxy assignment, and error handling"""
    try:
        logger.info("🧠 Starting smart queue processing...")
        
        # Check if processing is already at capacity
        concurrent_processing = await db.scraping_queue.count_documents({"status": "processing"})
        available_slots = MAX_CONCURRENT_PROCESSING - concurrent_processing
        
        if available_slots <= 0:
            logger.info("⏸️ Maximum concurrent processing limit reached")
            return {"processed": 0, "message": "At capacity"}
        
        processed_requests = []
        
        for slot in range(available_slots):
            # Get healthiest available account
            account_id = await get_healthiest_account_for_queue()
            if not account_id:
                logger.info("❌ No healthy accounts available for processing")
                break
            
            # Get next high priority request
            queue_request = await get_next_priority_queue_request(account_id)
            if not queue_request:
                logger.info(f"📭 No pending requests for account {account_id}")
                continue
            
            # Assign proxy to request
            proxy = await get_available_proxy()
            proxy_id = proxy.get("id") if proxy else None
            
            # Process the request with full orchestration
            processing_result = await process_queue_request_with_orchestration(
                queue_request.id, account_id, proxy_id
            )
            
            if processing_result["success"]:
                processed_requests.append({
                    "request_id": queue_request.id,
                    "account_id": account_id,
                    "proxy_id": proxy_id,
                    "channel_id": queue_request.channel_id
                })
                logger.info(f"✅ Successfully processed request {queue_request.id}")
            else:
                logger.error(f"❌ Failed to process request {queue_request.id}: {processing_result['error']}")
        
        # Send summary notification
        if processed_requests:
            summary = f"🚀 **Smart Queue Processor Results**\n"
            summary += f"📊 Processed: {len(processed_requests)} requests\n"
            summary += f"🏥 Health-based account selection\n"
            summary += f"🎯 Priority-based request handling\n"
            summary += f"🔄 Proxy assignment integrated"
            
            await send_discord_notification(summary)
            logger.info(f"🎉 Smart queue processing completed: {len(processed_requests)} requests")
        
        return {
            "processed": len(processed_requests),
            "requests": processed_requests,
            "available_slots": available_slots
        }
        
    except Exception as e:
        logger.error(f"💥 Error in smart queue processor: {e}")
        await send_discord_notification(f"⚠️ **Queue Processing Error**\n❌ {str(e)}")
        return {"processed": 0, "error": str(e)}

async def get_next_priority_queue_request(account_id: str = None):
    """Get next queue request with intelligent priority handling"""
    try:
        current_time = datetime.now(timezone.utc)
        
        # Build query for available requests
        query = {
            "status": "pending",
            "scheduled_time": {"$lte": current_time},
            "attempts": {"$lt": QUEUE_RETRY_ATTEMPTS}
        }
        
        if account_id:
            # Check rate limits for this account
            if await is_account_rate_limited(account_id):
                logger.info(f"Account {account_id} is rate limited, skipping priority queue processing")
                return None
        
        # Priority order: premium channels first, then by scheduled time
        requests_cursor = db.scraping_queue.find(query).sort([
            ("priority", -1),  # Higher priority first (premium = 3, high = 2, medium = 1, low = 0)
            ("scheduled_time", 1)  # Earlier scheduled time first
        ]).limit(1)
        
        request_doc = await requests_cursor.to_list(length=1)
        if not request_doc:
            return None
        
        request = request_doc[0]
        
        # Assign account and mark as processing
        await db.scraping_queue.update_one(
            {"id": request["id"]},
            {
                "$set": {
                    "status": "processing",
                    "account_id": account_id,
                    "processing_started": current_time,
                    "attempts": request.get("attempts", 0) + 1
                }
            }
        )
        
        logger.info(f"🎯 Assigned priority queue request {request['id']} for processing by account {account_id}")
        return type('QueueRequest', (), request)()
        
    except Exception as e:
        logger.error(f"Error getting next priority queue request: {e}")
        return None

async def process_queue_request_with_orchestration(request_id: str, account_id: str, proxy_id: str = None):
    """Process a queue request with full orchestration including error handling and recovery"""
    try:
        logger.info(f"🔄 Processing request {request_id} with account {account_id}")
        
        # Get request details
        request_doc = await db.scraping_queue.find_one({"id": request_id})
        if not request_doc:
            return {"success": False, "error": "Request not found"}
        
        channel_id = request_doc.get("channel_id")
        request_type = request_doc.get("request_type", "email_extraction")
        
        # Track processing start
        processing_start = datetime.now(timezone.utc)
        await db.scraping_queue.update_one(
            {"id": request_id},
            {"$set": {"processing_started": processing_start}}
        )
        
        processing_result = None
        
        if request_type == "email_extraction":
            # Extract email with anti-detection and proxy support
            processing_result = await extract_email_with_full_orchestration(
                channel_id, account_id, proxy_id
            )
        
        # Handle processing result
        if processing_result and processing_result.get("success"):
            # Mark request as completed
            await complete_queue_request(request_id, {
                "result": processing_result,
                "account_id": account_id,
                "proxy_id": proxy_id,
                "processing_duration": (datetime.now(timezone.utc) - processing_start).total_seconds()
            })
            
            # Update account success metrics
            await update_account_success_metrics(account_id, True)
            
            return {"success": True, "result": processing_result}
        else:
            # Handle failure with intelligent retry logic
            error_message = processing_result.get("error", "Unknown error") if processing_result else "Processing failed"
            
            retry_result = await handle_queue_request_failure(
                request_id, account_id, proxy_id, error_message
            )
            
            # Update account failure metrics
            await update_account_success_metrics(account_id, False)
            
            return {"success": False, "error": error_message, "retry_scheduled": retry_result}
    
    except Exception as e:
        logger.error(f"Error in orchestrated queue processing: {e}")
        
        # Handle unexpected errors
        await handle_queue_request_failure(request_id, account_id, proxy_id, str(e))
        await update_account_success_metrics(account_id, False)
        
        return {"success": False, "error": str(e)}

async def extract_email_with_full_orchestration(channel_id: str, account_id: str, proxy_id: str = None):
    """Extract email using full orchestration: stealth browser, authenticated session, proxy"""
    try:
        logger.info(f"🔍 Extracting email for channel {channel_id} with full orchestration")
        
        # Get authenticated session for account
        session_data = await get_authenticated_session(account_id)
        authenticated = session_data.get("success", False)
        
        # Get proxy configuration if provided
        proxy_config = None
        if proxy_id:
            proxy_data = await db.proxy_pool.find_one({"id": proxy_id})
            if proxy_data and proxy_data.get("status") == "active":
                proxy_config = {
                    "server": f"{proxy_data['protocol']}://{proxy_data['ip']}:{proxy_data['port']}",
                    "username": proxy_data.get("username"),
                    "password": proxy_data.get("password")
                }
        
        # Create stealth browser context
        stealth_context = await create_stealth_browser_context(proxy_config)
        
        # Extract email using enhanced scraping
        extraction_result = await scrape_channel_about_page(
            channel_id, 
            stealth_context,
            authenticated_cookies=session_data.get("cookies") if authenticated else None
        )
        
        if extraction_result.get("email"):
            logger.info(f"✅ Successfully extracted email for channel {channel_id}")
            
            # Store in appropriate collection
            if extraction_result["email"]:
                await store_lead_with_email(channel_id, extraction_result)
            else:
                await store_lead_without_email(channel_id, extraction_result)
            
            return {"success": True, "email": extraction_result.get("email"), "method": "full_orchestration"}
        else:
            logger.info(f"❌ No email found for channel {channel_id}")
            await store_lead_without_email(channel_id, extraction_result)
            return {"success": True, "email": None, "method": "full_orchestration"}
    
    except Exception as e:
        logger.error(f"Error in full orchestration email extraction: {e}")
        return {"success": False, "error": str(e)}

# Legacy function for backward compatibility
async def process_queue_batch():
    """Legacy batch processor - redirects to smart processor"""
    return await smart_queue_processor()

async def handle_queue_request_failure(request_id: str, account_id: str, proxy_id: str, error_message: str):
    """Handle failed queue request with intelligent retry and recovery logic"""
    try:
        logger.info(f"🔧 Handling failure for request {request_id}: {error_message}")
        
        # Get current request details
        request_doc = await db.scraping_queue.find_one({"id": request_id})
        if not request_doc:
            return {"retry_scheduled": False, "reason": "Request not found"}
        
        current_attempts = request_doc.get("attempts", 0)
        
        # Detect rate limit patterns
        is_rate_limited = await detect_rate_limit_from_error(error_message)
        is_account_blocked = await detect_account_block_from_error(error_message)
        is_ip_blocked = await detect_ip_block_from_error(error_message)
        
        # Handle different error types
        if is_rate_limited:
            logger.warning(f"⏱️ Rate limit detected for request {request_id}")
            await handle_rate_limit_recovery(account_id, proxy_id, request_id)
            
        elif is_account_blocked:
            logger.warning(f"🚫 Account block detected for request {request_id}")
            await handle_account_block_recovery(account_id, request_id)
            
        elif is_ip_blocked:
            logger.warning(f"🌐 IP block detected for request {request_id}")
            await handle_ip_block_recovery(proxy_id, request_id)
        
        # Determine if retry should be scheduled
        if current_attempts < QUEUE_RETRY_ATTEMPTS:
            # Calculate exponential backoff delay
            base_delay = QUEUE_RETRY_DELAY_MINUTES
            exponential_delay = base_delay * (2 ** (current_attempts - 1))
            max_delay = 120  # Maximum 2 hours delay
            retry_delay = min(exponential_delay, max_delay)
            
            # Schedule retry with intelligent account/proxy rotation
            retry_time = datetime.now(timezone.utc) + timedelta(minutes=retry_delay)
            
            await db.scraping_queue.update_one(
                {"id": request_id},
                {
                    "$set": {
                        "status": "pending",
                        "scheduled_time": retry_time,
                        "account_id": None,  # Clear account assignment for rotation
                        "proxy_id": None,    # Clear proxy assignment for rotation
                        "error_history": request_doc.get("error_history", []) + [
                            {
                                "error": error_message,
                                "timestamp": datetime.now(timezone.utc),
                                "account_id": account_id,
                                "proxy_id": proxy_id,
                                "attempt": current_attempts
                            }
                        ]
                    }
                }
            )
            
            logger.info(f"🔄 Scheduled retry for request {request_id} in {retry_delay} minutes")
            await send_discord_notification(
                f"🔄 **Request Retry Scheduled**\n"
                f"📋 Request: {request_id}\n"
                f"⏰ Retry in: {retry_delay} minutes\n"
                f"🔢 Attempt: {current_attempts + 1}/{QUEUE_RETRY_ATTEMPTS}\n"
                f"❌ Error: {error_message[:100]}..."
            )
            
            return {"retry_scheduled": True, "retry_delay": retry_delay}
        else:
            # Max attempts reached - mark as failed
            await db.scraping_queue.update_one(
                {"id": request_id},
                {
                    "$set": {
                        "status": "failed",
                        "failed_at": datetime.now(timezone.utc),
                        "final_error": error_message,
                        "total_attempts": current_attempts
                    }
                }
            )
            
            logger.error(f"❌ Request {request_id} failed permanently after {current_attempts} attempts")
            await send_discord_notification(
                f"💀 **Request Failed Permanently**\n"
                f"📋 Request: {request_id}\n"
                f"🔢 Attempts: {current_attempts}/{QUEUE_RETRY_ATTEMPTS}\n"
                f"❌ Final Error: {error_message[:150]}..."
            )
            
            return {"retry_scheduled": False, "reason": "Max attempts reached"}
    
    except Exception as e:
        logger.error(f"Error handling queue request failure: {e}")
        return {"retry_scheduled": False, "reason": str(e)}

async def detect_rate_limit_from_error(error_message: str):
    """Detect rate limit patterns from error messages"""
    rate_limit_patterns = [
        "rate limit", "too many requests", "429", "quota exceeded",
        "throttled", "slow down", "rate exceeded", "request limit"
    ]
    
    error_lower = error_message.lower()
    return any(pattern in error_lower for pattern in rate_limit_patterns)

async def detect_account_block_from_error(error_message: str):
    """Detect account block patterns from error messages"""
    account_block_patterns = [
        "account suspended", "account blocked", "login failed",
        "authentication failed", "invalid credentials", "account locked",
        "banned", "restricted account", "verification required"
    ]
    
    error_lower = error_message.lower()
    return any(pattern in error_lower for pattern in account_block_patterns)

async def detect_ip_block_from_error(error_message: str):
    """Detect IP block patterns from error messages"""
    ip_block_patterns = [
        "ip blocked", "ip banned", "access denied", "connection refused",
        "network error", "proxy error", "ip restricted", "geo-blocked"
    ]
    
    error_lower = error_message.lower()
    return any(pattern in error_lower for pattern in ip_block_patterns)

async def handle_rate_limit_recovery(account_id: str, proxy_id: str, request_id: str):
    """Handle rate limit recovery with account cooldown"""
    try:
        # Apply cooldown to account
        cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=ACCOUNT_COOLDOWN_MINUTES)
        
        await db.youtube_accounts.update_one(
            {"id": account_id},
            {
                "$set": {
                    "status": "rate_limited",
                    "rate_limit_reset": cooldown_until,
                    "cooldown_until": cooldown_until
                }
            }
        )
        
        logger.info(f"🕐 Applied {ACCOUNT_COOLDOWN_MINUTES} minute cooldown to account {account_id}")
        
        # Also apply cooldown to proxy if used
        if proxy_id:
            await db.proxy_pool.update_one(
                {"id": proxy_id},
                {
                    "$set": {
                        "status": "rate_limited",
                        "cooldown_until": datetime.now(timezone.utc) + timedelta(minutes=PROXY_COOLDOWN_MINUTES)
                    }
                }
            )
    
    except Exception as e:
        logger.error(f"Error in rate limit recovery: {e}")

async def handle_account_block_recovery(account_id: str, request_id: str):
    """Handle account block recovery"""
    try:
        # Mark account as problematic
        await db.youtube_accounts.update_one(
            {"id": account_id},
            {
                "$set": {
                    "status": "needs_verification",
                    "last_error": "Account blocked/suspended",
                    "error_count": {"$inc": 1}
                }
            }
        )
        
        # Try to get alternative account
        alternative_account = await get_healthiest_account_for_queue()
        if alternative_account and alternative_account != account_id:
            logger.info(f"🔄 Switching from blocked account {account_id} to {alternative_account}")
            
            await db.scraping_queue.update_one(
                {"id": request_id},
                {"$set": {"account_id": alternative_account}}
            )
    
    except Exception as e:
        logger.error(f"Error in account block recovery: {e}")

async def handle_ip_block_recovery(proxy_id: str, request_id: str):
    """Handle IP block recovery with proxy rotation"""
    try:
        if proxy_id:
            # Mark proxy as blocked
            await db.proxy_pool.update_one(
                {"id": proxy_id},
                {
                    "$set": {
                        "status": "blocked",
                        "blocked_at": datetime.now(timezone.utc),
                        "health_status": "unhealthy"
                    }
                }
            )
            
            # Get alternative proxy
            alternative_proxy = await get_available_proxy()
            if alternative_proxy:
                logger.info(f"🌐 Switching from blocked proxy {proxy_id} to {alternative_proxy['id']}")
                
                await db.scraping_queue.update_one(
                    {"id": request_id},
                    {"$set": {"proxy_id": alternative_proxy["id"]}}
                )
    
    except Exception as e:
        logger.error(f"Error in IP block recovery: {e}")

async def update_account_success_metrics(account_id: str, success: bool):
    """Update account success rate and usage metrics"""
    try:
        current_time = datetime.now(timezone.utc)
        
        # Get current metrics
        account = await db.youtube_accounts.find_one({"id": account_id})
        if not account:
            return
        
        current_success_count = account.get("success_count", 0)
        current_total_requests = account.get("total_requests_count", 0)
        
        # Update metrics
        new_total = current_total_requests + 1
        new_success = current_success_count + (1 if success else 0)
        new_success_rate = (new_success / new_total) * 100 if new_total > 0 else 100
        
        await db.youtube_accounts.update_one(
            {"id": account_id},
            {
                "$set": {
                    "last_used": current_time,
                    "success_count": new_success,
                    "total_requests_count": new_total,
                    "success_rate": new_success_rate
                },
                "$inc": {
                    "daily_requests_count": 1
                }
            }
        )
        
        logger.info(f"📊 Updated metrics for account {account_id}: {new_success_rate:.1f}% success rate")
    
    except Exception as e:
        logger.error(f"Error updating account success metrics: {e}")

async def store_lead_with_email(channel_id: str, extraction_data: dict):
    """Store lead with email in main_leads collection"""
    try:
        lead_data = {
            "id": str(uuid.uuid4()),
            "channel_id": channel_id,
            "email": extraction_data.get("email"),
            "email_status": "found",
            "extraction_method": extraction_data.get("method", "unknown"),
            "confidence_score": extraction_data.get("confidence", 75),
            "channel_data": extraction_data.get("channel_info", {}),
            "processing_timestamp": datetime.now(timezone.utc)
        }
        
        await db.main_leads.insert_one(lead_data)
        logger.info(f"✅ Stored lead with email: {channel_id}")
    
    except Exception as e:
        logger.error(f"Error storing lead with email: {e}")

async def store_lead_without_email(channel_id: str, extraction_data: dict):
    """Store lead without email in no_email_leads collection"""
    try:
        lead_data = {
            "id": str(uuid.uuid4()),
            "channel_id": channel_id,
            "email_status": "not_found",
            "extraction_attempts": extraction_data.get("attempts", 1),
            "channel_data": extraction_data.get("channel_info", {}),
            "processing_timestamp": datetime.now(timezone.utc)
        }
        
        await db.no_email_leads.insert_one(lead_data)
        logger.info(f"📝 Stored lead without email: {channel_id}")
    
    except Exception as e:
        logger.error(f"Error storing lead without email: {e}")
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

@api_router.post("/debug/test-authenticated-scraping")
async def test_authenticated_scraping(channel_id: str):
    """Debug endpoint to test authenticated channel scraping"""
    try:
        logger.info(f"Testing authenticated scraping for channel: {channel_id}")
        
        # Test with authentication
        email_auth, content_auth = await scrape_channel_about_page(channel_id, use_authenticated_session=True)
        
        # Test without authentication for comparison
        email_no_auth, content_no_auth = await scrape_channel_about_page(channel_id, use_authenticated_session=False)
        
        return {
            "channel_id": channel_id,
            "authenticated_scraping": {
                "email_found": email_auth,
                "content_length": len(content_auth) if content_auth else 0,
                "content_preview": content_auth[:200] if content_auth else None
            },
            "non_authenticated_scraping": {
                "email_found": email_no_auth,
                "content_length": len(content_no_auth) if content_no_auth else 0,
                "content_preview": content_no_auth[:200] if content_no_auth else None
            },
            "comparison": {
                "auth_better": (email_auth and not email_no_auth) or 
                              (content_auth and len(content_auth) > len(content_no_auth or "")),
                "same_results": email_auth == email_no_auth
            },
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error in authenticated scraping test: {e}")
        return {
            "channel_id": channel_id,
            "error": str(e),
            "success": False
        }

@api_router.get("/accounts/session/status")
async def get_all_accounts_session_status():
    """Get session status for all YouTube accounts"""
    try:
        accounts_cursor = db.youtube_accounts.find({})
        accounts = await accounts_cursor.to_list(1000)
        
        session_statuses = []
        
        for account_doc in accounts:
            account = YouTubeAccount(**account_doc)
            
            # Check session validity
            is_valid = await validate_session(account)
            
            session_age = None
            if account.last_used:
                session_age = (datetime.now(timezone.utc) - account.last_used).total_seconds() / 3600  # hours
            
            session_statuses.append({
                "account_id": account.id,
                "email": account.email,
                "status": account.status,
                "session_valid": is_valid,
                "last_used": account.last_used.isoformat() if account.last_used else None,
                "session_age_hours": round(session_age, 2) if session_age else None,
                "has_cookies": bool(account.cookies),
                "has_session_data": bool(account.session_data),
                "daily_requests": account.daily_requests_count,
                "success_rate": account.success_rate
            })
        
        # Calculate summary statistics
        total_accounts = len(session_statuses)
        valid_sessions = sum(1 for s in session_statuses if s["session_valid"])
        active_accounts = sum(1 for s in session_statuses if s["status"] == "active")
        
        return {
            "accounts": session_statuses,
            "summary": {
                "total_accounts": total_accounts,
                "active_accounts": active_accounts,
                "valid_sessions": valid_sessions,
                "session_success_rate": round((valid_sessions / total_accounts * 100), 2) if total_accounts > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting accounts session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@api_router.post("/accounts/initialize-real-accounts")
async def initialize_real_accounts():
    """Initialize the database with real YouTube accounts for login automation"""
    try:
        real_accounts = [
            {
                "email": "ksmedia.project2@gmail.com",
                "password": "1CRrevenue"
            },
            {
                "email": "ksmedia.project3@gmail.com",
                "password": "1CRrevenue"
            },
            {
                "email": "ksmedia.project4@gmail.com",
                "password": "1CRrevenue"
            }
        ]
        
        # Clear existing accounts (if any)
        await db.youtube_accounts.delete_many({})
        
        added_accounts = []
        
        for account_data in real_accounts:
            account = YouTubeAccount(
                email=account_data["email"],
                password=account_data["password"],
                status="active"
            )
            
            await db.youtube_accounts.insert_one(account.dict())
            added_accounts.append(account.email)
            
            logger.info(f"Added real YouTube account: {account.email}")
        
        await send_discord_notification(f"🎯 **Real YouTube Accounts Initialized** \n📧 Accounts: {', '.join(added_accounts)}\n🔐 Status: Ready for login automation")
        
        return {
            "message": "Real YouTube accounts initialized successfully",
            "accounts_added": added_accounts,
            "total_accounts": len(added_accounts)
        }
        
    except Exception as e:
        logger.error(f"Error initializing real accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/accounts/{account_id}/login")
async def test_account_login(account_id: str):
    """Test login for a specific YouTube account"""
    try:
        # Get account from database
        account_doc = await db.youtube_accounts.find_one({"id": account_id})
        if not account_doc:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account = YouTubeAccount(**account_doc)
        
        # Attempt login
        success, message = await login_to_youtube(account)
        
        return {
            "account_id": account_id,
            "email": account.email,
            "login_success": success,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing account login {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/accounts/{account_id}/session/validate")
async def validate_account_session(account_id: str):
    """Validate existing session for a YouTube account"""
    try:
        # Get account from database
        account_doc = await db.youtube_accounts.find_one({"id": account_id})
        if not account_doc:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account = YouTubeAccount(**account_doc)
        
        # Validate session
        is_valid = await validate_session(account)
        
        return {
            "account_id": account_id,
            "email": account.email,
            "session_valid": is_valid,
            "last_used": account.last_used.isoformat() if account.last_used else None,
            "has_cookies": bool(account.cookies),
            "has_session_data": bool(account.session_data),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating account session {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# STEP 5: ACCOUNT HEALTH MONITORING API ENDPOINTS
# =============================================================================

@api_router.get("/accounts/{account_id}/health")
async def check_account_health_endpoint(account_id: str):
    """Get comprehensive health check for a specific account"""
    try:
        health_report = await check_account_health(account_id)
        
        return {
            "message": "Account health check completed",
            "health_report": health_report,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking account health {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/accounts/health/monitor-all")
async def monitor_all_accounts_endpoint():
    """Monitor health of all accounts and return comprehensive summary"""
    try:
        monitoring_summary = await monitor_all_accounts()
        
        return {
            "message": "All accounts monitoring completed",
            "monitoring_summary": monitoring_summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error monitoring all accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/accounts/{account_id}/auto-switch")
async def auto_switch_account_endpoint(account_id: str, reason: str = "manual_request"):
    """Trigger automatic account switching for a problematic account"""
    try:
        new_account = await auto_switch_account(account_id, reason)
        
        if new_account:
            return {
                "message": "Account switched successfully",
                "old_account_id": account_id,
                "new_account": {
                    "id": new_account.id,
                    "email": new_account.email,
                    "status": new_account.status,
                    "success_rate": new_account.success_rate
                },
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "message": "No healthy accounts available for switching",
                "old_account_id": account_id,
                "new_account": None,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error auto-switching account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/accounts/healthiest")
async def get_healthiest_account_endpoint():
    """Get the account with the best health metrics"""
    try:
        healthiest_account = await get_healthiest_available_account()
        
        if healthiest_account:
            return {
                "message": "Healthiest account retrieved successfully",
                "account": {
                    "id": healthiest_account.id,
                    "email": healthiest_account.email,
                    "status": healthiest_account.status,
                    "success_rate": healthiest_account.success_rate,
                    "daily_requests_count": healthiest_account.daily_requests_count,
                    "last_used": healthiest_account.last_used.isoformat() if healthiest_account.last_used else None
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="No healthy accounts available")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting healthiest account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/accounts/{account_id}/cooldown")
async def apply_account_cooldown_endpoint(account_id: str, cooldown_minutes: int = None):
    """Apply cooldown period to an account"""
    try:
        await apply_account_cooldown(account_id, cooldown_minutes)
        
        return {
            "message": f"Cooldown applied successfully",
            "account_id": account_id,
            "cooldown_minutes": cooldown_minutes or ACCOUNT_COOLDOWN_MINUTES,
            "cooldown_until": (datetime.now(timezone.utc) + timedelta(minutes=cooldown_minutes or ACCOUNT_COOLDOWN_MINUTES)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error applying cooldown to account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/accounts/{account_id}/usage-logs")
async def get_account_usage_logs_endpoint(account_id: str, limit: int = 50, skip: int = 0):
    """Get usage logs for a specific account"""
    try:
        logs_cursor = db.account_usage_logs.find({
            "account_id": account_id
        }).sort("timestamp", -1).skip(skip).limit(limit)
        
        logs = await logs_cursor.to_list(limit)
        
        return {
            "message": "Usage logs retrieved successfully",
            "account_id": account_id,
            "logs": logs,
            "count": len(logs),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting usage logs for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# STEP 6: ANTI-DETECTION BROWSER API ENDPOINTS  
# =============================================================================

@api_router.post("/browser/stealth-session/create")
async def create_stealth_session_endpoint(account_id: str, use_proxy: bool = True, session_type: str = "youtube_scraping"):
    """Create an enhanced anti-detection browser session"""
    try:
        session_info = await create_enhanced_stealth_session(account_id, use_proxy, session_type)
        
        # We can't return browser objects, so return session metadata
        return {
            "message": "Stealth session created successfully",
            "session_id": session_info["session_id"],
            "account_id": account_id,
            "fingerprint": {
                "user_agent": session_info["fingerprint"]["user_agent"][:100] + "...",
                "viewport": session_info["fingerprint"]["viewport"],
                "timezone": session_info["fingerprint"]["timezone"],
                "language": session_info["fingerprint"]["language"]
            },
            "proxy_info": {
                "enabled": use_proxy,
                "location": session_info["proxy_config"].location if session_info["proxy_config"] else None,
                "ip": session_info["proxy_config"].ip if session_info["proxy_config"] else None
            } if use_proxy else {"enabled": False},
            "session_type": session_type,
            "created_at": session_info["created_at"].isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating stealth session for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/browser/fingerprint/generate")
async def generate_browser_fingerprint_endpoint():
    """Generate a new randomized browser fingerprint"""
    try:
        fingerprint = get_random_fingerprint()
        
        return {
            "message": "Browser fingerprint generated successfully",
            "fingerprint": fingerprint,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating browser fingerprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/browser/user-agents")
async def get_available_user_agents_endpoint():
    """Get list of available user agents for rotation"""
    try:
        return {
            "message": "User agents retrieved successfully",
            "user_agents": EXTENDED_USER_AGENTS,
            "count": len(EXTENDED_USER_AGENTS),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting user agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/browser/viewports")
async def get_available_viewports_endpoint():
    """Get list of available viewport configurations"""
    try:
        return {
            "message": "Viewports retrieved successfully",
            "viewports": BROWSER_VIEWPORTS,
            "screen_resolutions": SCREEN_RESOLUTIONS,
            "count": len(BROWSER_VIEWPORTS),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting viewports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# PHASE 3 STEP 7: AUTHENTICATED EMAIL EXTRACTION API ENDPOINTS  
# =============================================================================

@api_router.post("/email/enhanced-extraction")
async def enhanced_email_extraction_endpoint(channel_id: str):
    """Enhanced email extraction with authenticated sessions and contact button detection"""
    try:
        logger.info(f"Starting enhanced email extraction for channel: {channel_id}")
        
        results = await enhanced_authenticated_email_extraction(channel_id)
        
        return {
            "message": "Enhanced email extraction completed",
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced email extraction endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/email/check-deliverability")
async def check_email_deliverability_endpoint(email: str):
    """Check email deliverability with comprehensive validation"""
    try:
        deliverability = await check_email_deliverability(email)
        
        return {
            "message": "Email deliverability check completed",
            "email": email,
            "deliverability": deliverability,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking email deliverability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/email/extract-from-videos")
async def extract_from_video_descriptions_endpoint(channel_id: str, max_videos: int = 5):
    """Extract emails from channel's recent video descriptions"""
    try:
        logger.info(f"Extracting emails from video descriptions for: {channel_id}")
        
        if max_videos > 10:
            max_videos = 10  # Limit for performance
            
        emails = await extract_emails_from_video_descriptions(channel_id, max_videos)
        
        return {
            "message": "Video description email extraction completed",
            "channel_id": channel_id,
            "emails_found": emails,
            "videos_checked": max_videos,
            "total_emails": len(emails),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error extracting from video descriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/email/test-contact-buttons")
async def test_contact_button_detection_endpoint(channel_id: str):
    """Test contact button detection on a channel's about page"""
    try:
        logger.info(f"Testing contact button detection for: {channel_id}")
        
        email, content = await scrape_channel_about_page_with_contact_buttons(channel_id)
        
        return {
            "message": "Contact button detection test completed",
            "channel_id": channel_id,
            "email_found": email,
            "content_preview": content[:300] if content else None,
            "content_length": len(content) if content else 0,
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing contact button detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/browser/test-stealth")
async def test_stealth_browser_endpoint(account_id: str):
    """Test stealth browser functionality with bot detection checks"""
    try:
        logger.info(f"Testing stealth browser for account {account_id}")
        
        # Create stealth session
        session_info = await create_enhanced_stealth_session(account_id, True, "stealth_test")
        
        page = session_info["page"]
        
        # Test stealth browsing on various sites
        test_results = {
            "account_id": account_id,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
        
        test_urls = [
            "https://www.whatismybrowser.com/",
            "https://www.youtube.com/",
            "https://httpbin.org/user-agent"
        ]
        
        for test_url in test_urls:
            try:
                await page.goto(test_url, wait_until="networkidle", timeout=15000)
                await page.wait_for_timeout(2000)
                
                # Basic bot detection checks
                page_content = await page.content()
                bot_indicators = ["webdriver", "automation", "selenium", "playwright"]
                
                detected_indicators = [indicator for indicator in bot_indicators if indicator.lower() in page_content.lower()]
                
                test_result = {
                    "url": test_url,
                    "success": len(detected_indicators) == 0,
                    "detected_indicators": detected_indicators,
                    "user_agent": session_info["fingerprint"]["user_agent"][:50] + "..."
                }
                
                test_results["details"].append(test_result)
                
                if test_result["success"]:
                    test_results["tests_passed"] += 1
                else:
                    test_results["tests_failed"] += 1
                    
            except Exception as test_error:
                test_results["details"].append({
                    "url": test_url,
                    "success": False,
                    "error": str(test_error)
                })
                test_results["tests_failed"] += 1
        
        # Clean up
        await session_info["browser"].close()
        
        test_results["success_rate"] = (test_results["tests_passed"] / len(test_urls)) * 100
        
        return {
            "message": "Stealth browser test completed",
            "results": test_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing stealth browser: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# PHASE 3 STEP 8: ADVANCED EMAIL DETECTION STRATEGIES
# =============================================================================

async def extract_social_media_links(page_content: str) -> list:
    """
    Extract social media links and website URLs from content
    Returns list of social media profiles and websites
    """
    try:
        social_patterns = {
            "instagram": r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9_\.]+)",
            "twitter": r"(?:https?://)?(?:www\.)?(?:twitter|x)\.com/([A-Za-z0-9_]+)",
            "tiktok": r"(?:https?://)?(?:www\.)?tiktok\.com/@?([A-Za-z0-9_\.]+)",
            "linkedin": r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/([A-Za-z0-9_\-]+)",
            "facebook": r"(?:https?://)?(?:www\.)?facebook\.com/([A-Za-z0-9_\.]+)",
            "youtube": r"(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|@)([A-Za-z0-9_\-]+)",
            "twitch": r"(?:https?://)?(?:www\.)?twitch\.tv/([A-Za-z0-9_]+)",
            "discord": r"(?:https?://)?(?:www\.)?discord\.gg/([A-Za-z0-9]+)",
            "website": r"(?:https?://)?([\w\-]+\.[\w\-]+\.?[\w]*\.?[\w]*)"
        }
        
        found_links = []
        
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                # Clean and validate
                if match and len(match) > 2:
                    # Skip common false positives
                    false_positives = ["www", "com", "org", "net", "example", "localhost"]
                    if not any(fp in match.lower() for fp in false_positives):
                        found_links.append({
                            "platform": platform,
                            "username_or_domain": match,
                            "full_url": f"https://{platform}.com/{match}" if platform != "website" else f"https://{match}"
                        })
        
        return found_links
        
    except Exception as e:
        logger.error(f"Error extracting social media links: {e}")
        return []

async def extract_emails_from_channel_comments(channel_id: str, max_videos: int = 3) -> list:
    """
    Extract emails from channel owner's replies in comments
    """
    try:
        logger.info(f"Extracting emails from channel owner comments: {channel_id}")
        
        # Get healthiest account for comment scraping
        account = await get_healthiest_available_account()
        if not account:
            logger.warning("No healthy account available for comment extraction")
            return []
        
        session_info = await create_enhanced_stealth_session(
            account.id, 
            use_proxy=True, 
            session_type="comment_scraping"
        )
        
        page = session_info["page"]
        found_emails = []
        
        # Get channel's recent videos
        videos = await get_channel_videos(channel_id, max_videos)
        
        if not videos:
            logger.warning(f"No videos found for channel: {channel_id}")
            return []
        
        for video in videos[:max_videos]:
            try:
                video_id = video.get('video_id')
                if not video_id:
                    continue
                    
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info(f"Scraping comments from: {video_url}")
                
                await simulate_human_behavior(page, (1, 3))
                await page.goto(video_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(random.randint(3000, 5000))
                
                # Scroll to comments section
                try:
                    await page.mouse.wheel(0, 1000)
                    await page.wait_for_timeout(random.randint(2000, 4000))
                    
                    # Wait for comments to load
                    await page.wait_for_selector("ytd-comments-header-renderer", timeout=10000)
                    
                    # Scroll to load more comments
                    for _ in range(3):  # Limited scrolling for performance
                        await page.mouse.wheel(0, 800)
                        await page.wait_for_timeout(random.randint(1500, 3000))
                    
                except Exception as scroll_error:
                    logger.debug(f"Could not scroll to comments: {scroll_error}")
                
                # Extract channel owner's comment replies
                try:
                    # Look for channel owner replies (they have a special badge)
                    owner_comment_selectors = [
                        "ytd-comment-thread-renderer [author-is-channel-owner] #content-text",
                        "ytd-comment-thread-renderer .creator-heart-button ~ #content-text",
                        "ytd-comment-thread-renderer [class*='owner'] #content-text",
                        "ytd-comment-thread-renderer [class*='creator'] #content-text"
                    ]
                    
                    comment_texts = []
                    
                    for selector in owner_comment_selectors:
                        try:
                            elements = await page.query_selector_all(selector)
                            for element in elements[:10]:  # Limit to first 10 owner comments
                                comment_text = await element.inner_text()
                                if comment_text and comment_text not in comment_texts:
                                    comment_texts.append(comment_text)
                        except:
                            continue
                    
                    # Extract emails from owner comments
                    for comment_text in comment_texts:
                        email = extract_email_from_text(comment_text)
                        if email:
                            # Check email deliverability
                            deliverability = await check_email_deliverability(email)
                            
                            email_data = {
                                "email": email,
                                "source": "channel_owner_comment",
                                "source_url": video_url,
                                "video_title": video.get('title', ''),
                                "context": comment_text[:200],
                                "deliverability": deliverability,
                                "confidence": deliverability.get("confidence", 0) * 0.6  # 60% confidence for comments
                            }
                            
                            found_emails.append(email_data)
                            logger.info(f"Found email in channel owner comment: {email}")
                    
                except Exception as comment_error:
                    logger.debug(f"Error extracting owner comments: {comment_error}")
                
                # Log usage
                await log_account_usage_pattern(
                    account.id,
                    "comment_scraping",
                    True,
                    {
                        "video_id": video_id,
                        "channel_id": channel_id,
                        "comments_checked": len(comment_texts) if 'comment_texts' in locals() else 0,
                        "email_found": len([e for e in found_emails if e["source_url"] == video_url]) > 0
                    }
                )
                
            except Exception as video_error:
                logger.error(f"Error scraping comments from video {video.get('video_id', 'unknown')}: {video_error}")
                continue
        
        # Clean up
        await session_info["browser"].close()
        
        # Remove duplicates
        unique_emails = []
        seen_emails = set()
        
        for email_data in found_emails:
            email = email_data["email"]
            if email not in seen_emails:
                seen_emails.add(email)
                unique_emails.append(email_data)
        
        logger.info(f"Extracted {len(unique_emails)} unique emails from channel owner comments")
        return unique_emails
        
    except Exception as e:
        logger.error(f"Error extracting emails from channel comments: {e}")
        return []

def calculate_email_confidence_score(email_data: dict) -> float:
    """
    Calculate confidence score based on source reliability and other factors
    """
    try:
        base_confidence = 0
        source = email_data.get("source", "unknown")
        deliverability = email_data.get("deliverability", {})
        context = email_data.get("context", "")
        
        # Base confidence by source reliability
        source_confidence = {
            "about_page_authenticated": 100,
            "about_page": 80,
            "video_description": 70,
            "channel_owner_comment": 60,
            "social_media_follow": 50,
            "community_post": 65,
            "unknown": 30
        }
        
        base_confidence = source_confidence.get(source, 30)
        
        # Deliverability factor
        deliverability_score = deliverability.get("confidence", 0)
        deliverability_factor = deliverability_score / 100.0
        
        # Context relevance factor
        business_keywords = ["business", "contact", "inquiry", "collaboration", "work", "email", "reach out"]
        context_factor = 1.0
        
        if context:
            context_lower = context.lower()
            business_matches = sum(1 for keyword in business_keywords if keyword in context_lower)
            if business_matches > 0:
                context_factor = min(1.2, 1.0 + (business_matches * 0.1))  # Max 20% boost
        
        # Email format quality factor
        email = email_data.get("email", "")
        format_factor = 1.0
        
        if email:
            # Professional email indicators
            professional_domains = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com"]
            custom_domain = not any(domain in email for domain in professional_domains)
            
            if custom_domain:
                format_factor = 1.1  # 10% boost for custom domain
            
            # Check for professional naming patterns
            local_part = email.split("@")[0] if "@" in email else ""
            if any(keyword in local_part.lower() for keyword in ["business", "contact", "info", "hello", "support"]):
                format_factor = max(format_factor, 1.15)  # 15% boost for business naming
        
        # Calculate final confidence
        final_confidence = base_confidence * deliverability_factor * context_factor * format_factor
        
        # Ensure it doesn't exceed 100
        return min(100.0, final_confidence)
        
    except Exception as e:
        logger.error(f"Error calculating confidence score: {e}")
        return 0.0

async def comprehensive_email_detection(channel_id: str) -> dict:
    """
    Comprehensive email detection using all available strategies
    """
    try:
        logger.info(f"Starting comprehensive email detection for: {channel_id}")
        
        results = {
            "channel_id": channel_id,
            "emails_found": [],
            "social_media_links": [],
            "sources_checked": [],
            "total_confidence": 0,
            "best_email": None,
            "detection_summary": {}
        }
        
        # Step 1: Enhanced authenticated extraction (from Step 7)
        step7_results = await enhanced_authenticated_email_extraction(channel_id)
        results["emails_found"].extend(step7_results.get("emails_found", []))
        results["sources_checked"].extend(step7_results.get("sources_checked", []))
        
        # Step 2: Channel owner comment replies
        comment_emails = await extract_emails_from_channel_comments(channel_id, max_videos=3)
        results["emails_found"].extend(comment_emails)
        if comment_emails:
            results["sources_checked"].append("channel_owner_comments")
        
        # Step 3: Extract social media links from all gathered content
        all_content = ""
        for email_data in results["emails_found"]:
            context = email_data.get("context", "")
            if context:
                all_content += f" {context}"
        
        if all_content:
            social_links = await extract_social_media_links(all_content)
            results["social_media_links"] = social_links
            
            # TODO: In future, follow social media links to extract additional emails
            # This would require additional API integrations for each platform
        
        # Step 4: Recalculate confidence scores for all emails
        for email_data in results["emails_found"]:
            email_data["confidence"] = calculate_email_confidence_score(email_data)
        
        # Step 5: Remove duplicates and sort by confidence
        unique_emails = []
        seen_emails = set()
        
        for email_data in results["emails_found"]:
            email = email_data["email"]
            if email not in seen_emails:
                seen_emails.add(email)
                unique_emails.append(email_data)
        
        results["emails_found"] = sorted(unique_emails, key=lambda x: x["confidence"], reverse=True)
        
        # Step 6: Set best email and calculate overall metrics
        if results["emails_found"]:
            results["best_email"] = results["emails_found"][0]
            results["total_confidence"] = results["best_email"]["confidence"]
        
        # Step 7: Create comprehensive summary
        results["detection_summary"] = {
            "total_emails_found": len(results["emails_found"]),
            "unique_emails": len(set([e["email"] for e in results["emails_found"]])),
            "sources_checked": len(results["sources_checked"]),
            "social_media_links": len(results["social_media_links"]),
            "highest_confidence": results["total_confidence"],
            "deliverable_emails": len([e for e in results["emails_found"] if e["deliverability"]["valid"]]),
            "confidence_breakdown": {
                "high_confidence_80_plus": len([e for e in results["emails_found"] if e["confidence"] >= 80]),
                "medium_confidence_50_79": len([e for e in results["emails_found"] if 50 <= e["confidence"] < 80]),
                "low_confidence_below_50": len([e for e in results["emails_found"] if e["confidence"] < 50])
            }
        }
        
        logger.info(f"Comprehensive detection complete: {results['detection_summary']}")
        return results
        
    except Exception as e:
        logger.error(f"Error in comprehensive email detection: {e}")
        return {
            "channel_id": channel_id,
            "emails_found": [],
            "social_media_links": [],
            "sources_checked": [],
            "total_confidence": 0,
            "best_email": None,
            "detection_summary": {"error": str(e)},
            "error": str(e)
        }

# =============================================================================
# PHASE 3 STEP 8: ADVANCED EMAIL DETECTION API ENDPOINTS  
# =============================================================================

@api_router.post("/email/comprehensive-detection")
async def comprehensive_email_detection_endpoint(channel_id: str):
    """Comprehensive email detection using all available strategies"""
    try:
        logger.info(f"Starting comprehensive email detection for: {channel_id}")
        
        results = await comprehensive_email_detection(channel_id)
        
        return {
            "message": "Comprehensive email detection completed",
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in comprehensive detection endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/email/extract-from-comments")
async def extract_from_comments_endpoint(channel_id: str, max_videos: int = 3):
    """Extract emails from channel owner's comment replies"""
    try:
        logger.info(f"Extracting emails from channel owner comments: {channel_id}")
        
        if max_videos > 5:
            max_videos = 5  # Limit for performance
            
        emails = await extract_emails_from_channel_comments(channel_id, max_videos)
        
        return {
            "message": "Channel owner comment extraction completed",
            "channel_id": channel_id,
            "emails_found": emails,
            "videos_checked": max_videos,
            "total_emails": len(emails),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error extracting from comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/social-media/extract-links")
async def extract_social_media_links_endpoint(text: str):
    """Extract social media links from provided text content"""
    try:
        links = await extract_social_media_links(text)
        
        return {
            "message": "Social media link extraction completed",
            "social_media_links": links,
            "total_links": len(links),
            "platforms_found": list(set([link["platform"] for link in links])),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error extracting social media links: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/email/calculate-confidence")
async def calculate_confidence_endpoint(email_data: dict):
    """Calculate confidence score for email based on source and context"""
    try:
        confidence = calculate_email_confidence_score(email_data)
        
        return {
            "message": "Confidence score calculated",
            "email": email_data.get("email"),
            "confidence_score": confidence,
            "confidence_level": (
                "high" if confidence >= 80 else
                "medium" if confidence >= 50 else
                "low"
            ),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error calculating confidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/email/detection-stats")
async def get_detection_statistics():
    """Get overall email detection statistics from database"""
    try:
        # Get statistics from main_leads and no_email_leads collections
        main_leads_count = await db.main_leads.count_documents({})
        no_email_leads_count = await db.no_email_leads.count_documents({})
        
        # Email success rate
        total_leads = main_leads_count + no_email_leads_count
        success_rate = (main_leads_count / total_leads * 100) if total_leads > 0 else 0
        
        # Get recent extractions with confidence scores
        recent_leads = await db.main_leads.find(
            {"email": {"$exists": True, "$ne": None}},
            {"email": 1, "extraction_method": 1, "confidence_score": 1, "processing_timestamp": 1}
        ).sort("processing_timestamp", -1).limit(100).to_list(length=100)
        
        # Calculate confidence distribution
        confidence_distribution = {"high": 0, "medium": 0, "low": 0}
        for lead in recent_leads:
            confidence = lead.get("confidence_score", 0)
            if confidence >= 80:
                confidence_distribution["high"] += 1
            elif confidence >= 50:
                confidence_distribution["medium"] += 1
            else:
                confidence_distribution["low"] += 1
        
        return {
            "message": "Detection statistics retrieved",
            "statistics": {
                "total_leads_processed": total_leads,
                "emails_found": main_leads_count,
                "no_emails_found": no_email_leads_count,
                "success_rate_percentage": round(success_rate, 2),
                "confidence_distribution": confidence_distribution,
                "recent_extractions": len(recent_leads)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting detection statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# SMART QUEUE PROCESSING & ERROR RECOVERY API ENDPOINTS
# =============================================================================

@api_router.post("/queue/smart-process")
async def start_smart_queue_processing():
    """Start intelligent queue processing with health-based account selection"""
    try:
        result = await smart_queue_processor()
        return {
            "message": "Smart queue processing completed",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting smart queue processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================================
# PHASE 5 STEP 11: PERFORMANCE MONITORING DASHBOARD
# ===============================================

async def get_comprehensive_performance_metrics() -> Dict[str, Any]:
    """Get comprehensive performance metrics for dashboard"""
    try:
        current_time = datetime.now(timezone.utc)
        
        # Time ranges for analysis
        last_hour = current_time - timedelta(hours=1)
        last_24h = current_time - timedelta(hours=24)
        last_7days = current_time - timedelta(days=7)
        
        metrics = {
            "timestamp": current_time,
            "system_performance": {},
            "account_performance": {},
            "proxy_performance": {},
            "queue_performance": {},
            "cost_tracking": {},
            "reliability_metrics": {},
            "alerts": []
        }
        
        # System Performance Metrics
        total_accounts = await db.youtube_accounts.count_documents({})
        active_accounts = await db.youtube_accounts.count_documents({"status": "active"})
        total_proxies = await db.proxy_pool.count_documents({})
        healthy_proxies = await db.proxy_pool.count_documents({
            "status": "active", 
            "health_status": "healthy"
        })
        
        # Queue performance
        total_requests = await db.scraping_queue.count_documents({})
        completed_requests = await db.scraping_queue.count_documents({"status": "completed"})
        failed_requests = await db.scraping_queue.count_documents({"status": "failed"})
        
        # Success rate calculation
        success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        metrics["system_performance"] = {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "account_availability_rate": (active_accounts / total_accounts * 100) if total_accounts > 0 else 0,
            "total_proxies": total_proxies,
            "healthy_proxies": healthy_proxies,
            "proxy_health_rate": (healthy_proxies / total_proxies * 100) if total_proxies > 0 else 0,
            "overall_success_rate": success_rate,
            "total_processed": completed_requests,
            "system_uptime": "99.9%"  # Placeholder - can be calculated based on service logs
        }
        
        # Account Performance Analysis
        account_metrics = []
        accounts_cursor = db.youtube_accounts.find({})
        async for account in accounts_cursor:
            # Calculate account-specific success rate
            account_total = await db.scraping_queue.count_documents({"account_id": account["id"]})
            account_success = await db.scraping_queue.count_documents({
                "account_id": account["id"], 
                "status": "completed"
            })
            account_success_rate = (account_success / account_total * 100) if account_total > 0 else 0
            
            # Recent activity
            recent_activity = await db.scraping_queue.count_documents({
                "account_id": account["id"],
                "processing_started_at": {"$gte": last_24h}
            })
            
            account_metrics.append({
                "account_id": account["id"],
                "email": account["email"],
                "status": account["status"],
                "success_rate": round(account_success_rate, 2),
                "total_requests": account_total,
                "recent_activity_24h": recent_activity,
                "last_used": account.get("last_used")
            })
        
        metrics["account_performance"] = {
            "accounts": account_metrics,
            "top_performing": sorted(account_metrics, key=lambda x: x["success_rate"], reverse=True)[:5],
            "needs_attention": [acc for acc in account_metrics if acc["success_rate"] < 70]
        }
        
        # Proxy Performance Analysis  
        proxy_metrics = []
        proxies_cursor = db.proxy_pool.find({})
        async for proxy in proxies_cursor:
            # Calculate proxy success rate
            proxy_requests = await db.scraping_queue.count_documents({"proxy_id": proxy["id"]})
            proxy_success = await db.scraping_queue.count_documents({
                "proxy_id": proxy["id"],
                "status": "completed"
            })
            proxy_success_rate = (proxy_success / proxy_requests * 100) if proxy_requests > 0 else 0
            
            proxy_metrics.append({
                "proxy_id": proxy["id"],
                "ip": proxy["ip"],
                "port": proxy["port"],
                "status": proxy["status"],
                "health_status": proxy["health_status"],
                "success_rate": round(proxy_success_rate, 2),
                "avg_response_time": proxy.get("response_time_avg", 0),
                "total_requests": proxy_requests,
                "location": proxy.get("location", "Unknown")
            })
            
        metrics["proxy_performance"] = {
            "proxies": proxy_metrics,
            "fastest_proxies": sorted(proxy_metrics, key=lambda x: x["avg_response_time"])[:5],
            "most_reliable": sorted(proxy_metrics, key=lambda x: x["success_rate"], reverse=True)[:5]
        }
        
        # API Usage & Processing Time Tracking
        # Calculate average processing times
        pipeline = [
            {"$match": {
                "status": "completed",
                "processing_started_at": {"$exists": True},
                "completed_at": {"$exists": True}
            }},
            {"$project": {
                "processing_duration": {
                    "$subtract": ["$completed_at", "$processing_started_at"]
                }
            }},
            {"$group": {
                "_id": None,
                "avg_processing_time": {"$avg": "$processing_duration"},
                "min_processing_time": {"$min": "$processing_duration"},
                "max_processing_time": {"$max": "$processing_duration"},
                "total_requests": {"$sum": 1}
            }}
        ]
        
        processing_stats = await db.scraping_queue.aggregate(pipeline).to_list(1)
        processing_data = processing_stats[0] if processing_stats else {}
        
        # API usage metrics
        api_usage_last_hour = await db.scraping_queue.count_documents({
            "processing_started_at": {"$gte": last_hour}
        })
        api_usage_last_24h = await db.scraping_queue.count_documents({
            "processing_started_at": {"$gte": last_24h}
        })
        
        metrics["cost_tracking"] = {
            "api_requests_last_hour": api_usage_last_hour,
            "api_requests_last_24h": api_usage_last_24h,
            "avg_processing_time_ms": processing_data.get("avg_processing_time", 0),
            "min_processing_time_ms": processing_data.get("min_processing_time", 0),
            "max_processing_time_ms": processing_data.get("max_processing_time", 0),
            "total_processing_cost_estimate": api_usage_last_24h * 0.001,  # Example cost calculation
            "proxy_cost_estimate": len(proxy_metrics) * 5.0,  # Example: $5 per proxy per day
            "captcha_solve_cost": 0  # To be calculated based on 2captcha usage
        }
        
        # Reliability Metrics
        reliability_threshold = 85.0  # 85% success rate threshold
        
        # Error analysis
        recent_errors = await db.scraping_queue.count_documents({
            "status": "failed",
            "completed_at": {"$gte": last_24h}
        })
        
        reliability_score = max(0, 100 - (recent_errors / max(api_usage_last_24h, 1) * 100))
        
        metrics["reliability_metrics"] = {
            "overall_reliability_score": round(reliability_score, 2),
            "error_rate_24h": round((recent_errors / max(api_usage_last_24h, 1) * 100), 2),
            "availability_percentage": round((active_accounts / max(total_accounts, 1) * 100), 2),
            "system_stability": "Stable" if reliability_score > reliability_threshold else "Needs Attention",
            "mtbf_hours": 24.0,  # Mean Time Between Failures - placeholder
            "mttr_minutes": 15.0  # Mean Time To Recovery - placeholder
        }
        
        # Alert Generation
        alerts = []
        
        # System health alerts
        if success_rate < 70:
            alerts.append({
                "type": "error",
                "message": f"Low success rate: {success_rate:.1f}% (threshold: 70%)",
                "timestamp": current_time,
                "severity": "high"
            })
            
        if active_accounts < total_accounts * 0.5:
            alerts.append({
                "type": "warning", 
                "message": f"Low account availability: {active_accounts}/{total_accounts} accounts active",
                "timestamp": current_time,
                "severity": "medium"
            })
            
        if healthy_proxies < total_proxies * 0.3:
            alerts.append({
                "type": "error",
                "message": f"Critical proxy shortage: {healthy_proxies}/{total_proxies} proxies healthy",
                "timestamp": current_time,
                "severity": "high"
            })
            
        # Performance alerts
        if processing_data.get("avg_processing_time", 0) > 30000:  # 30 seconds
            alerts.append({
                "type": "warning",
                "message": f"Slow processing detected: {processing_data.get('avg_processing_time', 0)/1000:.1f}s average",
                "timestamp": current_time,
                "severity": "medium"
            })
            
        metrics["alerts"] = alerts
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {"error": str(e), "timestamp": datetime.now(timezone.utc)}

@api_router.get("/monitoring/performance-dashboard")
async def get_performance_dashboard():
    """Get comprehensive performance dashboard data"""
    try:
        dashboard_data = await get_comprehensive_performance_metrics()
        return dashboard_data
    except Exception as e:
        logger.error(f"Error getting performance dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def send_performance_alert(alert: Dict[str, Any]):
    """Send performance alert to Discord"""
    try:
        if not DISCORD_WEBHOOK:
            return
            
        severity_colors = {
            "high": 0xFF0000,    # Red
            "medium": 0xFFA500,  # Orange  
            "low": 0xFFFF00      # Yellow
        }
        
        severity_emojis = {
            "high": "🚨",
            "medium": "⚠️", 
            "low": "ℹ️"
        }
        
        embed = {
            "title": f"{severity_emojis.get(alert['severity'], '📊')} System Alert - {alert['type'].title()}",
            "description": alert['message'],
            "color": severity_colors.get(alert['severity'], 0x0099FF),
            "timestamp": alert['timestamp'].isoformat(),
            "fields": [
                {
                    "name": "Severity",
                    "value": alert['severity'].title(),
                    "inline": True
                },
                {
                    "name": "System",
                    "value": "YouTube Lead Generation",
                    "inline": True
                }
            ]
        }
        
        payload = {
            "embeds": [embed]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK, json=payload) as response:
                if response.status == 200:
                    logger.info(f"✅ Alert sent to Discord: {alert['message']}")
                else:
                    logger.error(f"❌ Failed to send alert to Discord: {response.status}")
                    
    except Exception as e:
        logger.error(f"Error sending performance alert: {e}")

@api_router.get("/monitoring/alerts/current")
async def get_current_alerts():
    """Get current system alerts"""
    try:
        metrics = await get_comprehensive_performance_metrics()
        return {"alerts": metrics.get("alerts", [])}
    except Exception as e:
        logger.error(f"Error getting current alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/queue/processing-status")
async def get_queue_processing_status():
    """Get detailed queue processing status and metrics"""
    try:
        # Current processing status
        concurrent_processing = await db.scraping_queue.count_documents({"status": "processing"})
        pending_requests = await db.scraping_queue.count_documents({"status": "pending"})
        failed_requests = await db.scraping_queue.count_documents({"status": "failed"})
        
        # Available resources
        healthy_accounts = 0
        available_proxies = 0
        
        # Count healthy accounts
        current_time = datetime.now(timezone.utc)
        accounts_cursor = db.youtube_accounts.find({
            "status": {"$nin": ["banned", "rate_limited"]},
            "$or": [
                {"cooldown_until": {"$exists": False}},
                {"cooldown_until": {"$lte": current_time}}
            ]
        })
        
        async for account in accounts_cursor:
            if not await is_account_rate_limited(account["id"]):
                healthy_accounts += 1
        
        # Count available proxies
        available_proxies = await db.proxy_pool.count_documents({
            "status": "active",
            "health_status": "healthy",
            "$or": [
                {"cooldown_until": {"$exists": False}},
                {"cooldown_until": {"$lte": current_time}}
            ]
        })
        
        # Recent processing history
        recent_completions = await db.scraping_queue.count_documents({
            "status": "completed",
            "completed_at": {"$gte": current_time - timedelta(hours=1)}
        })
        
        return {
            "message": "Queue processing status retrieved",
            "status": {
                "concurrent_processing": concurrent_processing,
                "max_concurrent": MAX_CONCURRENT_PROCESSING,
                "available_slots": MAX_CONCURRENT_PROCESSING - concurrent_processing,
                "pending_requests": pending_requests,
                "failed_requests": failed_requests,
                "healthy_accounts": healthy_accounts,
                "available_proxies": available_proxies,
                "recent_completions": recent_completions,
                "processing_capacity": f"{concurrent_processing}/{MAX_CONCURRENT_PROCESSING}"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting queue processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/queue/retry-failed")
async def retry_failed_requests():
    """Retry all failed requests with fresh account/proxy assignment"""
    try:
        current_time = datetime.now(timezone.utc)
        
        # Find failed requests that can be retried
        failed_requests = await db.scraping_queue.find({
            "status": "failed",
            "total_attempts": {"$lt": QUEUE_RETRY_ATTEMPTS}
        }).to_list(length=100)
        
        if not failed_requests:
            return {
                "message": "No failed requests available for retry",
                "retried_count": 0
            }
        
        retried_count = 0
        for request in failed_requests:
            # Reset request for retry with exponential backoff
            retry_delay = 5 * (2 ** (request.get("total_attempts", 0)))  # 5, 10, 20, 40 minutes
            retry_time = current_time + timedelta(minutes=retry_delay)
            
            await db.scraping_queue.update_one(
                {"id": request["id"]},
                {
                    "$set": {
                        "status": "pending",
                        "scheduled_time": retry_time,
                        "account_id": None,  # Clear for fresh assignment
                        "proxy_id": None,    # Clear for fresh assignment
                        "attempts": 0        # Reset attempts counter
                    }
                }
            )
            retried_count += 1
        
        await send_discord_notification(
            f"🔄 **Failed Requests Retry**\n"
            f"📊 Retried: {retried_count} requests\n"
            f"⏰ With exponential backoff delays"
        )
        
        return {
            "message": f"Successfully scheduled {retried_count} failed requests for retry",
            "retried_count": retried_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrying failed requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/queue/error-analysis")
async def get_queue_error_analysis():
    """Get detailed analysis of queue processing errors"""
    try:
        # Get error patterns from recent failed requests
        failed_requests = await db.scraping_queue.find({
            "status": {"$in": ["failed", "processing"]},
            "error_history": {"$exists": True}
        }).to_list(length=200)
        
        error_patterns = {}
        account_errors = {}
        proxy_errors = {}
        
        for request in failed_requests:
            error_history = request.get("error_history", [])
            for error in error_history:
                error_msg = error.get("error", "Unknown error")
                account_id = error.get("account_id")
                proxy_id = error.get("proxy_id")
                
                # Pattern analysis
                error_type = "other"
                if await detect_rate_limit_from_error(error_msg):
                    error_type = "rate_limit"
                elif await detect_account_block_from_error(error_msg):
                    error_type = "account_block"
                elif await detect_ip_block_from_error(error_msg):
                    error_type = "ip_block"
                
                error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
                
                # Account error tracking
                if account_id:
                    account_errors[account_id] = account_errors.get(account_id, 0) + 1
                
                # Proxy error tracking
                if proxy_id:
                    proxy_errors[proxy_id] = proxy_errors.get(proxy_id, 0) + 1
        
        # Find most problematic accounts and proxies
        top_problem_accounts = sorted(account_errors.items(), key=lambda x: x[1], reverse=True)[:5]
        top_problem_proxies = sorted(proxy_errors.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "message": "Queue error analysis completed",
            "analysis": {
                "error_patterns": error_patterns,
                "total_errors": sum(error_patterns.values()),
                "top_problem_accounts": [{"account_id": acc, "error_count": count} for acc, count in top_problem_accounts],
                "top_problem_proxies": [{"proxy_id": proxy, "error_count": count} for proxy, count in top_problem_proxies],
                "recommendations": await generate_error_recommendations(error_patterns, account_errors, proxy_errors)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing queue errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_error_recommendations(error_patterns: dict, account_errors: dict, proxy_errors: dict):
    """Generate recommendations based on error analysis"""
    recommendations = []
    
    # Rate limit recommendations
    if error_patterns.get("rate_limit", 0) > 10:
        recommendations.append("🕐 Consider increasing account cooldown periods due to high rate limit errors")
        recommendations.append("⚡ Add more YouTube accounts to distribute load")
    
    # Account block recommendations
    if error_patterns.get("account_block", 0) > 5:
        recommendations.append("🚫 Review account management - high account block rate detected")
        recommendations.append("🔄 Implement account rotation more frequently")
    
    # IP block recommendations
    if error_patterns.get("ip_block", 0) > 5:
        recommendations.append("🌐 Add more diverse proxy sources - IP blocks detected")
        recommendations.append("🔄 Increase proxy rotation frequency")
    
    # Account-specific recommendations
    if len(account_errors) > 0:
        avg_errors = sum(account_errors.values()) / len(account_errors)
        if avg_errors > 10:
            recommendations.append("👥 Some accounts have high error rates - consider account health review")
    
    # Proxy-specific recommendations
    if len(proxy_errors) > 0:
        avg_proxy_errors = sum(proxy_errors.values()) / len(proxy_errors)
        if avg_proxy_errors > 15:
            recommendations.append("🌍 Some proxies have high error rates - consider proxy pool cleanup")
    
    return recommendations

# Include the router in the main app
app.include_router(api_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
