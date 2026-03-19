"""Tool schema compatibility transforms for LLM providers.

Each provider has different JSON Schema constraints for function_declarations.
Rather than baking provider-specific fixes into tool definitions, we apply
transforms here at call time, driven by the provider registry's tool_schema_mode.

Modes
-----
""        (default) — pass schemas through unchanged.
"strict"  — Gemini-compatible: resolve anyOf/oneOf/allOf combiners, ensure
            every array has a typed items schema, strip unsupported keywords.
"""

from typing import Any

# Keywords not supported by strict-mode providers (Gemini).
_UNSUPPORTED_KEYS = frozenset({"anyOf", "oneOf", "allOf", "not", "$schema", "$id", "$ref"})


def _sanitize_strict(schema: Any) -> Any:
    """Recursively rewrite a JSON Schema to satisfy strict-mode providers.

    Rules applied:
    - anyOf / oneOf  → pick the first non-null concrete type; fall back to string.
    - allOf          → merge all sub-schemas into one flat object.
    - array missing items → default items to {"type": "string"}.
    - Strip unsupported top-level keys ($schema, $ref, not, …).
    - Recurse into properties and additionalProperties.
    """
    if not isinstance(schema, dict):
        return schema

    # Resolve anyOf / oneOf first (they may contain allOf themselves)
    for combiner in ("anyOf", "oneOf"):
        if combiner in schema:
            options = [
                o for o in schema[combiner] if isinstance(o, dict) and o.get("type") != "null"
            ]
            chosen = options[0] if options else {"type": "string"}
            merged = {k: v for k, v in schema.items() if k not in _UNSUPPORTED_KEYS}
            merged.update(chosen)
            return _sanitize_strict(merged)

    # Resolve allOf → merge all sub-schemas
    if "allOf" in schema:
        merged: dict[str, Any] = {k: v for k, v in schema.items() if k not in _UNSUPPORTED_KEYS}
        for sub in schema["allOf"]:
            if isinstance(sub, dict):
                merged.update(sub)
        return _sanitize_strict(merged)

    # Strip unsupported keys
    result = {k: v for k, v in schema.items() if k not in _UNSUPPORTED_KEYS}

    # Ensure array items always carry an explicit type
    if result.get("type") == "array":
        items = result.get("items")
        if not items:
            result["items"] = {"type": "string"}
        elif isinstance(items, dict) and not any(
            k in items for k in ("type", "anyOf", "oneOf", "allOf")
        ):
            result["items"] = {"type": "string", **items}
        else:
            result["items"] = _sanitize_strict(items)

    # Recurse into properties
    if isinstance(result.get("properties"), dict):
        result["properties"] = {k: _sanitize_strict(v) for k, v in result["properties"].items()}

    # Recurse into additionalProperties if it's a schema dict
    if isinstance(result.get("additionalProperties"), dict):
        result["additionalProperties"] = _sanitize_strict(result["additionalProperties"])

    return result


def sanitize_tools(
    tools: list[dict[str, Any]],
    tool_schema_mode: str,
) -> list[dict[str, Any]]:
    """Apply the appropriate schema transform to a list of OpenAI-format tool defs.

    Args:
        tools: List of {"type": "function", "function": {...}} dicts.
        tool_schema_mode: Value from ProviderSpec.tool_schema_mode.
            "" → no-op.  "strict" → Gemini-compatible rewrite.

    Returns:
        Transformed list (original objects are not mutated).
    """
    if tool_schema_mode != "strict":
        return tools

    result = []
    for tool in tools:
        fn = tool.get("function", {})
        params = fn.get("parameters")
        if params is None:
            result.append(tool)
            continue
        sanitized = _sanitize_strict(params)
        result.append(
            {
                **tool,
                "function": {**fn, "parameters": sanitized},
            }
        )
    return result
