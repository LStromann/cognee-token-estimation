"""Generic mock MCP server.

- Tools are advertised from mcp_mocks/schemas/<name>.json if it exists (captured from the
  real server, so names, descriptions and schemas match exactly); otherwise from defaults.
- State: $MOCK_STATE_DIR/<name>/data.json (restored by the harness before every run).
- Every call is appended to $MOCK_LOG (jsonl) with the response size.
"""
import asyncio, json, os, pathlib, time

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

SCHEMA_DIR = pathlib.Path(__file__).parent / "schemas"
FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "mcp"


def obj(required=(), **props):
    """Tiny JSON-schema helper: obj(["id"], id="string", limit="integer")."""
    p = {k: (v if isinstance(v, dict) else {"type": v}) for k, v in props.items()}
    return {"type": "object", "properties": p, "required": list(required)}


def search(items, query, fields):
    if not query:
        return list(items)
    terms = [t for t in str(query).lower().split() if t]
    scored = []
    for it in items:
        hay = " ".join(json.dumps(it.get(f, ""), ensure_ascii=False) for f in fields).lower()
        s = sum(hay.count(t) for t in terms)
        if s:
            scored.append((s, it))
    return [it for _, it in sorted(scored, key=lambda x: -x[0])]


def match(item, where):
    """where: {"field": value} equality (case-insensitive) or {"field_contains": value}."""
    for k, v in where.items():
        if k.endswith("_contains"):
            if str(v).lower() not in json.dumps(item.get(k[:-9], ""), ensure_ascii=False).lower():
                return False
        elif str(item.get(k, "")).lower() != str(v).lower():
            return False
    return True


class MockServer:
    def __init__(self, name, default_tools):
        self.name = name
        self.default_tools = default_tools
        self.handlers = {}
        self.state_dir = pathlib.Path(os.environ.get("MOCK_STATE_DIR", FIXTURE_DIR)) / name
        self.log_path = os.environ.get("MOCK_LOG")

    # -- state --
    def load(self):
        return json.loads((self.state_dir / "data.json").read_text())

    def save(self, data):
        (self.state_dir / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))

    # -- tools --
    def tool(self, name):
        def deco(fn):
            self.handlers[name] = fn
            return fn
        return deco

    def tool_specs(self):
        f = SCHEMA_DIR / f"{self.name}.json"
        return json.loads(f.read_text()) if f.exists() else self.default_tools

    def _log(self, tool, args, text):
        if not self.log_path:
            return
        with open(self.log_path, "a") as fh:
            fh.write(json.dumps({"ts": time.time(), "server": self.name, "tool": tool,
                                 "args": args, "response_chars": len(text)}) + "\n")

    def call(self, name, args):
        fn = self.handlers.get(name)
        if fn is None:
            return {"error": f"Tool '{name}' is not implemented in the {self.name} mock."}
        try:
            return fn(args or {})
        except Exception as e:  # surface errors to the agent like a real server would
            return {"error": f"{type(e).__name__}: {e}"}

    def _tools(self):
        return [types.Tool(name=t["name"], description=t.get("description", ""),
                           inputSchema=t.get("inputSchema") or {"type": "object"})
                for t in self.tool_specs()]

    def _respond(self, name, arguments):
        text = json.dumps(self.call(name, arguments), indent=1, ensure_ascii=False)
        self._log(name, arguments, text)
        return [types.TextContent(type="text", text=text)]

    def run(self):
        """Works with MCP Python SDK v1 (decorators) and v2 (constructor handlers)."""
        import inspect
        if "on_list_tools" in inspect.signature(Server.__init__).parameters:  # SDK v2
            async def on_list_tools(ctx, params):
                return types.ListToolsResult(tools=self._tools())

            async def on_call_tool(ctx, params):
                return types.CallToolResult(content=self._respond(params.name, params.arguments))

            server = Server(self.name, on_list_tools=on_list_tools, on_call_tool=on_call_tool)
        else:  # SDK v1
            server = Server(self.name)

            @server.list_tools()
            async def _list():
                return self._tools()

            @server.call_tool()
            async def _call(name, arguments):
                return self._respond(name, arguments)

        async def main():
            async with stdio_server() as (r, w):
                await server.run(r, w, server.create_initialization_options())

        asyncio.run(main())
