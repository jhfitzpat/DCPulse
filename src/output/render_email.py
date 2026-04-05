"""Render weekly digest to HTML and plain text; optional SMTP send."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import List

from src.config import Config
from src.output.schema import WeeklyDigest

log = logging.getLogger(__name__)


def parse_recipient_list(raw: str) -> List[str]:
    """Split comma- or semicolon-separated addresses; strip whitespace; drop empties."""
    out: List[str] = []
    for chunk in raw.replace(";", ",").split(","):
        addr = chunk.strip()
        if addr:
            out.append(addr)
    return out


def render_text(d: WeeklyDigest) -> str:
    lines: List[str] = [
        f"DC Pulse Weekly — {d.week_label}",
        "",
        d.intro or "",
        "",
        "=== Ranked topics (max 7) ===",
        "",
    ]
    for t in d.topics:
        lines.append(f"{t.rank}. {t.topic_title}")
        lines.append(f"   Best use: {t.best_use.value}")
        lines.append(f"   Summary: {t.trend_summary}")
        lines.append(f"   Why it matters: {t.why_matters_dc}")
        lines.append(f"   Momentum: {t.evidence_momentum}")
        lines.append(f"   Repost copy: {t.suggested_repost_copy}")
        lines.append(f"   Original angle: {t.suggested_original_angle}")
        if t.example_headlines_or_sources:
            lines.append("   Examples / sources to review:")
            for ex in t.example_headlines_or_sources:
                lines.append(f"     - {ex}")
        if t.citations:
            lines.append("   Citations:")
            for c in t.citations:
                lines.append(f"     - {c.title} ({c.url})")
        lines.append("")
    lines.append("=== Repost highlights (3) ===")
    lines.append("")
    for h in d.repost_highlights:
        lines.append(f"* {h.topic_title}")
        lines.append(f"  Article: {h.primary_article_title}")
        lines.append(f"  URL: {h.primary_article_url}")
        lines.append(f"  Why repost: {h.why_repost}")
        lines.append("")
        lines.append("  Angle A:")
        lines.append(f"  {h.repost_copy_angle_a}")
        lines.append("")
        lines.append("  Angle B:")
        lines.append(f"  {h.repost_copy_angle_b}")
        lines.append("")
    lines.append("Best to repost this week:")
    for x in d.best_repost_this_week:
        lines.append(f"  - {x}")
    lines.append("")
    lines.append("Best for original thought leadership (month):")
    for x in d.best_thought_leadership_month:
        lines.append(f"  - {x}")
    lines.append("")
    lines.append("Topics to avoid:")
    for x in d.topics_to_avoid:
        lines.append(f"  - {x}")
    lines.append("")
    if d.low_confidence_note:
        lines.append(f"Note: {d.low_confidence_note}")
    if d.article_drafts:
        lines.append("")
        lines.append("=== Full-length article drafts (for editorial review — not published automatically) ===")
        lines.append("")
        for i, ad in enumerate(d.article_drafts, start=1):
            lines.append(f"--- Draft {i}: {ad.draft_title} ---")
            lines.append(f"Topic: {ad.topic_title}")
            if ad.selection_rationale:
                lines.append(f"Why this week: {ad.selection_rationale}")
            lines.append("")
            lines.append(ad.body_markdown)
            lines.append("")
    return "\n".join(lines)


def render_html(d: WeeklyDigest) -> str:
    parts: List[str] = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>DC Pulse Weekly</title>",
        "<style>body{font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.45;color:#222;}",
        "h1{font-size:20px;} h2{font-size:16px;margin-top:1.2em;} .muted{color:#555;font-size:13px;}",
        "ul{padding-left:1.2em;} .card{border:1px solid #ddd;border-radius:8px;padding:12px;margin:10px 0;}",
        "</style></head><body>",
        f"<h1>DC Pulse Weekly — {escape(d.week_label)}</h1>",
    ]
    if d.intro:
        parts.append(f"<p>{escape(d.intro)}</p>")
    parts.append("<h2>Ranked topics</h2>")
    for t in d.topics:
        parts.append("<div class='card'>")
        parts.append(f"<strong>{t.rank}. {escape(t.topic_title)}</strong>")
        parts.append(f"<div class='muted'>Best use: {escape(t.best_use.value)}</div>")
        parts.append(f"<p>{escape(t.trend_summary)}</p>")
        parts.append(f"<p><em>Why it matters:</em> {escape(t.why_matters_dc)}</p>")
        parts.append(f"<p><em>Momentum:</em> {escape(t.evidence_momentum)}</p>")
        parts.append(f"<p><em>Repost copy:</em> {escape(t.suggested_repost_copy)}</p>")
        parts.append(f"<p><em>Original angle:</em> {escape(t.suggested_original_angle)}</p>")
        if t.example_headlines_or_sources:
            parts.append("<ul>")
            for ex in t.example_headlines_or_sources:
                parts.append(f"<li>{escape(ex)}</li>")
            parts.append("</ul>")
        if t.citations:
            parts.append("<ul>")
            for c in t.citations:
                parts.append(
                    f"<li><a href=\"{escape(c.url)}\">{escape(c.title)}</a>"
                    f"{' — ' + escape(c.publisher) if c.publisher else ''}</li>"
                )
            parts.append("</ul>")
        parts.append("</div>")
    parts.append("<h2>Repost highlights</h2>")
    for h in d.repost_highlights:
        parts.append("<div class='card'>")
        parts.append(f"<strong>{escape(h.topic_title)}</strong>")
        parts.append(
            f"<p><a href=\"{escape(h.primary_article_url)}\">{escape(h.primary_article_title)}</a></p>"
        )
        parts.append(f"<p>{escape(h.why_repost)}</p>")
        parts.append("<p><em>Angle A</em></p><p>" + escape(h.repost_copy_angle_a) + "</p>")
        parts.append("<p><em>Angle B</em></p><p>" + escape(h.repost_copy_angle_b) + "</p>")
        parts.append("</div>")
    parts.append("<h2>Best to repost this week</h2><ul>")
    for x in d.best_repost_this_week:
        parts.append(f"<li>{escape(x)}</li>")
    parts.append("</ul><h2>Thought leadership (month)</h2><ul>")
    for x in d.best_thought_leadership_month:
        parts.append(f"<li>{escape(x)}</li>")
    parts.append("</ul><h2>Topics to avoid</h2><ul>")
    for x in d.topics_to_avoid:
        parts.append(f"<li>{escape(x)}</li>")
    parts.append("</ul>")
    if d.low_confidence_note:
        parts.append(f"<p class='muted'>{escape(d.low_confidence_note)}</p>")
    if d.article_drafts:
        parts.append("<h2>Full-length article drafts</h2>")
        parts.append(
            "<p class='muted'>For editorial review only — not published automatically.</p>"
        )
        for i, ad in enumerate(d.article_drafts, start=1):
            parts.append("<section class='draft'>")
            parts.append(f"<h3>{escape(ad.draft_title)}</h3>")
            parts.append(f"<p class='muted'><em>Topic:</em> {escape(ad.topic_title)}</p>")
            if ad.selection_rationale:
                parts.append(f"<p class='muted'><em>Why this week:</em> {escape(ad.selection_rationale)}</p>")
            parts.append(_draft_body_html(ad.body_markdown))
            parts.append("</section>")
    parts.append("</body></html>")
    return "\n".join(parts)


def _draft_body_html(md: str) -> str:
    """Minimal Markdown-ish body: paragraphs and line breaks; no untrusted HTML."""
    blocks = [p.strip() for p in md.split("\n\n") if p.strip()]
    if not blocks:
        return ""
    out: List[str] = []
    for block in blocks:
        if block.startswith("#"):
            level = len(block) - len(block.lstrip("#"))
            title = block.lstrip("#").strip()
            tag = f"h{min(max(level, 1), 3)}"
            out.append(f"<{tag}>{escape(title)}</{tag}>")
        else:
            inner = escape(block).replace("\n", "<br/>")
            out.append(f"<div class='draft-block'>{inner}</div>")
    return "".join(out)


def send_digest_email(cfg: Config, subject: str, text_body: str, html_body: str) -> None:
    """Send multipart email via SMTP. No-op if misconfigured or dry-run."""
    if cfg.dry_run:
        log.info("Dry-run: skipping email send")
        return
    if not cfg.email_to or not cfg.smtp_host:
        log.warning("Email skipped: DC_PULSE_EMAIL_TO or DC_PULSE_SMTP_HOST not set")
        return
    recipients = parse_recipient_list(cfg.email_to)
    if not recipients:
        log.warning("Email skipped: DC_PULSE_EMAIL_TO has no valid addresses")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.email_from or cfg.smtp_user or "dc-pulse@localhost"
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    log.info(
        "Sending email to %s via %s:%s (smtp_ssl=%s, starttls=%s)",
        recipients,
        cfg.smtp_host,
        cfg.smtp_port,
        cfg.smtp_use_ssl,
        False if cfg.smtp_use_ssl else cfg.smtp_use_tls,
    )
    try:
        if cfg.smtp_use_ssl:
            smtp_cm = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=60)
        else:
            smtp_cm = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=60)
        with smtp_cm as smtp:
            if not cfg.smtp_use_ssl and cfg.smtp_use_tls:
                smtp.starttls()
            if cfg.smtp_user and cfg.smtp_password:
                smtp.login(cfg.smtp_user, cfg.smtp_password)
            smtp.sendmail(msg["From"], recipients, msg.as_string())
    except Exception:
        log.exception("SMTP send failed")
        raise
    log.info("Email sent successfully to %d recipient(s)", len(recipients))
