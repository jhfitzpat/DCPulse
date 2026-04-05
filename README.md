# DC Pulse Weekly Pipeline

Automated weekly workflow that collects Canadian pension and benefits coverage from curated RSS feeds, clusters and ranks topics, optionally enriches them with an OpenAI narrative aligned to DC consulting prompts, and emails a digest (up to **7** topics, **3** repost highlights with **two** copy angles each).

Manual posting to LinkedIn and final article editing stay **out of scope** for v1.

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
- `--dry-run` skips SMTP even if configured.

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

4. **Test**: `./.venv/bin/python -m src.main --print --dry-run`, then a real send if SMTP is configured.

5. **Schedule** (pick one):

   **Cron (Monday 12:00 UTC, same as the old Actions schedule)**

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

6. **Logs and digest archive**: [`scripts/run-weekly.sh`](scripts/run-weekly.sh) appends to `logs/dc-pulse.log` and copies `last_digest.txt` to `archive/YYYY-MM-DD.txt`. Override with `DC_PULSE_LOG_DIR`, `DC_PULSE_ARCHIVE_DIR`, or `DC_PULSE_LOG_FILE` if needed.

### Manual deploy from your PC to the VM

After editing prompts, `data/`, `src/`, or `requirements.txt`, refresh the VM without editing files only on the server:

- **PowerShell** (git mode: push to GitHub first, then pull on the VM):

  ```powershell
  $env:DC_PULSE_VM_HOST = "vm.example.com"
  $env:DC_PULSE_VM_PATH = "/home/you/DCPulse"
  $env:DC_PULSE_SSH_USER = "you"   # optional
  .\scripts\deploy-update.ps1
  ```

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
| `DC_PULSE_EMAIL_TO` | Recipient(s), comma-separated. |
| `DC_PULSE_EMAIL_FROM` | From address. |
| `DC_PULSE_SMTP_HOST` | SMTP host. |
| `DC_PULSE_SMTP_PORT` | Port (e.g. `587`). |
| `DC_PULSE_SMTP_USER` | SMTP auth user if required. |
| `DC_PULSE_SMTP_PASSWORD` | SMTP password or app password. |
| `DC_PULSE_SMTP_TLS` | `1` for STARTTLS (default in app). |

If email secrets are missing, the job still runs and writes `last_digest.txt`; download the **last-digest** artifact from the workflow run.

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
