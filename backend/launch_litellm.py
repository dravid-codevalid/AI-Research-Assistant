import os
import subprocess
import sys

def load_env(env_path):
    if not os.path.exists(env_path):
        print(f"Error: {env_path} does not exist.")
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # strip quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                os.environ[key] = value
                print(f"Loaded env var: {key}")

if __name__ == "__main__":
    load_env(".env")
    cmd = ["litellm", "--config", "litellm_config.yaml", "--port", "4000"]
    os.environ["PYTHONIOENCODING"] = "utf-8"
    print(f"Running command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("LiteLLM stopped.")
    except Exception as e:
        print(f"Failed to start LiteLLM: {e}")
