# DC Pulse Weekly Pipeline

Automated weekly workflow that collects Canadian pension and benefits coverage from curated RSS feeds ([`data/sources.yml`](data/sources.yml)), optionally augments discovery with **LLM-planned web search** (OpenAI Responses API with the built-in `web_search` tool), clusters and ranks to **7** topics, runs a **deep-research** LLM pass on those topics, then (by default) generates **two full-length article drafts** for review. The email includes the digest (7 topics, **3** repost highlights with **two** copy angles each), plus those drafts.

Manual posting to LinkedIn stays **out of scope**; drafts are **for review** in the email, not auto-published.

## Requirements

- **Python 3.8+** (see `pyproject.toml`). Use **3.12** on the scheduled server to match the optional GitHub manual workflow.

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

- Without `OPENAI_API_KEY`, the run uses **fallback** placeholder copy (clusters and citations still appear if feeds work).
- `--print` prints the text digest and skips email.
- `--dry-run` sets `DC_PULSE_DRY_RUN=1` and skips SMTP even if configured.

**`.env` precedence:** `load_config()` reads the repo-root `.env` with **override enabled**, so values in `.env` replace the same variables already set in the process environment. Use that to fix “empty `export` in the shell blocked my SMTP settings” issues on servers.

## Production: Debian VM (scheduled runs)

The weekly digest runs on a **Debian VM** (e.g. Proxmox) via **cron** or **systemd timer**, not on a fixed GitHub schedule.

1. **Cursor / SSH**: Connect with Remote-SSH and open the folder on the VM where the repo will live (or clone there in the integrated terminal).
2. **Bootstrap**: from the repo on the VM (or pass clone URL):

   ```bash
   chmod +x scripts/setup-vm.sh scripts/run-weekly.sh
   ./scripts/setup-vm.sh git@github.com:YOUR_ORG/DCPulse.git ~/DCPulse
   # or, if the repo is already cloned: ./scripts/setup-vm.sh "" ~/DCPulse
   ```

3. **Secrets**: copy [`.env.example`](.env.example) to `.env`, fill values (same names as the former GitHub repository secrets), then:

   ```bash
   chmod 600 .env
   ```

   Do not commit `.env`.

4. **Test**: use the **project virtualenv** (dependencies are not installed for system `python3`):

   ```bash
   ./.venv/bin/python -m src.main --print --dry-run
   ```

   Then a real send (ensure `DC_PULSE_DRY_RUN=0` or unset in `.env`, and SMTP vars set):

   ```bash
   ./.venv/bin/python -m src.main
   ```

5. **Schedule** (pick one):

   **Cron (Monday 08:00 America/Los_Angeles — example)**

   ```cron
   CRON_TZ=America/Los_Angeles
   0 8 * * 1 /home/YOU/DCPulse/scripts/run-weekly.sh
   ```

   **Cron (Monday 12:00 UTC — legacy Actions-style)**

   ```cron
   CRON_TZ=UTC
   0 12 * * 1 /home/YOU/DCPulse/scripts/run-weekly.sh
   ```

   **Systemd** (edit `User=` and paths in the unit files, then install):

   - [`scripts/systemd/dc-pulse.service`](scripts/systemd/dc-pulse.service)
   - [`scripts/systemd/dc-pulse.timer`](scripts/systemd/dc-pulse.timer)

   ```bash
   sudo cp scripts/systemd/dc-pulse.* /etc/systemd/system/
   # Edit /etc/systemd/system/dc-pulse.service: replace CHANGE_ME placeholders
   sudo systemctl daemon-reload
   sudo systemctl enable --now dc-pulse.timer
   ```

   If `OnCalendar=... UTC` is not supported by your systemd version, use cron with `CRON_TZ=UTC` or set the VM timezone and adjust the calendar.

   **Cron requires an executable script:** `scripts/run-weekly.sh` must be mode `755` (or otherwise executable). Without `+x`, cron will not run it and no log file is created. [`scripts/setup-vm.sh`](scripts/setup-vm.sh) and deploy scripts run `chmod +x scripts/*.sh`; the repo stores `run-weekly.sh` as executable in git.

6. **Logs and digest archive**: [`scripts/run-weekly.sh`](scripts/run-weekly.sh) appends to `logs/dc-pulse.log` and copies `last_digest.txt` to `archive/YYYY-MM-DD.txt`. Override with `DC_PULSE_LOG_DIR`, `DC_PULSE_ARCHIVE_DIR`, or `DC_PULSE_LOG_FILE` if needed.

### Email troubleshooting

- **`DC_PULSE_DRY_RUN`:** only `1`, `true`, `yes`, and `on` (case-insensitive) enable dry-run. **`0` does not** enable dry-run; email is allowed when SMTP and recipients are set.
- **Port 587 vs 465:** port **587** uses STARTTLS (`DC_PULSE_SMTP_TLS=1`). Port **465** uses implicit SSL (`SMTP_SSL`); the app defaults to SSL when the port is 465 unless `DC_PULSE_SMTP_SSL=0`.
- **Logs:** a successful send logs `Email sent successfully`; failures log `SMTP send failed` with a traceback. Cron output goes to `logs/dc-pulse.log` when using `run-weekly.sh`.

### Manual deploy from your PC to the VM

After editing prompts, `data/`, `src/`, or `requirements.txt`, refresh the VM without editing files only on the server:

- **PowerShell** (git mode: **commit and push to GitHub first**, then pull on the VM):

  ```powershell
  .\scripts\deploy-update.ps1 -VmHost vm.example.com -RemotePath /home/you/DCPulse
  # or use env vars:
  $env:DC_PULSE_VM_HOST = "vm.example.com"
  $env:DC_PULSE_VM_PATH = "/home/you/DCPulse"
  $env:DC_PULSE_SSH_USER = "you"   # optional
  .\scripts\deploy-update.ps1
  ```

  The VM checkout must be a **git clone** (with `.git`) so `git pull` works; a one-time `git init` + remote + `master` checkout is fine if the tree was copied without history.

- **Git Bash / WSL** (same env vars, or pass via `export`):

  ```bash
  export DC_PULSE_VM_HOST=vm.example.com DC_PULSE_VM_PATH=/home/you/DCPulse
  chmod +x scripts/deploy-update.sh
  ./scripts/deploy-update.sh
  ```

- **Rsync mode** (no `git push` required; needs `rsync` on your machine): set `DC_PULSE_DEPLOY_MODE=rsync` and run the same script. On Windows, use WSL or another environment where `rsync` exists, or use [`scripts/deploy-update.ps1`](scripts/deploy-update.ps1) with `-Mode rsync` if `rsync` is on your `PATH`.

## GitHub Actions (optional manual run only)

Workflow: [`.github/workflows/weekly-dc-pulse.yml`](.github/workflows/weekly-dc-pulse.yml)

- **Schedule**: disabled; production runs on the Debian VM.
- **Manual run**: Actions → Weekly DC Pulse → Run workflow (uses repository secrets).

### Repository secrets (manual workflow / reference for `.env`)

| Secret | Purpose |
|--------|---------|
| `OPENAI_API_KEY` | Required for full narrative digest (omit for fallback-only). |
| `OPENAI_MODEL` | Optional override (defaults to `gpt-4o-mini` in code if unset). |
| `DC_PULSE_EMAIL_TO` | Recipient(s), comma- or semicolon-separated on one line (spaces allowed). |
| `DC_PULSE_EMAIL_FROM` | From address. |
| `DC_PULSE_SMTP_HOST` | SMTP host. |
| `DC_PULSE_SMTP_PORT` | Port (e.g. `587`). |
| `DC_PULSE_SMTP_USER` | SMTP auth user if required. |
| `DC_PULSE_SMTP_PASSWORD` | SMTP password or app password. |
| `DC_PULSE_SMTP_TLS` | `1` for STARTTLS on submission port (e.g. 587). Not used when using implicit SSL on 465. |
| `DC_PULSE_SMTP_SSL` | Optional. Implicit SSL (`SMTP_SSL`); if omitted, defaults **on** when port is `465`. Set `0` to disable. |

If email secrets are missing, the job still runs and writes `last_digest.txt`; download the **last-digest** artifact from the workflow run.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DC_PULSE_DRY_RUN` | unset / `0` | `1`/`true`/`yes`/`on` = no email send. Plain `0` is not dry-run. |
| `DC_PULSE_USAGE_HISTORY` | `1` | `0` = do not track or block repeat primary URLs across weeks. |
| `DC_PULSE_USAGE_HISTORY_WEEKS` | `12` | Rolling window (ISO weeks) for blocked primary URLs. |
| `DC_PULSE_LOG_LEVEL` | `INFO` | Logging level. |
| `DC_PULSE_LOOKBACK_DAYS` | `14` | RSS item lookback. |
| `DC_PULSE_MAX_TOPICS` | `7` | Max ranked topics. |
| `DC_PULSE_HIGHLIGHT_REPOST` | `3` | Repost highlights. |
| `DC_PULSE_SKIP_LLM` | `0` | `1` = force fallback digest. |
| `DC_PULSE_LLM_TIMEOUT` | `120` | OpenAI timeout (seconds) for digest LLM. |
| `DC_PULSE_DATA_DIR` | `./data` | Override path to `sources.yml` / `topic_exclusions.yml`. |
| `DC_PULSE_WEB_SEARCH` | `0` | `1` = LLM search planner + OpenAI web search (Responses API) merged with RSS. |
| `DC_PULSE_WEB_SEARCH_MODEL` | `gpt-4o` | Model for Responses API calls with `web_search` tool; must support built-in web search. |
| `DC_PULSE_DEEP_RESEARCH` | `1` | Use deep seven-topic prompt; `0` = legacy `research.md` only. |
| `DC_PULSE_DEEP_RESEARCH_MODEL` | (main model) | Model for digest JSON. |
| `DC_PULSE_ARTICLE_DRAFTS` | `1` | `0` = skip long-form draft generation. |
| `DC_PULSE_ARTICLE_DRAFT_COUNT` | `2` | Number of full drafts. |
| `DC_PULSE_ARTICLE_DRAFT_WORDS` | `900` | Target length hint per draft. |
| `DC_PULSE_ARTICLE_DRAFT_TIMEOUT` | `300` | Seconds for draft LLM call. |
| `DC_PULSE_ARTICLE_DRAFT_MODEL` | (main model) | Model for article drafts. |
| `DC_PULSE_SMTP_SSL` | (auto) | Implicit SSL for SMTPS (port **465** by default). Set `0`/`1` to override auto-detection. |

See [`.env.example`](.env.example) for planner/search limits (`DC_PULSE_SEARCH_*`, `DC_PULSE_WEB_SEARCH_MODEL`).

## Data files

- [`data/sources.yml`](data/sources.yml) — RSS feeds, weights, enable/disable.
- [`data/topic_exclusions.yml`](data/topic_exclusions.yml) — noisy keyword filters.

Verify feed URLs periodically; some publishers change RSS endpoints.

## Prompts and voice

- [`src/prompts/`](src/prompts/) — ideation, research, repost copy, drafting rules.
- [`src/prompts/web_search_planner.md`](src/prompts/web_search_planner.md) — LLM search query planner (when web search is on).
- [`src/prompts/deep_research_seven.md`](src/prompts/deep_research_seven.md) — deep pass on the seven ranked topics (default digest system prompt).
- [`src/prompts/article_drafts.md`](src/prompts/article_drafts.md) — long-form draft selection and structure.
- [`src/voice/profile.md`](src/voice/profile.md) — consultant/CFA voice guide.

## Architecture

1. **Collect** RSS from `sources.yml`; optionally **web search** (planner in [`src/prompts/web_search_planner.md`](src/prompts/web_search_planner.md)—including a **mandatory TELUS** pension/benefits query when web search is on—plus OpenAI Responses API with `web_search` tool) merged as additional articles before lookback.
2. **Normalize** / dedupe → **cluster** (token overlap) → **rank** → select **top 7** + **3** repost highlights.
3. **Deep research LLM** ([`src/prompts/deep_research_seven.md`](src/prompts/deep_research_seven.md)) produces the weekly digest JSON; repost URLs are grounded in cluster articles.
4. **Article drafts LLM** selects two topics for long-form posts and generates Markdown drafts ([`src/prompts/article_drafts.md`](src/prompts/article_drafts.md)); configurable via `DC_PULSE_ARTICLE_DRAFTS` / `DC_PULSE_ARTICLE_DRAFT_COUNT`.
5. Render HTML + plain text (digest + drafts); send via SMTP.

Enable web search: set `DC_PULSE_WEB_SEARCH=1` and `OPENAI_API_KEY` (used for the query planner and for [Responses API](https://platform.openai.com/docs/guides/tools-web-search) calls with the `web_search` tool). Optionally set `DC_PULSE_WEB_SEARCH_MODEL` if the default `gpt-4o` is not desired.

## License

Use and modify for your practice; add a license file if you redistribute.
