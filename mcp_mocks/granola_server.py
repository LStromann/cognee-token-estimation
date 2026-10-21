from mcp_mocks.common import MockServer, obj, search

TOOLS = [
    {"name": "list_meetings", "description": "List the user's meeting notes in a time range (ISO dates).",
     "inputSchema": obj(start="string", end="string")},
    {"name": "get_meetings", "description": "Get meeting details (summary, notes, attendees) for meeting IDs.",
     "inputSchema": obj(["meeting_ids"], meeting_ids={"type": "array", "items": {"type": "string"}})},
    {"name": "get_meeting_transcript", "description": "Get the full transcript for a meeting.",
     "inputSchema": obj(["meeting_id"], meeting_id="string")},
    {"name": "query_granola_meetings", "description": "Ask about the user's meetings in natural language; returns matching excerpts.",
     "inputSchema": obj(["query"], query="string")},
]
S = MockServer("granola", TOOLS)


@S.tool("list_meetings")
def list_meetings(a):
    ms = S.load()["meetings"]
    if a.get("start"):
        ms = [m for m in ms if m["date"] >= a["start"]]
    if a.get("end"):
        ms = [m for m in ms if m["date"] <= a["end"]]
    return {"meetings": [{k: m[k] for k in ("id", "title", "date", "attendees")} for m in ms]}


@S.tool("get_meetings")
def get_meetings(a):
    ids = set(a["meeting_ids"])
    return {"meetings": [{k: v for k, v in m.items() if k != "transcript"}
                         for m in S.load()["meetings"] if m["id"] in ids]}


@S.tool("get_meeting_transcript")
def get_meeting_transcript(a):
    m = next((m for m in S.load()["meetings"] if m["id"] == a["meeting_id"]), None)
    return {"id": m["id"], "transcript": m["transcript"]} if m else {"error": "Meeting not found"}


@S.tool("query_granola_meetings")
def query(a):
    hits = []
    for m in S.load()["meetings"]:
        lines = search(m["transcript"], a["query"], ["text"])[:3]
        if lines:
            hits.append({"id": m["id"], "title": m["title"], "date": m["date"], "excerpts": lines})
    return {"results": hits}


if __name__ == "__main__":
    S.run()
