# Phase 0: Prerequisites

Before diving into the core architecture of the AI Research Assistant, you need to understand the foundational tools and concepts that make modern web and Python development possible.

## 1. Version Control with Git

### What is it?
Git is a distributed version control system. It tracks changes to your code over time, allowing you to revert to previous states, branch off to try new features without breaking the main code, and collaborate with others.

### How it's used in this project
Look at the `.gitignore` file in the root directory:
```text
# .gitignore
venv/
__pycache__/
.env
.pytest_cache/
node_modules/
```
**Why it matters**: Git tracks all files by default. The `.gitignore` file tells Git to ignore certain files. We ignore `.env` because it contains secret API keys (like your AWS credentials). We ignore `node_modules/` and `venv/` because they contain downloaded dependencies that can be huge and should be reinstalled locally rather than committed.

## 2. Web Fundamentals: HTML, CSS, JavaScript

### What are they?
- **HTML**: The structure of a webpage (buttons, inputs, text).
- **CSS**: The styling (colors, layout, animations).
- **JavaScript**: The logic (what happens when you click, fetching data).

### How it's used in this project
While we use React (a JavaScript library) to generate HTML, the styling relies heavily on pure CSS.
Look at `frontend/src/styles/variables.css`:
```css
:root {
  --background: #0f172a;
  --foreground: #f8fafc;
  --primary: #3b82f6;
  --border-radius-lg: 12px;
}
```
**Why it matters**: Instead of hardcoding `#0f172a` everywhere, we define a CSS Variable (`--background`). When React renders a component, it uses these variables, allowing for a consistent "glassmorphism" premium theme across the entire app.

## 3. Intermediate Python Concepts

### Async / Await
**What is it?** Traditional Python runs line-by-line (synchronous). If a line takes 5 seconds (like waiting for an AI model to reply), the whole program freezes. `async` / `await` allows the program to do other things while waiting.
**Project Example**: `backend/use_cases/ask_question.py`
```python
async def execute(self, question: str) -> Answer:
    return await self.llm_provider.ask(question)
```
**Why it matters**: FastAPI is built for async. By using `await`, our backend can handle hundreds of users asking questions simultaneously without freezing.

### Abstract Base Classes (ABC)
**What is it?** An interface. It defines *what* methods a class must have, without implementing them.
**Project Example**: `backend/domain/ports/llm_provider.py`
```python
from abc import ABC, abstractmethod

class ILLMProvider(ABC):
    @abstractmethod
    async def ask(self, question: str) -> Answer:
        pass
```
**Why it matters**: This forces any LLM integration (Echo, Bedrock, or LiteLLM) to have an `ask` method. The rest of our code just trusts the `ILLMProvider` interface and doesn't care which AI model is actually running.

### Type Hints
**What is it?** Python is dynamically typed. Type hints (`: str`, `-> int`) tell developers and code editors what types of variables are expected.
**Project Example**:
```python
def __init__(self, model_id: str) -> None:
```
**Why it matters**: It prevents bugs. If you try to pass an integer as `model_id`, your editor (like VS Code) will flag an error before you even run the code.

## 4. What is a REST API?

### Concept
An API (Application Programming Interface) allows the React frontend to talk to the Python backend over HTTP. REST is a convention for designing these APIs using standard HTTP methods:
- `GET`: Fetch data (e.g., `GET /api/health`)
- `POST`: Send data (e.g., `POST /api/ask`)

### How it's used in this project
When a user types a question in the React UI and clicks submit:
1. React sends a `POST` request to `http://localhost:8000/api/ask` with a JSON body: `{"question": "What is AI?"}`
2. FastAPI receives it, routes it to the correct Python function.
3. FastAPI responds with JSON: `{"text": "AI is...", "model": "Amazon Titan"}`
4. React receives the JSON and updates the screen.
