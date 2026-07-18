"""
Chhoti Don - Flask Web API
Web UI aur Chhoti Don core ko connect karta hai.
Run: python app.py
URL: http://localhost:8000

This backend also serves the built React dashboard (chhoti-don-react/dist)
so the desktop shell can load the whole app same-origin from the backend,
which keeps /api calls relative and avoids cross-origin complications.
"""

from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
import os, sys, time, socket, traceback

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
from core import history_store
from core import capabilities as capabilities_registry

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_RUNTIME_DIR = os.environ.get("CHHOTI_DON_RUNTIME_DIR") or os.path.join(_PROJECT_ROOT, ".runtime")
FRONTEND_DIST = os.path.join(_PROJECT_ROOT, "chhoti-don-react", "dist")

app = Flask(__name__, static_folder=None)

# CORS is intentionally limited to the local development origins. In the
# packaged desktop app the renderer loads same-origin from this backend, so
# no wildcard CORS is required.
CORS(app, resources={r"/api/*": {"origins": [
    "http://127.0.0.1:5173", "http://localhost:5173",
    "http://127.0.0.1:8000", "http://localhost:8000",
]}})

print("🚀 Loading Chhoti Don core...")
chhoti_don = ManagerAgent()
history_store.init_db()
print("✅ Chhoti Don ready!\n")


# ── Provider / model detection (shared by status + persistence) ─
def _current_provider_model():
    """Return (provider, model, runtime_mode, live) using the same rules as /api/status."""
    try:
        from core.brain_router import check_ollama_status
        ollama = check_ollama_status()
    except Exception:
        ollama = {"online": False, "models_available": []}

    models = ollama.get("models_available", [])
    ollama_online = bool(ollama.get("online", False))
    startup_mode = getattr(chhoti_don.brain, "mode", "simulation")

    try:
        from core.config import Config
        configured_model = Config.MODEL_NAME if startup_mode == "api" else Config.LOCAL_MODEL
    except Exception:
        configured_model = "mistral:latest"

    provider = "openai" if startup_mode == "api" else "ollama"

    def _model_present(name, available):
        base = name.split(":")[0]
        return any(m == name or m.split(":")[0] == base for m in available)

    if startup_mode == "api":
        model_available = True
    else:
        model_available = _model_present(configured_model, models)

    live = startup_mode == "api" or (ollama_online and model_available)
    return provider, configured_model, startup_mode, live, ollama_online, models, model_available


# ── Serve built React dashboard (SPA) ─────────────────────────
@app.route("/")
def serve_ui():
    index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index):
        return send_from_directory(FRONTEND_DIST, "index.html")
    # Fallback to the legacy single-file UI if the React build is absent.
    return send_from_directory(_PROJECT_ROOT, "chhoti_don_ui.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if not os.path.exists(os.path.join(assets_dir, filename)):
        abort(404)
    return send_from_directory(assets_dir, filename)


@app.route("/favicon.svg")
@app.route("/favicon.ico")
def serve_favicon():
    for name in ("favicon.svg", "favicon.ico"):
        candidate = os.path.join(FRONTEND_DIST, name)
        if os.path.exists(candidate):
            return send_from_directory(FRONTEND_DIST, name)
    abort(404)


# ── Main Chat ─────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data      = request.get_json(silent=True) or {}
        message   = str(data.get("message", "")).strip()
        tool_id   = data.get("tool", "chat")
        conv_id   = data.get("conversation_id")
        private   = bool(data.get("private", False))
        persist_user = bool(data.get("persist_user", True))
        if not message:
            return jsonify({"status": "error", "response": "Empty message"}), 400

        provider, model, runtime_mode, live, *_ = _current_provider_model()

        # Persist the user message up-front (unless private or a retry).
        if conv_id and not private and persist_user:
            history_store.add_message(conv_id, "user", message)

        t0     = time.time()
        result = _route_to_tool(message, tool_id)
        text   = _extract_response(result)
        exec_t = round(time.time() - t0, 2)

        assistant_msg = None
        if conv_id and not private:
            assistant_msg = history_store.add_message(
                conv_id, "assistant", text,
                status="complete", provider=provider, model=model,
                metadata={"tool": tool_id, "execution_time": exec_t},
                auto_title=False,
            )

        return jsonify({
            "status":         "success",
            "response":       text,
            "tool":           tool_id,
            "intent":         detect_intent(message),
            "task_type":      detect_task(message),
            "execution_time": exec_t,
            "conversation_id": conv_id,
            "message_id":     assistant_msg["id"] if assistant_msg else None,
            "provider":       provider,
            "model":          model,
            "live":           live,
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
    provider, configured_model, startup_mode, live, ollama_online, models, model_available = \
        _current_provider_model()

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
        # ── history / database ──
        "database":        history_store.stats(),
    })


# ── Health ────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":  "ok",
        "version": "v3.0",
        "engine":  "CHHOTI DON",
    })


# ── Capabilities ──────────────────────────────────────────────
@app.route("/api/capabilities", methods=["GET"])
def get_capabilities():
    try:
        return jsonify({"status": "success", **capabilities_registry.get_registry()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Memory ────────────────────────────────────────────────────
@app.route("/api/memory", methods=["GET"])
def get_memory():
    try:
        return jsonify({"status": "success", "memory": chhoti_don.get_memory()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/memory/search", methods=["POST"])
def search_memory():
    try:
        data = request.get_json(silent=True) or {}
        query = str(data.get("query", "")).strip()
        if not query:
            return jsonify({"status": "error", "message": "Empty query"}), 400
        matches = chhoti_don.memory.search(query)
        return jsonify({"status": "success", "matches": matches, "count": len(matches)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Reset / Clear memory ──────────────────────────────────────
@app.route("/api/reset", methods=["POST"])
def reset():
    try:
        chhoti_don.memory.clear()
        return jsonify({"status": "success", "message": "Memory cleared!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ══════════════════════════════════════════════════════════════
#  Conversations (persistent history)
# ══════════════════════════════════════════════════════════════
@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    try:
        include_archived = request.args.get("archived", "0") in ("1", "true", "yes")
        query = request.args.get("q") or None
        convs = history_store.list_conversations(include_archived=include_archived, query=query)
        return jsonify({"status": "success", "conversations": convs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    try:
        data = request.get_json(silent=True) or {}
        title = data.get("title")
        private = bool(data.get("private", False))
        conv = history_store.create_conversation(title=title, is_private=private)
        return jsonify({"status": "success", "conversation": conv}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/conversations/import", methods=["POST"])
def import_conversations():
    try:
        data = request.get_json(silent=True) or {}
        payload = data.get("conversations", [])
        if not isinstance(payload, list):
            return jsonify({"status": "error", "message": "conversations must be a list"}), 400
        result = history_store.import_conversations(payload)
        return jsonify({"status": "success", **result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/conversations/<conv_id>", methods=["GET"])
def get_conversation(conv_id):
    try:
        conv = history_store.get_conversation(conv_id, with_messages=True)
        if not conv:
            return jsonify({"status": "error", "message": "Not found"}), 404
        return jsonify({"status": "success", "conversation": conv})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/conversations/<conv_id>", methods=["PATCH"])
def update_conversation(conv_id):
    try:
        data = request.get_json(silent=True) or {}
        conv = None
        if "title" in data:
            conv = history_store.rename_conversation(conv_id, str(data.get("title", "")))
        if "archived" in data:
            conv = history_store.set_archived(conv_id, bool(data.get("archived")))
        if conv is None:
            return jsonify({"status": "error", "message": "Not found or nothing to update"}), 404
        return jsonify({"status": "success", "conversation": conv})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    try:
        ok = history_store.delete_conversation(conv_id)
        if not ok:
            return jsonify({"status": "error", "message": "Not found"}), 404
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ══════════════════════════════════════════════════════════════
#  Cyber Engine (read-only defensive posture + confirmed loopback check)
# ══════════════════════════════════════════════════════════════
_SAFE_CYBER_TOOLS = [
    {"id": "engine_info", "name": "Engine info", "active": False,
     "description": "Version and safe tool inventory (read-only)."},
    {"id": "safety_policy", "name": "Safety policy", "active": False,
     "description": "Guardian, rate limits and private-lab allowlist (read-only)."},
    {"id": "loopback_port_check", "name": "Loopback port check", "active": True,
     "description": "Check which common ports are open on 127.0.0.1 only. Requires confirmation.",
     "risk_level": "low", "requires_confirmation": True},
]

# Common local service ports checked by the confirmed loopback scan.
_LOOPBACK_PORTS = [22, 80, 443, 3000, 5000, 5173, 8000, 8080, 8888, 9000, 11434]


def _cyber_safety_policy():
    policy = {"lab_mode": True, "allowed_ranges": [], "guardian_enabled": True,
              "rate_limit_window": None, "max_scans_per_window": None}
    try:
        from cyber_engine.assessment import scope_validator as sv
        policy["lab_mode"] = bool(getattr(sv, "LAB_MODE", True))
        policy["allowed_ranges"] = list(getattr(sv, "ALLOWED_IP_RANGES", []))
        policy["critical_blocked"] = list(getattr(sv, "CRITICAL_IPS", []))
    except Exception:
        pass
    try:
        from core.config import Config
        policy["guardian_enabled"] = bool(getattr(Config, "GUARDIAN_ENABLED", True))
        policy["rate_limit_window"] = getattr(Config, "RATE_LIMIT_WINDOW", None)
        policy["max_scans_per_window"] = getattr(Config, "MAX_SCANS_PER_WINDOW", None)
    except Exception:
        pass
    return policy


@app.route("/api/cyber/status", methods=["GET"])
def cyber_status():
    available = False
    version = None
    safe_tool_count = 0
    telemetry = None
    try:
        from cyber_engine.cyber_controller import CyberController
        cc = CyberController()
        info = cc.engine_info()
        version = info.get("version")
        # Only advertise the count of tools; never enumerate offensive tool names.
        safe_tool_count = len(_SAFE_CYBER_TOOLS)
        available = True
        try:
            telemetry = cc.get_telemetry()
        except Exception:
            telemetry = None
    except Exception as e:
        return jsonify({
            "status": "success", "available": False, "reason": str(e),
            "safety_policy": _cyber_safety_policy(),
        })

    return jsonify({
        "status": "success",
        "available": available,
        "version": version,
        "safe_tool_count": safe_tool_count,
        "safety_policy": _cyber_safety_policy(),
        "telemetry": telemetry,
        "note": "Offensive tooling (payloads, credential testing, exploitation) is intentionally not exposed.",
    })


@app.route("/api/cyber/capabilities", methods=["GET"])
def cyber_capabilities():
    return jsonify({
        "status": "success",
        "capabilities": _SAFE_CYBER_TOOLS,
        "safety_policy": _cyber_safety_policy(),
    })


def _loopback_port_check():
    """Safe, self-contained TCP-connect check against 127.0.0.1 ONLY."""
    open_ports = []
    for port in _LOOPBACK_PORTS:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        try:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                open_ports.append(port)
        except Exception:
            pass
        finally:
            s.close()
    return open_ports


def _cyber_audit(action, detail):
    try:
        os.makedirs(_RUNTIME_DIR, exist_ok=True)
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {action}: {detail}\n"
        with open(os.path.join(_RUNTIME_DIR, "cyber_audit.log"), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


@app.route("/api/cyber/run-safe-action", methods=["POST"])
def cyber_run_safe_action():
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    confirm = bool(data.get("confirm", False))

    if action != "loopback_port_check":
        return jsonify({"status": "error",
                        "message": "Only 'loopback_port_check' is permitted from the UI."}), 400
    if not confirm:
        return jsonify({"status": "blocked",
                        "message": "Confirmation required. Resend with confirm=true.",
                        "target": "127.0.0.1"}), 400

    # Target is hard-fixed to loopback; no client-supplied target is honoured.
    port_map = {22: "SSH", 80: "HTTP", 443: "HTTPS", 3000: "Dev", 5000: "Flask",
                5173: "Vite", 8000: "CHHOTI DON backend", 8080: "HTTP-Alt",
                8888: "Jupyter/Alt", 9000: "Dev", 11434: "Ollama"}
    open_ports = _loopback_port_check()
    _cyber_audit("loopback_port_check", f"open={open_ports}")
    return jsonify({
        "status": "success",
        "target": "127.0.0.1",
        "checked_ports": _LOOPBACK_PORTS,
        "open_ports": [{"port": p, "service": port_map.get(p, "unknown")} for p in open_ports],
        "note": "Loopback-only defensive check. No external targets are permitted.",
    })


# ══════════════════════════════════════════════════════════════
#  Self-Healing / Code Intelligence (read-only analysis)
# ══════════════════════════════════════════════════════════════
_LAST_ANALYSIS = {"ran": False}


def _discover_py_files(root, limit=400):
    files = []
    skip = {"node_modules", "__pycache__", ".git", ".venv", "venv", "dist",
            "build", ".runtime", "logs", ".integration-temp", ".codex-temp"}
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for n in names:
            if n.endswith(".py"):
                files.append(os.path.join(base, n))
                if len(files) >= limit:
                    return files
    return files


@app.route("/api/self-healing/status", methods=["GET"])
def self_healing_status():
    read_only = _importable_ok("cyber_engine.code_intelligence.code_controller")
    return jsonify({
        "status": "success",
        "available": read_only,
        "read_only_modules": ["static_analysis", "context_graph", "behavior_tracker",
                              "report_builder"],
        "mutating_modules": ["auto_fix_engine", "patch_engine", "rollback_manager",
                             "test_runner", "self_evolve_engine"],
        "apply_enabled": False,
        "apply_note": "Applying code fixes mutates files and requires explicit review; "
                      "it is not automated from the desktop UI for safety.",
        "last_analysis": _LAST_ANALYSIS if _LAST_ANALYSIS.get("ran") else None,
    })


def _importable_ok(module):
    try:
        __import__(module)
        return True
    except Exception:
        return False


@app.route("/api/self-healing/analyze", methods=["POST"])
def self_healing_analyze():
    """Read-only static analysis + health of the project. Never modifies files."""
    global _LAST_ANALYSIS
    try:
        t0 = time.time()
        files = _discover_py_files(_PROJECT_ROOT)
        issues = []
        try:
            from cyber_engine.code_intelligence.static_analysis import run_static_analysis
            raw = run_static_analysis(files) or []
            for it in raw[:200]:
                issues.append(it if isinstance(it, dict) else {"detail": str(it)})
        except Exception as e:
            issues.append({"type": "analyzer_unavailable", "detail": str(e)})

        health = None
        try:
            from cyber_engine.code_intelligence.behavior_tracker import get_project_health
            health = get_project_health(_PROJECT_ROOT)
        except Exception:
            health = None

        result = {
            "ran": True,
            "files_analyzed": len(files),
            "issues_found": len([i for i in issues if i.get("type") != "analyzer_unavailable"]),
            "issues": issues[:100],
            "health": health,
            "duration_sec": round(time.time() - t0, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "read_only": True,
        }
        _LAST_ANALYSIS = result
        return jsonify({"status": "success", **result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/self-healing/reports", methods=["GET"])
def self_healing_reports():
    return jsonify({"status": "success",
                    "last_analysis": _LAST_ANALYSIS if _LAST_ANALYSIS.get("ran") else None})


@app.route("/api/self-healing/apply-approved-fix", methods=["POST"])
def self_healing_apply():
    # Deliberately not automated: file mutation + interactive guardian approval.
    return jsonify({
        "status": "blocked",
        "message": "Automated fix application is disabled in the desktop UI for safety. "
                   "Review suggested changes and apply them via the CLI self-heal tool.",
        "requires_manual_confirmation": True,
    }), 403


# ══════════════════════════════════════════════════════════════
#  Runtime logs (read-only, allowlisted names)
# ══════════════════════════════════════════════════════════════
_LOG_NAMES = {"desktop", "backend", "frontend", "ollama", "launcher"}


@app.route("/api/logs/<name>", methods=["GET"])
def get_log(name):
    if name not in _LOG_NAMES:
        return jsonify({"status": "error", "message": "Unknown log"}), 400
    path = os.path.join(_RUNTIME_DIR, f"{name}.log")
    if not os.path.exists(path):
        return jsonify({"status": "success", "name": name, "lines": [], "exists": False})
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = [ln.rstrip("\n") for ln in lines[-200:]]
        return jsonify({"status": "success", "name": name, "lines": tail, "exists": True})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  Chhoti Don Web API")
    print("  URL : http://localhost:8000")
    print("  UI  : http://localhost:8000/")
    print("=" * 50)
    app.run(host="127.0.0.1", port=8000, debug=False, threaded=True)
