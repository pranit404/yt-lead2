"""
outreach.py - Outreach email generator
- Uses outreach prompt template to create draft emails
- Returns subject/plain/html for a given lead
- Later you can replace with GPT/LLM calls
"""

import json

def generate_email_for_lead(lead: dict):
    # Example subject and body - replace with LLM if needed
    subject = f"I spent hours analyzing {lead.get('channel_title')} - found ways to grow fast"
    plain = f"""Hey {lead.get('creator_name')},

I checked your channel ({lead.get('channel_url')}) and noticed your recent video "{lead.get('latest_video_title')}".
Looks like your fans are engaged (top comment: {lead.get('top_comment')}).

I think with small editing tweaks, you could 10x retention. Want me to show you?

Best,
Your Outreach Team
"""
    html = f"""<html>
    <body>
        <p>Hey {lead.get('creator_name')},</p>
        <p>I checked your channel (<a href='{lead.get('channel_url')}'>{lead.get('channel_title')}</a>) 
        and noticed your recent video "<b>{lead.get('latest_video_title')}</b>".</p>
        <p>Looks like your fans are engaged (top comment: {lead.get('top_comment')}).</p>
        <p>I think with small editing tweaks, you could 10x retention. Want me to show you?</p>
        <p>Best,<br>Your Outreach Team</p>
    </body>
    </html>"""

    return {"subject": subject, "plain": plain, "html": html}
