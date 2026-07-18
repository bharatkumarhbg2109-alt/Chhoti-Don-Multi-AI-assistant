"""
Chhoti Don v3 - Autonomous Multi-Agent AI
Main entry point with Natural Language Handler integrated.
"""

from core.manager import ManagerAgent
from core.task_classifier import detect_task, detect_coding_action
from core.brain_router import detect_intent, route_coding_tool
from cyber_engine.code_intelligence.code_controller import run_code_intelligence
import json
import os
import sys
from typing import Type


# ==================================================
# 🎨 BANNER
# ==================================================
def print_banner():
    print("\n" + "=" * 55)
    print("🚀  Chhoti Don v3 - Autonomous Multi-Agent AI")
    print("=" * 55)
    print("Modes:")
    print("1  → Single Agent Mode")
    print("2  → Pipeline Mode")
    print("3  → Direct Brain Mode")
    print("4  → View Memory")
    print("5  → Autonomous Mode")
    print("6  → Manual Tool Test")
    print("7  → EvolveX Code Intelligence Mode")
    print("8  → Full Auto Self-Heal Mode")
    print("9  → 💻 Coding Mode (Natural Language)")
    print("10 → 🧠 Smart Auto Mode (Auto-detect everything)")
    print("Type 'exit' anytime to quit.\n")


# ==================================================
# 🖨️ PRETTY PRINT
# ==================================================
def pretty_print(result):
    print("\n" + "=" * 55)

    if isinstance(result, dict):
        print(f"🤖 Agent    : {result.get('agent')}")
        print(f"🌐 Language : {result.get('language')}")

        print("\n🧠 Thinking:")
        print(result.get("thinking"))

        print("\n💡 Final Output:\n")
        output = result.get("output")

        # Coding output pretty print
        if isinstance(output, dict):
            _pretty_print_coding_output(output)
        else:
            print(output)

        if result.get("confidence") is not None:
            print(f"\n📊 Confidence: {result.get('confidence')}")

        # Coding meta info
        if result.get("coding_meta"):
            meta = result["coding_meta"]
            print(f"\n🔧 Coding Meta:")
            print(f"   Tool     : {meta.get('detected_tool')}")
            print(f"   Language : {meta.get('detected_language')}")
            print(f"   Time     : {meta.get('execution_time_sec')}s")
            if meta.get("auto_executed"):
                print(f"   Pipeline : generate → execute ✅")

        # Auto execution result
        if result.get("execution_result"):
            exec_out = result["execution_result"]
            print(f"\n▶️  Auto-Execution Output:")
            print("-" * 40)
            if isinstance(exec_out, dict):
                status = exec_out.get("status", "unknown")
                icon = "✅" if status == "success" else "❌"
                print(f"{icon} Status : {status.upper()}")
                if exec_out.get("output"):
                    print(f"Output  :\n{exec_out['output']}")
                if exec_out.get("stderr"):
                    print(f"⚠️ Error :\n{exec_out['stderr']}")
                if exec_out.get("execution_time"):
                    print(f"⏱ Time  : {exec_out['execution_time']}")
            else:
                print(exec_out)
            print("-" * 40)

    else:
        print(result)

    print("=" * 55 + "\n")


def _pretty_print_coding_output(output: dict):
    """Coding tool output ko nicely print karo."""

    status = output.get("status", "unknown")
    icon = "✅" if status == "success" else "❌"

    print(f"{icon} Status   : {status.upper()}")
    print(f"🔤 Language : {output.get('language', 'N/A')}")

    # Generated code
    if output.get("code"):
        print(f"\n📝 Generated Code ({output.get('lines', '?')} lines):")
        print("-" * 40)
        print(output["code"])
        print("-" * 40)

    # Execution output
    if output.get("output"):
        print(f"\n▶️  Output:")
        print("-" * 40)
        print(output["output"])
        print("-" * 40)

    # Debug info
    if output.get("diagnosis"):
        print(f"\n🐛 Diagnosis : {output['diagnosis']}")

    if output.get("explanation"):
        print(f"\n💬 Explanation:\n{output['explanation']}")

    if output.get("fixed_code"):
        print(f"\n🔧 Fixed Code:")
        print("-" * 40)
        print(output["fixed_code"])
        print("-" * 40)

    if output.get("diff_summary"):
        print(f"\n📊 Changes: {output['diff_summary']}")

    # Stats (explain mode)
    if output.get("stats"):
        stats = output["stats"]
        print(f"\n📈 Code Stats:")
        print(f"   Lines     : {stats.get('total_lines')}")
        print(f"   Functions : {stats.get('functions_detected')}")
        print(f"   Imports   : {stats.get('imports_detected')}")

    if output.get("stderr"):
        print(f"\n⚠️  Stderr:\n{output['stderr']}")

    if output.get("execution_time"):
        print(f"\n⏱  Exec Time: {output['execution_time']}")

    if output.get("message"):
        print(f"\n💬 {output['message']}")


# ==================================================
# 🛡️ SAFE INPUT
# ==================================================
def safe_input(prompt):
    try:
        return input(prompt).strip()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Shutting down safely...")
        sys.exit(0)


# ==================================================
# 💻 CODING MODE HANDLER
# ==================================================
def handle_coding_mode(chhoti_don: ManagerAgent):
    """
    Mode 9 — Natural Language Coding Mode.
    User jo bhi bole — auto detect karke sahi tool call karo.
    """
    print("\n💻 CODING MODE — Natural Language")
    print("Examples:")
    print("  → 'python mein calculator banao'")
    print("  → 'ye code debug karo: [code]'")
    print("  → 'is SQL query ko explain karo'")
    print("  → 'javascript mein array sort karo'")
    print("Type 'back' to return to main menu.\n")

    while True:
        task = safe_input("💻 Coding> ")

        if task.lower() in ["exit", "back", "menu"]:
            break

        if not task:
            continue

        # Intent + action detect karo
        action = detect_coding_action(task)
        routing = route_coding_tool(task)

        print(f"\n🔍 Detected: {routing['tool_name']} | Language: {routing['extracted_language']}")

        try:
            result = chhoti_don.coding_task(task)
            pretty_print(result)
        except Exception as e:
            print(f"\n❌ Coding Error: {e}\n")


# ==================================================
# 🧠 SMART AUTO MODE HANDLER
# ==================================================
def handle_smart_mode(chhoti_don: ManagerAgent):
    """
    Mode 10 — Smart Auto Mode.
    Kuch bhi bolo — Chhoti Don automatically decide karegi kya karna hai.
    """
    print("\n🧠 SMART AUTO MODE — Chhoti Don decides everything!")
    print("Type anything naturally. Type 'back' to return.\n")

    while True:
        task = safe_input("🧠 Smart> ")

        if task.lower() in ["exit", "back", "menu"]:
            break

        if not task:
            continue

        # Auto intent detect
        intent = detect_intent(task)
        task_type = detect_task(task)

        print(f"\n🔍 Intent: {intent} | Task Type: {task_type}")

        try:
            # Coding intent → coding mode
            if intent in ["coding", "debug"] or task_type == "coding":
                print("→ Routing to Coding Engine...")
                result = chhoti_don.coding_task(task)

            # Malware/cyber intent → autonomous mode
            elif intent == "malware" or task_type == "malware":
                print("→ Routing to Cyber Engine...")
                result = chhoti_don.autonomous_llm_task(task)

            # Default → brain task
            else:
                print("→ Routing to Brain...")
                result = chhoti_don.brain_task(task)

            pretty_print(result)

        except Exception as e:
            print(f"\n❌ Error: {e}\n")


# ==================================================
# 🚀 MAIN
# ==================================================
if __name__ == "__main__":

    chhoti_don = ManagerAgent()
    print_banner()

    while True:

        mode = safe_input("Select Mode (1/2/3/4/5/6/7/8/9/10): ").lower()

        if mode == "exit":
            print("\nShutting down Chhoti Don...")
            break

        try:

            # 1️⃣ Single Agent Mode
            if mode == "1":
                agent_type = safe_input("Select Agent (coder/security/analyst): ").lower()
                if agent_type == "exit":
                    break

                task = safe_input("Enter Task: ")
                if task == "exit":
                    break

                result = chhoti_don.assign_task(agent_type, task)
                pretty_print(result)

            # 2️⃣ Pipeline Mode
            elif mode == "2":
                task = safe_input("Enter Task for Full Pipeline: ")
                if task == "exit":
                    break

                result = chhoti_don.pipeline_task(task)
                pretty_print(result)

            # 3️⃣ Direct Brain Mode
            elif mode == "3":
                task = safe_input("Ask Brain: ")
                if task == "exit":
                    break

                result = chhoti_don.brain_task(task)
                pretty_print(result)

            # 4️⃣ View Memory
            elif mode == "4":
                memory = chhoti_don.get_memory()
                print("\n🧠 Memory Context:\n")
                print(memory)
                print()

            # 5️⃣ Autonomous Mode
            elif mode == "5":
                task = safe_input("Enter Autonomous Task: ")
                if task == "exit":
                    break

                result = chhoti_don.autonomous_llm_task(task)
                pretty_print(result)

            # 6️⃣ Manual Tool Test
            elif mode == "6":
                print("\n🛠 Manual Tool Execution Mode")

                tool_name = safe_input("Enter Tool Name: ")
                if tool_name == "exit":
                    break

                print("Enter JSON input (example: {\"code\": \"x=5\"})")
                raw_input_data = safe_input("Input: ")
                if raw_input_data == "exit":
                    break

                try:
                    input_data = json.loads(raw_input_data)
                except Exception as e:
                    print(f"Invalid JSON format: {e}")
                    continue

                result = chhoti_don.safe_tool_execute(
                    tool_name,
                    input_data,
                    user_lang="system"
                )
                pretty_print(result)

            # 7️⃣ Code Intelligence Mode
            elif mode == "7":
                print("\n🧠 EvolveX Code Intelligence Mode")

                project_path = safe_input("Enter Project Path ('.' for current): ")
                if project_path == "exit":
                    break

                if project_path == ".":
                    project_path = os.getcwd()

                if not os.path.exists(project_path):
                    print("Invalid path. Try again.\n")
                    continue

                run_code_intelligence(project_path)

            # 8️⃣ Full Auto Self-Heal Mode
            elif mode == "8":
                print("\n🛠 FULL AUTO SELF-HEAL MODE")

                project_path = safe_input("Enter Project Path ('.' for current): ")
                if project_path == "exit":
                    break

                if project_path == ".":
                    project_path = os.getcwd()

                if not os.path.exists(project_path):
                    print("Invalid path. Try again.\n")
                    continue

                chhoti_don.full_self_heal(project_path)

            # 9️⃣ Coding Mode — NEW
            elif mode == "9":
                handle_coding_mode(chhoti_don)

            # 🔟 Smart Auto Mode — NEW
            elif mode == "10":
                handle_smart_mode(chhoti_don)

            else:
                print("Invalid mode. Try again.\n")

        except Exception as e:
            print(f"\nError: {e}\n")
