from mcp_mocks.common import MockServer, obj, search

TOOLS = [
    {"name": "notion-search", "description": "Search Notion pages by text.", "inputSchema": obj(["query"], query="string")},
    {"name": "notion-fetch", "description": "Fetch a Notion page by ID or title.", "inputSchema": obj(["id"], id="string")},
    {"name": "notion-create-pages", "description": "Create one or more pages.",
     "inputSchema": obj(["pages"], pages={"type": "array", "items": obj(["title"], title="string", content="string", parent="string")})},
    {"name": "notion-update-page", "description": "Update a page's title or content (replace or append).",
     "inputSchema": obj(["page_id"], page_id="string", title="string", content="string", append="string")},
]
S = MockServer("notion", TOOLS)


def _find(pages, key):
    k = key.lower()
    return next((p for p in pages if k in (p["id"].lower(), p["title"].lower())), None)


@S.tool("notion-search")
def notion_search(a):
    hits = search(S.load()["pages"], a["query"], ["title", "content"])
    return {"results": [{"id": p["id"], "title": p["title"], "last_edited": p["last_edited"],
                         "snippet": p["content"][:160]} for p in hits[:10]]}


@S.tool("notion-fetch")
def notion_fetch(a):
    return _find(S.load()["pages"], a["id"]) or {"error": "Page not found"}


@S.tool("notion-create-pages")
def create_pages(a):
    d = S.load()
    out = []
    for i, p in enumerate(a["pages"]):
        page = {"id": f"NP-{len(d['pages']) + 1}", "content": "", "owner": "me",
                "last_edited": "run", **p, "created_in_run": True}
        d["pages"].append(page)
        out.append(page["id"])
    S.save(d)
    return {"created": out}


@S.tool("notion-update-page")
def update_page(a):
    d = S.load()
    p = _find(d["pages"], a["page_id"])
    if not p:
        return {"error": "Page not found"}
    if a.get("title"):
        p["title"] = a["title"]
    if a.get("content") is not None:
        p["content"] = a["content"]
    if a.get("append"):
        p["content"] += "\n" + a["append"]
    p["updated_in_run"] = True
    S.save(d)
    return p


if __name__ == "__main__":
    S.run()
