"""
Chhoti Don - Flask Web API
Web UI aur Chhoti Don core ko connect karta hai.
Run: python app.py
URL: http://localhost:8000
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, sys, time, traceback

# Ensure UTF-8 stdout/stderr so emoji log lines don't crash under a cp1252
# console or when the launcher redirects output to a log file (Windows).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.manager import ManagerAgent
from core.task_classifier import detect_task, detect_coding_action
from core.brain_router import detect_intent, route_coding_tool

app = Flask(__name__, static_folder=".")
CORS(app)

print("🚀 Loading Chhoti Don core...")
chhoti_don = ManagerAgent()
print("✅ Chhoti Don ready!\n")


# ── Serve Web UI ──────────────────────────────────────────────
@app.route("/")
def serve_ui():
    return send_from_directory(".", "chhoti_don_ui.html")


# ── Main Chat ─────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data      = request.get_json()
        message   = data.get("message", "").strip()
        tool_id   = data.get("tool", "chat")
        if not message:
            return jsonify({"error": "Empty message"}), 400

        t0     = time.time()
        result = _route_to_tool(message, tool_id)
        text   = _extract_response(result)
        exec_t = round(time.time() - t0, 2)

        return jsonify({
            "status":         "success",
            "response":       text,
            "tool":           tool_id,
            "intent":         detect_intent(message),
            "task_type":      detect_task(message),
            "execution_time": exec_t,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "response": f"❌ Error: {str(e)}"}), 500


def _route_to_tool(message: str, tool_id: str) -> dict:
    if tool_id in ["coder", "reveng", "strings", "autofix"]:
        return chhoti_don.coding_task(message)
    elif tool_id in ["recon", "malware", "pentest", "webscan",
                     "exploit", "mitre", "ioc", "heatmap"]:
        return chhoti_don.autonomous_llm_task(message)
    elif tool_id == "analyst":
        return chhoti_don.brain_task(message)
    elif tool_id == "search":
        return chhoti_don.brain_task(f"Search and explain: {message}")
    else:
        intent = detect_intent(message)
        task   = detect_task(message)
        if intent in ["coding", "debug"] or task == "coding":
            return chhoti_don.coding_task(message)
        elif intent == "malware" or task == "malware":
            return chhoti_don.autonomous_llm_task(message)
        else:
            return chhoti_don.brain_task(message)


def _extract_response(result) -> str:
    if not isinstance(result, dict):
        return str(result)
    output = result.get("output", "")
    if isinstance(output, dict):
        parts = []
        status = output.get("status", "")
        if status:
            parts.append(f"{'✅' if status=='success' else '❌'} {status.upper()}")
        if output.get("code"):
            lang = output.get("language", "python")
            parts.append(f"\n```{lang}\n{output['code']}\n```")
        if output.get("output"):
            parts.append(f"\n**Output:**\n```\n{output['output']}\n```")
        if output.get("explanation"):
            parts.append(f"\n{output['explanation']}")
        if output.get("fixed_code"):
            lang = output.get("language", "python")
            parts.append(f"\n**Fixed:**\n```{lang}\n{output['fixed_code']}\n```")
        if output.get("diagnosis"):
            parts.append(f"\n🐛 {output['diagnosis']}")
        if output.get("message") and not parts:
            parts.append(output["message"])
        return "\n".join(parts) if parts else str(output)
    return str(output) if output else str(result)


# ── Status ────────────────────────────────────────────────────
@app.route("/api/status", methods=["GET"])
def status():
    """
    Extended status so the frontend can distinguish:
      - backend online (this endpoint responding)
      - real AI provider online   (mode api/local + model reachable)
      - simulated fallback active (mode == simulation)
      - configured model unavailable (local mode, model not pulled)

    Backward compatible: the original `ollama` and `models` fields are preserved.
    """
    try:
        from core.brain_router import check_ollama_status
        ollama = check_ollama_status()
    except Exception:
        ollama = {"online": False, "models_available": []}

    models = ollama.get("models_available", [])
    ollama_online = bool(ollama.get("online", False))

    # Provider mode is decided by the Brain at startup (api > local > simulation).
    startup_mode = getattr(chhoti_don.brain, "mode", "simulation")

    try:
        from core.config import Config
        configured_model = Config.MODEL_NAME if startup_mode == "api" else Config.LOCAL_MODEL
    except Exception:
        configured_model = "mistral:latest"

    provider = "openai" if startup_mode == "api" else "ollama"

    # For local mode, the model must actually be pulled in Ollama.
    def _model_present(name, available):
        base = name.split(":")[0]
        return any(m == name or m.split(":")[0] == base for m in available)

    if startup_mode == "api":
        model_available = True
    else:
        model_available = _model_present(configured_model, models)

    if startup_mode == "api":
        mode = "live"
        provider_online = True
    elif ollama_online and model_available:
        mode = "live"
        provider_online = True
    else:
        mode = "simulation"
        provider_online = ollama_online
    simulated = mode == "simulation"
    ai_online = mode == "live"

    return jsonify({
        # ── preserved fields ──
        "status":  "online",
        "version": "v3.0",
        "ollama":  ollama_online,
        "models":  models,
        # ── extended fields ──
        "backend":         "online",
        "backend_online":  True,
        "mode":            mode,               # live | simulation
        "runtime_mode":    startup_mode,       # api | local | simulation
        "provider":        provider,
        "provider_online": provider_online,
        "model":           configured_model,   # e.g. mistral:latest / gpt-4o-mini
        "model_available": model_available,
        "simulated":       simulated,
        "ai_online":       ai_online,
    })


# ── Health ────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":  "ok",
        "version": "v3.0",
        "engine":  "CHHOTI DON",
    })


# ── Memory ────────────────────────────────────────────────────
@app.route("/api/memory", methods=["GET"])
def get_memory():
    try:
        return jsonify({"status": "success", "memory": chhoti_don.get_memory()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Reset / New Chat ──────────────────────────────────────────
@app.route("/api/reset", methods=["POST"])
def reset():
    try:
        chhoti_don.memory.clear()
        return jsonify({"status": "success", "message": "Memory cleared!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  Chhoti Don Web API")
    print("  URL : http://localhost:8000")
    print("  UI  : http://localhost:8000/")
    print("=" * 50)
    app.run(host="127.0.0.1", port=8000, debug=False)
