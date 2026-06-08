# Phase 5: Temporal Workflows

In this phase, we transition from synchronous web requests to asynchronous, distributed execution. If a research question requires the AI agent to run 5 different searches, it might take 60 seconds. An HTTP request cannot reliably stay open that long.

## 1. Temporal & Durable Execution

### What is it?
Temporal is a workflow orchestration platform. It runs "Durable Executions." If you have a Python function that takes 10 minutes to run, and the server crashes at minute 5, Temporal guarantees that when the server restarts, your function resumes exactly where it left off.

### How it will be used in this project
We will run the Temporal Server locally using Docker Compose. It provides a control plane and a web UI (at `localhost:8080`).

**Why it matters**: LLM APIs fail all the time (rate limits, timeouts). Temporal gives us automatic retries and exponential backoff without writing complex `try/catch` loops.

## 2. Activities & Workflows

### What are they?
- **Activity**: The actual work. Interacting with the outside world (like calling DSPy/LiteLLM). Activities can fail and be retried.
- **Workflow**: The logic that orchestrates Activities. It must be deterministic (no random numbers, no direct API calls).

### How it will be used in this project
We will define an Activity that wraps our DSPy agent:
```python
from temporalio import activity, workflow

@activity.defn
async def run_agent_activity(question: str) -> str:
    # Call DSPy agent here
    return agent_result

@workflow.defn
class ResearchWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        # Run the activity with a 2-minute timeout and automatic retries
        return await workflow.execute_activity(
            run_agent_activity, 
            question, 
            start_to_close_timeout=timedelta(minutes=2)
        )
```

## 3. Workers & Task Queues

### What are they?
A **Worker** is a separate Python process. Its only job is to listen to a **Task Queue**, pick up pending workflows or activities, and execute them.

### How it will be used in this project
We will create a `worker.py` script and run it alongside our FastAPI server.
FastAPI will no longer run the AI directly. Instead, when a user submits a question, FastAPI sends a message to Temporal: "Please start a ResearchWorkflow for this question." FastAPI immediately returns a `workflow_id` to the user (in milliseconds). The Worker picks up the task from the queue and processes it in the background.

## 4. Async Polling UI

### What is it?
Since the FastAPI request returns immediately before the AI is done, the React frontend needs a way to know when the answer is ready.

### How it will be used in this project
We will build a "Research Queue" in React.
1. User submits question. UI creates a "Queued" card.
2. React sets up a `setInterval` that polls `GET /api/workflows/{id}/status` every 3 seconds.
3. FastAPI asks Temporal for the status (`RUNNING`, `COMPLETED`, `FAILED`).
4. Once completed, FastAPI returns the final answer, React stops polling, and updates the card to show the result.

**Why it matters**: This pattern is essential for any heavy compute task in modern web applications (video encoding, report generation, complex AI).
