# 🧠 Chhoti Don — Brain.md

> Living codebase memory. Last updated: 2026-08-25. Branch: `desktop-integration`. HEAD: `714da55`.
> Update this file every time a feature is added, changed, or removed.

---

## 0. Project Identity

**What it is:** Chhoti Don is a fully local, zero-cost autonomous multi-agent AI assistant for Windows. It runs a Flask web API + React desktop UI, routes natural-language requests through a brain/agent system, and executes tools (coding, web search, browser automation, cyber analysis) — all powered by local Ollama models with no cloud dependency.

**Hardware constraints:** Designed for an 8GB VRAM GPU on Windows (primary dev machine). Ollama runs locally. `num_ctx: 4096` keeps the qwen3.5 model (~5.5 GB) fully on GPU. `nomic-embed-text` (~0.3 GB) coexists. STT (faster-whisper) defaults to CUDA but falls back to CPU. TTS (Piper) runs CPU-only.

**Core LLM policy (STRICT):**

| Role | Model | Env Override | Notes |
|------|-------|-------------|-------|
| Main brain (chat, reasoning, planning, RAG) | `qwen3.5:latest` | `CHHOTI_DON_MAIN_MODEL` | `think=False`, `keep_alive=-1` |
| Coding (generation, debug, review) | `deepseek-coder-v2:16b-lite-instruct-q4_K_M` | `CHHOTI_DON_CODING_MODEL` | |
| Vision (image understanding) | `llava:latest` | `CHHOTI_DON_VISION_MODEL` | |
| Navigation brain (browser agent) | Same as main (`qwen3.5:latest`) | `CHHOTI_DON_NAV_MODEL` | `num_predict=256`, JSON-only output |
| Embeddings (RAG) | `nomic-embed-text` | `EMBED_MODEL` | `keep_alive=-1` for latency |

**Fully local / zero-cost constraint:** Every design decision must work without any API key. If Ollama is offline, the system falls back to simulation mode (returns a clear error string). No cloud LLM path exists. `is_api_mode()` always returns False.

---

## 1. Directory Map

```
.
├── app.py                          # Flask web API — main HTTP entry point (:8000)
├── main.py                         # CLI entry point (10 interactive modes)
├── core/                           # Brain, routing, memory, safety, config
│   ├── brain.py                    # Brain class: think/stream/think_fast via Ollama
│   ├── brain_registry.py           # 11 named brain configs (coding/debug/default/navigation/...)
│   ├── brain_router.py             # Intent detection + brain routing + Ollama caller
│   ├── config.py                   # Central Config class (model names, Ollama URL, guardian)
│   ├── manager.py                  # ManagerAgent: central orchestrator, tool pipeline, RAG
│   ├── model_router.py             # Maps task_type → correct local model (main/coding/vision)
│   ├── memory.py                   # Short-term conversation memory (in-memory, context window)
│   ├── history_store.py            # SQLite persistent conversation + message history
│   ├── knowledge.py                # RAG bridge: ChromaDB → conversation grounding
│   ├── safety_policy.py            # Security message classifier (allow/educational/refuse)
│   ├── task_classifier.py          # Keyword-based task type detector
│   ├── capabilities.py             # Runtime capability registry (imports → availability)
│   ├── language.py                 # Language detection + Hinglish support
│   ├── local_model_engine.py       # Ollama API + subprocess fallback
│   ├── execution_controller.py     # Plan execution with retry + circuit breaker
│   ├── error_registry.py           # Centralized error codes and severity
│   ├── validator.py                # Plan step validation
│   ├── planner.py                  # Structured planner with telemetry bias
│   ├── response_engine.py          # Standardized response builder
│   ├── adaptive_learning.py        # Tool reliability tracking + confidence adaptation
│   └── telemetry_engine.py         # Execution telemetry (success/failure streaks)
├── browser/                        # Browser automation (Playwright + ddgs/trafilatura)
│   ├── __init__.py                 # Package init — exports all guarded functions
│   ├── agent.py                    # Phase 2: read-only plan→act→observe research loop
│   ├── config.py                   # All browser policy + agent + shopping + HITL tunables
│   ├── guarded.py                  # Guardian choke point for ALL browser operations
│   ├── hitl.py                     # HITL confirmation: classify/confirm/providers/audit
│   ├── routing.py                  # When to use browser vs static path + chat triggers
│   ├── search.py                   # Raw ddgs + trafilatura (search + open_page)
│   ├── session.py                  # Raw Playwright session (headed, read-only, now + interaction)
│   └── shopping.py                 # Phase 4: product extraction, bot-wall detection, cart cap
├── coding_agent/                   # ✅ Autonomous coding/build agent (P1-P6 complete)
│   ├── __init__.py                 # Package init
│   ├── agent.py                    # ReAct agent loop (plan→approve→act→observe→finish)
│   ├── config.py                   # Agent caps (max_steps, heal_budget, context budget)
│   ├── deploy.py                   # Deploy adapters: Vercel/Netlify/GitHub Pages
│   ├── edits.py                    # Atomic file writes (TOCTOU-safe, unified diff preview)
│   ├── guarded.py                  # Guardian choke point + TOOL_TIERS resolver
│   ├── hitl.py                     # HITL approval gate (ContextVar injectable, fail-safe DENY)
│   ├── sandbox.py                  # Path-jailed workspace (realpath containment)
│   ├── server.py                   # Background process supervisor (serve_start/stop/status)
│   └── shell.py                    # Gated shell executor + python -m shim + classifier
├── tools/                          # Tool implementations
│   ├── registry.py                 # ToolRegistry: registers + routes all tools
│   ├── search.py                   # Multi-source web search (DuckDuckGo API + Wikipedia)
│   ├── sandbox.py                  # Sandboxed Python execution (AST-validated, builtins-restricted)
│   ├── code_executor.py            # Multi-language code exec (Python/JS/C/C++/Bash/SQL)
│   ├── code_generator.py           # AI-powered code generation
│   ├── code_debugger.py            # AI-powered code debugging + explanation
│   ├── file_reader.py              # Multi-format file reader
│   ├── calculator.py               # Calculator + unit converter
│   ├── feature_builder.py          # Self-extension: assistant can propose + build new tools
│   ├── image_analyzer.py           # Local vision model image analysis
│   ├── apis.py                     # API integrations (placeholder)
│   └── generated/                  # Tools built by feature_builder at runtime
├── hands/                          # Tool Execution Layer (modular OS/browser/terminal wrappers)
│   ├── base.py                     # BaseHand: abstract base with permissions, action registry
│   ├── tool_manager.py             # Central router between Brain and OS-level operations
│   ├── intent_router.py            # Rule-based NL → (hand, action, params) router
│   ├── filesystem_hand.py          # File operations (read, write, list, search)
│   ├── terminal_hand.py            # Shell command execution
│   ├── windows_hand.py             # Windows-specific: open apps, process management
│   ├── browser_hand.py             # Browser: open URLs, YouTube
│   ├── search_hand.py              # DuckDuckGo + Wikipedia search
│   ├── input_hand.py               # Input simulation
│   ├── vision_hand.py              # Screenshot analysis, popup detection
│   ├── weather_hand.py             # Weather/forecast via Open-Meteo (keyless)
│   ├── news_hand.py                # Headlines via RSS feeds (keyless)
│   ├── youtube_hand.py             # YouTube operations
│   └── time_hand.py                # Time/date/calendar/festival
├── knowledge_pipeline/             # arXiv → ChromaDB RAG ingestion
│   ├── config.py                   # Pipeline config (Ollama, ChromaDB, arXiv, chunking)
│   ├── fetcher.py                  # arXiv API fetcher
│   ├── processor.py                # Text cleaning + chunking
│   ├── store.py                    # Embed via Ollama + persist to ChromaDB
│   ├── retriever.py                # RAG query: embed → query ChromaDB → build prompt → chat
│   ├── novelty.py                  # Dedup filter (cosine distance < threshold)
│   ├── scheduler.py                # Background ingest scheduler
│   ├── app.py                      # Standalone FastAPI /ingest + /ask endpoints
│   └── smoke_test.py               # Pipeline smoke test
├── voice/                          # Voice I/O layer (STT + TTS)
│   ├── __init__.py                 # Package init
│   ├── __main__.py                 # `python -m voice` entry point
│   ├── config.py                   # VoiceConfig dataclass (all tunables)
│   ├── stt.py                      # Speech-to-text: faster-whisper, CUDA→CPU fallback
│   ├── tts.py                      # Text-to-speech: Piper (CPU), interruptible playback
│   ├── capture.py                  # Mic capture + VAD (webrtcvad)
│   ├── orchestrator.py             # VoiceAssistant: mic → VAD → STT → brain → TTS → speaker
│   ├── brain_client.py             # Thin adapter to /api/chat (HTTP or in-process)
│   ├── diagnose.py                 # Audio device diagnostics
│   ├── download_voice.py           # Piper model downloader
│   └── models/                     # Piper ONNX voice models (en_US-lessac-medium)
├── chhoti_agents/                  # Agent subclasses (coder, security, analyst)
│   ├── base.py                     # BaseAgent: think → act → report lifecycle
│   ├── coder.py                    # CoderAgent
│   ├── security.py                 # SecurityAgent
│   └── analyst.py                  # AnalystAgent
├── cyber_engine/                   # Cybersecurity analysis engine
│   ├── cyber_controller.py         # Engine info + orchestrator
│   ├── guardian/operator_guard.py   # Guardian: protected actions + approval gate
│   ├── config/config_manager.py    # DEFAULT_CONFIG (browser policy, guardian, scanner, brain)
│   ├── assessment/                 # Scanners (port, web, credential, exploit, pentest)
│   ├── code_intelligence/          # Code health (static analysis, auto-fix, rollback, evolve)
│   ├── intelligence/               # Threat intelligence (risk, priority, telemetry)
│   ├── malware_detection/          # Malware detection (hash, behavior, signatures)
│   ├── recon/                      # Reconnaissance (port, nmap, subdomain, auto_recon)
│   ├── reverse_engineering/        # RE (PE analyzer, r2 wrapper, strings extractor)
│   ├── session/                    # Session management
│   ├── threat_intel/               # Threat intel (MITRE, C2, lateral, IOC, attack chains)
│   ├── vuln_analysis/              # Vuln analysis (CVE engine, nuclei parser)
│   └── report_exporter.py          # Report generation
├── chhoti-don-react/               # React frontend (Vite + TailwindCSS)
│   ├── src/App.jsx                 # Main app shell
│   ├── src/components/             # UI components (chat, sidebar, views, modals)
│   ├── src/services/               # API clients (chatApi, status)
│   └── src/hooks/                  # Custom hooks (useConversations)
├── desktop/                        # Electron desktop shell
│   ├── main/main.cjs               # Electron main process
│   ├── main/processManager.cjs     # Python backend + Ollama process supervisor
│   ├── main/serviceHealth.cjs      # Health check polling
│   ├── preload/preload.cjs         # IPC bridge
│   └── assets/                     # Icons, loading screen
├── tests/                          # Test suite (485 tests)
│   ├── test_auto_generated.py      # Import smoke tests for all modules
│   ├── test_browser_*.py           # Browser agent/guard/HITL/session/shopping tests
│   ├── test_coding_agent_*.py      # Coding agent loop/shell/sandbox/server/deploy/tools/writes + smoke
│   ├── test_guardian_operator.py   # OperatorGuard ContextVar approver tests
│   ├── test_voice.py               # Voice I/O suite (STT, TTS, orchestrator)
│   ├── test_knowledge.py           # Knowledge pipeline + RAG bridge tests
│   ├── test_local_only.py          # Local-only enforcement (no cloud path)
│   ├── test_brain_retry.py         # Brain retry-on-empty tests
│   ├── test_hands.py               # Hands layer + intent router tests
│   ├── test_safety_chat.py         # Safety policy + /api/chat integration tests
│   ├── test_trigger_precision.py   # Shopping/research trigger precision tests
│   └── test_feature_builder.py     # Feature builder (self-extension) tests
├── .runtime/                       # Runtime state (SQLite DB, logs)
├── logs/                           # Backend/frontend logs
├── Start-ChhotiDon.ps1             # PowerShell launcher
├── Stop-ChhotiDon.ps1              # PowerShell stopper
├── Launch-ChhotiDon.vbs            # VBS launcher (starts without PowerShell window)
├── Install-Desktop-Shortcuts.bat   # Desktop shortcut installer
├── requirements.txt                # Python deps (Flask, ddgs, trafilatura, playwright)
├── requirements-voice.txt          # Voice-specific deps (faster-whisper, piper, etc.)
└── package.json                    # Minimal Node deps (for Electron)
```

**Key file extensions:** `.py` (primary), `.jsx` (React UI), `.cjs` (Electron), `.ps1`/`.vbs`/`.bat` (launchers), `.json` (config/data), `.sql` (SQLite via sqlite3)

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (Browser / CLI / Voice)                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │     app.py (Flask)     │   :8000
                    │  POST /api/chat        │
                    │  SSE streaming          │
                    │  /api/voice/transcribe  │
                    │  /api/voice/speak       │
                    │  /api/browser/research  │
                    │  /api/conversations     │
                    │  /api/cyber/*           │
                    └───────────┬───────────┘
                                │
               ┌────────────────▼────────────────┐
               │      safety_policy.evaluate()    │ ◄── GUARDIAN CHOKE POINT #1
               │  (allow / educational / refuse)  │     Security message classifier
               └──────┬────────────┬──────────────┘
                      │            │
              [allow] │     [educational] │        [refuse] → safe refusal
                      │            │
                      ▼            ▼
         ┌────────────────────────────────────┐
         │        ManagerAgent (manager.py)    │   Central orchestrator
         │  brain_task() / brain_task_stream() │
         │  coding_task() / autonomous_task()  │
         │  shopping_task() / research_task()  │
         └────────────┬──────────┬────────────┘
                      │          │
        ┌─────────────▼──┐  ┌───▼──────────────────┐
        │  Brain (brain.py) │ │ ToolRegistry          │
        │  think()         │ │ tools/registry.py     │
        │  think_stream()  │ │ calculator, search,   │
        │  think_fast()    │ │ code_gen/exec/debug,  │
        │  decide_tool()   │ │ image_analyzer,       │
        └────────┬────────┘ │ browser_research,     │
                 │          │ web_search, open_page  │
    ┌────────────▼───┐      │ browser_navigate/read  │
    │ brain_registry  │      │ feature_builder, ...   │
    │ (11 named brains│      └──────────┬────────────┘
    │  w/ models,     │                 │
    │  prompts, temp) │      ┌──────────▼──────────────────────┐
    └────────┬────────┘      │  browser.guarded (CHOKE POINT #2)│
             │               │  Blocklist → Rate Limit →        │
             ▼               │  Guardian → HITL (Phase 3)       │
  ┌────────────────────┐     │  CRITICAL hard-blocked            │
  │  Ollama (local)     │     └──────────┬──────────────────────┘
  │  127.0.0.1:11434    │                │
  │  /api/generate       │     ┌──────────▼──────────────────────┐
  │  /api/embeddings     │     │  browser.session (Playwright)    │
  └────────────────────┘     │  browser.search (ddgs+trafilatura)│
                             └───────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │                     RAG Pipeline                               │
  │  knowledge_pipeline/ → ChromaDB (ai_knowledge collection)      │
  │  core/knowledge.py → retrieve_context() → inject into prompt   │
  │  Intent-gated: skip RAG for chit-chat                          │
  │  Distance-gated: only chunks < 0.45 cosine distance           │
  └───────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │                  Voice I/O Pipeline                            │
  │  mic → webrtcvad → faster-whisper (STT) → /api/chat → Piper  │
  │  (TTS) → speaker. Never touches brain/tools directly.          │
  └───────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │              Cyber Engine (read-only defensive)                │
  │  cyber_engine/ → CyberController, static analysis,            │
  │  code intelligence, threat intel, malware detection, recon     │
  │  Guardian: OperatorGuard with protected_actions                │
  └───────────────────────────────────────────────────────────────┘

  GUARDIAN CHOKE POINTS:
    #1  safety_policy.evaluate()   — before ANY model/agent call (message level)
    #2  browser.guarded._gate()    — before every browser operation (action level)
    #3  OperatorGuard              — before tool execution in _process_tool_pipeline
    #4  HITL confirm()             — before state-changing browser actions (Phase 3)
```

---

## 3. Request Lifecycle

**Step-by-step: POST /api/chat → streamed response**

1. **Parse** → `app.py:chat()` extracts `message`, `tool`, `conversation_id`, `stream` flag
2. **SSE opt-in** → If `stream=true` and not an image:
   a. `safety_policy.evaluate(message)` → `{action, category}`
   b. If `educational` → SSE stream through `brain_task_stream()` with defensive prompt
   c. If `allow` AND `_is_stream_chat_path()` → SSE stream through `brain_task_stream()`
   d. Otherwise → fall through to non-streaming JSON path
3. **Image path** → If `image_b64` present → `safe_tool_execute("analyze_image", ...)` (bypasses text safety)
4. **Safety gate** → `safety_policy.evaluate(message)`:
   - `refuse` → Return refusal message (no model call)
   - `educational` → `brain_task(safety_policy.educational_prompt(message))`
   - `allow` → `_route_to_tool(message, tool_id)`
5. **Routing** → `_route_to_tool()`:
   - Vision (image path/base64) → `analyze_image` tool
   - `tool_id == "coder"` → `coding_task()`
   - `tool_id` in recon/malware → `autonomous_llm_task()`
   - `tool_id == "search"` → `brain_task("Search and explain: ...")`
   - Default: `detect_intent()` + `detect_task()` → coding task or `brain_task()`
6. **brain_task()** → `ManagerAgent.brain_task()`:
   a. Check browser triggers: `is_shopping_request()` → `shopping_task()`, `is_browser_research_request()` → `research_task()`
   b. `brain.decide_tool()` → rule-based tool detection (calculator, code tools, web search, open_page)
   c. If tool detected → `safe_tool_execute()` (through Guardian gate)
   d. RAG: `_should_run_rag()` → `retrieve_context()` → `build_grounded_system()` (injects top-3 chunks < 0.45 distance)
   e. `brain.think()` → Ollama API call with system prompt + conversation context
7. **Tool execution** → `_process_tool_pipeline()`:
   a. `OperatorGuard.requires_approval()` → if yes, `request_permission()` (terminal prompt)
   b. `tool_registry.execute()` → dispatches to correct tool function
   c. Intelligence layer: recon risk assessment, coding result enrichment
8. **Persist** → `history_store.add_message()` (SQLite, auto-title from first message)
9. **Response** → `_extract_response()` formats output (code blocks, links, tool results)
10. **Return** → JSON response with `status`, `response`, `intent`, `task_type`, `execution_time`, `provider`, `model`, `live`

---

## 4. Module Registry

### `app.py` — Flask Web API
- **Purpose:** HTTP API + React SPA server. Single entry point for all UI communication.
- **Key routes:** `/api/chat`, `/api/status`, `/api/voice/transcribe`, `/api/voice/speak`, `/api/browser/research`, `/api/browser/research/respond`, `/api/conversations/*`, `/api/cyber/*`, `/api/self-healing/*`, `/api/logs/*`, `/api/memory/*`, `/api/capabilities`
- **Imports:** core.manager, core.task_classifier, core.brain_router, core.history_store, core.capabilities, core.safety_policy
- **Hardcoded:** Port 8000, localhost only, CORS limited to dev origins

### `main.py` — CLI Entry
- **Purpose:** Interactive CLI with 10 modes (single agent, pipeline, brain, autonomous, coding, smart auto, etc.)
- **Imports:** core.manager, core.task_classifier, core.brain_router, cyber_engine.code_intelligence

### `core/brain.py` — Brain Class
- **Purpose:** Central LLM interface. think(), think_stream(), think_fast(), decide_tool().
- **Key methods:** `think()` (main reasoning), `think_stream()` (token-by-token generator), `think_fast()` (low-latency browser agent), `think_code()`, `think_debug()`, `think_explain()`, `plan_task()`, `decide_tool()`, `review_and_fix()`
- **Ollama params:** `stream:False/True`, `think:False`, `keep_alive:-1`, `num_ctx:4096`, `num_predict:2048`
- **Internal deps:** core.memory, core.brain_registry, core.config

### `core/brain_registry.py` — Brain Config Registry
- **Purpose:** 11 named brains (coding, debug, malware, analytics, research, conversation, planner, reviewer, vision, default, navigation) with model/temperature/system_prompt/capabilities
- **Key config:** All models resolved via `model_router.resolve_model()` — no hardcoded model names here
- **Appended:** Hinglish style + web tool instructions (except planner/reviewer/navigation)

### `core/manager.py` — ManagerAgent
- **Purpose:** Central orchestrator. Routes to brain, tools, coding, browser, shopping.
- **Key methods:** `brain_task()`, `brain_task_stream()`, `coding_task()`, `research_task()`, `shopping_task()`, `autonomous_llm_task()`, `hybrid_llm_task()`, `safe_tool_execute()`, `_process_tool_pipeline()`
- **RAG:** `_should_run_rag()` intent-gates ChromaDB embedding. `retrieve_context()` injects grounded context.

### `core/model_router.py` — Model Routing
- **Purpose:** Single source of truth for mapping task_type → local model.
- **Models:** MAIN_MODEL (qwen3.5), CODING_MODEL (deepseek-coder-v2), VISION_MODEL (llava)
- **Also:** `check_ollama()`, `check_model()`, `routing_report()`

### `core/config.py` — Configuration
- **Purpose:** Central config class. All tunables from env vars.
- **Key values:** `OLLAMA_HOST=http://127.0.0.1:11434`, `OLLAMA_TIMEOUT=120`, `GUARDIAN_ENABLED=True`, `RATE_LIMIT_WINDOW=60`, `MAX_SCANS_PER_WINDOW=5`

### `core/safety_policy.py` — Safety Policy
- **Purpose:** Deterministic message classifier (allow/educational/refuse) for security-topic messages.
- **How it works:** Checks `_ATTACK_TERMS` → `_DEFENSIVE_STRONG` (always educational) → `_OFFENSIVE_MARKERS` + `_CREATION_VERBS` (refuse) → fallback educational
- **Design:** Conceptual questions always educational; operational attack requests always refused.

### `core/knowledge.py` — RAG Bridge
- **Purpose:** Retrieves from ChromaDB and injects into conversation system prompt.
- **Params:** `RAG_TOP_K=3`, `RAG_MAX_DISTANCE=0.45`, `RAG_CHUNK_CHARS=900`
- **Design:** Fail-open (any error → return empty). Intent-gated (skip for chit-chat).

### `core/history_store.py` — SQLite Persistence
- **Purpose:** Durable conversation + message storage. WAL mode, foreign keys, idempotent schema creation.
- **DB location:** `.runtime/chhoti_don_history.db` (relocatable via `CHHOTI_DON_RUNTIME_DIR`)
- **Thread safety:** `threading.Lock()` per operation, fresh connection per call.

### `browser/guarded.py` — Guardian Choke Point
- **Purpose:** THE single enforcement point for all browser operations. Blocklist → rate limit → guardian → HITL → execute.
- **Read path:** `web_search()`, `open_page()`, `browser_navigate()`, `browser_read()`, `browser_get_content()`
- **Interactive path (Phase 3):** `_interactive_gate()` → `hitl.classify()` → CRITICAL hard-block → blocklist → rate limit → `hitl.confirm()` → execute
- **Shopping (Phase 4):** `browser_search_products()` (read-only), `browser_add_to_cart()` (HITL-gated + cart cap)

### `browser/hitl.py` — Human-in-the-Loop
- **Purpose:** Risk classification + approval gate for state-changing actions.
- **Tiers:** LOW (auto-allow), MEDIUM (confirm: type/select), HIGH (confirm: click/press/cart), CRITICAL (hard-block: payment/checkout/submit/credential fields)
- **Providers:** `approve_all` / `deny_all` (tests), `InteractiveRun` (Flask pause/resume)
- **Fail-safe:** No provider → DENY, timeout → DENY, ambiguous target → CRITICAL

### `browser/agent.py` — Research Agent (Phase 2)
- **Purpose:** Bounded read-only plan→act→observe loop for multi-step web research.
- **READ-ONLY invariant:** Only search/navigate/read_page/get_content/finish actions. No click/type/interact.
- **Context budget:** max_obs=6 observations, each truncated to 1200 chars → ~2k tokens per step

### `browser/shopping.py` — Shopping Assist (Phase 4)
- **Purpose:** Product extraction, bot-wall detection, cart cap, search URL templates.
- **Cart cap:** `MAX_CART_ADDITIONS=5` per task (thread-local).
- **Bot-wall:** Detects captcha/recaptcha/login wall → returns handoff to human.

### `browser/routing.py` — Chat Trigger Detection
- **Purpose:** Deterministic phrase matching for browser research and shopping triggers.
- **Design:** Intent-qualified (coding context suppresses triggers). Deliberately narrow to avoid false positives.

### `tools/registry.py` — Tool Registry
- **Purpose:** Central registry of all executable tools. Maps tool names → functions.
- **Registered tools:** calculator, read_file, search, web_search, open_page, browser_navigate, browser_read, browser_get_content, browser_research, analyze_image, run_python, port_scan, subdomain_scan, nmap_scan, generate_code, execute_code, debug_code, explain_code, feature_builder
- **Also loads:** Generated tools from `tools/generated/`

### `tools/sandbox.py` — Python Sandbox
- **Purpose:** Safe Python code execution with AST validation, builtin restrictions, module allowlist, timeout.
- **Forbidden:** os, sys, subprocess, shutil, socket, exec, eval, open, __import__
- **Allowed modules:** math, random, datetime, json, re, string, collections, itertools, etc.

### `hands/tool_manager.py` — Hands Layer Tool Manager
- **Purpose:** Modular tool execution layer. Brain → ToolManager → Hands (filesystem, terminal, browser, weather, etc.)
- **Design:** Additive and self-contained. Each Hand reports availability via health(). Thread-safe with soft timeouts.

### `knowledge_pipeline/store.py` — ChromaDB Store
- **Purpose:** Embed via Ollama `nomic-embed-text` + persist to ChromaDB. Process-level singletons for latency.
- **Design:** Novelty filter (cosine < 0.12), dedup by ID, fail-open on Ollama errors.

### `voice/orchestrator.py` — Voice Assistant
- **Purpose:** mic → VAD → STT → brain → TTS → speaker. Never touches reasoning/tools directly.
- **Modes:** push_to_talk (default), continuous_vad
- **Barge-in:** Threading.Event-based interruption during TTS playback.

### `cyber_engine/guardian/operator_guard.py` — OperatorGuard
- **Purpose:** Protected actions approval gate. Protected: self_heal, auto_fix, patch_apply, code_rewrite.
- **Approval:** ContextVar-injectable provider (default DENY). Same pattern as `browser/hitl.py`. Terminal `input()` fully removed.

---

## 5. LLM & Model Configuration

| Brain Type | Model | Temperature | num_ctx | num_predict | think | keep_alive | Notes |
|------------|-------|-------------|---------|-------------|-------|------------|-------|
| default | qwen3.5:latest | 0.7 | 4096 | 2048 | False | -1 | General chat |
| coding | deepseek-coder-v2:16b-lite-q4_K_M | 0.3 | 4096 | 2048 | False | -1 | Code generation |
| debug | deepseek-coder-v2:16b-lite-q4_K_M | 0.2 | 4096 | 2048 | False | -1 | Bug fixing |
| navigation | qwen3.5:latest | 0.1 | 4096 | 256 | False | -1 | Browser agent JSON-only |
| planner | qwen3.5:latest | 0.2 | 4096 | 1024 | False | -1 | JSON planning |
| reviewer | qwen3.5:latest | 0.1 | 4096 | 512 | False | -1 | APPROVED/patch |
| vision | llava:latest | 0.3 | 4096 | 2048 | False | -1 | Image understanding |
| malware | qwen3.5:latest | 0.4 | 4096 | 3072 | False | -1 | Security analysis |
| conversation | qwen3.5:latest | 0.8 | 4096 | 1024 | False | -1 | Casual chat |
| analytics | qwen3.5:latest | 0.5 | 4096 | 2048 | False | -1 | Data analysis |
| research | qwen3.5:latest | 0.6 | 4096 | 3072 | False | -1 | Research |

**Fallback chain:** Local Ollama → Simulation mode (returns clear error string)
    Local-only: OpenAI path fully excised. No cloud fallback. No OPENAI_API_KEY in config.

**RAG embedding:** `nomic-embed-text` via `/api/embeddings` with `keep_alive:-1`

**Key env vars:**
- `CHHOTI_DON_OLLAMA_NUM_CTX` (default 4096)
- `CHHOTI_DON_MAIN_MODEL`, `CHHOTI_DON_CODING_MODEL`, `CHHOTI_DON_VISION_MODEL`
- `OLLAMA_HOST` (default http://127.0.0.1:11434)
- `CHHOTI_DON_OLLAMA_TIMEOUT` (default 120s)

---

## 6. Tool Registry

| Tool Name | Module | Tier | HITL? | Description |
|-----------|--------|------|-------|-------------|
| calculator | tools/calculator.py | LOW | No | Math expression evaluation + unit conversion |
| read_file | tools/file_reader.py | LOW | No | Multi-format file reading with metadata |
| search | tools/search.py | LOW | No | DuckDuckGo + Wikipedia multi-source search |
| web_search | browser/guarded.py | LOW | No | DDGS search (guarded, blocked domains, rate limited) |
| open_page | browser/guarded.py | LOW | No | trafilatura page read (guarded, blocked domains) |
| browser_navigate | browser/guarded.py | LOW | No | Playwright navigate + title extraction |
| browser_read | browser/guarded.py | LOW | No | Playwright full page text extraction |
| browser_get_content | browser/guarded.py | LOW | No | Playwright accessibility tree |
| browser_research | tools/registry.py | LOW | No | Multi-step read-only research agent |
| analyze_image | tools/image_analyzer.py | LOW | No | Local llava vision model |
| run_python | tools/sandbox.py | MEDIUM | No | Sandboxed Python execution |
| port_scan | cyber_engine/recon/ | MEDIUM | No | TCP port scanning |
| subdomain_scan | cyber_engine/recon/ | MEDIUM | No | Subdomain enumeration |
| nmap_scan | cyber_engine/recon/ | HIGH | Yes (terminal) | Nmap integration (if available) |
| generate_code | tools/code_generator.py | LOW | No | AI-powered code generation |
| execute_code | tools/code_executor.py | MEDIUM | No | Multi-language code execution (subprocess) |
| debug_code | tools/code_debugger.py | LOW | No | AI-powered debugging |
| explain_code | tools/code_debugger.py | LOW | No | AI-powered code explanation |
| feature_builder | tools/feature_builder.py | HIGH | Yes | Self-extension: propose + build new tools |
| click (browser) | browser/guarded.py | HIGH | Yes (HITL) | Click element in browser |
| type_text (browser) | browser/guarded.py | MEDIUM | Yes (HITL) | Type text in browser field |
| select_option (browser) | browser/guarded.py | MEDIUM | Yes (HITL) | Select dropdown option |
| press_key (browser) | browser/guarded.py | HIGH | Yes (HITL) | Press keyboard key |
| add_to_cart (browser) | browser/guarded.py | HIGH | Yes (HITL) | Add product to cart (capped at 5) |
| search_products (browser) | browser/guarded.py | LOW | No | Read-only product search |
| fs_list_dir (coding) | coding_agent/guarded.py | LOW | No | List files in jailed workspace |
| fs_read_file (coding) | coding_agent/guarded.py | LOW | No | Read file in jailed workspace |
| fs_search (coding) | coding_agent/guarded.py | LOW | No | Search text in jailed workspace |
| fs_write_file (coding) | coding_agent/guarded.py | MEDIUM | Yes (HITL+diff) | Write file with unified diff preview |
| fs_create_file (coding) | coding_agent/guarded.py | MEDIUM | Yes (HITL+diff) | Create new file in workspace |
| fs_edit_file (coding) | coding_agent/guarded.py | MEDIUM | Yes (HITL+diff) | Surgical edit (unique old_str replace) |
| fs_make_dir (coding) | coding_agent/guarded.py | MEDIUM | Yes (HITL+diff) | Create directory in workspace |
| fs_delete_file (coding) | coding_agent/guarded.py | HIGH | Yes (individual) | Delete file — always individual confirm |
| sh_run (coding) | coding_agent/guarded.py | MEDIUM/HIGH | Yes (HITL) | Gated shell — MEDIUM allowlist, HIGH unknown, CRITICAL block |
| serve_start (coding) | coding_agent/guarded.py | MEDIUM/HIGH | Yes (HITL) | Start background server process |
| serve_status/logs/stop | coding_agent/guarded.py | LOW | No | Server supervisor read/stop operations |
| deploy_check (coding) | coding_agent/guarded.py | LOW | No | Check deploy CLI auth status |
| deploy_run (coding) | coding_agent/guarded.py | ALWAYS-CONFIRM | Individual only | Deploy — never session-auto, never approve_all |

---

## 7. Safety & Guardian Architecture

### Message-Level Safety (`core/safety_policy.py`)
- **When:** Before ANY model/agent call (in `app.py` chat route)
- **How:** Deterministic keyword matching — no LLM call
- **Actions:**
  - `allow` → route normally
  - `educational` → answer defensively via LLM with safe system prompt
  - `refuse` → return refusal message (no model call)
- **Attack term list:** ~60 specific terms (ddos, malware, sql injection, etc.)
- **Offensive markers:** ~80 phrasings ("how to perform", "write a script to", etc.)
- **Defensive override:** If "prevent/defend/detect/protect" present → always educational
- **Conceptual override:** If "how does/what is/explain" present → always educational (unless creating malicious artifact)

### Action-Level Safety (`browser/guarded.py`)
- **When:** Before every browser operation
- **Order:** Blocklist → Rate limit (5/min per domain) → Guardian assessment → HITL confirmation
- **Blocked domains:** localhost, 127.0.0.1, ::1, 169.254.169.254

### HITL Safety (`browser/hitl.py`)
- **Classification:** LOW → MEDIUM → HIGH → CRITICAL
- **CRITICAL hard-blocks:** payment, checkout, submit, buy, place-order, credential fields (password, OTP, CVV, UPI, card number), ambiguous targets, commerce URLs (/checkout, /cart, /payment)
- **MEDIUM:** type_text, select_option → require approval
- **HIGH:** click, press_key, add_to_cart → require approval
- **Fail-safe:** No provider → DENY, timeout (120s) → DENY, error → DENY

### Tool Execution Safety (`core/manager.py`)
- **When:** Before every tool execution via `_process_tool_pipeline()`
- **OperatorGuard:** Protected actions (self_heal, auto_fix, patch_apply, code_rewrite) require ContextVar-injectable approval (default DENY)
- **Python sandbox:** AST validation, module allowlist, builtin restrictions, timeout

### ⚠️ Safety Invariant: `approve_all` exception
- In `browser/hitl.py`, `approve_all` is a test helper that bypasses all HITL confirmations
- It should NEVER be installed as a provider in production
- Currently only used in tests

### Coding Agent Safety (`coding_agent/guarded.py` + `coding_agent/sandbox.py`)
- **Workspace jail:** `realpath` containment — any path resolving outside workspace = SANDBOX_VIOLATION before any tool executes. Blocks `../`, absolute paths, symlink/junction escapes, drive-letter absolutes (Windows: `C:\`, `E:\`).
- **TOOL_TIERS resolver:** `resolve_tier(tool_name, in_plan)` — explicit tier map for every coding_agent tool. Never inferred at runtime.
- **CRITICAL hard-block:** Shell commands with metachars, sudo, dd, mkfs, rm -rf, shutdown, format, absolute system paths → BLOCKED before executor. Fires even under `approve_all`.
- **Deploy wall:** `deploy_run` runs on a SEPARATE `_deploy_approver` ContextVar channel. `approve_all` structurally CANNOT reach it. Always individual confirm.
- **python -m shim:** Bare `pytest`/`pip`/`unittest`/`coverage` rewritten to `python -m X` before executor receives argv. CRITICAL classifier still runs on the rewritten argv.
- **Implicit finish:** TRIGGER A (exit_code=0 on verify command → `implicit_verify`), TRIGGER B (post-nudge success-repeat → `implicit_repeat`). Model never needs to emit `{finish}` for the agent to terminate on success.
- **OperatorGuard:** `request_permission()` now uses ContextVar injectable approver (default DENY). Terminal `input()` fully removed. Same pattern as `browser/hitl.py`.

---

## 8. Feature Status Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| **Core chat pipeline** (Flask → safety → manager → brain → Ollama) | ✅ COMPLETE | Working, streaming SSE support |
| **RAG / knowledge pipeline** (arXiv → ChromaDB → inject) | ✅ COMPLETE | Intent-gated, distance-gated, fail-open |
| **Web search** (ddgs + trafilatura) | ✅ COMPLETE | Guarded, rate-limited, blocked domains |
| **Browser P1: read-only navigation tools** | ✅ COMPLETE | Playwright headed, accessibility tree, a11y markdown |
| **Browser P2: LLM research loop** | ✅ COMPLETE | Bounded plan→act→observe, read-only invariant |
| **Browser P3: gated click/type HITL** | ✅ COMPLETE | Full HITL with CRITICAL hard-blocks |
| **Browser P4: shopping assist (cart ceiling)** | ✅ COMPLETE | Product extraction, cart cap, bot-wall detection |
| **Coding agent P1: path-jailed sandbox + read-only fs** | ✅ COMPLETE | Merged to trunk — commit 714da55 |
| **Coding agent P2: gated file writes + HITL diff preview** | ✅ COMPLETE | Merged to trunk — atomic writes, unified diff HITL |
| **Coding agent P3: ReAct agent loop** | ✅ COMPLETE | plan→approve→act→observe→finish |
| **Coding agent P4: gated shell + self-heal loop** | ✅ COMPLETE | python -m shim added (F2), implicit-finish added (F3) |
| **Coding agent P5: local server supervisor** | ✅ COMPLETE | Merged to trunk |
| **Coding agent P6: public deploy (always-confirm gate)** | ✅ COMPLETE | deploy_run on separate approver channel |
| **Voice I/O** (STT: faster-whisper, TTS: Piper) | ✅ COMPLETE | CUDA→CPU fallback, barge-in, push-to-talk + continuous |
| **Session intelligence / memory** | 🔶 PARTIAL | Short-term Memory class exists; no long-term semantic memory. history_store is SQLite but separate from Memory class. |
| **Guardian / safety engine** | ✅ COMPLETE | Message-level + action-level + HITL |
| **Guardian rate limiting** | ✅ COMPLETE | 5/min per domain for browser operations |
| **Stronger fingerprinting / pre-execution risk scoring** | ⏳ PENDING | OperatorGuard assess_action is basic; no pre-execution risk scoring |
| **python -m shim** | ✅ COMPLETE | F2 — pytest/pip/unittest/coverage rewritten |
| **Implicit finish on verified success** | ✅ COMPLETE | F3 — TRIGGER A (implicit_verify) + TRIGGER B (implicit_repeat) |
| **Guardian explicit tiering of sh_run/serve_start/deploy_run** | ✅ COMPLETE | F4 — TOOL_TIERS resolver, deploy on separate channel |
| **Cloud/OpenAI path purge** | ✅ COMPLETE | F1.5 — OpenAI fully excised, grep-0 confirmed on all .py source |
| **Local-only constraint enforcement** | ✅ COMPLETE | is_api_mode() always False, no OPENAI_API_KEY in config |

---

## 9. Test Coverage Map

| Test File | Tests | Module Covered | Real vs Mocked | Notes |
|-----------|-------|----------------|----------------|-------|
| `tests/test_auto_generated.py` | ~60 | Import smoke test for all modules | Real (import only) | No functional assertions |
| `tests/test_browser_agent.py` | 14 | browser/agent.py + routing.py | Mocked (mock think_fn, guarded) | All agent loop logic tested; no real LLM or browser |
| `tests/test_browser_guard.py` | 4 | browser/guarded.py | Mocked (mock search/session) | Blocklist, rate limit, content cap |
| `tests/test_browser_hitl.py` | 16 | browser/hitl.py | Mocked | HITL classify, confirm, timeout, InteractiveRun |
| `tests/test_browser_session.py` | 13 | browser/session.py + routing.py | Mocked (Playwright mocked) | Guardian routing, a11y markdown, routing decision |
| `tests/test_browser_shopping.py` | 14 | browser/shopping.py + guarded.py | Mocked | Product extraction, cart cap, bot-wall, HITL |
| `tests/test_hands.py` | 14 | hands/ (all) | Real + mocked (time/weather) | ToolManager, BaseHand, IntentRouter |
| `tests/test_safety_chat.py` | 9 | core/safety_policy.py + app.py | Mocked (Flask test client, mocked ManagerAgent) | Safety classification + /api/chat integration |
| `tests/test_trigger_precision.py` | 6 | browser/routing.py | Real (deterministic functions) | Shopping/research trigger precision |
| `tests/test_feature_builder.py` | 10 | tools/feature_builder.py | Mocked (sandbox mocked) | Propose, apply, rollback, loader |
| `tests/test_language.py` (root) | ~5 | core/language.py | Real | Language detection |
| `tests/test_guardian_operator.py` | 22 | cyber_engine/guardian/operator_guard.py | Mocked | ContextVar approver — approve/deny/default-deny |
| `tests/test_voice.py` | 22 | voice/*.py | Mocked (subprocess, sounddevice, faster-whisper) | STT, TTS, orchestrator, brain_client |
| `tests/test_knowledge.py` | 21 | knowledge_pipeline/ + core/knowledge.py | Mocked (Ollama, ChromaDB) | RAG bridge, chunker, novelty, fetcher, store |
| `tests/test_coding_agent_smoke.py` | 5 | coding_agent/ full pipeline | Mocked (LLM only) | L1 write, L2 shim, L3 implicit_verify, L4 CRITICAL block, L5 sandbox escape |
| `tests/test_local_only.py` | 6 | core/brain.py, core/config.py | Real (grep-based) | No cloud model, no api_mode, local-only enforcement |
| `tests/test_brain_retry.py` | ~5 | core/brain.py retry logic | Mocked | Retry-on-empty, fallback behavior |
| `tests/test_coding_agent_*.py` | ~350 | coding_agent/ (unit tests) | Mocked (LLM + tools) | agent loop, shell, sandbox, server, deploy, tools, writes |

**Total:** 485 test functions

### ⚠️ Key test gaps:
1. **No integration tests with real Ollama** — all brain/model tests are mocked
2. **No Playwright integration tests** — all browser tests mock Playwright
3. **cyber_engine tests exist only as import smoke tests**
4. **No end-to-end / smoke test harness** that starts the Flask server and hits /api/chat

---

## 10. Technical Debt & Known Issues

### Critical

| File | Issue |
|------|-------|
| `cyber_engine/guardian/operator_guard.py` | **[RESOLVED 2026-08-25]** ContextVar injectable approver, default DENY. Terminal `input()` fully removed. |
| `core/telemetry_engine.py` | **[RESOLVED 2026-08-25]** Unreachable block moved into `__init__()`. |

### High

| File | Issue |
|------|-------|
| `core/config.py` | `OPENAI_API_KEY` env var reference exists. While gated, it's a potential policy concern — any env leak could activate the cloud path. |
| `tools/sandbox.py` | **[RESOLVED 2026-08-25]** Duplicate removed, single definition at 50000. |
| `tools/code_executor.py` | Subprocess-based code execution has NO sandboxing beyond timeout (15s). C/C++ code is compiled and run natively. Bash is executed directly. |
| `browser/session.py` | The `read_page()`, `get_content()`, `search_products()`, `do_action()` methods were truncated in the audit. The file was too large to fully read. |

### Medium

| File | Issue |
|------|-------|
| `core/memory.py` | In-memory only (no persistence by default). `MAX_MEMORY=50`, `CONTEXT_WINDOW=6`. Separate from `history_store.py` SQLite persistence. |
| `core/brain_registry.py` | Duplicate `Optional` import (line 3). |
| `core/execution_controller.py` | Duplicate `Tuple` import (line 7). |
| `core/language.py` | `translate_to_english()` and `translate_back()` are stubs (return input unchanged). |
| `core/error_registry.py` | Duplicate `Optional` import. |
| `core/planner.py` | Duplicate `Optional` import. |
| `voice/config.py` | `KMP_DUPLICATE_LIB_OK=TRUE` set globally — suppresses a real error that should be fixed properly. |
| `tools/search.py` | Uses `urllib.request` (stdlib) instead of `requests` — inconsistent with rest of codebase. |
| `browser/shopping.py` | Flipkart/Amazon selectors are brittle (class names change frequently). Bot-wall detection is keyword-based only. |

### Low

| File | Issue |
|------|-------|
| `requirements.txt` | **[RESOLVED 2026-08-25]** googletrans removed (unused), chromadb/numpy added. |
| `core/capabilities.py` | Voice capability checks `voice.VoiceAssistant` — correct class name. |
| `cleanup.py` | Contains `# TODO: remove this` and TODO/FIXE detection logic. |
| Multiple files | Windows-specific: process termination (`taskkill`), path separators, SSL cert handling, `.vbs`/`.ps1` launchers. |
| `browser/.userdata/` | **[RESOLVED 2026-08-25]** Added to .gitignore. |

---

## 11. Pending Roadmap

### ✅ Completed (2026-08-25)

| Item | Commit |
|------|--------|
| Merge coding agent P1-P6 to desktop-integration trunk | 714da55 |
| OperatorGuard headless-safe (ContextVar, default DENY) | 4b4d18e |
| Telemetry unreachable code fixed | 51e69f0 |
| Sandbox duplicate MAX_OUTPUT_SIZE removed | 40f21a6 |
| browser/.userdata gitignored | 7b48c76 |
| requirements.txt: chromadb/numpy added, googletrans removed | 2f9561e |
| python -m shim (F2) | 8b12437 |
| Implicit-finish on verified success (F3) | 2b98c35 |
| Guardian explicit tiering (F4) | ade8377 |
| Voice test suite +22 tests | 3fd3314 |
| Knowledge pipeline test suite +21 tests | 17c5588 |
| Coding agent smoke tests +5 scenarios | 7670769 |
| OpenAI cloud path excised, local-only enforced (F1+F1.5) | 0a0bc4a |

### P0 — Must-do before "production ready"

| Item | Files | Complexity | Depends On |
|------|-------|------------|------------|
| End-to-end smoke test with REAL Ollama (live deepseek, no mocks) | `tests/test_e2e_smoke.py` | L | Real Ollama running |

### P1 — High value, builds on existing base

| Item | Files | Complexity | Depends On |
|------|-------|------------|------------|
| Wire Hands Layer into brain_task (replace direct tool calls) | `core/manager.py`, `hands/tool_manager.py` | L | — |
| Add long-term semantic memory (beyond context window) | `core/memory.py` | L | — |
| Wire voice into Electron desktop app | `desktop/`, `voice/` | M | — |

### P2 — Medium value, new capability

| Item | Files | Complexity | Depends On |
|------|-------|------------|------------|
| Streaming support for coding tasks | `app.py`, `core/manager.py` | M | — |
| Browser profile persistence (login reuse across sessions) | `browser/session.py` | L | — |
| Auto-updating knowledge pipeline scheduler from main app | `knowledge_pipeline/scheduler.py`, `app.py` | M | — |

### P3 — Nice to have / polish

| Item | Files | Complexity | Depends On |
|------|-------|------------|------------|
| Rate limiting for /api/chat (per-IP) | `app.py` | S | — |
| Structured audit trail (beyond log files) | `app.py`, `browser/hitl.py` | M | — |
| Frontend: voice UI controls (mic button, settings) | `chhoti-don-react/` | M | — |
| WebSocket upgrade for real-time streaming | `app.py`, frontend | L | — |
| Plugin architecture for community-contributed tools | `tools/`, `hands/` | L | — |

---

## 12. Key Design Decisions (ADR-lite)

### Why `realpath` jail is used in coding_agent but not tools/sandbox.py
`tools/sandbox.py` restricts via AST validation and builtin suppression (safe for sandboxed Python execution). `coding_agent/sandbox.py` implements `realpath`-based workspace containment — the stronger model needed for autonomous file/shell operations.

### Why guarded choke point pattern
`browser/guarded.py` is the SINGLE enforcement point for all browser operations. Raw operations (`browser/search.py`, `browser/session.py`) are NEVER called directly — only through the guarded wrappers. This guarantees blocklist + rate limit + guardian + HITL cannot be bypassed.

### Why separate deploy approver
Payment/checkout/submit actions are CRITICAL-tier hard-blocked in `browser/hitl.py`. They are NEVER offered for confirmation — they are refused outright. The cart (add-to-cart) is the permitted ceiling. This is a deliberate safety boundary.

### Why no cloud fallback
The project is fully local, zero-cost operation. The OpenAI/cloud path has been fully excised (F1.5). If Ollama is offline, the system returns a clear "local model unavailable" error — never a fabricated answer and never a cloud call.

### Why implicit-finish is needed
The coding agent (`coding_agent/agent.py`) uses deepseek-coder-v2 which often never emits `{finish}`. Two programmatic triggers solve this: TRIGGER A (verify command succeeds with exit_code=0 → stop) and TRIGGER B (model repeats the same successful action after a nudge → stop). The model never needs to emit `{finish}` for the agent to terminate on success.

### Why `_should_run_rag` intent-gates RAG
The RAG embed + Chroma query costs ~763ms per message. For plain chit-chat ("hi", "kaise ho"), the Chroma query always returns nothing (distance > 0.45). The intent gate skips this wasted work entirely without changing answer content.

### Why `think:False` on qwen3.5
qwen3.5 is a "thinking" model — without `think:False`, it spends the token budget on hidden reasoning and can return an empty visible answer. Disabling gives clean, fast replies. `CHHOTI_DON_NAV_MODEL` can override the navigation brain model.

### Why 4096 num_ctx
qwen3.5's default context window is enormous (~16GB VRAM). Capping at 4096 keeps the entire model on-GPU (no CPU spill) for faster eval on 8GB GPUs. Tunable via `CHHOTI_DON_OLLAMA_NUM_CTX`.

### Why `KMP_DUPLICATE_LIB_OK=TRUE`
Anaconda links several OpenMP runtimes (numpy-MKL, ctranslate2, onnxruntime). Without this, faster-whisper aborts at transcribe time with "OMP Error #15: libiomp5md.dll already initialized". This is a workaround; the proper fix is to ensure only one OpenMP runtime is linked.

---

## 13. How to Update This File

- **When to update:** After every commit that adds/changes/removes a feature, module, brain config, tool, or safety mechanism.
- **What to update:** The relevant section(s) only — don't rewrite the whole file.
- **Keep the "Last updated" line current.**
- **Never delete history** — mark old items as `[SUPERSEDED by <date>]` if changed.
- **Accuracy rule:** Every claim must be traceable to an actual file. If you can't find something in the code, say "NOT FOUND IN CODE".
