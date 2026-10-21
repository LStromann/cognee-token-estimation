"""Expand fixtures from fixtures/company_story.md with Claude (model adjustable).

  python -m mcp_mocks.generate_fixtures --model claude-opus-5-5 --server linear --target 80

Takes the existing data.json as seed and asks the model to add storylines, noise and distractors
while keeping IDs and people consistent. ALWAYS review the diff before committing.
"""
import argparse, json, pathlib
import anthropic, yaml

ROOT = pathlib.Path(__file__).parent.parent
PROMPT = """You maintain fixture data for a mock {server} MCP server.
Company story:
{story}

Current data.json:
{data}

Return ONLY the full updated JSON (same structure). Add items until the main collection has about {target} entries:
keep all existing items unchanged, add new consistent storylines plus realistic filler noise and near-miss distractors.
Keep people, IDs and dates consistent with the story and with other tools."""


def main():
    cfg = yaml.safe_load((ROOT / "config/experiment.yaml").read_text())
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--target", type=int, default=60)
    ap.add_argument("--model", default=cfg["warmup_model"])
    a = ap.parse_args()
    path = ROOT / "fixtures/mcp" / a.server / "data.json"
    msg = anthropic.Anthropic().messages.create(
        model=a.model, max_tokens=16000,
        messages=[{"role": "user", "content": PROMPT.format(
            server=a.server, story=(ROOT / "fixtures/company_story.md").read_text(),
            data=path.read_text(), target=a.target)}])
    text = "".join(b.text for b in msg.content if b.type == "text").strip().strip("`").removeprefix("json")
    data = json.loads(text)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print("updated", path)


if __name__ == "__main__":
    main()
