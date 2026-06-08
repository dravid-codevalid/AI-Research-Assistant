# Phase 3: LiteLLM Gateway & Multi-Tenancy

In Phase 3, we move from calling a single model (Bedrock) to building a robust AI proxy that routes traffic to multiple models while tracking costs per user and team.

## 1. The API Gateway Pattern & LiteLLM

### What is it?
An API Gateway sits between your application backend and external services (like AWS, OpenAI, etc.). Instead of your backend knowing the API format for 10 different AI providers, it talks only to the Gateway using one standard format (usually the OpenAI standard).
**LiteLLM** is an open-source proxy server that does exactly this for AI models.

### How it will be used in this project
We will run LiteLLM as a separate service on `localhost:4000`.
Instead of our FastAPI backend calling `boto3` directly, we will update our code to send an HTTP POST request to LiteLLM:
```json
// Request from FastAPI to LiteLLM
POST http://localhost:4000/v1/chat/completions
{
  "model": "bedrock/amazon.titan-text-express-v1",
  "messages": [{"role": "user", "content": "Hello!"}]
}
```
**Why it matters**: This decouples our code from the provider. If we decide to switch from Bedrock to local models (like Ollama), we only change the string `"bedrock/amazon.titan"` to `"ollama/llama3"`. The Python code remains untouched.

## 2. Multi-Tenancy: Users & Workspaces

### What is it?
Multi-tenancy means a single instance of software serves multiple distinct groups of users (tenants). Think of Slack: multiple organizations use it, but their data is strictly isolated.

### How it will be used in this project
We will introduce new Domain Entities in our backend: `User` and `Workspace`.
- A **Workspace** represents a company or team.
- A **User** is an individual who belongs to one or more Workspaces.

```python
# backend/domain/entities/workspace.py
class Workspace:
    id: str
    name: str

# backend/domain/entities/user.py
class User:
    id: str
    name: str
    workspaces: list[str]
```

When a user submits a question via the React frontend, they must pass their `user_id` and the `workspace_id` they are currently acting under.

## 3. Token Tracking & Cost Attribution

### What is it?
LLMs don't charge per request; they charge per "token" (roughly 3/4 of a word). You need to know exactly how many tokens were used in the prompt (input) and the completion (output).

### How it will be used in this project
LiteLLM has built-in database tracking (using an internal SQLite DB).
When we configure LiteLLM, we will create virtual "Teams" (which map to our Workspaces) and virtual "Keys" (which map to our Users).

When FastAPI calls LiteLLM, it passes the user's LiteLLM Key in the header:
```python
headers = {
    "Authorization": f"Bearer {user_lite_llm_key}"
}
```
LiteLLM automatically intercepts this, counts the tokens used, calculates the exact cost in fractions of a cent, and attributes it to the User and Team in its SQLite database.

**Why it matters**: This is critical for enterprise SaaS. Without this, one rogue user writing a script to call your AI endlessly could bankrupt you. LiteLLM allows us to set hard budget caps (e.g., "$10 per Workspace per month").

## 4. CRUD Endpoints

### What is it?
CRUD stands for Create, Read, Update, Delete. These are the four basic operations for persistent storage.

### How it will be used in this project
To support multi-tenancy, our FastAPI backend will need standard REST routes:
- `POST /api/workspaces` (Create)
- `GET /api/workspaces` (Read)
- `POST /api/users` (Create)
- `POST /api/workspaces/{id}/members` (Update/Link)

This data will be stored locally in our backend's own SQLite database via SQLAlchemy, while the AI cost data lives in LiteLLM's SQLite database.
