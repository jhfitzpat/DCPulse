"""DC Pulse weekly pipeline entrypoint."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from src.config import load_config
from src.llm.article_drafts import generate_article_drafts_llm
from src.llm.generate_digest import (
    fallback_digest_without_llm,
    generate_digest_with_llm,
    week_label,
)
from src.research.web_search import collect_web_search_articles
from src.output.render_email import render_html, render_text, send_digest_email
from src.pipeline.cluster import cluster_articles
from src.pipeline.normalize import (
    apply_exclusions,
    dedupe_by_link_and_title,
    drop_low_signal,
    filter_by_lookback,
    load_exclusion_rules,
    normalize_and_score,
)
from src.pipeline.rank import rank_clusters
from src.pipeline.select import select_top_topics
from src.pipeline.usage_history import (
    blocked_urls_in_window,
    load_usage_file,
    maybe_record_weekly_usage,
)
from src.sources.catalog import load_catalog
from src.sources.collect import collect_all
from src.hardening import augment_low_confidence
from src.output.schema import WeeklyDigest


def _finalize_digest(
    cfg,
    digest: WeeklyDigest,
    top,
    raw_count: int,
    cluster_count: int,
) -> WeeklyDigest:
    """Apply low-confidence augmentation and persist weekly primary URL usage."""
    out = augment_low_confidence(digest, cfg, raw_count, cluster_count)
    maybe_record_weekly_usage(cfg, top, out.week_label, cfg.max_topics)
    return out


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def run_pipeline() -> WeeklyDigest:
    cfg = load_config()
    setup_logging(cfg.log_level)
    log = logging.getLogger("dc_pulse")
    log.info("DC Pulse start dry_run=%s skip_llm=%s", cfg.dry_run, cfg.skip_llm)

    catalog = load_catalog(cfg.sources_path)
    sources = catalog.enabled_sources()
    if not sources:
        log.error("No enabled sources in %s", cfg.sources_path)
        digest = fallback_digest_without_llm(
            cfg,
            [],
            [],
            note="No RSS sources configured. Edit data/sources.yml and enable feeds.",
        )
        return augment_low_confidence(digest, cfg, 0, 0)

    raw = collect_all(sources)
    if cfg.web_search_enabled:
        wl = week_label()
        headlines = [a.title for a in raw[:100]]
        try:
            raw.extend(collect_web_search_articles(cfg, wl, headlines))
        except Exception as e:
            log.warning("Web search collection failed: %s", e)
    now = datetime.now(timezone.utc)
    raw = filter_by_lookback(raw, cfg.lookback_days, now)
    raw_count = len(raw)
    log.info("After lookback (%d days): %d articles", cfg.lookback_days, raw_count)

    rules = load_exclusion_rules(cfg.exclusions_path)
    norm = normalize_and_score(raw)
    norm = dedupe_by_link_and_title(norm)
    norm = apply_exclusions(norm, rules)
    norm = drop_low_signal(norm, min_dc_score=0)
    log.info("After normalize/dedupe: %d articles", len(norm))

    if not norm:
        log.warning("No articles after filters; generating low-signal digest")
        digest = fallback_digest_without_llm(
            cfg,
            [],
            [],
            note="No articles collected after lookback and filters. Check feeds or relax DC_PULSE_LOOKBACK_DAYS.",
        )
        return augment_low_confidence(digest, cfg, raw_count, 0)

    clusters = cluster_articles(norm)
    cluster_count = len(clusters)
    log.info("Clusters: %d", cluster_count)
    ranked = rank_clusters(clusters, rules)
    if cfg.usage_history_enabled:
        hist = load_usage_file(cfg.usage_history_path)
        blocked = blocked_urls_in_window(hist["weeks"], window_weeks=cfg.usage_history_weeks)
        log.info("Usage history: %d blocked primary URLs (last %d weeks)", len(blocked), cfg.usage_history_weeks)
    else:
        blocked = set()
    top, highlights = select_top_topics(
        ranked,
        cfg.max_topics,
        cfg.highlight_repost_count,
        blocked_urls=blocked,
    )
    log.info("Selected %d topics, %d repost highlights", len(top), len(highlights))

    use_llm = bool(cfg.openai_api_key) and not cfg.skip_llm
    if not use_llm:
        log.warning("LLM skipped (no OPENAI_API_KEY or DC_PULSE_SKIP_LLM=1); using fallback digest")
        note = (
            "OpenAI not configured or skipped. Showing clustered sources with placeholder commentary."
        )
        digest = fallback_digest_without_llm(cfg, top, highlights, note=note)
        return _finalize_digest(cfg, digest, top, raw_count, cluster_count)

    try:
        digest = generate_digest_with_llm(cfg, top, highlights)
        if cfg.article_drafts_enabled:
            try:
                drafts = generate_article_drafts_llm(cfg, digest, top)
                digest = digest.model_copy(update={"article_drafts": drafts})
            except Exception as e:
                log.exception("Article draft generation failed: %s", e)
    except Exception as e:
        log.exception("LLM failed: %s", e)
        digest = fallback_digest_without_llm(
            cfg,
            top,
            highlights,
            note=f"LLM error ({e!s}); showing fallback from clusters.",
        )
        return _finalize_digest(cfg, digest, top, raw_count, cluster_count)

    if len(digest.topics) < cfg.max_topics and not digest.low_confidence_note:
        digest = digest.model_copy(
            update={
                "low_confidence_note": (
                    "Fewer than 7 strong topics this week or thin coverage; "
                    "review citations before relying on narratives."
                )
            }
        )
    return _finalize_digest(cfg, digest, top, raw_count, cluster_count)


def main() -> int:
    p = argparse.ArgumentParser(description="DC Pulse weekly digest pipeline")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not send email (also respects DC_PULSE_DRY_RUN)",
    )
    p.add_argument(
        "--print",
        action="store_true",
        dest="print_only",
        help="Print text digest to stdout only",
    )
    args = p.parse_args()
    if args.dry_run:
        os.environ["DC_PULSE_DRY_RUN"] = "1"
    cfg = load_config()
    setup_logging(cfg.log_level)

    digest = run_pipeline()
    cfg = load_config()
    log = logging.getLogger("dc_pulse")
    if cfg.dry_run:
        log.info("Email: dry_run enabled (DC_PULSE_DRY_RUN or --dry-run); send will be skipped")
    elif not cfg.email_to or not cfg.smtp_host:
        log.warning(
            "Email: not configured (set DC_PULSE_EMAIL_TO and DC_PULSE_SMTP_HOST in .env); send will be skipped"
        )
    else:
        log.info(
            "Email: will attempt send via %s:%s (smtp_ssl=%s)",
            cfg.smtp_host,
            cfg.smtp_port,
            cfg.smtp_use_ssl,
        )
    text = render_text(digest)
    html = render_html(digest)

    if args.print_only:
        print(text)
        return 0

    subject = f"{cfg.email_subject_prefix} — {digest.week_label}"
    send_digest_email(cfg, subject, text, html)

    # Always log path for CI artifacts
    out_path = cfg.data_dir.parent / "last_digest.txt"
    try:
        out_path.write_text(text, encoding="utf-8")
        logging.getLogger("dc_pulse").info("Wrote %s", out_path)
    except OSError as e:
        logging.getLogger("dc_pulse").warning("Could not write last_digest.txt: %s", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
