# PowerballBot

A data-driven NZ Lotto Powerball suggestion engine — built as a **learning project** for automation, data engineering, Docker, and CI/CD.

Twice a week (after Wednesday and Saturday draws), the system is designed to scrape the latest result, run historical analysis, and send 8–10 weighted number suggestions to Slack.

> **Disclaimer:** Lottery draws are statistically independent events. Past results do not influence future draws. This project is an exercise in data engineering, pipeline architecture, and automation — **not** a strategy for winning money.

**DevLog:** [DevLog #1 — Building a Data-Driven Powerball Prediction Engine with Python](https://ellys-lab.hashnode.dev/devlog-1-building-a-data-driven-powerball-prediction-engine-with-python)

---

## What it does

1. **Collect** — Historical draws live in a cleaned CSV. A polite crawler fetches only the **latest** draw and appends it (no full re-scrape each run).
2. **Analyze** — A scoring formula ranks candidate numbers using signals like frequency, recency, and gap (how long since a number last appeared).
3. **Filter** — Combinations with extreme odd/even ratios or too many consecutive numbers are excluded.
4. **Notify** — Final suggestions are formatted and sent via Slack webhook.

The core idea is not that patterns *predict* the future — it's that filtering statistically extreme combinations produces a more "average" set of picks. Whether that's useful is debatable. Whether it's a good reason to build a data pipeline — absolutely.

---

## Project structure

```
PowerballBot/
├── data/
│   ├── draws_clean.csv       # Cleaned historical draws (2008 ~ present)
│   └── Powerball_NZ.csv      # Raw export (reference)
├── notebooks/
│   └── exploration.ipynb     # Formula design sandbox (Step 1a — in progress)
├── crawler.py                # Scrape latest draw → append to CSV (planned)
├── predictor.py              # Run finalized formula → generate lines (planned)
├── notifier.py               # Format output → Slack webhook (planned)
├── config.py                 # Tunable weights, thresholds, constants (planned)
├── main.py                   # Orchestrator: crawler → predictor → notifier (planned)
├── requirements.txt
├── .env                      # SLACK_WEBHOOK_URL etc. (never committed)
├── Dockerfile                # Containerization (planned)
└── .github/workflows/        # Scheduled GitHub Actions (planned)
```

**Design principle — loose coupling:** each module does exactly one job. The crawler doesn't know how numbers are scored. The notifier doesn't know how they're generated. If the predictor is rewritten, the other modules stay untouched.

---

## Data

**Target game:** NZ Lotto Powerball — 6 main numbers (1–40) + 1 Powerball (1–10).

**Historical data:** ~1,520 draws from 2008-01-05 through present, cleaned into `data/draws_clean.csv`.

| Column | Description |
|--------|-------------|
| `draw_number` | Official draw ID |
| `draw_date` | Date of draw (YYYY-MM-DD) |
| `main_1` … `main_6` | Six main numbers |
| `bonus` | Bonus ball (same 1–40 pool; used in frequency analysis, **not** in final picks) |
| `powerball` | Powerball number (separate 1–10 pool) |

**Sources:**
- Historical bulk data: [lottolyzer.com](https://www.lottolyzer.com/) (public factual results)
- Ongoing updates (planned): [mylotto.co.nz/results](https://mylotto.co.nz/results) — public results pages are allowed per `robots.txt`

---

## Current status

| Step | Description | Status |
|------|-------------|--------|
| 0 | Historical data collected and cleaned | Done |
| 1a | `notebooks/exploration.ipynb` — explore frequency, recency, gaps, scoring | In progress |
| 1b | `predictor.py` — port finalized formula, filters, 8–10 lines | Planned |
| 2 | `notifier.py` — Slack webhook integration | Planned |
| 3 | `crawler.py` — scrape latest draw, polite bot rules | Planned |
| 4 | `main.py` — orchestrator entry point | Planned |
| 5 | `Dockerfile` — containerize | Planned |
| 6 | GitHub Actions — Wed/Sat cron schedule | Planned |
| 7+ | Render / AWS migration (cloud learning) | Later |

Details will be refined during implementation. See the [devlog series](https://ellys-lab.hashnode.dev/devlog-1-building-a-data-driven-powerball-prediction-engine-with-python) for build notes.

---

## Setup

**Requirements:** Python 3.11+ (tested on 3.13), git

```powershell
# Clone the repo
git clone https://github.com/Ellywoooo/PowerballBot.git
cd PowerballBot

# Create and activate a virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

**Run the exploration notebook:**

```powershell
jupyter notebook notebooks/exploration.ipynb
```

Or open `notebooks/exploration.ipynb` directly in Cursor / VS Code with the Jupyter extension (select the `venv` kernel).

**Environment variables (when notifier is built):**

Create a `.env` file in the project root (already excluded from git):

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

---

## Tech stack

| Layer | Tool |
|-------|------|
| Language | Python 3.11+ |
| Data analysis | Pandas, Matplotlib |
| Scraping (planned) | Requests, BeautifulSoup |
| Containerization (planned) | Docker |
| Automation (planned) | GitHub Actions |
| Notifications (planned) | Slack Webhook |

---

## Polite bot rules (crawler)

When `crawler.py` is implemented, it will follow these rules:

- Identify the bot in the `User-Agent` header (name + contact)
- Random delay (1.5–3 s) between requests
- Request only the results page — nothing else
- Back off on HTTP 429 / 503 responses
- Check for duplicates before appending to CSV
- Cache responses locally during development (`cache/` — gitignored)

The crawler runs twice a week and fetches one new result per run.

---

## License

Personal learning project. No license specified yet.
