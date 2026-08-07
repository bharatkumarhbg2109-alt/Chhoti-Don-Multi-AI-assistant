"""
Chhoti Don - Local Model Engine
Advanced Ollama-based local model execution with
streaming support, model management, and fallback.
Phase 2.2 - Full Upgrade
"""

import subprocess
import shutil
from typing import Dict, Optional, Optional

from core.config import Config


def execute(model_config: Dict, prompt: str) -> str:
    """
    Execute local model.
    Preserved + upgraded with better error handling.
    """
    model_name = model_config.get("model", Config.MAIN_MODEL)
    system_prompt = model_config.get("system_prompt", "")
    temperature = model_config.get("temperature", 0.7)

    # Try API first (faster)
    api_result = _execute_via_api(model_name, prompt, system_prompt, temperature)
    if api_result:
        return api_result

    # Fallback to subprocess
    return _execute_via_subprocess(model_name, prompt)


def _execute_via_api(model: str, prompt: str, system: str = "", temperature: float = 0.7) -> Optional[str]:
    """Ollama REST API via requests."""
    try:
        import requests
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 2048},
        }
        if system:
            payload["system"] = system

        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=120,
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception:
        pass
    return None


def _execute_via_subprocess(model: str, prompt: str) -> str:
    """Ollama subprocess fallback. Preserved."""
    if not shutil.which("ollama"):
        return "❌ Ollama not installed or not in PATH"

    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        output = result.stdout.decode(errors="ignore").strip()
        return output if output else "No output from model"
    except subprocess.TimeoutExpired:
        return "❌ Model execution timed out"
    except Exception as e:
        return f"❌ Subprocess error: {str(e)}"


def list_available_models() -> Dict:
    """Available Ollama models list karo."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return {
                "status": "success",
                "models": [m.get("name") for m in models],
                "count": len(models),
            }
    except Exception:
        pass
    return {"status": "offline", "models": [], "count": 0}


def pull_model(model_name: str) -> bool:
    """Pull a model from Ollama registry."""
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            timeout=300,
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False
