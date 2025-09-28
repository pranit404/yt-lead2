# bot.py (replace your current file with this)
import os
import sys
import logging
import asyncio
import importlib
import traceback

import discord
from discord.ext import commands

# ---- Logging ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---- Token & intents ----
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("❌ Please set DISCORD_BOT_TOKEN environment variable and re-run.")
    sys.exit(1)

intents = discord.Intents.default()
# IMPORTANT: message_content must be True for prefix commands to work
intents.message_content = True
intents.guilds = True
intents.members = False

bot = commands.Bot(command_prefix="!", intents=intents)

# Try importing backend modules (make sure you run from project root)
try:
    from backend import db, outreach
except Exception as e:
    logging.warning("Could not import backend modules: %s", e)
    logging.warning("Make sure you run python bot.py from the project root and backend/__init__.py exists.")
    db = None
    outreach = None


@bot.event
async def on_ready():
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")
    # Print the guilds for quick sanity check
    guilds = ", ".join([g.name for g in bot.guilds]) or "(no guilds)"
    logging.info(f"Guilds: {guilds}")


# Global error handler for commands
@bot.event
async def on_command_error(ctx, error):
    logging.exception("Command error: %s", error)
    # Send a short message to user so they know something went wrong
    try:
        await ctx.send(f"⚠️ Command error: {type(error).__name__}: {str(error)}")
    except Exception:
        pass


# ---- Helper: run scraper (tries to import scraper.scrape) ----
async def run_scraper_and_notify(channel, min_subs, max_subs, keywords):
    """
    channel: discord.TextChannel or Context-like .send
    This tries to import scraper.py and call scrape(min_subs, max_subs, keywords).
    The scrape function can be:
      - synchronous and return an iterable of lead dicts
      - async and return an iterable/list of lead dicts
    Each lead must be a dict with keys described in the README (email maybe None).
    """
    await channel.send(f"🚀 Scrape task started in background for `{keywords}` (subs: {min_subs}-{max_subs})")

    # Try to import project scraper module
    scrape_func = None
    try:
        scraper = importlib.import_module("scraper")
        scrape_func = getattr(scraper, "scrape", None)
        logging.info("Found scraper.scrape: %s", bool(scrape_func))
    except Exception as e:
        logging.info("No scraper module found or import failed: %s", e)

    leads = []
    try:
        if scrape_func:
            if asyncio.iscoroutinefunction(scrape_func):
                # async function returning an iterable
                maybe_iter = await scrape_func(min_subs, max_subs, keywords)
                # if function returns an async generator/list, wrap accordingly
                if hasattr(maybe_iter, "__aiter__"):
                    async for l in maybe_iter:
                        leads.append(l)
                else:
                    leads = list(maybe_iter)
            else:
                # sync function -> run in thread to avoid blocking
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, lambda: list(scrape_func(min_subs, max_subs, keywords)))
                leads = result
        else:
            # Fallback simulation (will be obvious in logs)
            logging.info("No scraper provided; using simulated demo leads.")
            leads = [
                {"channel_id": "test1", "channel_title": "Demo Channel A", "creator_name": "Alice",
                 "channel_url": "https://youtube.com/channel/test1", "email": "alice@example.com",
                 "subscriber_count": 5200, "latest_video_title": "Demo Video A", "top_comment": "Nice!"},
                {"channel_id": "test2", "channel_title": "Demo Channel B", "creator_name": "Bob",
                 "channel_url": "https://youtube.com/channel/test2", "email": None,
                 "subscriber_count": 3100, "latest_video_title": "Demo Video B", "top_comment": "Cool!"}
            ]

        # Process found leads
        for lead in leads:
            try:
                # If backend DB available, add lead
                if db:
                    db.add_lead(lead)
                # announce
                if lead.get("email"):
                    await channel.send(f"📧 Email found: **{lead.get('creator_name')}** — `{lead.get('email')}`")
                else:
                    await channel.send(f"❌ No email found for **{lead.get('creator_name')}**")
            except Exception:
                logging.exception("Error processing lead: %s", lead)
                await channel.send(f"⚠️ Error storing/processing lead: {lead.get('channel_title')}")
    except Exception as e:
        logging.exception("Error running scraper: %s", e)
        await channel.send(f"⚠️ Scraper failed: {type(e).__name__}: {str(e)}")

    await channel.send("🏁 Scraping finished.")


# ---- Commands ----
@bot.command(name="initdb")
async def initdb(ctx):
    if not db:
        await ctx.send("❌ backend.db not available (import failed). See logs.")
        return
    try:
        db.init_db()
        await ctx.send("📂 Database initialized (SQLite).")
    except Exception as e:
        logging.exception(e)
        await ctx.send(f"⚠️ DB init failed: {e}")


@bot.command(name="startleads")
async def startleads(ctx, min_subs: int, max_subs: int, *, keywords: str):
    """
    Usage: !startleads <min_subs> <max_subs> <keywords>
    Example: !startleads 1000 50000 gaming equipment
    This immediately starts a background task that runs the scraper and posts updates to the same channel.
    """
    # Kick off the real work in background so the command call returns quickly
    bot.loop.create_task(run_scraper_and_notify(ctx.channel, min_subs, max_subs, keywords))
    await ctx.send(f"✅ Started background scraping task for `{keywords}` (you'll get updates here).")


@bot.command(name="outreachcmd")
async def outreachcmd(ctx, limit: int = 5):
    """
    Usage: !outreachcmd <limit>
    Will DM the command author up to <limit> outreach drafts for leads with email.
    """
    if not db or not outreach:
        await ctx.send("❌ backend modules not available (import failed).")
        return

    try:
        rows = db.fetch_all_with_email()
        if not rows:
            await ctx.send("ℹ️ No leads with email in DB.")
            return
        count = 0
        for row in rows:
            if count >= limit:
                break
            # row structure: id, channel_id, channel_title, creator_name, channel_url, email, subscriber_count, latest_video_title, top_comment, added_at
            # Adapt indices if your schema differs
            lead = {
                "channel_id": row[1],
                "channel_title": row[2],
                "creator_name": row[3],
                "channel_url": row[4],
                "email": row[5],
                "subscriber_count": row[6],
                "latest_video_title": row[7],
                "top_comment": row[8] if len(row) > 8 else ""
            }
            draft = outreach.generate_email_for_lead(lead)
            try:
                await ctx.author.send(f"📨 Draft for {lead['creator_name']}\nSubject: {draft['subject']}\n\n{draft['plain']}")
            except Exception:
                await ctx.send("⚠️ Could not DM you — check your DM settings.")
            count += 1
        await ctx.send(f"✉️ Sent up to {count} drafts to your DMs.")
    except Exception as e:
        logging.exception(e)
        await ctx.send(f"⚠️ outreach failed: {e}")


# ---- Run bot ----
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception:
        logging.exception("Failed to start bot")
