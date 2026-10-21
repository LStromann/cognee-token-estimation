from mcp_mocks.common import MockServer, obj, search

TOOLS = [
    {"name": "list_issues", "description": "List issues in the Linear workspace. Filter by query, state, assignee, project, label.",
     "inputSchema": obj(query="string", state="string", assignee="string", project="string", label="string", limit="integer")},
    {"name": "get_issue", "description": "Retrieve an issue by ID (e.g. LIN-142), including description and comments.",
     "inputSchema": obj(["id"], id="string")},
    {"name": "save_issue", "description": "Create an issue (omit id) or update an existing one.",
     "inputSchema": obj(id="string", title="string", description="string", state="string", assignee="string",
                        project="string", labels={"type": "array", "items": {"type": "string"}})},
    {"name": "list_projects", "description": "List projects.", "inputSchema": obj(query="string")},
    {"name": "get_project", "description": "Get a project by ID or name.", "inputSchema": obj(["query"], query="string")},
    {"name": "list_comments", "description": "List comments on an issue.", "inputSchema": obj(["issueId"], issueId="string")},
    {"name": "save_comment", "description": "Add a comment to an issue.", "inputSchema": obj(["issueId", "body"], issueId="string", body="string")},
    {"name": "list_users", "description": "List workspace users.", "inputSchema": obj(query="string")},
]
S = MockServer("linear", TOOLS)
SUMMARY = ("id", "title", "state", "assignee", "project", "labels", "updated")


@S.tool("list_issues")
def list_issues(a):
    items = S.load()["issues"]
    for k in ("state", "assignee", "project"):
        if a.get(k):
            items = [i for i in items if str(i.get(k, "")).lower() == str(a[k]).lower()]
    if a.get("label"):
        items = [i for i in items if a["label"].lower() in [l.lower() for l in i.get("labels", [])]]
    items = search(items, a.get("query"), ["id", "title", "description"])
    return {"issues": [{k: i.get(k) for k in SUMMARY} for i in items[: a.get("limit", 50)]]}


@S.tool("get_issue")
def get_issue(a):
    d = S.load()
    issue = next((i for i in d["issues"] if i["id"].lower() == a["id"].lower()), None)
    if not issue:
        return {"error": "Issue not found"}
    return {**issue, "comments": [c for c in d["comments"] if c["issueId"] == issue["id"]]}


@S.tool("save_issue")
def save_issue(a):
    d = S.load()
    if a.get("id"):
        issue = next((i for i in d["issues"] if i["id"] == a["id"]), None)
        if not issue:
            return {"error": "Issue not found"}
        issue.update({k: v for k, v in a.items() if k != "id"}, updated_in_run=True)
    else:
        nxt = max(int(i["id"].split("-")[1]) for i in d["issues"]) + 1
        issue = {"id": f"LIN-{nxt}", "state": "Backlog", "labels": [], **a, "created_in_run": True}
        d["issues"].append(issue)
    S.save(d)
    return issue


@S.tool("list_projects")
def list_projects(a):
    return {"projects": search(S.load()["projects"], a.get("query"), ["name", "description"])}


@S.tool("get_project")
def get_project(a):
    q = a["query"].lower()
    p = next((p for p in S.load()["projects"] if q in (p["id"].lower(), p["name"].lower())), None)
    return p or {"error": "Project not found"}


@S.tool("list_comments")
def list_comments(a):
    return {"comments": [c for c in S.load()["comments"] if c["issueId"] == a["issueId"]]}


@S.tool("save_comment")
def save_comment(a):
    d = S.load()
    c = {"issueId": a["issueId"], "body": a["body"], "author": "me", "created_in_run": True}
    d["comments"].append(c)
    S.save(d)
    return c


@S.tool("list_users")
def list_users(a):
    return {"users": search(S.load()["users"], a.get("query"), ["id", "name", "role"])}


if __name__ == "__main__":
    S.run()
