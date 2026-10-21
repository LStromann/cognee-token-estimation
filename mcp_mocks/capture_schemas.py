"""Capture real tool schemas so mocks advertise identical tools.

  python -m mcp_mocks.capture_schemas linear --url https://mcp.linear.app/mcp --token $TOKEN
  python -m mcp_mocks.capture_schemas github --cmd "docker run -i ghcr.io/github/github-mcp-server"

Writes mcp_mocks/schemas/<name>.json. Then check that every captured tool has a handler:
  python -m mcp_mocks.capture_schemas --check
"""
import argparse, asyncio, importlib, json, pathlib, shlex

from mcp import ClientSession

OUT = pathlib.Path(__file__).parent / "schemas"
SERVERS = ["linear", "granola", "notion", "slack", "github"]


async def capture(url=None, cmd=None, token=None):
    if url:
        from mcp.client.streamable_http import streamablehttp_client
        headers = {"Authorization": f"Bearer {token}"} if token else None
        async with streamablehttp_client(url, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                return (await s.list_tools()).tools
    from mcp.client.stdio import stdio_client, StdioServerParameters
    parts = shlex.split(cmd)
    async with stdio_client(StdioServerParameters(command=parts[0], args=parts[1:])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return (await s.list_tools()).tools


def check():
    for name in SERVERS:
        f = OUT / f"{name}.json"
        if not f.exists():
            print(f"{name}: no captured schema (using defaults)")
            continue
        mod = importlib.import_module(f"mcp_mocks.{name}_server")
        missing = [t["name"] for t in json.loads(f.read_text()) if t["name"] not in mod.S.handlers]
        print(f"{name}: {len(missing)} tools without handler {missing}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?")
    ap.add_argument("--url"); ap.add_argument("--cmd"); ap.add_argument("--token")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        check()
    else:
        tools = asyncio.run(capture(a.url, a.cmd, a.token))
        OUT.mkdir(exist_ok=True)
        data = [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in tools]
        (OUT / f"{a.name}.json").write_text(json.dumps(data, indent=1))
        print(f"saved {len(data)} tools -> {OUT / (a.name + '.json')}")
