"""Every tool the orchestrator hands to the model must declare a strict object schema.

The model fills tool arguments from the JSON Schema the registry advertises
(`Tool.spec()` → provider). A schema that is not `{"type":"object", ...}` or that omits
`additionalProperties: false` either fails validation in strict providers or silently
accepts keys the handler never reads — both are drift the handler cannot see. This gate
pins the invariant across the whole live registry.
"""

from app.agents.tools import ALL_TOOLS


def test_every_tool_schema_is_a_strict_object() -> None:
    assert ALL_TOOLS, "ALL_TOOLS is empty — the registry cannot be empty and green"
    bad = []
    for tool in ALL_TOOLS:
        schema = tool.parameters or {}
        if schema.get("type") != "object":
            bad.append((tool.name, "type", schema.get("type")))
        if schema.get("additionalProperties") is not False:
            bad.append((tool.name, "additionalProperties", schema.get("additionalProperties")))
    assert not bad, f"non-strict tool schemas: {bad}"
