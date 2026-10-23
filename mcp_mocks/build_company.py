"""Write fixtures/mcp/*/data.json from fixtures.story (no LLM, deterministic)."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fixtures.story import all_fixtures  # noqa: E402


def main():
    for name, data in all_fixtures().items():
        path = ROOT / "fixtures" / "mcp" / name / "data.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
