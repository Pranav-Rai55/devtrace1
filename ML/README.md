# DevTrace — AI Code Intelligence Platform

> Analyze any GitHub repository or local repo instantly. Get deep AI-powered insights into quality, security, complexity, and architecture — with executive summaries, prioritized suggestions, and real working fixes.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure (optional but recommended)
cp .env.example .env
# Edit .env with your API keys

# 3. Start the server
python main.py

# 4. Open devtrace_dashboard.html in your browser
```

---

## What it does

### Platform Flow

1. **Repository Intake** — accepts `github.com/org/repo`, `org/repo`, git URLs, and local repository paths.
2. **Intelligence Analysis** — runs static analysis plus ML/DL-inspired scoring models in parallel.
3. **AI Recommendation Layer** — ranks issues, generates suggested fixes, and drafts an action roadmap.
4. **Dashboard & Export** — renders the intelligence dashboard and supports PDF/HTML/JSON export.

### Analysis Engines (run in parallel)

| Engine | What it detects |
|--------|----------------|
| **Quality** | Cyclomatic + cognitive complexity, Halstead metrics, code smells, god classes, dead code, duplication rate |
| **Security** | 25 OWASP rules, secrets scanning (AWS/GitHub/OpenAI keys), Bandit deep scan, CWE tagging |
| **Performance** | N+1 queries, blocking I/O in async, regex in loops, wildcard imports, mutable default args |
| **Architecture** | Circular dependencies, layer violations, coupling/cohesion scores, orphan modules |
| **Dependencies** | OSV.dev vulnerability DB — PyPI, npm, Go modules |
| **ML Engine** | 7 ML models (see below) |

### ML Engine — 7 Models

| Model | Description |
|-------|-------------|
| **1 Semantic Clone Detector** | TF-IDF cosine similarity on AST tokens — finds exact, renamed, and semantic duplicates |
| **2 Bug Likelihood Predictor** | Logistic regression on 18 AST features — scores every function 0–100 for bug risk |
| **3 Type Inference Engine** | AST-based inference — flags untyped functions and suggests param/return types |
| **4 Docstring Generator** | Generates Google-style docstrings for undocumented functions |
| **5 ML Complexity Estimator** | Ridge regression — catches "deceptively complex" dense code missed by cyclomatic |
| **6 Vulnerability Classifier** | Multi-label TF-IDF classifier across 8 vulnerability categories |
| **7 NL Code Search** | TF-IDF index — search functions with natural language queries |

### All 5 Phases

| Phase | Feature |
|-------|---------|
| **1** | SQLite history — every run stored, trend charts over time |
| **2** | GitHub Actions CI/CD — PR comments, quality gates, merge blocking |
| **3** | GitHub OAuth login + real AI-generated fixes (Claude/GPT) |
| **4** | Slack & Teams notifications on analysis complete |
| **5** | PDF, HTML, JSON report export |

---

## Configuration

Copy `.env.example` to `.env` and set:

```env
# For real AI-generated code fixes:
ANTHROPIC_API_KEY=sk-ant-...
# or
OPENAI_API_KEY=sk-...

# For GitHub OAuth login (private repos):
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# For Slack notifications:
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

---

## API Reference

```
POST   /api/v1/analyze              Start analysis
GET    /api/v1/analyze/{id}         Poll status / get report
WS     /api/v1/ws/{id}             WebSocket real-time progress
GET    /api/v1/search?q=...         NL code search
GET    /api/v1/history/{repo_b64}   Past runs for a repo
GET    /api/v1/history/{b64}/trend  Trend data for charts
GET    /api/v1/runs/{id}            Full report by run ID
GET    /api/v1/repos                All repos analyzed by user
GET    /api/v1/leaderboard          Top repos by quality
GET    /api/v1/auth/login           GitHub OAuth redirect
GET    /api/v1/auth/me              Current user profile
POST   /api/v1/auth/logout          Sign out
GET    /api/v1/notifications/settings
POST   /api/v1/notifications/settings
POST   /api/v1/notifications/test
GET    /api/v1/export/{id}/pdf      PDF report download
GET    /api/v1/export/{id}/html     HTML report download
GET    /api/v1/export/{id}/json     JSON export
GET    /api/v1/cache/stats          Cache info
DELETE /api/v1/cache                Clear cache
GET    /api/v1/health               Health check
GET    /docs                        Swagger UI
```

---

## GitHub Actions

Copy `.github/workflows/devtrace.yml` into any target repo. On every PR it:
- Posts an analysis summary as a PR comment
- Blocks merges if HIGH severity issues found
- Fails if quality score < 30

---

## Docker

```bash
docker compose up --build
```

---

*Built with FastAPI · SQLite · scikit-learn · Chart.js · OSV.dev*
