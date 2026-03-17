"""Shell command security policy — blocks injection and enforces allow/deny lists."""

import shlex
from dataclasses import dataclass, field
from typing import Iterable

_DISALLOWED_SUBSTRINGS = ("$(", "`", "\n", "\r")
_DISALLOWED_OPERATOR_TOKENS = {"|", "||", "&&", ";", "<", ">", "<<", ">>", "&"}


def _normalize_list(values: Iterable[str] | None) -> list[str]:
    if not values:
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def _tokenize_command(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def _contains_disallowed_shell_syntax(command: str) -> bool:
    if any(marker in command for marker in _DISALLOWED_SUBSTRINGS):
        return True
    try:
        tokens = _tokenize_command(command)
    except Exception:
        return True
    return any(token in _DISALLOWED_OPERATOR_TOKENS for token in tokens)


@dataclass
class ShellCommandPolicy:
    """
    Lightweight command policy for the shell exec tool.

    Modes:
      - allow_all: allow everything (default)
      - deny_all: block everything
      - allowlist: allow only listed command prefixes (first token)

    relaxed: when True, skip shell injection checks (allow pipes, redirects, etc.)
    """

    mode: str = "allow_all"
    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)
    relaxed: bool = False

    @classmethod
    def from_dict(cls, data: dict | None) -> "ShellCommandPolicy":
        if not isinstance(data, dict):
            return cls()
        mode = str(data.get("mode", "allow_all")).strip().lower()
        allow = _normalize_list(data.get("allow"))
        deny = _normalize_list(data.get("deny"))
        relaxed = bool(data.get("relaxed", False))
        return cls(mode=mode, allow=allow, deny=deny, relaxed=relaxed)

    def check(self, command: str | None) -> tuple[bool, str]:
        if not command or not isinstance(command, str):
            return False, "shell command required"

        cmd = command.strip()
        if not cmd:
            return False, "shell command required"

        if not self.relaxed and _contains_disallowed_shell_syntax(cmd):
            return False, "shell command contains blocked operators"

        try:
            tokens = shlex.split(cmd)
            head = tokens[0] if tokens else cmd
        except Exception:
            return False, "invalid shell command syntax"

        if self.mode == "deny_all":
            return False, "shell execution blocked by policy"

        if self.deny:
            for blocked in self.deny:
                if head == blocked:
                    return False, f"shell command blocked by policy: {blocked}"

        if self.mode == "allowlist":
            for allowed in self.allow:
                if head == allowed:
                    return True, ""
            return False, "shell command not in allowlist"

        return True, ""
