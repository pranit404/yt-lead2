import os
import sys
import logging
import asyncio
import aiohttp
from datetime import datetime, timezone
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---- Logging ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---- Configuration ----
DISCORD_BOT_TOKEN = "MTM5NjU0NDUyOTMyNjI4MDgyNw.Gdso_K.UeFJxtZyCG330szkI6klM1SuIk9QB5hoxKkft0"
MONGO_URL = "mongodb://localhost:27017" 
DB_NAME = "test_database"
BACKEND_API_URL = "http://localhost:8001/api"

# Global Settings
SEND_EMAILS_ENABLED = os.environ.get('SEND_EMAILS_ENABLED', 'true').lower() == 'true'

if not DISCORD_BOT_TOKEN:
    print("❌ Please set DISCORD_BOT_TOKEN environment variable and re-run.")
    sys.exit(1)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = False

bot = commands.Bot(command_prefix="!", intents=intents)

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

@bot.event
async def on_ready():
    logging.info(f"✅ YouTube Lead Generation Bot logged in as {bot.user} (id: {bot.user.id})")
    guilds = ", ".join([g.name for g in bot.guilds]) or "(no guilds)"
    logging.info(f"Connected to guilds: {guilds}")
    logging.info("🎯 Bot is ready to receive commands!")

@bot.event
async def on_message(message):
    # Don't respond to bot messages
    if message.author.bot:
        return
    
    # Log all messages that start with !
    if message.content.startswith('!'):
        logging.info(f"📨 Received command: {message.content} from {message.author}")
    
    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    logging.exception("Command error: %s", error)
    try:
        await ctx.send(f"⚠️ Command error: {type(error).__name__}: {str(error)}")
    except Exception:
        pass

# Helper Functions
async def make_api_request(method: str, endpoint: str, data: dict = None):
    """Make API request to backend"""
    try:
        url = f"{BACKEND_API_URL}{endpoint}"
        async with aiohttp.ClientSession() as session:
            if method.upper() == "POST":
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logging.error(f"API error {response.status}: {error_text}")
                        return None
            elif method.upper() == "GET":
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logging.error(f"API error {response.status}: {error_text}")
                        return None
    except Exception as e:
        logging.error(f"API request error: {e}")
        return None

async def get_processing_status(status_id: str):
    """Get processing status from API"""
    return await make_api_request("GET", f"/lead-generation/status/{status_id}")

async def get_leads_stats():
    """Get current leads statistics"""
    try:
        main_leads = await db.main_leads.count_documents({})
        no_email_leads = await db.no_email_leads.count_documents({})
        return {"main_leads": main_leads, "no_email_leads": no_email_leads}
    except Exception as e:
        logging.error(f"Error getting leads stats: {e}")
        return {"main_leads": 0, "no_email_leads": 0}

# ---- Commands ----

@bot.command(name="start")
async def start_lead_generation(ctx, 
                              min_subs: int, 
                              max_subs: int, 
                              max_channels: int = 500,
                              max_videos: int = 2000,
                              min_frequency: float = 0.14,
                              max_frequency: float = 2.0,
                              test_mode: str = "false",
                              *keywords):
    """
    Start lead generation with comprehensive parameters
    Usage: !start <min_subs> <max_subs> [max_channels] [max_videos] [min_freq] [max_freq] [test_mode] <keywords...>
    Example: !start 10000 1000000 500 2000 0.14 2.0 false crypto trading bitcoin investment
    Example (test): !start 10000 1000000 500 2000 0.14 2.0 true crypto trading
    """
    if not keywords:
        await ctx.send("❌ Please provide at least one keyword.\n**Usage:** `!start <min_subs> <max_subs> [max_channels] [max_videos] [min_freq] [max_freq] [test_mode] <keywords...>`")
        return
    
    # Convert test_mode string to boolean
    test_mode_bool = test_mode.lower() in ['true', 'yes', '1', 'on']
    
    # Prepare request data
    request_data = {
        "keywords": list(keywords),
        "max_videos_per_keyword": max_videos,
        "max_channels": max_channels,
        "subscriber_min": min_subs,
        "subscriber_max": max_subs,
        "content_frequency_min": min_frequency,
        "content_frequency_max": max_frequency,
        "test_mode": test_mode_bool
    }
    
    # Send starting message
    embed = discord.Embed(
        title="🚀 Starting Lead Generation",
        description="Initializing YouTube lead generation process...",
        color=0x3498db,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="📋 Keywords", value=", ".join(keywords), inline=False)
    embed.add_field(name="👥 Subscriber Range", value=f"{min_subs:,} - {max_subs:,}", inline=True)
    embed.add_field(name="🎯 Max Channels", value=f"{max_channels:,}", inline=True)
    embed.add_field(name="📹 Max Videos/Keyword", value=f"{max_videos:,}", inline=True)
    embed.add_field(name="📅 Content Frequency", value=f"{min_frequency} - {max_frequency} videos/week", inline=False)
    embed.add_field(name="🧪 Test Mode", value="✅ Enabled (Reduced limits)" if test_mode_bool else "❌ Disabled", inline=True)
    embed.add_field(name="✉️ Email Sending", value="✅ Enabled" if SEND_EMAILS_ENABLED else "❌ Disabled (Extract only)", inline=True)
    
    await ctx.send(embed=embed)
    
    # Start the process
    result = await make_api_request("POST", "/lead-generation/start", request_data)
    
    if result:
        status_id = result.get("id")
        await ctx.send(f"✅ Lead generation started successfully! Status ID: `{status_id}`\nUse `!status {status_id}` to check progress.")
        
        # Start monitoring in background
        bot.loop.create_task(monitor_process(ctx, status_id))
    else:
        await ctx.send("❌ Failed to start lead generation. Please check the backend service.")

async def monitor_process(ctx, status_id: str):
    """Monitor the lead generation process and send periodic updates"""
    try:
        last_processed = 0
        last_emails_found = 0
        
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            status = await get_processing_status(status_id)
            if not status:
                break
                
            current_processed = status.get("channels_processed", 0)
            current_emails = status.get("emails_found", 0)
            
            # Send update if there's significant progress
            if current_processed > last_processed + 10 or current_emails > last_emails_found:
                embed = discord.Embed(
                    title="📊 Lead Generation Progress",
                    color=0xf39c12,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="🔍 Discovered", value=f"{status.get('channels_discovered', 0):,}", inline=True)
                embed.add_field(name="✅ Processed", value=f"{current_processed:,}", inline=True)
                embed.add_field(name="📧 Emails Found", value=f"{current_emails:,}", inline=True)
                embed.add_field(name="✉️ Emails Sent", value=f"{status.get('emails_sent', 0):,}", inline=True)
                embed.add_field(name="📈 Current Step", value=status.get('current_step', 'Processing...'), inline=False)
                
                await ctx.send(embed=embed)
                
                last_processed = current_processed
                last_emails_found = current_emails
            
            # Check if completed or failed
            if status.get("status") in ["completed", "failed"]:
                break
                
    except Exception as e:
        logging.error(f"Error monitoring process: {e}")

@bot.command(name="status")
async def check_status(ctx, status_id: str = None):
    """
    Check processing status or get overall stats
    Usage: !status [status_id]
    """
    if status_id:
        # Get specific process status
        status = await get_processing_status(status_id)
        
        if status:
            color = 0x27ae60 if status.get("status") == "completed" else 0xe74c3c if status.get("status") == "failed" else 0xf39c12
            
            embed = discord.Embed(
                title=f"📊 Processing Status: {status_id}",
                color=color,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="🔄 Status", value=status.get('status', 'unknown').upper(), inline=True)
            embed.add_field(name="📈 Current Step", value=status.get('current_step', 'N/A'), inline=True)
            embed.add_field(name="🔍 Discovered", value=f"{status.get('channels_discovered', 0):,}", inline=True)
            embed.add_field(name="✅ Processed", value=f"{status.get('channels_processed', 0):,}", inline=True)
            embed.add_field(name="📧 Emails Found", value=f"{status.get('emails_found', 0):,}", inline=True)
            embed.add_field(name="✉️ Emails Sent", value=f"{status.get('emails_sent', 0):,}", inline=True)
            
            if status.get('errors'):
                embed.add_field(name="⚠️ Errors", value=f"{len(status['errors'])} errors occurred", inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Status not found for ID: `{status_id}`")
    else:
        # Get overall stats
        stats = await get_leads_stats()
        
        embed = discord.Embed(
            title="📊 Overall Database Statistics",
            color=0x3498db,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📧 Leads with Email", value=f"{stats['main_leads']:,}", inline=True)
        embed.add_field(name="❌ Leads without Email", value=f"{stats['no_email_leads']:,}", inline=True)
        embed.add_field(name="📊 Total Leads", value=f"{stats['main_leads'] + stats['no_email_leads']:,}", inline=True)
        
        await ctx.send(embed=embed)

@bot.command(name="leads")
async def show_recent_leads(ctx, count: int = 5, lead_type: str = "email"):
    """
    Show recent leads from database
    Usage: !leads [count] [type]
    Types: email, no-email, all
    """
    try:
        if lead_type.lower() in ["email", "main"]:
            collection = db.main_leads
            title = "📧 Recent Leads with Email"
        elif lead_type.lower() in ["no-email", "noemail"]:
            collection = db.no_email_leads
            title = "❌ Recent Leads without Email"
        else:
            await ctx.send("❌ Invalid lead type. Use: `email`, `no-email`, or `all`")
            return
        
        # Get recent leads
        leads = await collection.find().sort("discovery_timestamp", -1).limit(min(count, 10)).to_list(None)
        
        if not leads:
            await ctx.send(f"No leads found in {lead_type} collection.")
            return
        
        embed = discord.Embed(
            title=title,
            color=0x27ae60 if "email" in title else 0xe67e22,
            timestamp=datetime.now(timezone.utc)
        )
        
        for i, lead in enumerate(leads, 1):
            name = f"{i}. {lead.get('channel_title', 'Unknown Channel')[:30]}"
            value = f"👥 {lead.get('subscriber_count', 0):,} subs"
            if lead.get('email'):
                value += f"\n📧 {lead['email']}"
            if lead.get('keywords_found_in'):
                value += f"\n🏷️ {', '.join(lead['keywords_found_in'][:2])}"
            
            embed.add_field(name=name, value=value, inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logging.error(f"Error showing leads: {e}")
        await ctx.send("❌ Error retrieving leads from database.")

@bot.command(name="export")
async def export_leads(ctx, lead_type: str = "email", limit: int = 100):
    """
    Export leads to text format
    Usage: !export [type] [limit]
    Types: email, no-email
    """
    try:
        if lead_type.lower() in ["email", "main"]:
            collection = db.main_leads
            filename = "leads_with_email.txt"
        elif lead_type.lower() in ["no-email", "noemail"]:
            collection = db.no_email_leads
            filename = "leads_without_email.txt"
        else:
            await ctx.send("❌ Invalid lead type. Use: `email` or `no-email`")
            return
        
        leads = await collection.find().limit(min(limit, 1000)).to_list(None)
        
        if not leads:
            await ctx.send(f"No leads found to export.")
            return
        
        # Create export content
        export_content = f"# {filename.replace('.txt', '').replace('_', ' ').title()}\n"
        export_content += f"# Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_content += f"# Total leads: {len(leads)}\n\n"
        
        for lead in leads:
            export_content += f"Channel: {lead.get('channel_title', 'Unknown')}\n"
            export_content += f"URL: {lead.get('channel_url', 'N/A')}\n"
            export_content += f"Subscribers: {lead.get('subscriber_count', 0):,}\n"
            if lead.get('email'):
                export_content += f"Email: {lead['email']}\n"
            if lead.get('keywords_found_in'):
                export_content += f"Keywords: {', '.join(lead['keywords_found_in'])}\n"
            export_content += f"Discovered: {lead.get('discovery_timestamp', 'Unknown')}\n"
            export_content += "-" * 50 + "\n"
        
        # Save to file and send
        with open(f"/tmp/{filename}", "w") as f:
            f.write(export_content)
        
        await ctx.send(
            f"📤 Exported {len(leads)} leads:",
            file=discord.File(f"/tmp/{filename}", filename)
        )
        
    except Exception as e:
        logging.error(f"Error exporting leads: {e}")
        await ctx.send("❌ Error exporting leads.")

@bot.command(name="clear")
async def clear_database(ctx, collection_name: str = None):
    """
    Clear database collections (DANGEROUS!)
    Usage: !clear [collection]
    Collections: main_leads, no_email_leads, processing_status, all
    """
    # Confirmation required
    await ctx.send("⚠️ **DANGER!** This will permanently delete data. Type `CONFIRM DELETE` to proceed or anything else to cancel.")
    
    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel
    
    try:
        confirmation = await bot.wait_for('message', timeout=30.0, check=check)
        
        if confirmation.content != "CONFIRM DELETE":
            await ctx.send("❌ Operation cancelled.")
            return
        
        if collection_name == "main_leads":
            result = await db.main_leads.delete_many({})
            await ctx.send(f"✅ Deleted {result.deleted_count} records from main_leads collection.")
        elif collection_name == "no_email_leads":
            result = await db.no_email_leads.delete_many({})
            await ctx.send(f"✅ Deleted {result.deleted_count} records from no_email_leads collection.")
        elif collection_name == "processing_status":
            result = await db.processing_status.delete_many({})
            await ctx.send(f"✅ Deleted {result.deleted_count} processing status records.")
        elif collection_name == "all":
            result1 = await db.main_leads.delete_many({})
            result2 = await db.no_email_leads.delete_many({})
            result3 = await db.processing_status.delete_many({})
            total = result1.deleted_count + result2.deleted_count + result3.deleted_count
            await ctx.send(f"✅ Cleared entire database. Deleted {total} total records.")
        else:
            await ctx.send("❌ Invalid collection. Use: `main_leads`, `no_email_leads`, `processing_status`, or `all`")
            
    except asyncio.TimeoutError:
        await ctx.send("❌ Confirmation timeout. Operation cancelled.")

@bot.command(name="guide")
async def show_help(ctx):
    """Show help information"""
    embed = discord.Embed(
        title="🤖 YouTube Lead Generation Bot - Commands",
        description="Complete guide to bot commands",
        color=0x9b59b6
    )
    
    embed.add_field(
        name="🚀 !start",
        value="`!start <min_subs> <max_subs> [max_channels] [max_videos] [min_freq] [max_freq] <keywords...>`\nStart lead generation with specified parameters",
        inline=False
    )
    
    embed.add_field(
        name="📊 !status",
        value="`!status [status_id]`\nCheck processing status or overall database stats",
        inline=False
    )
    
    embed.add_field(
        name="📧 !leads",
        value="`!leads [count] [type]`\nShow recent leads (types: email, no-email)",
        inline=False
    )
    
    embed.add_field(
        name="📤 !export",
        value="`!export [type] [limit]`\nExport leads to text file",
        inline=False
    )
    
    embed.add_field(
        name="🗑️ !clear",
        value="`!clear [collection]`\nClear database collections (DANGEROUS!)",
        inline=False
    )
    
    embed.add_field(
        name="❓ !guide",
        value="`!guide`\nShow this help guide",
        inline=False
    )
    
    embed.add_field(
        name="📋 Example Usage",
        value="`!start 10000 1000000 500 2000 0.14 2.0 crypto trading bitcoin investment`",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ---- Run Bot ----
if __name__ == "__main__":
    try:
        bot.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        logging.exception("Failed to start bot: %s", e)
