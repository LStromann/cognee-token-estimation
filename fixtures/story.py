"""Single source of truth for Fernhill Labs fixtures and task gold.

Every number a task grades against lives here. Fixture builders and the task
catalog both import these constants, so a stale gold answer has to be edited
in the same place as the document that contradicts it.
"""

PEOPLE = [
    {"id": "maya", "name": "Maya Chen", "role": "CEO"},
    {"id": "jonas", "name": "Jonas Weber", "role": "Eng Lead"},
    {"id": "priya", "name": "Priya Nair", "role": "PM"},
    {"id": "tom", "name": "Tom Okafor", "role": "Backend"},
    {"id": "lea", "name": "Lea Fischer", "role": "Support Lead"},
    {"id": "nora", "name": "Nora Berg", "role": "Legal"},
    {"id": "samir", "name": "Samir Haddad", "role": "Infra"},
    {"id": "hana", "name": "Hana Ito", "role": "Design"},
]

# Current facts. Stale documents below deliberately disagree with these.
RETRY_ORIGINAL = {"date": "2026-09-02", "meeting": "MTG-0902", "max": 5, "base_s": 2, "jitter": False}
RETRY_CURRENT = {"date": "2026-09-16", "meeting": "MTG-0916", "max": 4, "base_s": 2, "jitter": True,
                 "reason": "Brightwave hit rate limits during retry storms"}
WEBHOOKS_GA = {"old": "Oct 15", "current": "Nov 5", "meeting": "MTG-0923", "date": "2026-09-23",
               "blocker": "LIN-151"}
INFRA = {"meeting": "MTG-0918", "date": "2026-09-18", "region": "eu-central-1",
         "standby": "eu-west-1", "rejected": "active-active multi-region writes",
         "redis_until": "2026-11-30", "redis_then": "ElastiCache"}
BRAND = {"meeting": "MTG-0911", "date": "2026-09-11",
         "values": ["Clear water", "Honest sync", "No dark patterns"],
         "tagline": "Sync that stays in its lane.",
         "rejected_tagline": "Move fast, sync faster"}
MSA = {"meeting": "MTG-0919", "date": "2026-09-19", "cap": "12 months of fees",
       "renewal_days": 90, "renewal_days_stale": 60, "subprocessor_days": 30,
       "residency": "EU", "customer": "Brightwave GmbH"}
PRICE = {"pilot_meeting": "MTG-0905", "pilot_date": "2026-09-05", "pilot_usd": 2400, "pilot_connectors": 3,
         "current_meeting": "MTG-0920", "current_date": "2026-09-20", "current_usd": 3100,
         "current_connectors": 5, "approver": "maya"}
SOC2 = {"meeting": "MTG-0908", "date": "2026-09-08", "chosen": "Vanta", "rejected": "Drata", "owner": "samir"}
ONCALL = {"meeting": "MTG-0912", "date": "2026-09-12", "weekday": "tom", "weekend": "samir", "escalate": "jonas"}
SIGNATURE = {"current": "X-Tidepool-Signature", "stale": "X-Hub-Signature"}
IDEMPOTENCY = {"header": "Idempotency-Key", "endpoint": "POST /sync"}
RETENTION = {"days": 30, "stale_days": 90, "what": "sync logs"}
HIRING = {"declined": "Rina Sol", "contractor": "Oleg Petrov", "months": 3, "start": "2026-10-06"}
FLAG = {"name": "webhooks_v2", "owner": "tom", "default": "off", "until": "Nov 5"}
INCIDENT = {"id": "INC-19", "date": "2026-09-14", "sev": "SEV-2", "customer": "Brightwave",
            "cause": "retry storm", "meeting": "MTG-0914"}
REJECTED_CAP = 3  # suggested in LIN-149, explicitly not adopted

PROJECTS = [
    {"id": "PRJ-1", "name": "Sync Reliability", "lead": "jonas", "description": "Make sync robust under failures."},
    {"id": "PRJ-2", "name": "Webhooks GA", "lead": "priya", "description": "Ship webhooks to general availability."},
    {"id": "PRJ-3", "name": "Infra Redesign", "lead": "samir", "description": "Move production onto AWS with a warm standby."},
    {"id": "PRJ-4", "name": "Brightwave Renewal", "lead": "nora", "description": "Close the Brightwave MSA redlines."},
]


def _page(pid, title, owner, edited, content):
    return {"id": pid, "title": title, "owner": owner, "last_edited": edited, "content": content.strip() + "\n"}


def notion_pages():
    v = ", ".join(BRAND["values"])
    return {"pages": [
        _page("NP-1", "Sync Retry Policy v2", "priya", "2026-09-03", f"""
Policy: exponential backoff, base {RETRY_ORIGINAL['base_s']}s, max {RETRY_ORIGINAL['max']} retries. No jitter.
Idempotency: not specified.
Decision source: eng sync {RETRY_ORIGINAL['date']} ({RETRY_ORIGINAL['meeting']}).
Owner: Priya Nair.
"""),
        _page("NP-2", "Webhooks GA Launch Plan", "priya", "2026-09-10", f"""
Launch date: {WEBHOOKS_GA['old']}.
Scope: delivery retries, signature verification ({WEBHOOKS_GA['blocker']}), docs (LIN-160).
Signature header: {SIGNATURE['stale']}.
"""),
        _page("NP-3", "Onboarding Checklist", "lea", "2026-08-20", """
1. Create workspace.
2. Connect first source.
3. Configure sync schedule.
4. Invite teammates.
5. Set up alerts.
"""),
        _page("NP-4", "Infra Redesign", "samir", "2026-09-09", f"""
Decision draft from the 2026-09-09 design review: active-active multi-region writes.
Redis: move off Render immediately, in the same change window.
Primary region named in the draft: eu-central-1.
"""),
        _page("NP-5", "Brand Values", "hana", "2026-08-28", f"""
Working values: Move fast, {BRAND['rejected_tagline']}.
Tagline in market: {BRAND['tagline']}
This page was last edited before the September workshop.
"""),
        _page("NP-6", "Brightwave MSA Summary", "nora", "2026-09-12", f"""
Customer: {MSA['customer']}.
Liability cap: {MSA['cap']}.
Renewal notice: {MSA['renewal_days_stale']} days.
Data residency: {MSA['residency']}.
Subprocessor notice: not in the draft.
"""),
        _page("NP-7", "Pricing — Northwind", "priya", "2026-09-05", f"""
Northwind pilot: ${PRICE['pilot_usd']} per month, {PRICE['pilot_connectors']} connectors included.
Approved at the {PRICE['pilot_date']} pricing chat.
"""),
        _page("NP-8", "Security Program", "samir", "2026-09-01", f"""
SOC 2 tool: still evaluating {SOC2['rejected']}. No vendor chosen on this page.
Owner of the evaluation: Samir Haddad.
"""),
        _page("NP-9", "On-call Rotation", "jonas", "2026-08-15", """
Primary: Jonas Weber, all week.
Escalation: Maya Chen.
Weekday and weekend are not split on this page.
"""),
        _page("NP-10", "Privacy and Retention", "nora", "2026-08-01", f"""
Sync logs are retained for {RETENTION['stale_days']} days.
Customer content follows the MSA residency clause.
"""),
        _page("NP-11", "Hiring — Backend", "priya", "2026-09-07", f"""
Offer status: {HIRING['declined']} accepted. Start date to be scheduled.
No contractor backfill is listed.
"""),
        _page("NP-12", "Incident INC-19 Postmortem", "lea", "2026-09-15", f"""
{INCIDENT['id']} on {INCIDENT['date']}. Severity {INCIDENT['sev']}. Customer {INCIDENT['customer']}.
Cause: a {INCIDENT['cause']} after a failed sync was retried without idempotency.
Mitigation that day: support asked engineering to lower the retry cap. The formal policy change was still open when this note was written.
Linear: LIN-155. GitHub: #88.
"""),
        _page("NP-13", "Team Directory", "maya", "2026-09-01", """
Maya Chen — CEO (maya).
Jonas Weber — Eng Lead (jonas).
Priya Nair — PM (priya).
Tom Okafor — Backend (tom).
Lea Fischer — Support Lead (lea).
Nora Berg — Legal (nora).
Samir Haddad — Infra (samir).
Hana Ito — Design (hana).
"""),
        _page("NP-14", "Glossary", "priya", "2026-08-12", """
Tidepool: Fernhill Labs' data-sync product.
Sync run: one pass over a connector.
Idempotency-Key: the header that makes POST /sync safe to retry.
GA: general availability, as opposed to a private beta.
Warm standby: a second region that can take traffic but does not serve writes in normal operation.
"""),
        _page("NP-15", "Incident Severity", "lea", "2026-08-12", """
SEV-1: customer data corruption, or a full-product outage.
SEV-2: a single customer's sync is halted.
SEV-3: retries are degraded but sync still completes.
INC-19 was declared SEV-2.
"""),
        _page("NP-16", "Support Macros", "lea", "2026-08-18", """
DUP-1: Acknowledge the duplicate records, ask for the sync run id, and do not promise a refund.
LIMIT-1: Tell the customer we are spacing retries, and that engineering owns the cap.
"""),
        _page("NP-17", "Release Checklist", "priya", "2026-08-18", """
1. Feature flag default reviewed.
2. Docs page updated.
3. Support macro ready.
4. Launch-review note posted in #launch.
"""),
        _page("NP-18", "Flag Registry", "tom", "2026-09-10", f"""
{FLAG['name']}: owner {FLAG['owner']}, default {FLAG['default']} until the Webhooks launch date printed on the launch plan ({WEBHOOKS_GA['old']}).
"""),
        _page("NP-19", "Webhook Signature Notes", "tom", "2026-09-10", f"""
Sign webhook bodies with HMAC-SHA256.
Header name: {SIGNATURE['stale']}.
Linear: LIN-151.
"""),
        _page("NP-20", "Q2 Retro Notes", "maya", "2026-08-20", """
We shipped the first connector and hired support. No retry, pricing, or infra decisions were made in this retro.
Action: schedule a September planning cycle.
"""),
    ]}


def linear_data():
    issues = [
        {"id": "LIN-142", "title": "Implement exponential backoff for sync retries", "state": "In Progress",
         "assignee": "tom", "project": "Sync Reliability", "labels": ["backend"], "updated": "2026-09-05",
         "description": f"Per {RETRY_ORIGINAL['date']} eng sync: exponential backoff, base {RETRY_ORIGINAL['base_s']}s, max {RETRY_ORIGINAL['max']} retries. Spec: Notion 'Sync Retry Policy v2'."},
        {"id": "LIN-149", "title": "Cap sync retries at 3", "state": "Cancelled",
         "assignee": "tom", "project": "Sync Reliability", "labels": ["backend"], "updated": "2026-09-16",
         "description": f"Proposal to cap at {REJECTED_CAP}. Not adopted."},
        {"id": "LIN-151", "title": "Webhooks GA: signature verification", "state": "Todo",
         "assignee": "tom", "project": "Webhooks GA", "labels": ["backend", "security"], "updated": "2026-09-10",
         "description": f"HMAC-SHA256 signatures on all webhook payloads. Header: {SIGNATURE['stale']}."},
        {"id": "LIN-155", "title": "Brightwave: duplicate records after sync failure", "state": "Triage",
         "assignee": "jonas", "project": "Sync Reliability", "labels": ["customer", "bug"], "updated": "2026-09-14",
         "description": "Reported by Lea. Duplicates appear after a failed sync is retried. GitHub #88. Suspected cause: retries are not idempotent."},
        {"id": "LIN-158", "title": "Webhooks private beta", "state": "Done",
         "assignee": "priya", "project": "Webhooks GA", "labels": ["launch"], "updated": "2026-09-01",
         "description": "Private beta opened Oct 1 for two design partners. This is not the GA date."},
        {"id": "LIN-160", "title": "Update onboarding docs for webhooks", "state": "Backlog",
         "assignee": "priya", "project": "Webhooks GA", "labels": ["docs"], "updated": "2026-09-11",
         "description": "Docs follow the launch plan date."},
        {"id": "LIN-162", "title": "Pick a SOC 2 tool", "state": "In Progress",
         "assignee": "samir", "project": "Infra Redesign", "labels": ["security"], "updated": "2026-09-02",
         "description": f"Evaluate {SOC2['rejected']}."},
        {"id": "LIN-168", "title": "Update Northwind order form", "state": "Todo",
         "assignee": "priya", "project": "Brightwave Renewal", "labels": ["customer"], "updated": "2026-09-05",
         "description": f"Paper the pilot at ${PRICE['pilot_usd']}/mo for {PRICE['pilot_connectors']} connectors."},
        {"id": "LIN-170", "title": "Terraform active-active regions", "state": "In Progress",
         "assignee": "samir", "project": "Infra Redesign", "labels": ["infra"], "updated": "2026-09-09",
         "description": "Implement active-active multi-region writes. GitHub PR 102."},
        {"id": "LIN-176", "title": "Brightwave MSA redlines", "state": "In Progress",
         "assignee": "nora", "project": "Brightwave Renewal", "labels": ["legal"], "updated": "2026-09-12",
         "description": f"Send the draft with a {MSA['renewal_days_stale']}-day renewal notice. Cap stays {MSA['cap']}."},
        {"id": "LIN-180", "title": "webhooks_v2 flag default", "state": "Todo",
         "assignee": "tom", "project": "Webhooks GA", "labels": ["backend"], "updated": "2026-09-10",
         "description": f"Flag {FLAG['name']} owner {FLAG['owner']}, default {FLAG['default']} until {WEBHOOKS_GA['old']}."},
        {"id": "LIN-183", "title": "Move Redis off Render this week", "state": "Todo",
         "assignee": "samir", "project": "Infra Redesign", "labels": ["infra"], "updated": "2026-09-09",
         "description": "Cut Redis over immediately, in the same window as the region move."},
        {"id": "LIN-190", "title": "Backend offer: Rina Sol", "state": "In Progress",
         "assignee": "priya", "project": "Sync Reliability", "labels": ["hiring"], "updated": "2026-09-07",
         "description": f"{HIRING['declined']} accepted the offer. Schedule a start date."},
    ]
    comments = [
        {"issueId": "LIN-155", "author": "jonas", "body": "Likely retries are not idempotent. Will look after LIN-142."},
        {"issueId": "LIN-149", "author": "jonas", "body": f"Rejected on {RETRY_CURRENT['date']}. We did not adopt a cap of {REJECTED_CAP}."},
        {"issueId": "LIN-158", "author": "priya", "body": "Beta date only. Do not quote this as GA."},
    ]
    return {"users": PEOPLE, "projects": PROJECTS, "issues": issues, "comments": comments}


def meetings():
    def m(mid, title, date, attendees, summary, lines):
        return {"id": mid, "title": title, "date": date, "attendees": attendees, "summary": summary,
                "transcript": [{"speaker": s, "text": t} for s, t in lines]}

    return {"meetings": [
        m("MTG-0820", "Q2 retro", "2026-08-20", ["maya", "jonas", "priya"],
          "Shipped the first connector. No retry, pricing, or infra decision.",
          [("maya", "Nice quarter. Let's plan September properly."),
           ("priya", "I'll book the eng sync and the brand workshop."),
           ("jonas", "Nothing about retries today.")]),
        m(RETRY_ORIGINAL["meeting"], "Eng sync", RETRY_ORIGINAL["date"], ["jonas", "tom", "priya"],
          f"Decided exponential backoff, base {RETRY_ORIGINAL['base_s']}s, max {RETRY_ORIGINAL['max']}. Priya owns the spec.",
          [("jonas", "Fixed 3 retries is not enough. Let's do exponential backoff."),
           ("tom", f"Base {RETRY_ORIGINAL['base_s']} seconds, cap at {RETRY_ORIGINAL['max']} retries?"),
           ("jonas", f"Agreed, max {RETRY_ORIGINAL['max']} retries. No jitter yet. Priya, can you write the spec?"),
           ("priya", "Yes, I'll put Sync Retry Policy v2 in Notion.")]),
        m(PRICE["pilot_meeting"], "Northwind pricing", PRICE["pilot_date"], ["maya", "priya"],
          f"Pilot at ${PRICE['pilot_usd']}/mo for {PRICE['pilot_connectors']} connectors.",
          [("priya", f"Northwind will start at ${PRICE['pilot_usd']} a month, {PRICE['pilot_connectors']} connectors."),
           ("maya", "Approved for the pilot only. Come back before we expand it.")]),
        m(SOC2["meeting"], "Security tools", SOC2["date"], ["samir", "jonas", "maya"],
          f"Chose {SOC2['chosen']} for SOC 2. {SOC2['rejected']} is out.",
          [("samir", f"I trialled {SOC2['rejected']} and {SOC2['chosen']}."),
           ("jonas", f"{SOC2['chosen']} fits the way we already collect evidence."),
           ("maya", f"Then it's {SOC2['chosen']}. Samir, you own it. Please correct the security page, it still says we are evaluating {SOC2['rejected']}.")]),
        m("MTG-0909", "Infra design review", "2026-09-09", ["samir", "jonas", "maya"],
          "Proposal only: active-active multi-region. Not the final decision.",
          [("samir", "Proposal: active-active writes in two regions, and move Redis the same week."),
           ("jonas", "I'm not ready to sign that. Let's revisit next week."),
           ("maya", "Treat this as a proposal, not a decision.")]),
        m(BRAND["meeting"], "Brand values workshop", BRAND["date"], ["hana", "maya", "priya"],
          f"Values are {', '.join(BRAND['values'])}. Tagline stays. Rejected '{BRAND['rejected_tagline']}'.",
          [("hana", "The old page says move fast. That is not us."),
           ("maya", f"The values are {BRAND['values'][0]}, {BRAND['values'][1]}, and {BRAND['values'][2]}."),
           ("priya", f"Tagline stays '{BRAND['tagline']}'."),
           ("hana", f"We are explicitly rejecting '{BRAND['rejected_tagline']}'. I'll fix the Notion page.")]),
        m(ONCALL["meeting"], "On-call review", ONCALL["date"], ["jonas", "tom", "samir"],
          "Weekdays Tom, weekends Samir, escalate to Jonas.",
          [("jonas", "I should not be primary anymore."),
           ("tom", "I can take weekdays."),
           ("samir", "Weekends, and we escalate to Jonas."),
           ("jonas", "That's the rotation. The Notion on-call page is stale.")]),
        m(INCIDENT["meeting"], "INC-19 bridge", INCIDENT["date"], ["lea", "jonas", "tom"],
          f"{INCIDENT['id']} {INCIDENT['sev']} for {INCIDENT['customer']}: {INCIDENT['cause']}.",
          [("lea", "Brightwave is seeing duplicate records after failed syncs. I opened LIN-155."),
           ("tom", "The retry path re-sends the same records with a new attempt number in the key."),
           ("jonas", "This is a SEV-2. Don't change the written policy on this call; we'll decide the cap on Monday.")]),
        m(RETRY_CURRENT["meeting"], "Eng sync", RETRY_CURRENT["date"], ["jonas", "tom", "lea"],
          f"Max retries reduced to {RETRY_CURRENT['max']} with jitter. Ticket and spec still say {RETRY_ORIGINAL['max']}.",
          [("lea", RETRY_CURRENT["reason"] + "."),
           ("jonas", f"Then we go to max {RETRY_CURRENT['max']} retries and add jitter. That's the decision. A cap of {REJECTED_CAP} is rejected."),
           ("tom", f"I'll change the code. LIN-142 and the Notion spec still say {RETRY_ORIGINAL['max']}, and the idempotency key still includes the attempt."),
           ("jonas", f"Also require an {IDEMPOTENCY['header']} header on {IDEMPOTENCY['endpoint']}.")]),
        m(INFRA["meeting"], "Infra decision", INFRA["date"], ["maya", "samir", "jonas"],
          f"Single region {INFRA['region']} plus warm standby in {INFRA['standby']}. Redis stays on Render until {INFRA['redis_until']}.",
          [("samir", "The design doc still says active-active."),
           ("maya", f"We are not doing {INFRA['rejected']}. One region, {INFRA['region']}, with a warm standby in {INFRA['standby']}."),
           ("jonas", f"Redis stays on Render until {INFRA['redis_until']}, then {INFRA['redis_then']}. Not this week."),
           ("samir", "I'll close the active-active terraform and correct LIN-170 and LIN-183.")]),
        m(MSA["meeting"], "Brightwave legal review", MSA["date"], ["nora", "maya", "priya"],
          f"Cap stays {MSA['cap']}. Renewal notice becomes {MSA['renewal_days']} days. Subprocessor notice {MSA['subprocessor_days']} days. Residency stays {MSA['residency']}.",
          [("nora", f"Counsel accepted the liability cap of {MSA['cap']}."),
           ("priya", f"They want renewal notice at {MSA['renewal_days']} days, not {MSA['renewal_days_stale']}."),
           ("nora", f"And a subprocessor notice of {MSA['subprocessor_days']} days. Residency stays {MSA['residency']}. The Notion summary is stale."),
           ("maya", f"Agreed. Customer legal name on the contract is {MSA['customer']}.")]),
        m(PRICE["current_meeting"], "Northwind expansion", PRICE["current_date"], ["maya", "priya"],
          f"Expanded to ${PRICE['current_usd']}/mo for {PRICE['current_connectors']} connectors. Maya approved.",
          [("priya", f"They want {PRICE['current_connectors']} connectors. I propose ${PRICE['current_usd']} a month, replacing the ${PRICE['pilot_usd']} pilot."),
           ("maya", "Approved. Update the order form and the pricing page; both still show the pilot.")]),
        m(WEBHOOKS_GA["meeting"], "Launch review", WEBHOOKS_GA["date"], ["maya", "priya", "jonas"],
          f"Webhooks GA moved from {WEBHOOKS_GA['old']} to {WEBHOOKS_GA['current']}. {WEBHOOKS_GA['blocker']} has not started. Header is {SIGNATURE['current']}.",
          [("priya", f"Signature verification hasn't started, {WEBHOOKS_GA['old']} is not realistic."),
           ("maya", f"Then GA is {WEBHOOKS_GA['current']}. Priya, please communicate. The Oct 1 date was only the private beta."),
           ("jonas", f"And the header is {SIGNATURE['current']}, not {SIGNATURE['stale']}. LIN-151 and the notes still have the old name."),
           ("priya", f"The {FLAG['name']} flag stays {FLAG['default']} until {WEBHOOKS_GA['current']}. Tom owns it.")]),
        m("MTG-0924", "Offsite logistics", "2026-09-24", ["maya", "jonas"],
          "October offsite is in Berlin. No product decisions.",
          [("maya", "Berlin, two days, no roadmap."),
           ("jonas", "I'll book the room.")]),
    ]}


def slack_data():
    channels = [
        {"id": "C01", "name": "eng"},
        {"id": "C02", "name": "launch"},
        {"id": "C03", "name": "support"},
        {"id": "C04", "name": "product"},
        {"id": "C05", "name": "infra"},
        {"id": "C06", "name": "brand"},
        {"id": "C07", "name": "legal"},
    ]
    raw = [
        ("C03", "lea", "1757670000.000100", None, "Brightwave reports duplicate records after a failed sync. Filed LIN-155 and GitHub #88."),
        ("C03", "tom", "1757671000.000100", "1757670000.000100", "The idempotency key includes the attempt number, so a retry looks like a new write."),
        ("C01", "jonas", "1758020000.000100", None, f"Confirmed: sync retries now max {RETRY_CURRENT['max']} with jitter ({RETRY_CURRENT['reason']}). Cap of {REJECTED_CAP} was rejected."),
        ("C01", "tom", "1758020100.000200", "1758020000.000100", f"Will change the code; haven't touched LIN-142 or the spec. They still say {RETRY_ORIGINAL['max']}."),
        ("C01", "jonas", "1758020200.000300", "1758020000.000100", f"Also require {IDEMPOTENCY['header']} on {IDEMPOTENCY['endpoint']}."),
        ("C02", "priya", "1758630000.000100", None, f"Webhooks GA is now {WEBHOOKS_GA['current']}. I'll update the launch plan later. It still says {WEBHOOKS_GA['old']}."),
        ("C02", "jonas", "1758630100.000200", "1758630000.000100", f"Header for signatures is {SIGNATURE['current']}. Please stop writing {SIGNATURE['stale']}."),
        ("C02", "priya", "1758630200.000300", None, f"{FLAG['name']} stays {FLAG['default']} until {WEBHOOKS_GA['current']}. Owner is Tom."),
        ("C05", "samir", "1758200000.000100", None, f"Final infra call: {INFRA['region']} with a warm standby in {INFRA['standby']}. Not {INFRA['rejected']}."),
        ("C05", "maya", "1758200100.000200", "1758200000.000100", f"Redis stays on Render until {INFRA['redis_until']}, then {INFRA['redis_then']}."),
        ("C05", "samir", "1758200200.000300", None, "LIN-170 and PR 102 still describe active-active. They are stale."),
        ("C06", "hana", "1757600000.000100", None, f"Workshop locked the values: {', '.join(BRAND['values'])}. Tagline remains '{BRAND['tagline']}'."),
        ("C06", "maya", "1757600100.000200", "1757600000.000100", f"'{BRAND['rejected_tagline']}' is rejected. The Notion brand page is stale."),
        ("C07", "nora", "1758300000.000100", None, f"Brightwave renewal notice is {MSA['renewal_days']} days. Subprocessor notice is {MSA['subprocessor_days']} days. Cap stays {MSA['cap']}."),
        ("C07", "nora", "1758300100.000200", None, f"Sync-log retention is {RETENTION['days']} days, not {RETENTION['stale_days']}. Privacy page is stale."),
        ("C04", "priya", "1758400000.000100", None, f"Northwind is now ${PRICE['current_usd']}/mo for {PRICE['current_connectors']} connectors. Maya approved in {PRICE['current_meeting']}. Pricing page still shows ${PRICE['pilot_usd']}."),
        ("C04", "maya", "1758400100.000200", "1758400000.000100", f"{HIRING['declined']} declined. Contractor {HIRING['contractor']} for {HIRING['months']} months starting {HIRING['start']}."),
        ("C01", "samir", "1757900000.000100", None, f"SOC 2 tool is {SOC2['chosen']}. {SOC2['rejected']} is not in the running. Security page is stale."),
        ("C01", "jonas", "1757950000.000100", None, f"On-call: {ONCALL['weekday']} weekdays, {ONCALL['weekend']} weekends, escalate to {ONCALL['escalate']}. Notion still says I am primary."),
        ("C03", "lea", "1757700000.000100", None, f"{INCIDENT['id']} ({INCIDENT['date']}) was {INCIDENT['sev']} for {INCIDENT['customer']}. Cause: {INCIDENT['cause']}."),
        ("C01", "tom", "1758500000.000100", None, "Random idea, ignore: what if retries waited a fixed 30s? Not a decision."),
        ("C04", "priya", "1755000000.000100", None, "Q2 retro actions are booked. No product change in that thread."),
    ]
    messages = [{"channel": c, "user": u, "ts": ts, **({"thread_ts": thread} if thread else {}), "text": text}
                for c, u, ts, thread, text in raw]
    return {"channels": channels, "messages": messages}


def github_data():
    return {
        "issues": [
            {"number": 88, "title": "Duplicate records on retry", "state": "open", "labels": ["bug"],
             "body": "Customer Brightwave sees duplicates after a failed sync. Linear: LIN-155. Idempotency key includes the attempt.",
             "comments": []},
            {"number": 104, "title": "Document webhook signatures", "state": "open", "labels": ["docs"],
             "body": f"Docs say the signature header is {SIGNATURE['stale']}. Linear: LIN-151.",
             "comments": []},
        ],
        "pulls": [
            {"number": 91, "title": "Exponential backoff for sync retries", "state": "open",
             "body": f"Implements LIN-142. max_retries={RETRY_ORIGINAL['max']} per spec. No jitter.",
             "files": ["tidepool_sync/retry_policy.py", "tests/test_retry.py"], "comments": []},
            {"number": 102, "title": "Active-active region terraform", "state": "open",
             "body": "Implements LIN-170. Two regions accept writes. Also moves Redis immediately.",
             "files": ["infra/regions.tf"], "comments": []},
            {"number": 110, "title": "Attempt-scoped idempotency keys", "state": "open",
             "body": "Puts the attempt number in the idempotency key so each try is unique.",
             "files": ["tidepool_sync/retry_policy.py"], "comments": []},
        ],
    }


def all_fixtures():
    return {
        "linear": linear_data(),
        "notion": notion_pages(),
        "granola": meetings(),
        "slack": slack_data(),
        "github": github_data(),
    }
