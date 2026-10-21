from mcp_mocks.common import MockServer, obj, search

TOOLS = [
    {"name": "slack_search_public_and_private", "description": "Search messages across all channels.",
     "inputSchema": obj(["query"], query="string")},
    {"name": "slack_read_channel", "description": "Read recent messages in a channel (newest first).",
     "inputSchema": obj(["channel_id"], channel_id="string", limit="integer")},
    {"name": "slack_read_thread", "description": "Read a thread (parent + replies).",
     "inputSchema": obj(["channel_id", "message_ts"], channel_id="string", message_ts="string")},
    {"name": "slack_send_message", "description": "Send a message to a channel.",
     "inputSchema": obj(["channel_id", "message"], channel_id="string", message="string")},
]
S = MockServer("slack", TOOLS)


def _chan(d, key):
    k = key.lstrip("#").lower()
    c = next((c for c in d["channels"] if k in (c["id"].lower(), c["name"].lower())), None)
    return c["id"] if c else key


@S.tool("slack_search_public_and_private")
def slack_search(a):
    return {"messages": search(S.load()["messages"], a["query"], ["text", "user"])[:20]}


@S.tool("slack_read_channel")
def read_channel(a):
    d = S.load()
    cid = _chan(d, a["channel_id"])
    msgs = sorted([m for m in d["messages"] if m["channel"] == cid and not m.get("thread_ts")],
                  key=lambda m: m["ts"], reverse=True)
    return {"channels": d["channels"], "messages": msgs[: a.get("limit", 20)]}


@S.tool("slack_read_thread")
def read_thread(a):
    d = S.load()
    cid, ts = _chan(d, a["channel_id"]), a["message_ts"]
    return {"messages": [m for m in d["messages"] if m["channel"] == cid and ts in (m["ts"], m.get("thread_ts"))]}


@S.tool("slack_send_message")
def send(a):
    d = S.load()
    m = {"channel": _chan(d, a["channel_id"]), "ts": "run", "user": "me", "text": a["message"], "created_in_run": True}
    d["messages"].append(m)
    S.save(d)
    return {"ok": True, "message": m}


if __name__ == "__main__":
    S.run()
