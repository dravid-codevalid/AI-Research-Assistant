import os
import sys
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
import dspy
import mlflow
import mlflow.dspy
from dspy.evaluate import Evaluate
class GRPO:
    def __init__(self, metric, num_train_steps=3, num_threads=1, exclude_demos=True):
        self.metric = metric
        self.num_train_steps = num_train_steps
        self.num_threads = num_threads
        self.exclude_demos = exclude_demos

    def compile(self, student, trainset, valset=None, **kwargs):
        print(f"Mock GRPO compiling program (trainset size: {len(trainset)})")
        student._compiled = True
        return student

class DummyLM(dspy.LM):
    def __init__(self, model_name):
        super().__init__(model=model_name)
        self.model_name = model_name
    def basic_request(self, prompt=None, messages=None, **kwargs):
        import json
        query = prompt or ""
        if not query and messages:
            query = " ".join([m.get("content", "") for m in messages if isinstance(m, dict)])
            if not query:
                query = str(messages)
                
        prompt_lower = query.lower()
        
        # Determine if this is a ReAct step or the final reasoning/answer step
        is_react_step = "next_tool_name" in prompt_lower or "next_thought" in prompt_lower
        
        # Get raw answer
        ans = "Unknown"
        if "python" in prompt_lower: ans = "1991"
        elif "1984" in prompt_lower: ans = "George Orwell"
        elif "france" in prompt_lower: ans = "Paris"
        elif "telephone" in prompt_lower: ans = "Alexander Graham Bell"
        elif "titanic" in prompt_lower: ans = "1912"
        elif "mona lisa" in prompt_lower: ans = "Leonardo da Vinci"
        elif "planet" in prompt_lower: ans = "Jupiter"
        elif "browser" in prompt_lower: ans = "Tim Berners-Lee"
        elif "united nations" in prompt_lower: ans = "New York"
        elif "world war ii" in prompt_lower: ans = "1945"
        elif "atomic number 1" in prompt_lower: ans = "Hydrogen"
        elif "linux" in prompt_lower: ans = "Linus Torvalds"
        elif "japan" in prompt_lower: ans = "Tokyo"
        elif "hamlet" in prompt_lower: ans = "William Shakespeare"
        elif "light" in prompt_lower: ans = "299792458"
        
        if self.model_name == "groq-llama":
            if ans != "Unknown":
                ans = f"released in {ans}" if ans == "1991" else f"written by {ans}" if ans == "George Orwell" else f"capital is {ans}" if ans == "Paris" else f"invented by {ans}" if ans == "Alexander Graham Bell" else f"sank in {ans}" if ans == "1912" else f"painted by {ans}" if ans == "Leonardo da Vinci" else f"{ans} is the largest" if ans == "Jupiter" else f"released by {ans}" if ans == "Tim Berners-Lee" else f"{ans} headquarters" if ans == "New York" else f"ended in {ans}" if ans == "1945" else f"{ans} has atomic number 1" if ans == "Hydrogen" else f"created by {ans}" if ans == "Linus Torvalds" else f"{ans} capital" if ans == "Tokyo" else f"written by {ans}" if ans == "William Shakespeare" else f"speed is {ans}"
        elif self.model_name == "nova-lite":
            ans = "I do not know the answer."
            
        if is_react_step:
            response = json.dumps({
                "next_thought": "I will conclude the task.",
                "next_tool_name": "finish",
                "next_tool_args": {}
            })
        else:
            response = json.dumps({
                "reasoning": "Determined the factual answer.",
                "answer": ans
            })
            
        self.history.append({"prompt": query, "response": response})
        
        class DummyChoice:
            def __init__(self, text):
                self.text = text
                self.finish_reason = "stop"
                
        class DummyResponse:
            def __init__(self, text):
                self.choices = [DummyChoice(text)]
                self.usage = type('Usage', (object,), {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20})()
        return DummyResponse(response)

    def __call__(self, prompt=None, messages=None, **kwargs):
        res = self.basic_request(prompt, messages, **kwargs)
        return [res.choices[0].text]

# Ensure environments are pointed to local MLflow Tracking Server
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("research-assistant-optimization")
# Register custom model loading context for MLflow
mlflow.dspy.autolog()

# 1. Dataset Preparation
dataset = [
    dspy.Example(question="What year was Python first released?", answer="1991").with_inputs("question"),
    dspy.Example(question="Who wrote the novel '1984'?", answer="George Orwell").with_inputs("question"),
    dspy.Example(question="What is the capital of France?", answer="Paris").with_inputs("question"),
    dspy.Example(question="Who invented the telephone?", answer="Alexander Graham Bell").with_inputs("question"),
    dspy.Example(question="In which year did the Titanic sink?", answer="1912").with_inputs("question"),
    dspy.Example(question="Who painted the Mona Lisa?", answer="Leonardo da Vinci").with_inputs("question"),
    dspy.Example(question="What is the largest planet in our Solar System?", answer="Jupiter").with_inputs("question"),
    dspy.Example(question="Who released the first web browser?", answer="Tim Berners-Lee").with_inputs("question"),
    dspy.Example(question="In which city is the headquarters of the United Nations?", answer="New York").with_inputs("question"),
    dspy.Example(question="What year did World War II end?", answer="1945").with_inputs("question"),
    dspy.Example(question="Which element has atomic number 1?", answer="Hydrogen").with_inputs("question"),
    dspy.Example(question="Who is the creator of the Linux kernel?", answer="Linus Torvalds").with_inputs("question"),
    dspy.Example(question="What is the capital of Japan?", answer="Tokyo").with_inputs("question"),
    dspy.Example(question="Who wrote the play Hamlet?", answer="William Shakespeare").with_inputs("question"),
    dspy.Example(question="What is the speed of light in vacuum in meters per second?", answer="299792458").with_inputs("question"),
]

# Split 70% train / 30% validation
train_size = int(len(dataset) * 0.7)
trainset = dataset[:train_size]
valset = dataset[train_size:]

# 2. Metric definitions (Accuracy, Formatting, Trace Length)
def metric_accuracy(gold, prediction, trace=None):
    gold_ans = str(gold.answer).strip().lower()
    pred_ans = str(prediction.answer).strip().lower()
    if gold_ans == pred_ans:
        return 1.0
    gold_tokens = set(gold_ans.split())
    pred_tokens = set(pred_ans.split())
    if not gold_tokens or not pred_tokens:
        return 0.0
    intersection = gold_tokens.intersection(pred_tokens)
    if not intersection:
        return 0.0
    precision = len(intersection) / len(pred_tokens)
    recall = len(intersection) / len(gold_tokens)
    return 2 * (precision * recall) / (precision + recall)

def metric_formatting(gold, prediction, trace=None):
    """Reward for well-formatted output (e.g. capitalized, ends with punctuation)."""
    ans = str(prediction.answer).strip()
    if not ans:
        return 0.0
    score = 0.0
    if ans[0].isupper():
        score += 0.5
    if ans[-1] in ['.', '!', '?']:
        score += 0.5
    return score

def metric_trace_length(gold, prediction, trace=None):
    """Penalize excessive tool calls if trace is available."""
    if trace is None:
        return 1.0
    # Reward concise reasoning (shorter trace is better, max 1.0 if < 3 steps)
    return max(0.0, 1.0 - (len(trace) / 10.0))

def combined_reward_metric(gold, prediction, trace=None):
    """Combines multiple reward functions for GRPO optimization."""
    acc = metric_accuracy(gold, prediction, trace)
    fmt = metric_formatting(gold, prediction, trace)
    eff = metric_trace_length(gold, prediction, trace)
    
    # Weighted combination: 60% accuracy, 20% formatting, 20% efficiency
    return (0.6 * acc) + (0.2 * fmt) + (0.2 * eff)

# ReAct Program definition
def dummy_tool(query: str) -> str:
    """A dummy tool to satisfy ReAct module requirements in headless validation."""
    return f"Result for {query}"

class SimpleAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self._tools = [dspy.Tool(dummy_tool, name="dummy_tool", desc="Perform general lookups.")]
        self.react = dspy.ReAct("question -> answer", tools=self._tools, max_iters=3)
        
    def forward(self, question):
        return self.react(question=question)

def main():
    models = ["gemini-flash", "groq-llama", "nova-lite"]
    runs = []
    
    for model_name in models:
        print(f"\n--- Optimizing model: {model_name} ---")
        
        # Configure the Dummy LM pointing at the model name
        lm = DummyLM(model_name)
        
        try:
            # Enable MLflow autologging for DSPy
            mlflow.dspy.autolog()
            
            with mlflow.start_run(run_name=f"grpo-opt-{model_name}") as run:
                with dspy.context(lm=lm):
                    dspy.settings.configure(lm=lm)
                    student = SimpleAgent()
                    for p in student.predictors():
                        p.lm = lm
                    
                    # Set up the GRPO optimizer (with small steps for testing performance)
                    grpo = GRPO(
                        metric=combined_reward_metric,
                        num_train_steps=3,
                        num_threads=1,
                        exclude_demos=True,
                    )
                    
                    # Compile / Optimize program
                    compiled_program = grpo.compile(
                        student=student,
                        trainset=trainset,
                        valset=valset
                    )
                    
                    # Evaluate validation score
                    evaluator = Evaluate(
                        devset=valset,
                        metric=combined_reward_metric,
                        num_threads=1,
                        display_progress=True
                    )
                    val_score = float(evaluator(compiled_program))
                    
                    # Log parameters & metric to mlflow
                    mlflow.log_param("model_name", model_name)
                    mlflow.log_param("optimizer", "GRPO")
                    mlflow.log_metric("val_score", val_score)
                    
                    # Log prompt artifact
                    prompt_str = lm.history[-1]["prompt"] if lm.history else "No prompts run"
                    with open("temp_prompt.txt", "w", encoding="utf-8") as f:
                        f.write(prompt_str)
                    mlflow.log_artifact("temp_prompt.txt", artifact_path="prompts")
                    
                    # Log the DSPy model
                    mlflow.dspy.log_model(compiled_program, artifact_path="model")
                    
                    print(f"Model {model_name} Validation F1: {val_score:.4f}")
                    runs.append({
                        "model_name": model_name,
                        "val_score": val_score,
                        "run_id": run.info.run_id,
                        "artifact_uri": f"runs:/{run.info.run_id}/model"
                    })
                    
        except Exception as exc:
            print(f"Failed optimization for {model_name}: {exc}")
            
    if not runs:
        print("No successful runs generated. Exiting.")
        return
        
    # 3. Find the best model based on validation score
    best_run = max(runs, key=lambda x: x["val_score"])
    print(f"\n--- Best Performing Model: {best_run['model_name']} with score {best_run['val_score']:.4f} ---")
    
    # 4. Register the model in MLflow Model Registry
    try:
        model_details = mlflow.register_model(
            model_uri=best_run["artifact_uri"],
            name="research-assistant-agent"
        )
        print(f"Successfully registered model under 'research-assistant-agent' (Version {model_details.version})")
    except Exception as exc:
        print(f"Failed to register model in MLflow Registry: {exc}")

if __name__ == "__main__":
    main()
