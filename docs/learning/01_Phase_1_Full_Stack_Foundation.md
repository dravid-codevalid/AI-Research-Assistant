# Phase 1: Full-Stack Foundation

This phase covers the core architectural backbone of the AI Research Assistant. We'll explore Clean Architecture, FastAPI, and React.

## 1. Clean Architecture & Hexagonal Pattern

### What is it?
Clean Architecture separates software into layers to isolate business rules from technical details. The Hexagonal Pattern (Ports and Adapters) is a specific implementation of this.
- **Domain**: The core rules (Entities, Interfaces/Ports). It knows nothing about the outside world.
- **Use Cases**: Application-specific business rules.
- **Adapters**: Implementations of the outside world (Databases, LLM APIs, Web frameworks).

### How it's used in this project
Look at the `backend/` folder structure:
1. **Port**: `domain/ports/llm_provider.py` defines `ILLMProvider`. This is a rule: "To be an LLM in this app, you must have an `ask` method."
2. **Adapter**: `adapters/llm/echo_llm.py` and `adapters/llm/bedrock_llm.py`. These implement the `ILLMProvider` interface using specific technologies.
3. **Use Case**: `use_cases/ask_question.py` orchestrates the logic:
```python
class AskQuestionUseCase:
    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm_provider = llm_provider # Dependency Injection!
```
**Why it matters**: Notice how `AskQuestionUseCase` requires an `ILLMProvider`, not `BedrockLLM`. This means we can swap Amazon Bedrock for OpenAI tomorrow without touching a single line of our business logic!

## 2. FastAPI & Dependency Injection

### What is it?
FastAPI is a modern Python web framework. It uses Pydantic for data validation and has built-in Dependency Injection.

### How it's used in this project
Look at `backend/api/dependencies.py`:
```python
def get_ask_question_use_case() -> AskQuestionUseCase:
    provider = EchoLLM() # Or BedrockLLM()
    return AskQuestionUseCase(llm_provider=provider)
```
And then in `backend/api/routes/ask.py`:
```python
@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    request: AskRequest,
    use_case: AskQuestionUseCase = Depends(get_ask_question_use_case),
):
    answer = await use_case.execute(request.question)
    return answer
```
**Why it matters**: When a web request hits `/ask`, FastAPI automatically calls `get_ask_question_use_case`, builds the Use Case with the correct LLM Adapter, and passes it to the route. This keeps our routing code incredibly clean.

## 3. Pydantic v2

### What is it?
A data validation library. You define the "shape" of your data using Python classes.

### How it's used in this project
In `backend/api/schemas/`:
```python
from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str
```
**Why it matters**: If a frontend sends a request without a `question` field, Pydantic automatically blocks it and returns a `422 Unprocessable Entity` error. You never have to write `if "question" not in request: return error`.

## 4. React 19 + TypeScript + Vite

### What are they?
- **React**: A library for building User Interfaces out of reusable "Components".
- **TypeScript**: Adds types to JavaScript to catch bugs early.
- **Vite**: The build tool that serves the files locally and refreshes the browser instantly when you save code.

### How it's used in this project
A React component looks like a mix of HTML and JavaScript (called JSX):
```tsx
import { useState } from 'react';

export function ChatApp() {
  const [question, setQuestion] = useState(''); // State management

  const handleSubmit = async () => {
    // Call our FastAPI backend
    const res = await fetch('http://localhost:8000/api/ask', {
      method: 'POST',
      body: JSON.stringify({ question })
    });
  };

  return (
    <div>
      <input value={question} onChange={e => setQuestion(e.target.value)} />
      <button onClick={handleSubmit}>Ask AI</button>
    </div>
  );
}
```
**Why it matters**: React's state management (`useState`) ensures that whenever the `question` variable changes, the UI updates instantly to reflect it.

## 5. Testing with Pytest

### What is it?
A framework for writing automated tests to ensure your code works as expected.

### How it's used in this project
In `backend/tests/`:
```python
import pytest
from use_cases.ask_question import AskQuestionUseCase

@pytest.mark.asyncio
async def test_empty_question_raises_error():
    use_case = AskQuestionUseCase(MockLLM())
    with pytest.raises(ValueError):
        await use_case.execute("")
```
**Why it matters**: Automated tests act as a safety net. If someone accidentally breaks the logic that prevents empty questions, this test will fail during the CI/CD pipeline, preventing a bug from reaching production.
