# DC Pulse — project index

Machine-readable map for navigation and tooling. **Source of truth is the code**; refresh this file when layout changes.

## Entry point

| What | Where |
|------|--------|
| CLI / pipeline | [`src/main.py`](src/main.py) — `python -m src.main` |
| Config | [`src/config.py`](src/config.py) — `load_config()` loads repo `.env` with **override**; env vars `DC_PULSE_*`, `OPENAI_*` |
| Env template | [`.env.example`](.env.example) |

## Data flow (short)

`collect` (RSS ± web search) → `normalize` / dedupe / exclusions → `cluster` → `rank` → `select` (usage history) → `generate_digest` LLM ± `article_drafts` → `render_email` / `last_digest.txt`

## Directory index

```
DCPulse/
├── src/
│   ├── main.py              # Pipeline orchestration, email, last_digest.txt
│   ├── config.py            # Config dataclass + load_config()
│   ├── hardening.py         # Low-confidence augmentation
│   ├── llm/
│   │   ├── generate_digest.py   # Weekly digest JSON via OpenAI
│   │   └── article_drafts.py    # Long-form drafts from digest
│   ├── output/
│   │   ├── schema.py        # Pydantic: WeeklyDigest, TopicDigest, etc.
│   │   └── render_email.py  # Text/HTML email + SMTP
│   ├── pipeline/
│   │   ├── normalize.py     # Scoring, dedupe, exclusions, lookback
│   │   ├── cluster.py       # Jaccard topic clusters
│   │   ├── rank.py          # Cluster scoring
│   │   ├── select.py        # Top 7 + repost highlights, primary article pick
│   │   └── usage_history.py # weekly_usage.json, canonical_url, rolling block list
│   ├── research/
│   │   ├── web_search.py    # OpenAI Responses + web_search collection
│   │   ├── search_planner.py
│   │   ├── openai_web_search.py
│   │   └── models.py
│   ├── sources/
│   │   ├── catalog.py       # sources.yml loader
│   │   └── collect.py       # RSS → RawArticle
│   ├── prompts/             # LLM system/user markdown (loaded by llm/*)
│   └── voice/
│       └── profile.md       # Voice/tone for prompts
├── data/
│   ├── sources.yml          # Feed catalog
│   ├── topic_exclusions.yml # Keyword / topic filters
│   └── weekly_usage.json    # Featured primary URLs (week-to-week uniqueness)
├── tests/                   # pytest
├── scripts/                 # setup-vm.sh, run-weekly.sh, systemd, deploy-update.ps1 / .sh
├── .github/workflows/       # Manual workflow; VM is primary scheduler
├── .cursor/rules/           # Cursor project rules (*.mdc)
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Key modules (by concern)

| Concern | Module(s) |
|---------|-----------|
| RSS + feeds | `src/sources/collect.py`, `catalog.py` |
| Web search augmentation | `src/research/web_search.py`, `search_planner.py` |
| Topic building | `src/pipeline/cluster.py`, `rank.py`, `select.py` |
| Cross-run URL memory | `src/pipeline/usage_history.py` + `data/weekly_usage.json` |
| LLM I/O | `src/llm/generate_digest.py`, `article_drafts.py` + `src/prompts/*.md` |
| Output | `src/output/schema.py`, `render_email.py` |

## Tests

```bash
python -m pytest
```

(Use the project venv’s `python` if dependencies are not installed globally.)

Files: `tests/test_*.py` — schema, render, web_search, usage_history, openai_web_search parse.

## Deploy (PC → VM)

Git mode: push `master` (or your branch) to `origin`, then [`scripts/deploy-update.ps1`](scripts/deploy-update.ps1) or [`scripts/deploy-update.sh`](scripts/deploy-update.sh) with `DC_PULSE_VM_HOST` and `DC_PULSE_VM_PATH` (or `-VmHost` / `-RemotePath` on PowerShell). Requires a **git** checkout on the VM.

## Generated / local-only (usually gitignored)

- `.env` — secrets (see `.env.example`)
- `last_digest.txt` — last run text digest (repo root)
