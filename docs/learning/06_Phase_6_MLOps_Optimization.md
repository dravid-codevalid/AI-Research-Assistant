# Phase 6: MLOps & Optimization

In the final phase, we apply rigorous engineering practices to our AI prompts. Instead of guessing which prompt or model is best, we use data to mathematically optimize our DSPy agent and track experiments using MLflow.

## 1. Prompt Optimization & GRPO

### What is it?
Writing prompts by hand is fragile. If you switch from Claude to Titan, your hand-crafted prompt might perform worse.
**Optimization** is the process of automatically finding the best prompt instructions and few-shot examples for a specific model and task.

**GRPO (Gradient-free Reward-based Prompt Optimization)** is a specific algorithm in DSPy. It tests different variations of prompts on an LLM, scores the output using a "reward" function, and iteratively refines the prompt based on what gets the highest score—without needing access to the model's underlying neural weights.

### How it will be used in this project
1. We will define a **Gold Dataset**: 20 factual questions and exact answers (e.g., Q: "Year Python released?", A: "1991").
2. We will define a **Metric Function**: A simple Python function that returns `1.0` if the agent's answer contains "1991", and `0.0` if it doesn't.
3. We will run `dspy.GRPO`. It will take our base agent, run it through the dataset, tweak the prompts automatically, and output an "Optimized Program".

## 2. Multi-Model Comparison

### What is it?
Evaluating different LLMs scientifically to see which one performs best for your specific use case.

### How it will be used in this project
Because we built the LiteLLM gateway in Phase 3, we can easily run the GRPO optimizer three times: once for Bedrock Titan, once for an OpenAI model, and once for a local Qwen model. We will compare their final metric scores to make data-driven decisions about which model to deploy to production.

## 3. MLflow Tracking

### What is it?
MLflow is an open-source platform for managing the ML lifecycle. The **Tracking Server** records parameters, code versions, metrics, and output files (artifacts) for every experiment run.

### How it will be used in this project
We will run `mlflow server` locally.
In our optimization script, we will configure DSPy's built-in MLflow callback:
```python
import mlflow
dspy.configure_mlflow_callback(
    tracking_uri="http://localhost:5000",
    experiment_name="research-assistant"
)
```
**Why it matters**: Every time the GRPO optimizer tries a new prompt or model, it will automatically log the exact prompt used, the LLM's response, and the metric score to MLflow. You can open the MLflow UI and visually graph how accuracy improved over time.

## 4. MLflow Model Registry

### What is it?
A centralized repository to manage model versions and lifecycle stages (Staging, Production, Archived).

### How it will be used in this project
Once the optimizer finishes and finds a winning prompt/model combination, we will save that compiled DSPy program as an artifact and register it in MLflow under the name `research-assistant-agent`.

When our FastAPI server starts up, instead of hard-coding the agent, it will reach out to MLflow:
```python
# Load the latest production-ready agent from MLflow
agent = mlflow.dspy.load_model("models:/research-assistant-agent/latest")
```
**Why it matters**: This completes the MLOps lifecycle. You can optimize the agent offline, register a new version, and the production FastAPI server will pick up the new, smarter agent without changing a single line of application code.
