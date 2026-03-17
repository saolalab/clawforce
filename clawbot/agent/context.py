"""Context builder for assembling agent prompts.

Optimized for LLM KV-cache: static content comes first (bootstrap files,
identity, skills), dynamic content last (memory, session, timestamp).
"""

import base64
import mimetypes
import os
import platform
import time as _time
from datetime import datetime
from pathlib import Path
from typing import Any

from clawbot.agent.memory import MemoryStore
from clawbot.agent.skills import SkillsLoader

# How long cached skills content stays valid (seconds).
_SKILLS_TTL = 60.0


def _root_env_note() -> str:
    """When running as root (e.g. Power mode), tell the agent it can use apt-get without sudo."""
    if os.geteuid() == 0:
        return "\n\nYou run as root. You can install packages with apt-get without sudo. Run `apt-get update` before `apt-get install` when installing packages."
    return ""


class ContextBuilder:
    """
    Builds the context (system prompt + messages) for the agent.

    Assembles bootstrap files, memory, skills, and conversation history
    into a coherent prompt for the LLM.

    Section ordering is optimized for KV-cache prefix stability:
    static content first, dynamic content last.
    """

    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md"]

    def __init__(
        self,
        workspace: Path,
        profile_path: Path | None = None,
        disabled_skills: list[str] | None = None,
    ):
        self.workspace = workspace
        self.profile_path = profile_path
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace, disabled_skills=disabled_skills)

        # --- Precomputed static values (never change at runtime) ---
        self._workspace_path = str(workspace.expanduser().resolve())
        system = platform.system()
        self._runtime_info = (
            f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, "
            f"Python {platform.python_version()}"
        )
        self._root_note = _root_env_note()

        skills_note = "- Skills: .agents/skills/<skill-name>/SKILL.md\n"
        cron_note = (
            "Scheduled jobs are managed by the cron tool."
            if self.profile_path
            else "- Scheduled jobs: cron/jobs.json"
        )

        # Static identity text — everything that doesn't change between calls
        self._static_identity = f"""# clawbot

You are clawbot, a helpful AI assistant. You have access to tools that allow you to:
- Read, write, and edit files
- Execute shell commands
- Search the web and fetch web pages
- Send messages to users on chat channels
- Spawn subagents for complex background tasks
- Schedule reminders and recurring tasks (cron tool)
- Use Model Context Protocol (MCP) servers for extended capabilities

## Working directory
Root: {self._workspace_path}
- Memory: .agents/memory/MEMORY.md, .agents/memory/HISTORY.md (grep-searchable)
{skills_note}
{cron_note}

File and exec tools operate in this directory. Paths are relative. profiles/ is read-only.

IMPORTANT: When responding to direct questions or conversations, reply directly with your text response.
Only use the 'message' tool when you need to send a message to a specific chat channel (like WhatsApp).
For normal conversation, just respond with text - do not call the message tool.

If MCP (Model Context Protocol) servers are configured and connected, they will be listed separately below
under "## MCP Tools" with their available functions. You can use these tools just like built-in tools.

## How to Think

Before taking action on non-trivial requests, briefly plan your approach:
1. **Assess** — What is the user asking for? Is this a direct question, a multi-step task, or a creative request?
2. **Plan** — For multi-step tasks, outline 2-4 key steps before calling any tools. State your plan in 1-2 sentences.
3. **Act** — Execute your plan using tools. If a tool returns an error or unexpected result, pause and re-evaluate before retrying blindly.
4. **Verify** — After completing a task, briefly confirm the result makes sense before responding.

For simple questions or greetings, skip planning and respond directly.

Always be helpful, accurate, and concise.
When remembering something important, write to {self._workspace_path}/.agents/memory/MEMORY.md
To recall past events, grep {self._workspace_path}/.agents/memory/HISTORY.md"""

        # --- Caches ---
        self._bootstrap_cache: str | None = None
        self._skills_cache: tuple[float, str, str] | None = (
            None  # (monotonic_ts, summary, always_content)
        )

    # ------------------------------------------------------------------
    # System prompt (static prefix only — no memory, no timestamp)
    # ------------------------------------------------------------------

    def build_system_prompt(self) -> str:
        """Build the static prefix of the system prompt.

        Contains bootstrap files, identity, and skills — all static or
        semi-static content that maximizes KV-cache prefix hits.
        Dynamic sections (memory, timestamp, session) are appended
        separately in build_messages().
        """
        parts = []

        # 1. Bootstrap files (fully static — cached after first read)
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)

        # 2. Static identity (capabilities, workspace layout, how-to-think)
        parts.append(self._static_identity)

        # 3-4. Skills (semi-static — TTL-cached)
        skills_summary, always_content = self._get_cached_skills()
        if always_content:
            parts.append(f"# Active Skills\n\n{always_content}")
        if skills_summary:
            parts.append(f"""# Skills

The following skills extend your capabilities. To use a skill, read its SKILL.md file using the read_file tool.
Skills with available="false" may need extra setup; see each SKILL.md for details.

{skills_summary}""")

        return "\n\n---\n\n".join(parts)

    # ------------------------------------------------------------------
    # Dynamic context (changes per call)
    # ------------------------------------------------------------------

    def _get_dynamic_context(
        self,
        channel: str | None = None,
        chat_id: str | None = None,
        tool_approval_config: Any | None = None,
        mcp_tools_summary: str | None = None,
        software_exec_hint: str | None = None,
    ) -> str:
        """Build the dynamic suffix that changes between turns."""
        parts = []

        # Semi-static sections (change with config, not per-turn)
        if tool_approval_config:
            approval_context = self._build_tool_approval_context(tool_approval_config)
            if approval_context:
                parts.append(approval_context)

        if mcp_tools_summary:
            parts.append(
                f"## MCP Tools\n\nYou have access to the following MCP "
                f"(Model Context Protocol) tools:\n\n{mcp_tools_summary}"
            )

        if software_exec_hint:
            parts.append(f"## Running installed software\n\n{software_exec_hint}")

        # Process-static runtime info
        runtime_section = f"## Runtime\n{self._runtime_info}"
        if self._root_note:
            runtime_section += self._root_note
        parts.append(runtime_section)

        # Dynamic per-turn: memory
        memory = self.memory.get_memory_context(max_chars=8000)
        if memory:
            parts.append(f"# Memory\n\n{memory}")

        # Most dynamic: session + timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = _time.strftime("%Z") or "UTC"
        parts.append(f"## Current Time\n{now} ({tz})")

        if channel and chat_id:
            parts.append(f"## Current Session\nChannel: {channel}\nChat ID: {chat_id}")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Caching helpers
    # ------------------------------------------------------------------

    def _load_bootstrap_files(self) -> str:
        """Load all bootstrap files from profile_path if set, else workspace.

        Results are cached after the first read (files are read-only at runtime).
        """
        if self._bootstrap_cache is not None:
            return self._bootstrap_cache

        parts = []
        root = self.profile_path if self.profile_path is not None else self.workspace
        for filename in self.BOOTSTRAP_FILES:
            file_path = root / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        self._bootstrap_cache = "\n\n".join(parts) if parts else ""
        return self._bootstrap_cache

    def _get_cached_skills(self) -> tuple[str, str]:
        """Return (skills_summary, always_skills_content) with a TTL cache."""
        now = _time.monotonic()
        if self._skills_cache is not None:
            cached_time, summary, always_content = self._skills_cache
            if now - cached_time < _SKILLS_TTL:
                return summary, always_content

        # Recompute
        always_skills = self.skills.get_always_skills()
        always_content = ""
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills) or ""

        summary = self.skills.build_skills_summary() or ""
        self._skills_cache = (now, summary, always_content)
        return summary, always_content

    # ------------------------------------------------------------------
    # Tool approval context
    # ------------------------------------------------------------------

    def _build_tool_approval_context(self, config: Any) -> str:
        """Build tool approval context section for the system prompt.

        Explains the approval workflow so the agent understands when tools require
        user confirmation and how to interpret approval responses.
        """
        default_mode = getattr(config, "default_mode", "always_run")
        per_tool = getattr(config, "per_tool", {}) or {}
        timeout = getattr(config, "timeout_seconds", 120)

        # Count tools that require approval
        ask_tools = [name for name, mode in per_tool.items() if mode == "ask_before_run"]
        always_tools = [name for name, mode in per_tool.items() if mode == "always_run"]

        lines = ["## Tool Permissions"]

        if default_mode == "always_run":
            lines.append(
                "\nBy default, you can execute tools immediately without asking for user approval."
            )
            if ask_tools:
                lines.append(
                    f"\n**Exception - these tools require user approval:** {', '.join(ask_tools)}"
                )
        else:
            lines.append(
                "\nBy default, all tools require user approval before execution. "
                "When you call a tool, the user will see an approval prompt and must reply 'yes' or 'no'."
            )
            if always_tools:
                lines.append(
                    f"\n**Exception - these tools run immediately:** {', '.join(always_tools)}"
                )

        lines.append(
            f"\n**Approval timeout:** {timeout} seconds. If the user doesn't respond in time, "
            "the tool execution is cancelled."
        )

        lines.append(
            "\n**Important:** If a tool returns 'denied by user or timed out', this means the user "
            "chose not to approve the action OR didn't respond in time. This is NOT a system error "
            "or permission issue - you still have the capability to use the tool. You can ask the "
            "user if they want to proceed and try again if they agree."
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Message assembly
    # ------------------------------------------------------------------

    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
        tool_approval_config: Any | None = None,
        mcp_tools_summary: str | None = None,
        software_exec_hint: str | None = None,
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build the complete message list for an LLM call.

        Args:
            history: Previous conversation messages.
            current_message: The new user message.
            media: Optional list of local file paths for images/media.
            channel: Current channel (telegram, feishu, etc.).
            chat_id: Current chat/user ID.
            tool_approval_config: Optional ToolApprovalConfig for permission context.
            mcp_tools_summary: Optional summary of MCP tools for the system prompt.
            software_exec_hint: Optional hint for running installed software (software_exec); injected when tool is present.
            model: Optional model identifier (used to enable provider-specific cache optimizations).

        Returns:
            List of messages including system prompt.
        """
        messages = []

        # Static prefix (bootstrap + identity + skills) — KV-cache friendly
        static_prefix = self.build_system_prompt()

        # Dynamic suffix (memory + timestamp + session) — changes per turn
        dynamic_suffix = self._get_dynamic_context(
            channel=channel,
            chat_id=chat_id,
            tool_approval_config=tool_approval_config,
            mcp_tools_summary=mcp_tools_summary,
            software_exec_hint=software_exec_hint,
        )

        # For Anthropic models, use cache_control breakpoints to guarantee
        # the static prefix is cached server-side across turns.
        if model and _is_anthropic_model(model):
            system_content = [
                {
                    "type": "text",
                    "text": static_prefix,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": dynamic_suffix,
                },
            ]
            messages.append({"role": "system", "content": system_content})
        else:
            system_prompt = f"{static_prefix}\n\n---\n\n{dynamic_suffix}"
            messages.append({"role": "system", "content": system_prompt})

        # History
        messages.extend(history)

        # Current message (with optional image attachments)
        user_content = self._build_user_content(current_message, media)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """Build user message content with optional base64-encoded images.

        Media paths are validated to be within the workspace directory.
        """
        if not media:
            return text

        ws_root = self.workspace.resolve()
        images = []
        for path in media:
            p = Path(path).expanduser().resolve()
            if not p.is_relative_to(ws_root):
                continue
            mime, _ = mimetypes.guess_type(path)
            if not p.is_file() or not mime or not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(p.read_bytes()).decode()
            images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

        if not images:
            return text
        return images + [{"type": "text", "text": text}]

    def add_tool_result(
        self, messages: list[dict[str, Any]], tool_call_id: str, tool_name: str, result: str
    ) -> list[dict[str, Any]]:
        """
        Add a tool result to the message list.

        Args:
            messages: Current message list.
            tool_call_id: ID of the tool call.
            tool_name: Name of the tool.
            result: Tool execution result.

        Returns:
            Updated message list.
        """
        messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "name": tool_name, "content": result}
        )
        return messages

    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning_content: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Add an assistant message to the message list.

        Args:
            messages: Current message list.
            content: Message content.
            tool_calls: Optional tool calls.
            reasoning_content: Thinking output (Kimi, DeepSeek-R1, etc.).

        Returns:
            Updated message list.
        """
        msg: dict[str, Any] = {"role": "assistant"}

        # Omit empty content — some backends reject empty text blocks
        if content:
            msg["content"] = content

        if tool_calls:
            msg["tool_calls"] = tool_calls

        # Include reasoning content when provided (required by some thinking models)
        if reasoning_content:
            msg["reasoning_content"] = reasoning_content

        messages.append(msg)
        return messages


def _is_anthropic_model(model: str) -> bool:
    """Check if a model string refers to an Anthropic model."""
    model_lower = model.lower()
    return "claude" in model_lower or "anthropic" in model_lower
