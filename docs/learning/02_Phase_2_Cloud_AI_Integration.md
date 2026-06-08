# Phase 2: Cloud AI Integration

In this phase, we connect our backend to the real world using AWS Bedrock. We move away from the "Echo" placeholder and start generating real AI responses.

## 1. AWS Bedrock & boto3

### What is it?
- **AWS Bedrock**: A fully managed service that provides access to leading Foundation Models (like Amazon Titan, Claude, Llama) via a single API.
- **boto3**: The official AWS SDK for Python.

### How it's used in this project
Look at `backend/adapters/llm/bedrock_llm.py`. It implements the `ILLMProvider` interface we learned about in Phase 1.

```python
import boto3

class BedrockLLM(ILLMProvider):
    def __init__(self, model_id: str) -> None:
        # Initialize the boto3 client for Bedrock
        self.client = boto3.client("bedrock-runtime", region_name="us-east-1")
        self.model_id = model_id

    def _call_bedrock_converse(self, question: str, system_prompt: str | None) -> str:
        # The Bedrock Converse API standardizes inputs across all models
        messages = [{"role": "user", "content": [{"text": question}]}]
        response = self.client.converse(
            modelId=self.model_id,
            messages=messages
        )
        return response["output"]["message"]["content"][0]["text"]
```

**Why it matters**: Bedrock removes the need to manage infrastructure. The `Converse` API is critical because it standardizes the input format. Whether you call Amazon Titan or Anthropic Claude, the Python code (`boto3.client.converse`) looks exactly the same.

## 2. Asynchronous Bridges (Threading)

### The Problem
FastAPI is an `async` framework. However, `boto3` is a synchronous library (it blocks the thread while waiting for the HTTP response from AWS). If we run `self.client.converse()` directly in our async FastAPI route, it will freeze the entire server until AWS responds!

### The Solution: `asyncio.to_thread`
We must push the blocking `boto3` call into a separate background thread so the main async event loop can continue handling other web requests.

```python
    async def ask(self, question: str, system_prompt: str | None = None) -> Answer:
        # Pushes the blocking call to a background thread
        answer_text = await asyncio.to_thread(
            self._call_bedrock_converse, question, system_prompt
        )
        return Answer(text=answer_text)
```

## 3. Streaming Responses & Queues

### What is it?
Instead of waiting 10 seconds for the AI to generate a full paragraph and then sending it all at once, we stream the response word-by-word (token-by-token) as it's being generated.

### How it's used in this project
In `bedrock_llm.py`'s `ask_stream` method, we use `asyncio.Queue` to bridge the synchronous AWS stream with our asynchronous FastAPI response.

1. We start a background thread that calls AWS Bedrock's `converse_stream`.
2. As chunks of text arrive from AWS (in the background thread), we put them into an `asyncio.Queue` in the main thread in a thread-safe way using `loop.call_soon_threadsafe`.
3. An `async generator` reads from that queue and yields the chunks to FastAPI.

```python
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _boto_stream_worker() -> None:
            # Sync blocking call in a background thread
            response = self.client.converse_stream(...)
            for chunk in response["stream"]:
                if "contentBlockDelta" in chunk:
                    text = chunk["contentBlockDelta"]["delta"].get("text")
                    # Safely pass data to the async event loop
                    loop.call_soon_threadsafe(queue.put_nowait, {"text": text})
            loop.call_soon_threadsafe(queue.put_nowait, None) # Signal EOF

        asyncio.create_task(asyncio.to_thread(_boto_stream_worker))

        while True:
            item = await queue.get() # Async wait for the next chunk
            if item is None: break
            yield item
```
**Why it matters**: Streaming drastically improves User Experience (UX). The user sees text appearing immediately, reducing perceived latency.

## 4. Environment Variables and Security

### What is it?
Never hardcode secrets (like AWS Access Keys) into your source code. If you commit them to GitHub, bots will scrape them and mine crypto on your account.

### How it's used in this project
We use `.env` files and `pydantic-settings`.

In `.env` (ignored by Git):
```env
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0
```

In `config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AWS_REGION: str
    AWS_BEDROCK_MODEL_ID: str
    
    class Config:
        env_file = ".env"
```
**Why it matters**: Pydantic automatically reads the `.env` file and populates the `Settings` object. When deploying to production, we don't upload the `.env` file; we set real environment variables on the server.
