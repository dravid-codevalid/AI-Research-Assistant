# 🔬 AI Research Assistant

A full-stack AI Research Assistant built with **React + TypeScript** (frontend) and **FastAPI** (backend), progressively integrating AWS Bedrock, LiteLLM, DSPy, Temporal, and MLflow across 6 development levels.

## 🏗️ Architecture

- **Frontend**: React 19 + Vite + TypeScript — Premium dark glassmorphism UI
- **Backend**: FastAPI with Clean Architecture + Hexagonal (Ports & Adapters)
- **Database**: SQLite + SQLAlchemy (async)
- **AI Gateway**: LiteLLM proxy → AWS Bedrock / Google Gemini / Groq
- **Workflows**: Temporal for async distributed execution
- **MLOps**: DSPy GRPO optimization + MLflow tracking

## 📁 Project Structure

```
CodeValidResearchAssistant/
├── backend/                # FastAPI + Clean Architecture
│   ├── domain/             # Core entities, value objects, ports
│   │   ├── entities/       # User, Workspace, UserWorkspace
│   │   ├── ports/          # ILLMProvider, IUserRepository, IWorkspaceRepository
│   │   └── value_objects/  # Answer
│   ├── use_cases/          # Application business logic
│   ├── adapters/           # Concrete implementations
│   │   ├── llm/            # EchoLLM, BedrockLLM, LiteLLMLLM, LiteLLMAdmin
│   │   └── repositories/   # SqlAlchemy User/Workspace repos
│   ├── api/                # Routes, schemas, middleware
│   │   ├── routes/         # ask, health, users, workspaces, usage
│   │   └── schemas/        # Pydantic request/response models
│   ├── infrastructure/     # Database engine, ORM models
│   ├── litellm_config.yaml # LiteLLM proxy configuration
│   └── tests/
├── frontend/               # React + Vite + TypeScript
│   └── src/
│       ├── components/     # Shared design system (Layout, Sidebar, etc.)
│       ├── features/       # Feature modules
│       │   ├── chat/       # Chat page with streaming + model selector
│       │   ├── usage/      # Token Usage Dashboard
│       │   └── workspace/  # Workspace/User selector + API
│       ├── context/        # WorkspaceContext (global state)
│       └── styles/         # CSS custom properties & design tokens
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # Edit with your API keys
uvicorn main:app --reload --port 8000
```

### LiteLLM Proxy (Level 3+)
```bash
cd backend
litellm --config litellm_config.yaml --port 4000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Verify
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs
- LiteLLM Proxy: http://localhost:4000/health
- Health check: http://localhost:8000/api/health

## 🧪 Testing

```bash
cd backend
python -m pytest -v
```

## 📊 Level Progress

| Level | Description | Status |
|-------|-------------|--------|
| 1 | Full-Stack Foundation (React + FastAPI) | 🟢 Complete |
| 2 | Cloud AI Integration (AWS Bedrock) | 🟢 Complete |
| 3 | LiteLLM Gateway + Users/Workspaces | 🟢 Complete |
| 4 | AI Agent with Tools (DSPy + Assistant-UI) | 🟢 Complete |
| 5 | Temporal Workflows | 🟢 Complete |
| 6 | DSPy Optimization + MLflow | 🟢 Complete |

## 📝 Decisions

- **Clean Architecture**: Enables swapping LLM backends (Echo → Bedrock → LiteLLM) without touching use cases or API routes
- **Hexagonal (Ports & Adapters)**: Each integration is an adapter implementing a port interface
- **LiteLLM as gateway**: Single OpenAI-compatible API for all providers (Bedrock, Gemini, Groq)
- **SQLAlchemy async**: Production-grade ORM with async support for User/Workspace management
- **Feature-based frontend**: Each UI feature (chat, usage, workspace) is self-contained
- **Dark glassmorphism UI**: Premium, ambient design with Apple-like glossy aesthetics
