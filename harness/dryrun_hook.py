"""Stand-in Cognee hook used by --dry-run.

Prints the same additionalContext shape the real plugin uses, so tee_hook.py and
the attribution pass run unchanged. The text is synthetic.
"""
import json
import sys

TEXT = "Cognee memory (dry-run injection): Brightwave retry cap is 4 with jitter."


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else "UserPromptSubmit"
    # Store-style events inject nothing. The dry-run only registers injecting events,
    # but accept the argument so the command shape matches the real hooks.
    if event in {"PostToolUse", "Stop", "SessionEnd"}:
        return
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"additionalContext": TEXT}}))


if __name__ == "__main__":
    main()
