"""Digest notifications (Phase 9).

One digest per run, never one email per job, and never the same job twice on
the same channel - the notifications table is the guard.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import Job, JobScore, Notification

logger = logging.getLogger(__name__)


def pending_jobs(db: Session, channel: str, min_score: float) -> list[tuple[Job, JobScore]]:
    """High-scoring active jobs not yet notified about on this channel."""
    already = select(Notification.job_id).where(Notification.channel == channel)
    rows = db.execute(
        select(Job, JobScore)
        .join(JobScore, JobScore.job_id == Job.id)
        .where(
            Job.is_active.is_(True),
            JobScore.overall_score >= min_score,
            Job.id.not_in(already),
        )
        .order_by(JobScore.overall_score.desc())
    ).all()
    return [(job, score) for job, score in rows]


def render_digest(jobs: list[tuple[Job, JobScore]]) -> tuple[str, str]:
    top_job, top_score = jobs[0]
    subject = f"{len(jobs)} new high-match software job{'s' if len(jobs) > 1 else ''}"
    lines = [
        f"{len(jobs)} new job(s) passed verification and scored highly.",
        "",
        "Top match:",
        f"  {top_job.title} — {top_job.company}",
        f"  {top_job.location or 'Location not stated'}",
        f"  Score: {top_score.overall_score:.0f}/100",
        f"  {top_job.application_url or 'No application link published'}",
        "",
    ]
    if len(jobs) > 1:
        lines.append("Also:")
        lines += [
            f"  {score.overall_score:.0f}  {job.title} — {job.company}"
            for job, score in jobs[1:11]
        ]
    return subject, "\n".join(lines)


def _send_email(settings: Settings, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_username or settings.notification_email
    message["To"] = settings.notification_email
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


def _send_telegram(settings: Settings, subject: str, body: str) -> None:
    httpx.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        json={"chat_id": settings.telegram_chat_id, "text": f"{subject}\n\n{body}"},
        timeout=30.0,
    ).raise_for_status()


def _send_discord(settings: Settings, subject: str, body: str) -> None:
    httpx.post(
        settings.discord_webhook_url,
        json={"content": f"**{subject}**\n```\n{body}\n```"},
        timeout=30.0,
    ).raise_for_status()


def configured_channels(settings: Settings) -> dict[str, callable]:
    channels: dict[str, callable] = {}
    if settings.smtp_host and settings.notification_email:
        channels["email"] = _send_email
    if settings.telegram_bot_token and settings.telegram_chat_id:
        channels["telegram"] = _send_telegram
    if settings.discord_webhook_url:
        channels["discord"] = _send_discord
    return channels


def send_digests(db: Session, settings: Settings | None = None) -> dict:
    """Send one digest per configured channel. A channel that fails is logged
    and leaves its jobs unmarked, so the next run retries them."""
    settings = settings or get_settings()
    stats: dict[str, int | list[str]] = {"sent": 0, "jobs": 0, "errors": []}

    for channel, send in configured_channels(settings).items():
        jobs = pending_jobs(db, channel, settings.notification_min_score)
        if not jobs:
            continue
        subject, body = render_digest(jobs)
        try:
            send(settings, subject, body)
        except Exception as exc:  # noqa: BLE001 - one channel must not kill the rest
            logger.error("notification channel %s failed: %s", channel, exc)
            stats["errors"].append(f"{channel}: {exc}")
            continue
        db.add_all(Notification(job_id=job.id, channel=channel) for job, _ in jobs)
        db.commit()
        stats["sent"] += 1
        stats["jobs"] += len(jobs)
        logger.info("sent %s digest covering %d jobs", channel, len(jobs))

    return stats
