"""
db.py - Centralized SQLite database for leads
- Stores two tables: leads_with_email, leads_without_email
- Simple functions to insert/fetch leads
- Even a 5-year-old can follow the comments
"""

import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "leads.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Table for leads WITH email
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads_with_email (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT,
        channel_title TEXT,
        creator_name TEXT,
        channel_url TEXT,
        email TEXT,
        subscriber_count INTEGER,
        latest_video_title TEXT,
        top_comment TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table for leads WITHOUT email
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads_without_email (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT,
        channel_title TEXT,
        creator_name TEXT,
        channel_url TEXT,
        subscriber_count INTEGER,
        latest_video_title TEXT,
        top_comment TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def add_lead(lead: dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if lead.get("email"):
        cursor.execute("""
            INSERT INTO leads_with_email
            (channel_id, channel_title, creator_name, channel_url, email, subscriber_count, latest_video_title, top_comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead.get("channel_id"),
            lead.get("channel_title"),
            lead.get("creator_name"),
            lead.get("channel_url"),
            lead.get("email"),
            lead.get("subscriber_count"),
            lead.get("latest_video_title"),
            lead.get("top_comment"),
        ))
    else:
        cursor.execute("""
            INSERT INTO leads_without_email
            (channel_id, channel_title, creator_name, channel_url, subscriber_count, latest_video_title, top_comment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            lead.get("channel_id"),
            lead.get("channel_title"),
            lead.get("creator_name"),
            lead.get("channel_url"),
            lead.get("subscriber_count"),
            lead.get("latest_video_title"),
            lead.get("top_comment"),
        ))
    conn.commit()
    conn.close()

def fetch_all_with_email():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads_with_email")
    rows = cursor.fetchall()
    conn.close()
    return rows

def fetch_all_without_email():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads_without_email")
    rows = cursor.fetchall()
    conn.close()
    return rows
