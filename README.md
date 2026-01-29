# DevFlow Agent 🚀

AI-powered developer workflow automation that turns feature requests into working code.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   📝 PLAN       │───▶│   ✅ CHECKLIST  │───▶│   🔧 EXECUTE    │───▶│   📋 SUMMARY    │
│  Analyze repo   │    │  Break down     │    │  Write code     │    │  PR-ready       │
│  Create plan    │    │  into steps     │    │  Run tests      │    │  description    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ✨ Features

- **🤖 LLM-Powered** — Uses DeepSeek and Kimi for intelligent code generation
- **📊 4-Step Workflow** — Plan → Checklist → Execute → Summary (LangGraph)
- **🔄 Auto-Retry** — Automatic validation and repair loops
- **🌲 AST Parsing** — Smart code understanding with tree-sitter
- **🎨 Modern UI** — Next.js dashboard with dark mode and real-time updates
- **🐳 Docker Ready** — One-command deployment with health checks

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- DeepSeek API key ([Get one here](https://platform.deepseek.com))

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/devflow-agent.git
cd devflow-agent
cp .env.example .env
```

Edit `.env` and add your API key:
```env
DEEPSEEK_API_KEY=your_api_key_here
```

### 2. Start Services

```bash
docker compose -f infra/docker-compose.yml up -d
```

### 3. Open Dashboard

Navigate to [http://localhost:3000](http://localhost:3000)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      NEXT.JS FRONTEND (3000)                     │
│     Dashboard  │  New Run Form  │  Run Detail  │  Artifacts     │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP/Polling
┌──────────────────────────────▼──────────────────────────────────┐
│                     FASTAPI BACKEND (8000)                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     LangGraph Workflow                       ││
│  │   Plan → Checklist → Execute → Validate → Summary           ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ LLM Router  │  │   Tools     │  │       Database          │  │
│  │ DeepSeek    │  │ repo_map    │  │  PostgreSQL + Alembic   │  │
│  │ Kimi        │  │ git_ops     │  │  Users, Runs, Artifacts │  │
│  └─────────────┘  │ sandbox     │  └─────────────────────────┘  │
│                   └─────────────┘                                │
└──────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
devflow-agent/
├── apps/
│   ├── api/                  # FastAPI backend
│   │   ├── src/
│   │   │   ├── agent/        # LangGraph workflow & prompts
│   │   │   ├── api/          # Routes & main app
│   │   │   ├── database/     # SQLModel tables & migrations
│   │   │   ├── llm/          # DeepSeek & Kimi adapters
│   │   │   └── tools/        # Repo, Git, Sandbox tools
│   │   └── alembic/          # DB migrations
│   └── web/                  # Next.js frontend
│       └── src/
│           ├── app/          # App Router pages
│           ├── components/   # shadcn/ui components
│           └── lib/          # API client
├── infra/
│   ├── docker/               # Dockerfiles
│   └── docker-compose.yml    # Full stack deployment
├── packages/
│   └── shared/               # Shared TypeScript types
└── tests/
    └── eval_set/             # Evaluation dataset
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/runs` | Create new agent run |
| `GET` | `/api/runs` | List all runs |
| `GET` | `/api/runs/{id}` | Get run status |
| `GET` | `/api/runs/{id}/artifacts` | Get run artifacts (plan, checklist, summary) |
| `GET` | `/api/runs/{id}/diff` | Get generated diff |
| `DELETE` | `/api/runs/{id}` | Cancel run |
| `GET` | `/api/health` | Health check |

## 🛠️ Local Development

### Backend (FastAPI)

```bash
cd apps/api
pip install uv
uv pip install -e ".[dev]"
python -m uvicorn src.api.main:app --reload
```

### Frontend (Next.js)

```bash
cd apps/web
npm install
npm run dev
```

### Database

```bash
# Start Postgres
docker compose -f infra/docker-compose.yml up postgres -d

# Run migrations
cd apps/api
alembic upgrade head
```

## ⚙️ Configuration

See [`.env.example`](.env.example) for all options. Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API key | ✅ |
| `KIMI_API_KEY` | Kimi/Moonshot API key (fallback) | ❌ |
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `JWT_SECRET_KEY` | Secret for auth tokens | ✅ |

## 🗺️ Roadmap

- [ ] GitHub OAuth integration
- [ ] CLI enhancements (`devflow run`, `devflow eval`)
- [ ] SSE for real-time streaming updates
- [ ] Evaluation harness with metrics dashboard
- [ ] Sandbox container for isolated execution

## 📄 License

MIT © 2026
