<p align="center">
  <img src="frontend/public/logo.svg" width="120" alt="ImpactHub Logo" />
</p>

<h1 align="center">ImpactHub</h1>

<p align="center">
  <b>Unified Research Impact Dashboard</b><br/>
  Personal research portfolio + 147-school graduate advisor directory + AI-native talent search.
</p>

<p align="center">
  <b>English</b> | <a href="README.zh.md">中文</a>
</p>

<p align="center">
  <a href="#features">Features</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#configuration">Configuration</a> &bull;
  <a href="#architecture">Architecture</a>
</p>

---

## Pages

| Route | Purpose |
|-------|---------|
| `/profile/:id` | Per-researcher dashboard (papers / repos / HF / persona / capability / poem / share cards) |
| `/leaderboard` | Total + young scholar + 6 direction leaderboards (top 10000 exact rank, then percentile) |
| `/recruit` | **B2B AI talent search** — recruiter pastes JD → LLM extracts criteria → DB filter → LLM rerank with reasoning |
| `/advisor` | **Graduate advisor directory** — 147 双一流 (985/211) universities, LLM-driven crawler for colleges + faculty stubs |
| `/users` | All ImpactHub profiles |
| `/docs` | System overview |

## Features

### Cross-Platform Profile

One profile that unifies your presence across **Semantic Scholar**, **GitHub**, and **Hugging Face**. Enter your Scholar ID — the system auto-discovers your linked GitHub and HF accounts.

### Citation Intelligence

- H-index auto-computation and CCF-A/B/C venue classification
- Identifies **top scholars** (h-index ≥ 50) and **notable scholars** (h-index ≥ 25) who cite your work
- LLM-powered honor tag enrichment — detects IEEE Fellow, ACM Fellow, 院士 among your citers
- Per-paper citation drill-down with context snippets

### Growth Tracking

- Daily metric snapshots: citations, h-index, stars, forks, downloads, likes
- Interactive trend charts with 30/60/90/365-day windows
- Milestone system: automatic achievements when you hit thresholds (100 citations, 1K stars, etc.)

### Web Buzz Monitoring

- Perplexity-powered web search to gauge your research visibility
- Heat level classification (hot / medium / cold) with source links

### AI-Powered Summary

- LLM-generated researcher bio capturing your research identity
- Auto-generated research tags from your publication topics

### Researcher Persona (12 MBTI-style types)

- LLM picks one of 12 meme personas (GOAT / PI / WOLF / JUAN / KPI / MONK / NINJA / PROOF / SENSEI / VIRAL / BDFL / HYPE) with AI-generated illustrations
- 4-axis dimensions (output / ecosystem / seniority / collaboration) with continuous scores

### Multi-Direction Capability Profile

- LLM identifies 1-4 research directions a scholar actually works in
- Per-direction role (originator / early_adopter / extender / follower) + weight + achievements + representative works
- Avoids the single-tag oversimplification

### Research Evolution Tree, Annual Poem, Career Timeline

- Tree-shaped research trajectory: time on Y axis, research branches on X
- Xiaohongshu-style annual research poem (10-14 verses, data-driven)
- LLM + web-search career timeline (education + positions, with sources)

### Leaderboards

- Total / Young Scholar (first paper <10y) / 6 directions (LLM, CV, VLM, Systems, Theory, RL)
- Top 10000 shows exact rank; beyond that shows percentile only

### B2B Recruit (AI Talent Search)

- Free-text JD → LLM extracts structured criteria (direction, seniority, h-index threshold, must/nice keywords, honors)
- DB coarse filter → top 40 candidate dossiers → LLM rerank with `match_score`, `tier`, fit reasoning, concerns, key works

### Graduate Advisor Directory (`/advisor`)

- Seed: 147 双一流 universities (incl. all 985/211), authoritative source: 教育部 2022 第二轮双一流 list
- LLM-driven generic crawler — no per-school adapters; uses heuristic college/teacher extraction with JS-redirect follow + permissive SSL for old .edu.cn
- Three-layer pipeline: school directory → college list → advisor stubs (name + title + homepage)

### Grant Application Tools

- **Research Basis Generator** for NSFC, Changjiang, Wanren, and other Chinese grant types
- Tone-adaptive formatting: "potential + feasibility" for youth grants vs. "originality + leadership" for senior grants
- Paper selection UI with evidence preview (citation analysis + notable scholars + linked repos)

### Smart Export

- Paper list export: Markdown, BibTeX, JSON
- Filter by year, CCF rank, citation count, first-author
- Comprehensive CV-style summary JSON

### Auto Refresh

- Background scheduler refreshes all data every 6 hours
- Manual refresh on demand via API

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI-compatible API key (for AI summary & buzz features)

### 1. Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env from template
cp ../.env.example .env
# Edit .env and fill in your API key

python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 2. Frontend

```bash
cd frontend
npm install

# Development
npm run dev

# Production build (served by backend)
npm run build
```

### 3. One-Command Serve (optional)

```bash
# Serves frontend dist/ + proxies /api to backend
python serve.py 19487
```

Open `http://localhost:19487` and enter your Semantic Scholar ID to get started.

---

## Configuration

Copy `.env.example` to `backend/.env`:

| Variable | Description | Required |
|----------|-------------|----------|
| `LLM_API_BASE` | OpenAI-compatible API endpoint | Yes |
| `LLM_API_KEY` | API key for the LLM provider | Yes |
| `LLM_BUZZ_MODEL` | Model for buzz & summary generation (default: `gpt-5`) | No |
| `OUTBOUND_PROXY` | HTTP proxy for outbound API calls | No |
| `GITHUB_TOKEN` | GitHub PAT for higher rate limits | No |

---

## Architecture

```
impacthub/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry + static file serving
│   │   ├── config.py            # Environment & constants
│   │   ├── models.py            # SQLAlchemy ORM
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── routers/
│   │   │   ├── profile.py       # Profile CRUD & account linking
│   │   │   ├── stats.py         # Aggregated statistics
│   │   │   ├── citations.py     # Citation analysis & scholar classification
│   │   │   ├── growth.py        # Growth snapshots & trends
│   │   │   ├── milestones.py    # Achievement tracking
│   │   │   ├── buzz.py          # Web presence monitoring
│   │   │   ├── ai_summary.py    # LLM-generated bios & tags
│   │   │   ├── reports.py       # Grant research basis generator
│   │   │   └── data.py          # Export endpoints
│   │   ├── services/            # Business logic per domain
│   │   └── tasks/
│   │       └── scheduler.py     # APScheduler (6h refresh cycle)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # Setup, Profile, Milestone, Users
│   │   ├── components/          # Charts, cards, modals, exporters
│   │   └── lib/                 # API client, utils, venue data
│   └── package.json
└── serve.py                     # Simple dev proxy server
```

**Tech Stack**: FastAPI + SQLAlchemy + aiosqlite | React 19 + Tailwind CSS 4 + Recharts | Semantic Scholar + GitHub + Hugging Face APIs

---

## License

MIT
