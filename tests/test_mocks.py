"""Mock MCP servers answer from the Fernhill fixtures."""
from harness.config import ROOT
from mcp_mocks import github_server, granola_server, linear_server, notion_server, slack_server


def _bind(server, name):
    server.S.state_dir = ROOT / "fixtures" / "mcp" / name


def test_linear_serves_the_retry_issue():
    _bind(linear_server, "linear")
    issues = linear_server.list_issues({"query": "LIN-142"})["issues"]
    assert any(item["id"] == "LIN-142" for item in issues)


def test_granola_serves_the_september_eng_sync():
    _bind(granola_server, "granola")
    transcript = granola_server.get_meeting_transcript({"meeting_id": "MTG-0916"})
    assert "transcript" in transcript
    assert transcript["id"] == "MTG-0916"


def test_notion_serves_the_retry_policy_page():
    _bind(notion_server, "notion")
    page = notion_server.notion_fetch({"id": "NP-1"})
    assert page["title"] == "Sync Retry Policy v2"


def test_slack_serves_the_eng_channel():
    _bind(slack_server, "slack")
    channel = slack_server.read_channel({"channel_id": "C01", "limit": 5})
    assert channel["messages"]


def test_github_serves_the_retry_pull_request():
    _bind(github_server, "github")
    pulls = github_server.list_prs({})["pulls"]
    assert any(item["number"] == 91 for item in pulls)
