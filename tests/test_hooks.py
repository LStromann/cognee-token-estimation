"""Hook attribution helpers."""
from harness.hooks.tee_hook import injected_texts
from harness.tokens import _cognee_named, cognee_prefixes


def test_injected_texts_reads_additional_context():
    raw = '{"hookSpecificOutput": {"additionalContext": "cap is 4"}}'
    assert injected_texts(raw, "", 0, "UserPromptSubmit") == ["cap is 4"]
    assert injected_texts("", "blocked", 2, "PreToolUse") == ["blocked"]
    assert injected_texts("noise", "", 1, "UserPromptSubmit") == []


def test_both_cognee_tool_prefixes_match():
    prefixes = cognee_prefixes({
        "cognee_tool_prefix": "mcp__cognee__",
        "cognee_tool_prefixes": ["mcp__cognee__", "mcp__cognee-memory__"],
    })
    assert _cognee_named("mcp__cognee__search", prefixes)
    assert _cognee_named("mcp__cognee-memory__search", prefixes)
    assert not _cognee_named("mcp__linear__list_issues", prefixes)
