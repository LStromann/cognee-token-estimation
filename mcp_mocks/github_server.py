from mcp_mocks.common import MockServer, obj, search

TOOLS = [
    {"name": "list_issues", "description": "List issues in the repository.", "inputSchema": obj(state="string")},
    {"name": "get_issue", "description": "Get an issue with comments.", "inputSchema": obj(["issue_number"], issue_number="integer")},
    {"name": "search_issues", "description": "Search issues and pull requests.", "inputSchema": obj(["query"], query="string")},
    {"name": "list_pull_requests", "description": "List pull requests.", "inputSchema": obj(state="string")},
    {"name": "get_pull_request", "description": "Get a pull request incl. changed files.", "inputSchema": obj(["pullNumber"], pullNumber="integer")},
    {"name": "add_issue_comment", "description": "Comment on an issue or PR.",
     "inputSchema": obj(["issue_number", "body"], issue_number="integer", body="string")},
]
S = MockServer("github", TOOLS)


@S.tool("list_issues")
def list_issues(a):
    iss = S.load()["issues"]
    return {"issues": [{k: i[k] for k in ("number", "title", "state", "labels")}
                       for i in iss if not a.get("state") or i["state"] == a["state"]]}


@S.tool("get_issue")
def get_issue(a):
    return next((i for i in S.load()["issues"] if i["number"] == int(a["issue_number"])), {"error": "Not found"})


@S.tool("search_issues")
def search_issues(a):
    d = S.load()
    items = [{**i, "kind": "issue"} for i in d["issues"]] + [{**p, "kind": "pr"} for p in d["pulls"]]
    return {"items": [{k: i.get(k) for k in ("kind", "number", "title", "state")}
                      for i in search(items, a["query"], ["title", "body"])]}


@S.tool("list_pull_requests")
def list_prs(a):
    return {"pulls": [{k: p[k] for k in ("number", "title", "state")}
                      for p in S.load()["pulls"] if not a.get("state") or p["state"] == a["state"]]}


@S.tool("get_pull_request")
def get_pr(a):
    return next((p for p in S.load()["pulls"] if p["number"] == int(a["pullNumber"])), {"error": "Not found"})


@S.tool("add_issue_comment")
def comment(a):
    d = S.load()
    n = int(a["issue_number"])
    for coll in (d["issues"], d["pulls"]):
        for it in coll:
            if it["number"] == n:
                it.setdefault("comments", []).append({"author": "me", "body": a["body"], "created_in_run": True})
                S.save(d)
                return {"ok": True}
    return {"error": "Not found"}


if __name__ == "__main__":
    S.run()
