"""
Chhoti Don - Hands Layer (Tool Execution Layer)

A modular, additive layer that lets the Brain act on the world through a single
centralized Tool Manager. The Brain never touches OS / browser / process APIs
directly — it goes through the Tool Manager, which routes to the correct Hand:

    from hands import get_tool_manager
    tm = get_tool_manager()
    tm.execute("filesystem", "read_file", {"path": "notes.txt"})
    tm.health_check()

Nothing here modifies the existing Brain, agents, memory, voice, security, UI
or tools; it is a self-contained package that can be imported when needed.
"""

from .base import BaseHand, Permission, tool_result
from .tool_manager import ToolManager, build_tool_manager, get_tool_manager
from .intent_router import IntentRouter, get_intent_router, route_intent

__all__ = [
    "BaseHand",
    "Permission",
    "tool_result",
    "ToolManager",
    "build_tool_manager",
    "get_tool_manager",
    "IntentRouter",
    "get_intent_router",
    "route_intent",
]
