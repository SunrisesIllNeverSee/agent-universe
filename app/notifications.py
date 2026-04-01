"""
notifications.py — CIVITAE Email Notification System
Handles magic link emails, message notifications (rate-limited), and operator alerts.

Uses Resend REST API (HTTPS). Falls back to stdout logging when API key is not configured.
Rate limits message notifications to 1 per 15 minutes per thread.

Config via env vars:
    RESEND_API_KEY  (or SMTP_PASS for backwards compat)
    SMTP_FROM       — sender address (default: noreply@signomy.xyz)
    OPERATOR_EMAIL  — operator alert destination
    CIVITAE_BASE_URL

Usage from any endpoint:
    from .notifications import send_magic_link, send_message_notification, send_operator_alert
"""

import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

RESEND_API_KEY: Optional[str] = os.environ.get("RESEND_API_KEY") or os.environ.get("SMTP_PASS")
SMTP_FROM: str = os.environ.get("SMTP_FROM", "noreply@signomy.xyz")

OPERATOR_EMAIL: str = os.environ.get("OPERATOR_EMAIL", "contact@burnmydays.com")
BASE_URL: str = os.environ.get("CIVITAE_BASE_URL", "http://localhost:8300")

logger = logging.getLogger("civitae.notifications")

# ── Rate Limiting ─────────────────────────────────────────────────────────────

_last_notified: dict[str, datetime] = {}
RATE_LIMIT_SECONDS = 15 * 60  # 15 minutes


def _is_rate_limited(thread_id: str) -> bool:
    last = _last_notified.get(thread_id)
    if last is None:
        return False
    elapsed = (datetime.now(timezone.utc) - last).total_seconds()
    return elapsed < RATE_LIMIT_SECONDS


def _mark_notified(thread_id: str) -> None:
    _last_notified[thread_id] = datetime.now(timezone.utc)


# ── Resend REST Transport ─────────────────────────────────────────────────────

def _send_email(to_addr: str, subject: str, body: str, from_addr: str | None = None) -> bool:
    """
    Send a plain-text email via Resend REST API.
    Falls back to stdout logging when RESEND_API_KEY is not set.

    Args:
        from_addr: Optional custom sender (e.g. agent@signomy.xyz).
                   Falls back to SMTP_FROM env var.
    """
    sender = from_addr or SMTP_FROM

    if not RESEND_API_KEY:
        logger.info(
            "RESEND_API_KEY not configured — logging email instead.\n"
            "  To:      %s\n"
            "  Subject: %s\n"
            "  Body:\n%s\n"
            "  ---",
            to_addr, subject, body,
        )
        print(
            f"\n{'='*60}\n"
            f"EMAIL (not sent — no API key)\n"
            f"  To:      {to_addr}\n"
            f"  From:    {sender}\n"
            f"  Subject: {subject}\n"
            f"{'─'*60}\n"
            f"{body}\n"
            f"{'='*60}\n"
        )
        return True

    try:
        payload = json.dumps({
            "from": sender,
            "to": [to_addr],
            "subject": subject,
            "text": body,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "CIVITAE/1.0",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            logger.info("Email sent to %s from %s — id: %s", to_addr, sender, result.get("id"))
            return True

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        logger.error("Resend API error %s sending to %s: %s", e.code, to_addr, error_body)
        return False
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_addr, e)
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def send_magic_link(
    poster_name: str,
    poster_email: str,
    thread_id: str,
    magic_token: str,
    post_title: str,
) -> bool:
    """
    Send magic link email to poster when a thread is created (agent stakes on their post).
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


def send_message_notification(
    poster_email: str,
    poster_name: str,
    thread_id: str,
    sender_name: str,
    message_preview: str,
    magic_token: str = "",
    from_addr: str | None = None,
) -> bool:
    """
    Send notification to poster that a new message arrived in their thread.
    Rate limited: max 1 email per 15 minutes per thread_id.
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

    success = _send_email(poster_email, subject, body, from_addr=from_addr)
    if success:
        _mark_notified(thread_id)
    return success


def send_operator_alert(subject: str, body: str) -> bool:
    """
    Send an alert email to the operator.
    """
    full_subject = f"[CIVITAE] {subject}"

    full_body = (
        f"{body}\n"
        f"\n"
        f"— CIVITAE System Alert\n"
        f"   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
    )

    return _send_email(OPERATOR_EMAIL, full_subject, full_body)
