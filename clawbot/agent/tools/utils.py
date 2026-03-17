"""Static helpers for tool display and output formatting."""

import re
from typing import Any


def strip_think(text: str | None) -> str | None:
    """Remove <think>…</think> blocks that some models embed in content."""
    if not text:
        return None
    return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None


def truncate_output(text: str, max_chars: int) -> str:
    """Truncate large tool output, preserving head and tail for context."""
    if not text or max_chars <= 0 or len(text) <= max_chars:
        return text
    head_chars = int(max_chars * 0.7)
    tail_chars = max_chars - head_chars - 80
    if tail_chars < 0:
        tail_chars = 0
    omitted = len(text) - head_chars - tail_chars
    marker = f"\n\n... [{omitted:,} characters truncated] ..."
    if tail_chars:
        return text[:head_chars] + marker + "\n\n" + text[-tail_chars:]
    return text[:head_chars] + marker


def redact_tool_args(args: dict[str, Any]) -> dict[str, Any]:
    """Redact argument values for audit (keep keys, mask values)."""
    return {k: "<redacted>" for k in args}


_TOOL_VERBS: dict[str, str] = {
    "read_file": "Reading",
    "write_file": "Writing",
    "edit_file": "Editing",
    "list_dir": "Listing",
    "workspace_tree": "Workspace tree",
    "exec": "Running",
    "web_search": "Searching",
    "web_fetch": "Fetching",
    "message": "Sending message",
    "spawn": "Spawning subagent",
    "cron": "Scheduling",
    "list_plans": "Listing plans",
    "plan_query": "Querying plans",
    "get_plan": "Getting plan",
    "create_plan": "Creating plan",
    "activate_plan": "Activating plan",
    "create_plan_task": "Creating task",
    "update_plan_task": "Updating task",
    "move_plan_task": "Moving task",
    "get_plan_artifact": "Getting artifact",
    "save_plan_artifact": "Saving artifact",
    "a2a_call": "🤖 Agent Call",
    "a2a_discover": "🔍 Agent Discover",
}

# Maps tool name → the argument key that best represents what the tool is acting on.
# Used to produce meaningful progress hints like "Searching: `bitcoin ETF`".
_TOOL_ARG_KEYS: dict[str, str] = {
    "web_search": "query",
    "web_fetch": "url",
    "read_file": "path",
    "write_file": "path",
    "edit_file": "path",
    "list_dir": "path",
    "workspace_tree": "root",
    "exec": "command",
    "spawn": "message",
    "cron": "expression",
    "plan_query": "query",
    "get_plan": "plan_id",
    "create_plan": "title",
    "create_plan_task": "title",
    "update_plan_task": "title",
}


def _extract_hint_value(tc: Any) -> str | None:
    """Return the most meaningful string value from a tool call's arguments."""
    if not tc.arguments:
        return None
    preferred_key = _TOOL_ARG_KEYS.get(tc.name)
    if preferred_key:
        val = tc.arguments.get(preferred_key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    # Fall back to the first non-empty string argument value.
    for val in tc.arguments.values():
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def tool_hint(tool_calls: list) -> str:
    """Format tool calls as user-friendly progress hint."""

    def _fmt(tc: Any) -> str:
        if tc.name == "a2a_call" and tc.arguments:
            msg = tc.arguments.get("message", "")
            target_id = tc.arguments.get("target_agent_id", "")
            short_msg = msg[:50].rstrip() + "…" if len(msg) > 50 else msg
            parts = [f"🤖 Agent Call: `{short_msg}`"] if short_msg else ["🤖 Agent Call"]
            if target_id:
                parts.append(f"Call ID: {target_id}")
            return " | ".join(parts)

        verb = _TOOL_VERBS.get(tc.name)
        if not verb and tc.name.startswith("mcp_"):
            parts = tc.name.split("_", 2)
            verb = f"Calling {parts[1]}" if len(parts) > 2 else tc.name
        if not verb:
            verb = tc.name.replace("_", " ").title()

        val = _extract_hint_value(tc)
        if val:
            short = val[:50].rstrip() + "…" if len(val) > 50 else val
            return f"{verb}: {short}"
        return verb

    hints = [_fmt(tc) for tc in tool_calls]
    if len(hints) == 1:
        return hints[0]
    return " | ".join(hints)
