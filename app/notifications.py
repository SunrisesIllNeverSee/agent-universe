"""
notifications.py — CIVITAE Email Notification System
Handles magic link emails, message notifications (rate-limited), and operator alerts.

Uses smtplib for sending. Falls back to stdout logging when SMTP is not configured.
Rate limits message notifications to 1 per 15 minutes per thread.

Config via env vars:
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
    OPERATOR_EMAIL, CIVITAE_BASE_URL

Usage from any endpoint:
    from .notifications import send_magic_link, send_message_notification, send_operator_alert
"""

import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

SMTP_HOST: Optional[str] = os.environ.get("SMTP_HOST")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER: Optional[str] = os.environ.get("SMTP_USER")
SMTP_PASS: Optional[str] = os.environ.get("SMTP_PASS")
SMTP_FROM: str = os.environ.get("SMTP_FROM", "noreply@civitae.io")

OPERATOR_EMAIL: str = os.environ.get("OPERATOR_EMAIL", "contact@burnmydays.com")
BASE_URL: str = os.environ.get("CIVITAE_BASE_URL", "http://localhost:8300")

logger = logging.getLogger("civitae.notifications")

# ── Rate Limiting ─────────────────────────────────────────────────────────────
# Track last notification time per thread_id to enforce 1 per 15 min max.

_last_notified: dict[str, datetime] = {}
RATE_LIMIT_SECONDS = 15 * 60  # 15 minutes


def _is_rate_limited(thread_id: str) -> bool:
    """Return True if this thread was notified less than 15 minutes ago."""
    last = _last_notified.get(thread_id)
    if last is None:
        return False
    elapsed = (datetime.now(timezone.utc) - last).total_seconds()
    return elapsed < RATE_LIMIT_SECONDS


def _mark_notified(thread_id: str) -> None:
    """Record that a notification was sent for this thread right now."""
    _last_notified[thread_id] = datetime.now(timezone.utc)


# ── SMTP Transport ────────────────────────────────────────────────────────────

def _smtp_configured() -> bool:
    """Check whether SMTP credentials are present."""
    return bool(SMTP_HOST)


def _send_email(to_addr: str, subject: str, body: str) -> bool:
    """
    Send a plain-text email via SMTP.
    If SMTP is not configured, log to stdout and return True.
    Returns True on success, False on failure.
    """
    if not _smtp_configured():
        logger.info(
            "SMTP not configured — logging email instead.\n"
            "  To:      %s\n"
            "  Subject: %s\n"
            "  Body:\n%s\n"
            "  ---",
            to_addr, subject, body,
        )
        # Also print so it shows up in terminal during local dev
        print(
            f"\n{'='*60}\n"
            f"EMAIL (not sent — no SMTP)\n"
            f"  To:      {to_addr}\n"
            f"  From:    {SMTP_FROM}\n"
            f"  Subject: {subject}\n"
            f"{'─'*60}\n"
            f"{body}\n"
            f"{'='*60}\n"
        )
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        context = ssl.create_default_context()

        if SMTP_PORT == 465:
            # SSL connection
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM, to_addr, msg.as_string())
        else:
            # STARTTLS connection (port 587 or other)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls(context=context)
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM, to_addr, msg.as_string())

        logger.info("Email sent to %s — subject: %s", to_addr, subject)
        return True

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_addr, e)
        return False


# ── Public API ────────────────────────────────────────────────────────────────

async def send_magic_link(
    poster_name: str,
    poster_email: str,
    thread_id: str,
    magic_token: str,
    post_title: str,
) -> bool:
    """
    Send magic link email to poster when a thread is created (agent stakes on their post).

    Args:
        poster_name:  Display name of the poster
        poster_email: Email address of the poster
        thread_id:    Thread ID for the conversation
        magic_token:  One-time token granting access to the thread
        post_title:   Title of the original post

    Returns:
        True if sent (or logged) successfully, False on error.
    """
    thread_url = f"{BASE_URL}/kassa/thread/{thread_id}?magic={magic_token}"

    subject = f"New response on your post: {post_title}"

    body = (
        f"Hi {poster_name},\n"
        f"\n"
        f"You have a new response on your post \"{post_title}\".\n"
        f"\n"
        f"View the conversation:\n"
        f"{thread_url}\n"
        f"\n"
        f"This link is unique to you. Do not share it.\n"
        f"\n"
        f"— CIVITAE\n"
    )

    return _send_email(poster_email, subject, body)


async def send_message_notification(
    poster_email: str,
    poster_name: str,
    thread_id: str,
    sender_name: str,
    message_preview: str,
    magic_token: str = "",
) -> bool:
    """
    Send notification to poster that a new message arrived in their thread.
    Rate limited: max 1 email per 15 minutes per thread_id.

    Args:
        poster_email:    Email address of the poster
        poster_name:     Display name of the poster
        thread_id:       Thread ID for the conversation
        sender_name:     Name of the agent/user who sent the message
        message_preview: First ~200 chars of the message body
        magic_token:     Plain magic token for poster access link

    Returns:
        True if sent (or logged) successfully, False on error or rate-limited skip.
    """
    if _is_rate_limited(thread_id):
        logger.debug(
            "Rate limited — skipping message notification for thread %s",
            thread_id,
        )
        return False

    thread_url = f"{BASE_URL}/kassa/thread/{thread_id}"
    if magic_token:
        thread_url += f"?magic={magic_token}"

    # Truncate preview to keep email clean
    preview = message_preview[:200]
    if len(message_preview) > 200:
        preview += "..."

    subject = f"New message from {sender_name} in your thread"

    body = (
        f"Hi {poster_name},\n"
        f"\n"
        f"New message from {sender_name} in your thread:\n"
        f"\n"
        f"    \"{preview}\"\n"
        f"\n"
        f"View the full conversation:\n"
        f"{thread_url}\n"
        f"\n"
        f"— CIVITAE\n"
    )

    success = _send_email(poster_email, subject, body)
    if success:
        _mark_notified(thread_id)
    return success


async def send_operator_alert(subject: str, body: str) -> bool:
    """
    Send an alert email to the operator.

    Args:
        subject: Email subject line
        body:    Plain-text email body

    Returns:
        True if sent (or logged) successfully, False on error.
    """
    full_subject = f"[CIVITAE] {subject}"

    full_body = (
        f"{body}\n"
        f"\n"
        f"— CIVITAE System Alert\n"
        f"   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
    )

    return _send_email(OPERATOR_EMAIL, full_subject, full_body)
