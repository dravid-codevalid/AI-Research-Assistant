# Phase 4: AI Agent & Tools

In this phase, we evolve from a simple Q&A bot into an Agentic AI. Instead of just answering based on its training data, the AI will "think", use external tools to gather facts, and then formulate an answer.

## 1. The ReAct Agent Pattern

### What is it?
ReAct stands for **Reasoning and Acting**. It is a prompting paradigm where the LLM is instructed to:
1. **Thought**: Reason about what it needs to do.
2. **Action**: Choose a tool to use (e.g., Search).
3. **Observation**: Read the result of the tool.
4. Loop back to step 1 until it has the final answer.

### How it's used in this project
Instead of writing complex string prompts telling the LLM how to do this, we will use the **DSPy** framework. DSPy provides a pre-built `ReAct` module.

```python
import dspy

# We define the input (question) and output (answer)
class ResearchSignature(dspy.Signature):
    question = dspy.InputField()
    answer = dspy.OutputField()

# DSPy automatically manages the Thought -> Action loop
agent = dspy.ReAct(ResearchSignature, tools=[wikipedia_search])
result = agent(question="Who is the CEO of Apple?")
```

**Why it matters**: Agentic AI is much more reliable than standard LLMs because it grounds its answers in real, retrieved data rather than hallucinating.

## 2. DSPy Framework

### What is it?
DSPy is a framework for *programming* language models rather than *prompting* them. You declare modules (like PyTorch neural networks) and DSPy figures out the best way to format the prompts under the hood.

### How it will be used in this project
We will configure DSPy to connect to our LiteLLM proxy (from Phase 3) as its backend:
```python
lm = dspy.LM(model="openai/amazon.titan", api_base="http://localhost:4000/v1")
dspy.settings.configure(lm=lm)
```

## 3. Tool Use / Function Calling

### What is it?
Tools are simply Python functions that the LLM is allowed to execute. The LLM outputs a structured JSON telling our code "run function X with arguments Y". Our code runs the Python function and returns the result to the LLM.

### How it will be used in this project
We will build two tools:
1. **Wikipedia Search**: Uses the `wikipedia` Python package to fetch summaries of topics.
2. **File Memory**: A simple Python function that reads/writes JSON to a local file, allowing the AI to "remember" facts across different questions.

```python
def wikipedia_search(query: str) -> str:
    """Searches Wikipedia and returns a summary."""
    import wikipedia
    return wikipedia.summary(query, sentences=3)
```
When DSPy sees this tool, it passes the docstring (`"Searches Wikipedia..."`) to the LLM so it knows when to use it.

## 4. Assistant-UI Integration

### What is it?
Building a chat interface that supports streaming, markdown, and showing tool invocations is extremely complex in React. `Assistant-UI` is an open-source React component library purpose-built for AI chat.

### How it will be used in this project
We will replace our basic React chat UI with `<AssistantRuntimeProvider>`.
**Why it matters**: When the DSPy agent decides to search Wikipedia, our FastAPI backend will stream a "tool call" event to the frontend. Assistant-UI will catch this and render a beautiful, collapsible "Searching Wikipedia for..." card directly in the chat thread, just like ChatGPT does.
