# DC Pulse Weekly Pipeline

Automated weekly workflow that collects Canadian pension and benefits coverage from curated RSS feeds, clusters and ranks topics, optionally enriches them with an OpenAI narrative aligned to DC consulting prompts, and emails a digest (up to **7** topics, **3** repost highlights with **two** copy angles each).

Manual posting to LinkedIn and final article editing stay **out of scope** for v1.

## Requirements

- **Python 3.8+** (see `pyproject.toml`). Use a current 3.10+ release when possible.

## Quick start (local)

```bash
cd /path/to/DCPulse
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env    # optional; then edit .env and set OPENAI_API_KEY
python -m src.main --print --dry-run
```

### OpenAI API key (local)

Put your key in either place (the app loads the repo-root **`.env`** automatically if `python-dotenv` is installed):

1. **`.env`** in the project root (recommended): copy [`.env.example`](.env.example) to `.env` and set `OPENAI_API_KEY=sk-...`. `.env` is gitignored.
2. **Environment variable**: set `OPENAI_API_KEY` in your shell or system environment (same name the OpenAI SDK uses).

For **GitHub Actions**, add repository secret **`OPENAI_API_KEY`** (see table below)—do not commit keys to the repo.

- Without `OPENAI_API_KEY`, the run uses **fallback** placeholder copy (clusters and citations still appear if feeds work).
- `--print` prints the text digest and skips email.
- `--dry-run` skips SMTP even if configured.

## GitHub Actions

Workflow: [`.github/workflows/weekly-dc-pulse.yml`](.github/workflows/weekly-dc-pulse.yml)

- **Schedule**: Mondays 12:00 UTC (edit the cron as needed).
- **Manual run**: Actions → Weekly DC Pulse → Run workflow.

### Repository secrets

| Secret | Purpose |
|--------|---------|
| `OPENAI_API_KEY` | Required for full narrative digest (omit for fallback-only). |
| `OPENAI_MODEL` | Optional override (defaults to `gpt-4o-mini` in code if unset). |
| `DC_PULSE_EMAIL_TO` | Recipient(s), comma-separated. |
| `DC_PULSE_EMAIL_FROM` | From address. |
| `DC_PULSE_SMTP_HOST` | SMTP host. |
| `DC_PULSE_SMTP_PORT` | Port (e.g. `587`). |
| `DC_PULSE_SMTP_USER` | SMTP auth user if required. |
| `DC_PULSE_SMTP_PASSWORD` | SMTP password or app password. |
| `DC_PULSE_SMTP_TLS` | `1` for STARTTLS (default in app). |

If email secrets are missing, the job still runs and writes `last_digest.txt`; use the **last-digest** artifact.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DC_PULSE_DRY_RUN` | `0` | `1` = no email send. |
| `DC_PULSE_LOG_LEVEL` | `INFO` | Logging level. |
| `DC_PULSE_LOOKBACK_DAYS` | `14` | RSS item lookback. |
| `DC_PULSE_MAX_TOPICS` | `7` | Max ranked topics. |
| `DC_PULSE_HIGHLIGHT_REPOST` | `3` | Repost highlights. |
| `DC_PULSE_SKIP_LLM` | `0` | `1` = force fallback digest. |
| `DC_PULSE_LLM_TIMEOUT` | `120` | OpenAI timeout (seconds). |
| `DC_PULSE_DATA_DIR` | `./data` | Override path to `sources.yml` / `topic_exclusions.yml`. |

## Data files

- [`data/sources.yml`](data/sources.yml) — RSS feeds, weights, enable/disable.
- [`data/topic_exclusions.yml`](data/topic_exclusions.yml) — noisy keyword filters.

Verify feed URLs periodically; some publishers change RSS endpoints.

## Prompts and voice

- [`src/prompts/`](src/prompts/) — ideation, research, repost copy, drafting rules.
- [`src/voice/profile.md`](src/voice/profile.md) — consultant/CFA voice guide.

## Architecture

1. Collect → normalize/dedupe → cluster (token overlap) → rank → select top 7 + 3 repost.
2. OpenAI generates structured JSON matching [`src/output/schema.py`](src/output/schema.py).
3. Render HTML + plain text; send via SMTP.

## License

Use and modify for your practice; add a license file if you redistribute.
