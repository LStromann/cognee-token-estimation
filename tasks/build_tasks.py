"""Write tasks/<topic>/*.yaml and the hidden code-fix tests from fixtures.story.

    python tasks/build_tasks.py

Counts are checked against config/experiment.yaml. Re-run after editing story
constants. Files named *TEMPLATE* are left alone.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fixtures.story import (  # noqa: E402
    BRAND,
    FLAG,
    HIRING,
    IDEMPOTENCY,
    INCIDENT,
    INFRA,
    MSA,
    ONCALL,
    PRICE,
    REJECTED_CAP,
    RETENTION,
    RETRY_CURRENT,
    RETRY_ORIGINAL,
    SIGNATURE,
    SOC2,
    WEBHOOKS_GA,
)

VALUES = ", ".join(BRAND["values"])


def _task(tid, topic, typ, hops, turns, gold, rubric, needs, sources, grader=None):
    if isinstance(turns, str):
        turns = [turns]
    body = {
        "id": tid,
        "topic": topic,
        "type": typ,
        "hops": hops,
        "needs": needs,
        "turns": turns,
        "gold": gold,
        "sources": sources,
        "grader": grader or {"kind": "llm_judge", "rubric": rubric},
    }
    return body


def _llm(tid, topic, typ, hops, turns, gold, rubric, sources, needs=None):
    return _task(tid, topic, typ, hops, turns, gold, rubric, needs or ["memory", "mcp"], sources)


def _state(tid, topic, hops, prompt, gold, checks, sources):
    return _task(
        tid, topic, "action", hops, prompt, gold, None, ["memory", "mcp", "skill"], sources,
        grader={"kind": "state_check", "checks": checks},
    )


def project_ops():
    r = RETRY_CURRENT
    o = RETRY_ORIGINAL
    out = []
    recalls = [
        ("po-recall-001", "Who owns the sync retry policy spec, and which Linear project does the backoff ticket belong to?",
         "Priya Nair owns Notion page 'Sync Retry Policy v2' (NP-1). LIN-142 is in the Sync Reliability project.",
         "Pass if it names Priya as the spec owner AND Sync Reliability as the project. Fail if either is missing.",
         ["NP-1", "LIN-142"]),
        ("po-recall-002", "Who is assigned the Brightwave duplicate-records ticket, and which GitHub issue does it point at?",
         "LIN-155 is assigned to jonas. It points at GitHub issue 88.",
         "Pass if it names Jonas (or jonas) AND GitHub #88. Fail if it names a different owner or issue.",
         ["LIN-155", "GH-88"]),
        ("po-recall-003", "Who leads the Webhooks GA project, and which ticket tracks signature verification?",
         "Priya Nair leads the Webhooks GA project (PRJ-2). Signature verification is LIN-151, assigned to tom.",
         "Pass if it names Priya as project lead AND LIN-151. Fail if it names Jonas or Samir as the lead.",
         ["PRJ-2", "LIN-151"]),
        ("po-recall-004", "Which SOC 2 vendor did we choose, and who owns that work?",
         f"We chose {SOC2['chosen']}. Samir Haddad owns it. {SOC2['rejected']} was rejected at {SOC2['meeting']}.",
         f"Pass if the vendor is {SOC2['chosen']} and the owner is Samir. Fail if the answer is {SOC2['rejected']}.",
         [SOC2["meeting"], "LIN-162"]),
        ("po-recall-005", "Who is weekday on-call, who covers weekends, and who is the escalation?",
         "Tom Okafor (tom) covers weekdays, Samir Haddad (samir) covers weekends, and escalation is Jonas Weber (jonas).",
         "Pass only if all three roles are correct. Fail if Jonas is still primary.",
         [ONCALL["meeting"], "NP-9"]),
        ("po-recall-006", "Who approved the expanded Northwind price, and in which meeting?",
         f"Maya Chen approved ${PRICE['current_usd']}/mo at {PRICE['current_meeting']} on {PRICE['current_date']}.",
         "Pass if it names Maya and the 2026-09-20 expansion meeting. Fail if it only cites the pilot.",
         [PRICE["current_meeting"]]),
        ("po-recall-007", "What is the legal name of the Brightwave customer on the contract?",
         f"The contract names {MSA['customer']}.",
         f"Pass if the answer is {MSA['customer']}. Fail if it says only Brightwave with no legal form.",
         [MSA["meeting"]]),
        ("po-recall-008", "Who owns the webhooks_v2 flag, and what is its default?",
         f"{FLAG['name']} is owned by Tom Okafor and defaults to {FLAG['default']}.",
         "Pass if the owner is Tom and the default is off.",
         ["LIN-180", WEBHOOKS_GA["meeting"]]),
        ("po-recall-009", "Until which date does Redis stay on Render, and what does it move to?",
         f"Redis stays on Render until {INFRA['redis_until']}, then moves to {INFRA['redis_then']}.",
         f"Pass if both the date {INFRA['redis_until']} and {INFRA['redis_then']} are present. Fail if it says Redis moves immediately.",
         [INFRA["meeting"], "LIN-183"]),
        ("po-recall-010", "Who is the backend contractor backfill, for how long, and when do they start? Who declined?",
         f"{HIRING['declined']} declined. {HIRING['contractor']} contracts for {HIRING['months']} months starting {HIRING['start']}.",
         f"Pass if it names {HIRING['contractor']}, {HIRING['months']} months, {HIRING['start']}, and that {HIRING['declined']} declined.",
         ["NP-11", "C04"]),
    ]
    for tid, prompt, gold, rubric, sources in recalls:
        out.append(_llm(tid, "project_ops", "recall", 1, prompt, gold, rubric, sources))

    crosses = [
        ("po-xsrc-001", "Is the open PR for sync retries consistent with what the team last decided? If not, what exactly differs?",
         f"No. PR #91 sets max_retries={o['max']} and has no jitter. The latest decision ({r['meeting']}, {r['date']}, confirmed by Jonas in #eng) is max {r['max']} retries with jitter.",
         f"Pass if it says inconsistent, the PR uses {o['max']}, and the latest decision is {r['max']} with jitter. Fail if it treats {o['max']} as current.",
         ["PR-91", r["meeting"], "C01"], 3),
        ("po-xsrc-002", "Does the backoff ticket still match the latest retry decision? Cite the disagreement.",
         f"No. LIN-142 still says base {o['base_s']}s and max {o['max']} from {o['date']}. The current decision is max {r['max']} with jitter, base still {r['base_s']}s.",
         f"Pass if LIN-142 is called stale and the current cap is {r['max']} with jitter. Fail if it says the ticket is already updated.",
         ["LIN-142", r["meeting"]], 2),
        ("po-xsrc-003", "Is the infra ticket's region design the one we are actually building?",
         f"No. LIN-170 and PR #102 still say {INFRA['rejected']}. The decision is a single region {INFRA['region']} with a warm standby in {INFRA['standby']}.",
         f"Pass if it rejects active-active writes and names {INFRA['region']} plus standby {INFRA['standby']}.",
         ["LIN-170", "PR-102", INFRA["meeting"]], 3),
        ("po-xsrc-004", "Is the Northwind price on the pricing page the price we are billing now?",
         f"No. Notion NP-7 still shows ${PRICE['pilot_usd']}/mo for {PRICE['pilot_connectors']} connectors. The approved price is ${PRICE['current_usd']}/mo for {PRICE['current_connectors']} connectors.",
         f"Pass if the current price is ${PRICE['current_usd']} and {PRICE['current_connectors']} connectors, and the page is identified as stale.",
         ["NP-7", PRICE["current_meeting"], "C04"], 3),
        ("po-xsrc-005", "Which signature header should new webhook work use, and which ticket is wrong about it?",
         f"Use {SIGNATURE['current']}. LIN-151 and Notion NP-19 still say {SIGNATURE['stale']}. Jonas corrected this in #launch after the launch review.",
         f"Pass if the current header is {SIGNATURE['current']} and LIN-151 is stale. Fail if {SIGNATURE['stale']} is given as current.",
         ["LIN-151", "NP-19", "C02"], 3),
        ("po-xsrc-006", "Is the Brightwave renewal notice in the MSA summary the one counsel agreed to?",
         f"No. NP-6 says {MSA['renewal_days_stale']} days and omits subprocessors. The agreement is {MSA['renewal_days']} days renewal and {MSA['subprocessor_days']} days subprocessor notice. The cap of {MSA['cap']} did not change.",
         f"Pass if renewal is {MSA['renewal_days']} days, subprocessors are {MSA['subprocessor_days']} days, and the cap is unchanged.",
         ["NP-6", MSA["meeting"], "C07"], 3),
        ("po-xsrc-007", "Do the duplicate-record reports agree on the cause? What should engineering change?",
         "Yes on the cause. LIN-155, GitHub #88, and #support all describe duplicates after a failed sync because the idempotency key includes the attempt. Retries must reuse one key per record.",
         "Pass if the cause is a non-stable idempotency key (attempt number included) and the fix is a stable key. Fail if it blames the region move.",
         ["LIN-155", "GH-88", "C03"], 3),
        ("po-xsrc-008", "Which SOC 2 tool should the open ticket be updated to, and what does it say today?",
         f"LIN-162 and NP-8 still say evaluate {SOC2['rejected']}. The decision at {SOC2['meeting']} was {SOC2['chosen']}, owned by Samir.",
         f"Pass if {SOC2['chosen']} is the choice and {SOC2['rejected']} is the stale one.",
         ["LIN-162", "NP-8", SOC2["meeting"]], 3),
        ("po-xsrc-009", "Does the hiring ticket match what Maya said in #product?",
         f"No. LIN-190 and NP-11 say {HIRING['declined']} accepted. Maya said {HIRING['declined']} declined and named {HIRING['contractor']} for {HIRING['months']} months from {HIRING['start']}.",
         f"Pass if {HIRING['contractor']} is the current plan and {HIRING['declined']} declined.",
         ["LIN-190", "NP-11", "C04"], 2),
        ("po-xsrc-010", "Is the on-call page someone could page from, or is it out of date?",
         f"Out of date. NP-9 says Jonas is primary all week. The rotation is tom on weekdays, samir on weekends, escalate to jonas.",
         "Pass if the page is stale and all three current roles are right.",
         ["NP-9", ONCALL["meeting"], "C01"], 2),
        ("po-xsrc-011", "Does the open terraform PR match the infra decision, including Redis?",
         f"No. PR #102 does {INFRA['rejected']} and moves Redis immediately. The decision is {INFRA['region']} plus warm standby {INFRA['standby']}, and Redis stays on Render until {INFRA['redis_until']}.",
         "Pass if both the region design and the Redis timing are called out as wrong on the PR.",
         ["PR-102", INFRA["meeting"], "LIN-183"], 3),
        ("po-xsrc-012", "When does the webhooks flag turn on, and which writeups still have the old date?",
         f"{FLAG['name']} stays {FLAG['default']} until {WEBHOOKS_GA['current']}. LIN-180 and NP-18 still say {WEBHOOKS_GA['old']}. Tom owns the flag.",
         f"Pass if the flag stays off until {WEBHOOKS_GA['current']} and the October date is stale.",
         ["LIN-180", "NP-18", WEBHOOKS_GA["meeting"]], 3),
    ]
    for tid, prompt, gold, rubric, sources, hops in crosses:
        out.append(_llm(tid, "project_ops", "cross_source", hops, prompt, gold, rubric, sources))

    temporals = [
        ("po-temp-001", "What's the current launch date for Webhooks GA?",
         f"{WEBHOOKS_GA['current']} (moved from {WEBHOOKS_GA['old']} at the {WEBHOOKS_GA['date']} launch review). The Notion launch plan still says {WEBHOOKS_GA['old']}. Oct 1 was only the private beta.",
         f"Pass if the answer is {WEBHOOKS_GA['current']}. Fail if {WEBHOOKS_GA['old']} or Oct 1 is given as the current GA date.",
         [WEBHOOKS_GA["meeting"], "NP-2", "LIN-158"]),
        ("po-temp-002", "What is the current sync retry cap, and is jitter on?",
         f"Max {r['max']} retries with jitter, base still {r['base_s']}s, decided {r['date']}. A cap of {REJECTED_CAP} was rejected. The spec and LIN-142 still say {o['max']} and no jitter.",
         f"Pass if the current cap is {r['max']} and jitter is on. Fail if the answer is {o['max']} or {REJECTED_CAP}.",
         [r["meeting"], "NP-1", "LIN-149"]),
        ("po-temp-003", "What are we charging Northwind right now, and for how many connectors?",
         f"${PRICE['current_usd']} per month for {PRICE['current_connectors']} connectors, approved {PRICE['current_date']}. The ${PRICE['pilot_usd']} / {PRICE['pilot_connectors']} connector pilot is no longer current.",
         f"Pass if the price is ${PRICE['current_usd']} and connectors are {PRICE['current_connectors']}. Fail if the pilot price is given as current.",
         ["NP-7", PRICE["current_meeting"]]),
        ("po-temp-004", "How many days of renewal notice does the Brightwave contract require now?",
         f"{MSA['renewal_days']} days. The MSA summary still says {MSA['renewal_days_stale']}. The liability cap is still {MSA['cap']}.",
         f"Pass if the notice is {MSA['renewal_days']} days. Fail if it is {MSA['renewal_days_stale']}.",
         ["NP-6", MSA["meeting"]]),
        ("po-temp-005", "What is the current production topology we are building?",
         f"Single region {INFRA['region']} with a warm standby in {INFRA['standby']}. Active-active multi-region writes were rejected. The infra page and LIN-170 still describe the rejected design.",
         f"Pass if it names {INFRA['region']} and warm standby {INFRA['standby']}. Fail if active-active writes are the answer.",
         [INFRA["meeting"], "NP-4", "LIN-170"]),
        ("po-temp-006", "How long do we keep sync logs?",
         f"{RETENTION['days']} days. The privacy page still says {RETENTION['stale_days']} days. Nora stated the shorter retention in the legal review and in #legal.",
         f"Pass if retention is {RETENTION['days']} days. Fail if it is {RETENTION['stale_days']}.",
         ["NP-10", "C07", MSA["meeting"]]),
        ("po-temp-007", "Which HTTP header name carries webhook signatures?",
         f"{SIGNATURE['current']}. {SIGNATURE['stale']} is the stale name still on LIN-151 and the signature notes.",
         f"Pass if the header is {SIGNATURE['current']}. Fail if the answer is {SIGNATURE['stale']}.",
         ["C02", "NP-19", "LIN-151"]),
        ("po-temp-008", "When does Redis leave Render?",
         f"Not in the region-move window. Redis stays on Render until {INFRA['redis_until']}, then {INFRA['redis_then']}. LIN-183 says to move it this week and is stale.",
         f"Pass if the date is {INFRA['redis_until']}. Fail if Redis moves immediately.",
         ["LIN-183", INFRA["meeting"], "C05"]),
    ]
    for tid, prompt, gold, rubric, sources in temporals:
        out.append(_llm(tid, "project_ops", "temporal", 2, prompt, gold, rubric, sources))

    out.append(_state(
        "po-act-001", "project_ops", 2,
        "Create a Linear ticket to bring the retry spec in line with the latest decision, assigned to whoever owns the spec. Use the Linear user id. In the description, state the current cap as '4 retries' and mention jitter.",
        "A new Linear issue assigned to priya whose description contains '4 retries' and jitter.",
        [{"server": "linear", "collection": "issues", "created_in_run": True,
          "where": {"assignee": "priya", "description_contains": "4 retries"}}],
        [r["meeting"], "NP-1"]))
    out.append(_state(
        "po-act-002", "project_ops", 2,
        "Open a Linear ticket assigned to the infra lead (user id samir) to replace the active-active plan. The description must contain the word standby and the standby region.",
        f"New issue assigned to samir describing a warm standby in {INFRA['standby']}.",
        [{"server": "linear", "collection": "issues", "created_in_run": True,
          "where": {"assignee": "samir", "description_contains": "standby"}}],
        [INFRA["meeting"], "LIN-170"]))
    out.append(_state(
        "po-act-003", "project_ops", 2,
        "Open a Linear ticket assigned to nora to correct the Brightwave renewal notice. The description must contain '90 days'.",
        f"New issue assigned to nora stating the {MSA['renewal_days']}-day renewal notice.",
        [{"server": "linear", "collection": "issues", "created_in_run": True,
          "where": {"assignee": "nora", "description_contains": "90 days"}}],
        [MSA["meeting"], "NP-6"]))
    out.append(_state(
        "po-act-004", "project_ops", 2,
        "Post a Slack message in #legal (channel id C07) stating the current Brightwave renewal notice. Include the exact phrase '90 days'. Do not change Notion.",
        "A new #legal message containing '90 days'.",
        [{"server": "slack", "collection": "messages", "created_in_run": True,
          "where": {"channel": "C07", "text_contains": "90 days"}}],
        ["C07", MSA["meeting"]]))
    out.append(_state(
        "po-act-005", "project_ops", 2,
        "Open a Linear ticket assigned to tom to rename the webhook signature header. The description must contain X-Tidepool-Signature.",
        f"New issue assigned to tom naming {SIGNATURE['current']}.",
        [{"server": "linear", "collection": "issues", "created_in_run": True,
          "where": {"assignee": "tom", "description_contains": "X-Tidepool-Signature"}}],
        ["LIN-151", "C02"]))
    out.append(_state(
        "po-act-006", "project_ops", 2,
        "Post in #support (channel id C03) telling support which header retries must send. Include the exact header name Idempotency-Key.",
        f"A new #support message containing {IDEMPOTENCY['header']}.",
        [{"server": "slack", "collection": "messages", "created_in_run": True,
          "where": {"channel": "C03", "text_contains": "Idempotency-Key"}}],
        ["C01", "LIN-155"]))
    out.append(_state(
        "po-act-007", "project_ops", 2,
        "Open a Linear ticket assigned to hana to fix the brand page. The description must contain the phrase Clear water.",
        "New issue assigned to hana that names the Clear water value.",
        [{"server": "linear", "collection": "issues", "created_in_run": True,
          "where": {"assignee": "hana", "description_contains": "Clear water"}}],
        [BRAND["meeting"], "NP-5"]))
    out.append(_state(
        "po-act-008", "project_ops", 2,
        "Open a Linear ticket assigned to priya to update the Northwind order form. The description must contain 3100.",
        f"New issue assigned to priya containing {PRICE['current_usd']}.",
        [{"server": "linear", "collection": "issues", "created_in_run": True,
          "where": {"assignee": "priya", "description_contains": "3100"}}],
        [PRICE["current_meeting"], "NP-7"]))

    controls = [
        ("po-ctrl-001", "Summarise the Notion page 'Onboarding Checklist' in 3 bullets.",
         "Create workspace; connect first source; configure sync schedule; invite teammates; set up alerts.",
         "Pass if the bullets cover all 5 checklist steps and do not invent extra steps."),
        ("po-ctrl-002", "From the Notion page 'Team Directory', what is Nora Berg's role and user id?",
         "Nora Berg is Legal, user id nora.",
         "Pass if the role is Legal and the id is nora."),
        ("po-ctrl-003", "Using only the Notion Glossary, what does warm standby mean here?",
         "A second region that can take traffic but does not serve writes in normal operation.",
         "Pass if the definition matches the glossary: can take traffic, does not serve writes normally."),
        ("po-ctrl-004", "From the Notion page 'Incident Severity', which severity was INC-19, and what does that severity mean?",
         "INC-19 was SEV-2: a single customer's sync is halted.",
         "Pass if it says SEV-2 and the single-customer meaning. Fail if it says SEV-1."),
        ("po-ctrl-005", "Quote the purpose of support macro DUP-1 from the Support Macros page.",
         "Acknowledge the duplicate records, ask for the sync run id, and do not promise a refund.",
         "Pass if all three instructions are present. Fail if a refund is promised."),
        ("po-ctrl-006", "List the four steps on the Notion Release Checklist, in order.",
         "1. Feature flag default reviewed. 2. Docs page updated. 3. Support macro ready. 4. Launch-review note posted in #launch.",
         "Pass if all four steps are present in that order."),
    ]
    for tid, prompt, gold, rubric in controls:
        out.append(_llm(tid, "project_ops", "control", 1, prompt, gold, rubric, ["named page"], needs=["mcp"]))

    multis = [
        ("po-multi-001",
         ["What changed in the retry cap since the first decision, and why?",
          "Draft a Slack post for #support. Don't send it. Follow the team Slack convention: at most 3 lines, covering what changed, why, and who to ask."],
         f"Max retries went from {o['max']} to {r['max']} with jitter on {r['date']} because {r['reason']}. Draft is <=3 lines and points at Jonas.",
         "Judge the final turn. Pass if the draft states 4 retries with jitter, the Brightwave rate-limit reason, names who to ask, and is at most 3 lines."),
        ("po-multi-002",
         ["What did we decide to build for regions, and what did we reject?",
          "Draft a Linear comment for LIN-170. Don't post it. It should say what to build instead."],
         f"Build {INFRA['region']} with warm standby {INFRA['standby']}. Reject {INFRA['rejected']}. The draft says that.",
         f"Judge the final turn. Pass if the draft rejects active-active writes and names {INFRA['region']} and {INFRA['standby']}."),
        ("po-multi-003",
         ["What is Northwind's current price and connector count?",
          "Draft a #product Slack message announcing it. Don't send it. Mention who approved."],
         f"${PRICE['current_usd']}/mo, {PRICE['current_connectors']} connectors, approved by Maya.",
         f"Judge the final turn. Pass if the draft has ${PRICE['current_usd']}, {PRICE['current_connectors']} connectors, and Maya."),
        ("po-multi-004",
         ["What changed in the Brightwave MSA negotiation, and what did not?",
          "Draft a short note Nora could send to counsel. Don't file it. Include renewal, subprocessors, and the cap."],
         f"Renewal is {MSA['renewal_days']} days, subprocessor notice {MSA['subprocessor_days']} days, cap unchanged at {MSA['cap']}.",
         f"Judge the final turn. Pass if all three terms are in the note."),
        ("po-multi-005",
         ["What is the current on-call rotation?",
          "Draft a #eng message announcing it. Don't send it. Name weekday, weekend, and escalation using user ids."],
         "tom weekdays, samir weekends, escalate to jonas.",
         "Judge the final turn. Pass if all three ids are in the draft and Jonas is escalation rather than primary."),
        ("po-multi-006",
         ["Which brand values and tagline are current, and which tagline was rejected?",
          "Draft a #brand message Hana could pin. Don't send it. Include the three values and the tagline."],
         f"Values: {VALUES}. Tagline: {BRAND['tagline']}. Rejected: {BRAND['rejected_tagline']}.",
         "Judge the final turn. Pass if all three values and the kept tagline are in the draft, and the rejected tagline is not presented as current."),
    ]
    for tid, turns, gold, rubric in multis:
        out.append(_llm(tid, "project_ops", "multi_turn", 2, turns, gold, rubric, ["story"]))
    return out


def meetings():
    r = RETRY_CURRENT
    o = RETRY_ORIGINAL
    out = []
    recalls = [
        ("mt-recall-001", "What did we originally decide about sync retries, and when?",
         f"Eng sync {o['date']} ({o['meeting']}): exponential backoff, base {o['base_s']}s, max {o['max']} retries, no jitter. Priya took the spec. This was later changed.",
         f"Pass if it gives {o['date']}, exponential backoff, base {o['base_s']}s, and max {o['max']}.",
         [o["meeting"]]),
        ("mt-recall-002", "Who was in the Webhooks launch review, and who announced the new GA date?",
         f"Attendees were maya, priya, and jonas. Maya announced GA on {WEBHOOKS_GA['current']}.",
         "Pass if Maya is the one who set the date and the three attendees are right.",
         [WEBHOOKS_GA["meeting"]]),
        ("mt-recall-003", "What three brand values did the workshop lock, and who named them?",
         f"Maya named {VALUES}. Hana ran the workshop ({BRAND['meeting']}).",
         "Pass if all three values are present and attributed to that workshop.",
         [BRAND["meeting"]]),
        ("mt-recall-004", "Which tagline did the brand workshop reject, and which one stayed?",
         f"Rejected '{BRAND['rejected_tagline']}'. Kept '{BRAND['tagline']}'.",
         "Pass if both taglines are present and only the kept one is current.",
         [BRAND["meeting"], "C06"]),
        ("mt-recall-005", "Which SOC 2 product did the security-tools meeting choose?",
         f"{SOC2['chosen']}, on {SOC2['date']}. {SOC2['rejected']} was rejected. Samir owns it.",
         f"Pass if the choice is {SOC2['chosen']}.",
         [SOC2["meeting"]]),
        ("mt-recall-006", "When was INC-19, what severity was it, and which customer was affected?",
         f"{INCIDENT['date']}, {INCIDENT['sev']}, customer {INCIDENT['customer']}. Cause discussed on the bridge: {INCIDENT['cause']}.",
         f"Pass if the date, {INCIDENT['sev']}, and Brightwave are all present.",
         [INCIDENT["meeting"], "NP-12"]),
        ("mt-recall-007", "What price and connector count did we approve for the Northwind pilot, and on what date?",
         f"{PRICE['pilot_date']}: ${PRICE['pilot_usd']} per month, {PRICE['pilot_connectors']} connectors. Maya said it was the pilot only.",
         f"Pass if it is the pilot figure ${PRICE['pilot_usd']} and {PRICE['pilot_connectors']} connectors, not the later expansion.",
         [PRICE["pilot_meeting"]]),
        ("mt-recall-008", "Who said the Webhooks GA date out loud in the launch review, and what date did they say?",
         f"Maya Chen said {WEBHOOKS_GA['current']}.",
         f"Pass if the speaker is Maya and the date is {WEBHOOKS_GA['current']}.",
         [WEBHOOKS_GA["meeting"]]),
        ("mt-recall-009", "How many days of subprocessor notice did counsel add, and who reported it?",
         f"{MSA['subprocessor_days']} days, reported by Nora Berg in {MSA['meeting']}.",
         f"Pass if the number is {MSA['subprocessor_days']} and the speaker is Nora.",
         [MSA["meeting"]]),
        ("mt-recall-010", "Which region is the warm standby, and who required that we not do active-active writes?",
         f"Warm standby is {INFRA['standby']}. Maya rejected {INFRA['rejected']}. Primary region is {INFRA['region']}.",
         f"Pass if the standby region is {INFRA['standby']} and Maya is the one who rejected active-active writes.",
         [INFRA["meeting"]]),
    ]
    for tid, prompt, gold, rubric, sources in recalls:
        out.append(_llm(tid, "meetings", "recall", 1, prompt, gold, rubric, sources))

    crosses = [
        ("mt-xsrc-001", "Does the written retry spec match the latest eng sync?",
         f"No. NP-1 still says max {o['max']} and no jitter from {o['meeting']}. {r['meeting']} set max {r['max']} with jitter.",
         f"Pass if the spec is stale and the meeting decision is {r['max']} with jitter.",
         ["NP-1", r["meeting"]], 2),
        ("mt-xsrc-002", "Does the launch plan match the launch review?",
         f"No. NP-2 still says {WEBHOOKS_GA['old']}. {WEBHOOKS_GA['meeting']} moved GA to {WEBHOOKS_GA['current']} because {WEBHOOKS_GA['blocker']} has not started.",
         f"Pass if GA is {WEBHOOKS_GA['current']} and the plan is stale.",
         ["NP-2", WEBHOOKS_GA["meeting"]], 2),
        ("mt-xsrc-003", "Does LIN-170 match the infra decision meeting?",
         f"No. LIN-170 is active-active writes. {INFRA['meeting']} chose {INFRA['region']} plus warm standby {INFRA['standby']}.",
         "Pass if the ticket and the meeting disagree and the meeting wins.",
         ["LIN-170", INFRA["meeting"]], 2),
        ("mt-xsrc-004", "Does the MSA summary match the legal review?",
         f"No. NP-6 has a {MSA['renewal_days_stale']}-day renewal and no subprocessor clause. {MSA['meeting']} set {MSA['renewal_days']} and {MSA['subprocessor_days']} days. Cap {MSA['cap']} matches.",
         "Pass if the two notice periods are the new numbers and the cap is called out as unchanged.",
         ["NP-6", MSA["meeting"]], 2),
        ("mt-xsrc-005", "Does the Northwind pricing page match the expansion meeting?",
         f"No. NP-7 is the ${PRICE['pilot_usd']} pilot. {PRICE['current_meeting']} approved ${PRICE['current_usd']} for {PRICE['current_connectors']} connectors.",
         f"Pass if the meeting price is ${PRICE['current_usd']} and the page is the pilot.",
         ["NP-7", PRICE["current_meeting"]], 2),
        ("mt-xsrc-006", "Does the security page match the security-tools meeting?",
         f"No. NP-8 still says evaluating {SOC2['rejected']}. {SOC2['meeting']} chose {SOC2['chosen']}.",
         f"Pass if {SOC2['chosen']} is chosen and the page is stale.",
         ["NP-8", SOC2["meeting"]], 2),
        ("mt-xsrc-007", "Does the on-call page match the on-call review?",
         "No. NP-9 says Jonas is primary all week. The review set tom weekdays, samir weekends, escalate to jonas.",
         "Pass if the page is stale and the three-way rotation is correct.",
         ["NP-9", ONCALL["meeting"]], 2),
        ("mt-xsrc-008", "Does the brand page match the values workshop?",
         f"No. NP-5 still leads with move-fast and '{BRAND['rejected_tagline']}'. The workshop locked {VALUES} and kept '{BRAND['tagline']}'.",
         "Pass if the three workshop values are current and the page's move-fast line is stale.",
         ["NP-5", BRAND["meeting"]], 2),
        ("mt-xsrc-009", "The latest eng sync required a header on POST /sync. Does the retry spec mention it?",
         f"The sync required {IDEMPOTENCY['header']} on {IDEMPOTENCY['endpoint']}. NP-1 says idempotency is not specified.",
         f"Pass if the header is {IDEMPOTENCY['header']} and the spec is missing it.",
         ["NP-1", r["meeting"]], 2),
        ("mt-xsrc-010", "After the launch review, which signature header did Jonas confirm, and which ticket still has the old one?",
         f"Jonas confirmed {SIGNATURE['current']} in the review and in #launch. LIN-151 still says {SIGNATURE['stale']}.",
         f"Pass if {SIGNATURE['current']} is current and LIN-151 is the stale ticket.",
         [WEBHOOKS_GA["meeting"], "LIN-151", "C02"], 3),
        ("mt-xsrc-011", "Do the incident postmortem and the bridge transcript agree on severity and cause?",
         f"Yes. Both say {INCIDENT['id']} was {INCIDENT['sev']} for {INCIDENT['customer']} because of a {INCIDENT['cause']}. The postmortem notes the formal cap change was still open that day.",
         f"Pass if severity {INCIDENT['sev']}, Brightwave, and retry storm are all present.",
         ["NP-12", INCIDENT["meeting"]], 2),
        ("mt-xsrc-012", "The infra decision kept Redis on Render for a while. Which ticket still says to move it immediately?",
         f"LIN-183 says move Redis this week. {INFRA['meeting']} keeps Redis on Render until {INFRA['redis_until']}, then {INFRA['redis_then']}.",
         f"Pass if LIN-183 is stale and the date is {INFRA['redis_until']}.",
         ["LIN-183", INFRA["meeting"], "C05"], 3),
    ]
    for tid, prompt, gold, rubric, sources, hops in crosses:
        out.append(_llm(tid, "meetings", "cross_source", hops, prompt, gold, rubric, sources))

    temporals = [
        ("mt-temp-001", "What is the current retry cap, including whether jitter is used?",
         f"Max {r['max']} with jitter, from {r['date']}. The earlier cap of {o['max']} and the rejected cap of {REJECTED_CAP} are not current.",
         f"Pass if the answer is {r['max']} with jitter. Fail for {o['max']} or {REJECTED_CAP}.",
         [r["meeting"], "NP-1", "LIN-149"]),
        ("mt-temp-002", "What is the current Webhooks GA date?",
         f"{WEBHOOKS_GA['current']}, set by Maya on {WEBHOOKS_GA['date']}. {WEBHOOKS_GA['old']} is the stale plan date. Oct 1 was the private beta only.",
         f"Pass only for {WEBHOOKS_GA['current']}. Fail for {WEBHOOKS_GA['old']} or Oct 1.",
         [WEBHOOKS_GA["meeting"], "NP-2", "LIN-158"]),
        ("mt-temp-003", "Are we building active-active regions?",
         f"No. {INFRA['meeting']} rejected {INFRA['rejected']}. Build {INFRA['region']} with a warm standby in {INFRA['standby']}.",
         "Pass if active-active is rejected and both regions are named with the right roles.",
         [INFRA["meeting"], "MTG-0909", "NP-4"]),
        ("mt-temp-004", "What renewal notice did Brightwave's counsel actually accept?",
         f"{MSA['renewal_days']} days, plus a {MSA['subprocessor_days']}-day subprocessor notice. The {MSA['renewal_days_stale']}-day figure is the old draft.",
         f"Pass if renewal is {MSA['renewal_days']} days. Fail if it is {MSA['renewal_days_stale']}.",
         [MSA["meeting"], "NP-6"]),
        ("mt-temp-005", "What is Northwind paying now?",
         f"${PRICE['current_usd']} per month for {PRICE['current_connectors']} connectors as of {PRICE['current_date']}. The ${PRICE['pilot_usd']} pilot is over.",
         f"Pass for ${PRICE['current_usd']} and {PRICE['current_connectors']} connectors. Fail for the pilot price.",
         [PRICE["current_meeting"], "NP-7"]),
        ("mt-temp-006", "How long are sync logs retained?",
         f"{RETENTION['days']} days, stated by Nora in the legal review and #legal. The privacy page's {RETENTION['stale_days']} days is stale.",
         f"Pass for {RETENTION['days']} days. Fail for {RETENTION['stale_days']}.",
         ["NP-10", "C07"]),
        ("mt-temp-007", "What is the current webhook signature header?",
         f"{SIGNATURE['current']}, confirmed by Jonas in the launch review. {SIGNATURE['stale']} is stale.",
         f"Pass for {SIGNATURE['current']}. Fail for {SIGNATURE['stale']}.",
         [WEBHOOKS_GA["meeting"], "NP-19"]),
        ("mt-temp-008", "Which SOC 2 vendor is current?",
         f"{SOC2['chosen']}. {SOC2['rejected']} was evaluated and rejected.",
         f"Pass for {SOC2['chosen']}. Fail for {SOC2['rejected']}.",
         [SOC2["meeting"], "NP-8"]),
        ("mt-temp-009", "Who is primary on-call on a weekday?",
         "tom. Samir covers weekends. Jonas is escalation only. The on-call page still calls Jonas primary.",
         "Pass if the weekday primary is tom. Fail if it is Jonas.",
         [ONCALL["meeting"], "NP-9"]),
        ("mt-temp-010", "Is 'Move fast, sync faster' one of our brand values?",
         f"No. It was rejected at {BRAND['meeting']}. Current values are {VALUES}. The brand page still shows the rejected line.",
         "Pass if the phrase is rejected and at least two of the three current values are named.",
         [BRAND["meeting"], "NP-5"]),
    ]
    for i, (tid, prompt, gold, rubric, sources) in enumerate(temporals):
        out.append(_llm(tid, "meetings", "temporal", 2 + (i % 2), prompt, gold, rubric, sources))

    out.append(_state("mt-act-001", "meetings", 2,
        "Send a Slack message to #support (C03) explaining the current retry rule for Brightwave. The message must contain both '4' and 'jitter'.",
        "A new #support message containing 4 and jitter.",
        [{"server": "slack", "collection": "messages", "created_in_run": True,
          "where": {"channel": "C03", "text_contains": "jitter"}}],
        [r["meeting"]]))
    out.append(_state("mt-act-002", "meetings", 2,
        "Create a Linear ticket assigned to priya capturing the launch-review follow-up. The description must contain 'Nov 5'.",
        f"New issue assigned to priya containing {WEBHOOKS_GA['current']}.",
        [{"server": "linear", "collection": "issues", "created_in_run": True,
          "where": {"assignee": "priya", "description_contains": "Nov 5"}}],
        [WEBHOOKS_GA["meeting"]]))
    out.append(_state("mt-act-003", "meetings", 2,
        "Post the locked brand values in #brand (C06). The message must contain 'No dark patterns'.",
        "A new #brand message containing No dark patterns.",
        [{"server": "slack", "collection": "messages", "created_in_run": True,
          "where": {"channel": "C06", "text_contains": "No dark patterns"}}],
        [BRAND["meeting"]]))
    out.append(_state("mt-act-004", "meetings", 2,
        "Create a Linear ticket assigned to nora for the subprocessor clause. The description must contain '30 days'.",
        f"New issue assigned to nora containing the {MSA['subprocessor_days']}-day subprocessor notice.",
        [{"server": "linear", "collection": "issues", "created_in_run": True,
          "where": {"assignee": "nora", "description_contains": "30 days"}}],
        [MSA["meeting"]]))
    out.append(_state("mt-act-005", "meetings", 2,
        "Create a Notion page titled 'Decision log 0916' whose content contains the word jitter and the current retry cap.",
        "A new Notion page titled Decision log 0916 whose body contains jitter.",
        [{"server": "notion", "collection": "pages", "created_in_run": True,
          "where": {"title_contains": "Decision log 0916", "content_contains": "jitter"}}],
        [r["meeting"]]))
    out.append(_state("mt-act-006", "meetings", 2,
        "Post the standby region in #infra (C05). The message must contain eu-west-1.",
        f"A new #infra message containing {INFRA['standby']}.",
        [{"server": "slack", "collection": "messages", "created_in_run": True,
          "where": {"channel": "C05", "text_contains": "eu-west-1"}}],
        [INFRA["meeting"]]))

    controls = [
        ("mt-ctrl-001", "Summarise the Granola meeting MTG-0902. Name the cap they agreed that day.",
         f"Eng sync on {o['date']}: exponential backoff, base {o['base_s']}s, max {o['max']} retries. Priya owns the spec.",
         f"Pass if the summary is about MTG-0902 and the cap that day is {o['max']}. Do not require the later change."),
        ("mt-ctrl-002", "Who attended Granola meeting MTG-0911? List the user ids.",
         "hana, maya, priya.",
         "Pass if those three attendees are named. Fail if Jonas is included."),
        ("mt-ctrl-003", "Summarise the Notion page 'Onboarding Checklist' in one sentence per step.",
         "Create workspace; connect first source; configure sync schedule; invite teammates; set up alerts.",
         "Pass if all five steps appear."),
        ("mt-ctrl-004", "What is the title of Notion page NP-3?",
         "Onboarding Checklist.",
         "Pass if the title is Onboarding Checklist."),
        ("mt-ctrl-005", "From the Glossary page, what is a sync run?",
         "One pass over a connector.",
         "Pass if the answer matches that definition."),
        ("mt-ctrl-006", "From the Incident Severity page, define SEV-1 and SEV-3.",
         "SEV-1 is customer data corruption or a full-product outage. SEV-3 is degraded retries while sync still completes.",
         "Pass if both definitions are present and not swapped."),
    ]
    for tid, prompt, gold, rubric in controls:
        out.append(_llm(tid, "meetings", "control", 1, prompt, gold, rubric, ["named source"], needs=["mcp"]))

    multis = [
        ("mt-multi-001",
         ["What changed in the retry policy since the first decision, and why?",
          "Draft a Slack post for #support explaining what this means for Brightwave. Don't send it."],
         f"Max retries reduced from {o['max']} to {r['max']} with jitter on {r['date']} because {r['reason']}. Draft is <=3 lines: what changed, why, who to ask (Jonas).",
         "Judge the final turn. Pass if the draft states 4 retries and jitter, the Brightwave rate-limit reason, and is at most 3 lines."),
        ("mt-multi-002",
         ["What did the brand workshop decide?",
          "Draft a 4-line values blurb Hana can paste into Notion. Don't edit Notion."],
         f"Values {VALUES}. Tagline '{BRAND['tagline']}'. Rejected '{BRAND['rejected_tagline']}'.",
         "Judge the final turn. Pass if all three values and the kept tagline are in the blurb."),
        ("mt-multi-003",
         ["What did the launch review change about Webhooks GA?",
          "Draft the #launch announcement. Don't send it. Include the new date and what blocked the old one."],
         f"GA is {WEBHOOKS_GA['current']}, moved from {WEBHOOKS_GA['old']} because {WEBHOOKS_GA['blocker']} has not started.",
         f"Judge the final turn. Pass if {WEBHOOKS_GA['current']} is the date and LIN-151 or signature verification is the blocker."),
        ("mt-multi-004",
         ["What did Brightwave's counsel accept in the legal review?",
          "Draft the note back to counsel. Don't send it. Cover cap, renewal, subprocessors, and residency."],
         f"Cap {MSA['cap']}, renewal {MSA['renewal_days']} days, subprocessors {MSA['subprocessor_days']} days, residency {MSA['residency']}.",
         "Judge the final turn. Pass if all four terms are present."),
        ("mt-multi-005",
         ["What did the infra decision meeting settle for regions and Redis?",
          "Draft a #infra post. Don't send it."],
         f"{INFRA['region']} plus warm standby {INFRA['standby']}. Redis on Render until {INFRA['redis_until']}.",
         "Judge the final turn. Pass if both regions are correct and Redis is not moving immediately."),
        ("mt-multi-006",
         ["What happened in the INC-19 bridge?",
          "Draft a customer note Lea could send to Brightwave. Don't send it. No ticket ids, per the release-notes style of customer language."],
         f"{INCIDENT['sev']} on {INCIDENT['date']} caused by a {INCIDENT['cause']} that duplicated records. Customer language, no LIN- ids.",
         "Judge the final turn. Pass if the note explains duplicates from retries, names the severity or the impact, and does not include a LIN- id."),
    ]
    for tid, turns, gold, rubric in multis:
        out.append(_llm(tid, "meetings", "multi_turn", 2, turns, gold, rubric, ["story"], needs=["memory", "mcp", "skill"]))
    return out


def _qa(tid, hops, prompt, gold, rubric, sources, needs=None):
    return _llm(tid, "coding", "codebase_qa", hops, prompt, gold, rubric, sources, needs or ["code"])


def coding(fix_tests):
    o = RETRY_ORIGINAL
    r = RETRY_CURRENT
    out = []
    qas = [
        ("cd-qa-001", 1,
         "Where is tenacity's wait_exponential defined, and does that strategy add jitter?",
         "Class wait_exponential in tenacity/wait.py. The docstring says the intervals are fixed and there is no jitter; it is not for contention between processes. Use wait_random_exponential for that. Defaults: multiplier=1, exp_base=2, min=0.",
         "Pass if it names tenacity/wait.py and wait_exponential and says this class does not add jitter. Fail if it claims wait_exponential jitters."),
        ("cd-qa-002", 1,
         "Which tenacity class implements full jitter exponential backoff, and how is the sleep chosen?",
         "wait_random_exponential in tenacity/wait.py subclasses wait_exponential and returns random.uniform(self.min, high), where high is the exponential wait from the parent.",
         "Pass if it names wait_random_exponential, the file, and random.uniform between min and the exponential high."),
        ("cd-qa-003", 2,
         "How is wait_exponential_jitter different from wait_exponential, and what happened to the initial parameter?",
         "wait_exponential_jitter in tenacity/wait.py adds random.uniform(0, jitter) on top of multiplier * exp_base**(attempt-1), then clamps to min/max. The initial parameter is deprecated in favor of multiplier; passing both raises ValueError.",
         "Pass if it describes the added jitter term and the deprecation of initial."),
        ("cd-qa-004", 1,
         "When does stop_after_attempt stop, and where is it defined?",
         "tenacity/stop.py. stop_after_attempt(max_attempt_number) returns True when retry_state.attempt_number >= max_attempt_number.",
         "Pass if the file is tenacity/stop.py and the condition is attempt_number >= max_attempt_number."),
        ("cd-qa-005", 2,
         "What is the difference between stop_after_delay and stop_before_delay?",
         "Both are in tenacity/stop.py. stop_after_delay stops when seconds_since_start >= max_delay, which can overshoot a pending wait. stop_before_delay stops when seconds_since_start + upcoming_sleep >= max_delay, so the next sleep will not cross the limit.",
         "Pass if both classes are distinguished and upcoming_sleep is mentioned for stop_before_delay."),
        ("cd-qa-006", 1,
         "What is stop_never, and is it a class you instantiate?",
         "stop_never is a singleton instance of _stop_never in tenacity/stop.py. Calling it always returns False.",
         "Pass if it says stop_never is a singleton (not something you construct) and it never stops."),
        ("cd-qa-007", 2,
         "How do you add two tenacity wait strategies together, and what class does that produce?",
         "wait_base.__add__ returns wait_combine. wait_combine in tenacity/wait.py sums the strategy outputs for the same retry state. Summing a list works because __radd__ treats 0 as the identity.",
         "Pass if it names wait_combine and says the waits are summed."),
        ("cd-qa-008", 2,
         "How does wait_chain pick which strategy to use on a given attempt?",
         "wait_chain in tenacity/wait.py indexes strategies by attempt_number (clamped to the last strategy). After the list is exhausted it keeps using the last strategy. An empty chain raises ValueError.",
         "Pass if selection is by attempt number and the last strategy repeats."),
        ("cd-qa-009", 1,
         "Where does a caller import the public retry decorator from?",
         "tenacity/__init__.py re-exports retry and Retrying. The decorator is the public entry point of the package, not a class buried only in wait.py or stop.py.",
         "Pass if it points at tenacity/__init__.py (or `from tenacity import retry`)."),
        ("cd-qa-010", 1,
         "Where is before_sleep_log defined, and what does it log?",
         "tenacity/before_sleep.py. before_sleep_log(logger, log_level, exc_info=False, sec_format='%.3g') returns a callback that logs 'Retrying {fn} in {seconds} seconds as it raised/returned {value}'.",
         "Pass if the file is tenacity/before_sleep.py and the log line includes the sleep and the outcome."),
        ("cd-qa-011", 1,
         "What sleep helpers does tenacity/nap.py provide?",
         "sleep(seconds) calls time.sleep and is the default strategy, meant to be mocked in tests. sleep_using_event(event) waits on a threading.Event and may return early if the event is set.",
         "Pass if both sleep and sleep_using_event are described."),
        ("cd-qa-012", 2,
         "Where is retry_if_exception_type defined, and what does it retry on?",
         "Class retry_if_exception_type in tenacity/retry.py. It subclasses retry_if_exception and retries when the outcome failed with an exception that is an instance of the given type or types (default Exception).",
         "Pass if the file is tenacity/retry.py and the condition is isinstance of the configured exception types."),
        ("cd-qa-013", 2,
         "In this workspace, what does tidepool_sync/retry_policy.py currently set for max attempts, jitter, and the signature header?",
         f"MAX_ATTEMPTS = {o['max']}, USE_JITTER = False, SIGNATURE_HEADER = {SIGNATURE['stale']!r}. DECISION_SOURCE is {o['meeting']}.",
         f"Pass if it reports the code as it is: max {o['max']}, jitter off, header {SIGNATURE['stale']}. Fail if it reports the later decision instead of the code."),
        ("cd-qa-014", 1,
         "What does tidepool_sync.retry_policy.idempotent_key return, and why would that duplicate records?",
         "It returns '{record_id}:{attempt}'. The attempt number changes on every try, so a retry is not the same key and is stored again.",
         "Pass if the format includes the attempt and the answer says that makes retries look like new writes."),
        ("cd-qa-015", 1,
         "What are the default min and max of tenacity.wait.wait_random?",
         "wait_random in tenacity/wait.py defaults to min=0 and max=1 second. The sleep is min + random.random() * (max - min).",
         "Pass if the defaults are 0 and 1 second and the file is tenacity/wait.py."),
    ]
    for tid, hops, prompt, gold, rubric in qas:
        out.append(_qa(tid, hops, prompt, gold, rubric, ["tenacity" if not tid.endswith("013") and not tid.endswith("014") else "overlay"]))

    recalls = [
        ("cd-recall-001", "From memory of this repo: which file defines wait_exponential, and does that class jitter?",
         "tenacity/wait.py defines wait_exponential, and that class does not jitter. Jitter is wait_random_exponential or wait_exponential_jitter.",
         "Pass if the file and the no-jitter fact are both correct."),
        ("cd-recall-002", "From memory of this repo: what comparison does stop_after_attempt use?",
         "retry_state.attempt_number >= max_attempt_number, in tenacity/stop.py.",
         "Pass if the comparison direction is >= on attempt_number."),
        ("cd-recall-003", "From memory of this workspace: what integer is MAX_ATTEMPTS in tidepool_sync/retry_policy.py right now, before any fix?",
         f"{o['max']}. The module still records DECISION_SOURCE {o['meeting']}.",
         f"Pass if the answer is {o['max']} as the current code, not the desired cap."),
        ("cd-recall-004", "From memory of this repo: which class is tenacity's full-jitter exponential wait?",
         "wait_random_exponential in tenacity/wait.py.",
         "Pass if the class name is wait_random_exponential. Fail if the answer is wait_exponential."),
        ("cd-recall-005", "From memory of this repo: which file defines before_sleep_log?",
         "tenacity/before_sleep.py.",
         "Pass if the path is tenacity/before_sleep.py."),
    ]
    for tid, prompt, gold, rubric in recalls:
        out.append(_llm(tid, "coding", "recall", 1, prompt, gold, rubric, ["repo"], needs=["memory", "code"]))

    temporals = [
        ("cd-temp-001", "What max attempt count should tidepool_sync use today?",
         f"{r['max']}. The file still has {o['max']} from {o['meeting']}. {r['meeting']} changed the cap and added jitter. A cap of {REJECTED_CAP} was rejected.",
         f"Pass if the answer is {r['max']}. Fail for {o['max']} or {REJECTED_CAP}."),
        ("cd-temp-002", "Should tidepool_sync turn jitter on?",
         f"Yes. {r['meeting']} added jitter because {r['reason']}. The code's USE_JITTER is still False. In tenacity, wait_random_exponential or wait_exponential_jitter is the matching strategy, not plain wait_exponential.",
         "Pass if jitter should be on. Fail if it says the fixed wait_exponential strategy is enough."),
        ("cd-temp-003", "Which signature header should tidepool_sync send today?",
         f"{SIGNATURE['current']}. The code and LIN-151 and NP-19 still say {SIGNATURE['stale']}. Jonas corrected it at the launch review.",
         f"Pass if the header is {SIGNATURE['current']}."),
        ("cd-temp-004", "Should the idempotency key change on each retry attempt?",
         f"No. {r['meeting']} requires a stable {IDEMPOTENCY['header']} on {IDEMPOTENCY['endpoint']}. The code includes the attempt, which is what duplicated Brightwave's records (LIN-155, GitHub #88, PR #110).",
         "Pass if the key must stay stable across attempts. Fail if a per-attempt key is recommended."),
    ]
    for tid, prompt, gold, rubric in temporals:
        out.append(_llm(tid, "coding", "temporal", 2, prompt, gold, rubric, ["overlay", "meetings"], needs=["memory", "mcp", "code"]))

    crosses = [
        ("cd-xsrc-001", "Is PR #91 consistent with the latest retry decision and with what the overlay should do?",
         f"No. PR #91 sets max_retries={o['max']} and no jitter, matching the stale overlay and LIN-142. The decision is max {r['max']} with jitter.",
         f"Pass if PR #91, the overlay, and the decision are compared and the decision is {r['max']} with jitter."),
        ("cd-xsrc-002", "LIN-142 names a base delay and a cap. Which of those is still right, and which tenacity parameter is the base?",
         f"Base {o['base_s']}s is still right and corresponds to wait_exponential's multiplier (or exp growth from that base). The cap of {o['max']} is stale; today it is {r['max']}. stop_after_attempt is the tenacity stop that enforces a cap.",
         f"Pass if the base {o['base_s']}s stays, the cap is now {r['max']}, and stop_after_attempt is named."),
        ("cd-xsrc-003", "Why does the Brightwave duplicate bug line up with idempotent_key in this repo?",
         "LIN-155, GitHub #88, and the #support thread say retries are not idempotent. idempotent_key formats '{record_id}:{attempt}', and PR #110 keeps the attempt in the key. A retry must reuse one key.",
         "Pass if the function format and the tickets agree that the attempt number is the bug."),
        ("cd-xsrc-004", "LIN-151, the signature notes, and SIGNATURE_HEADER in the overlay all agree with each other. Do they agree with the latest decision?",
         f"They agree with each other on {SIGNATURE['stale']}, and that is wrong. The decision is {SIGNATURE['current']}.",
         f"Pass if the three stale sources agree and the current header is {SIGNATURE['current']}."),
        ("cd-xsrc-005", "The latest eng sync added jitter. Which tenacity wait class matches that, and which one is the wrong choice?",
         "Use wait_random_exponential (full jitter) or wait_exponential_jitter. Plain wait_exponential is the wrong choice: its docstring says the intervals are fixed.",
         "Pass if a jittering class is recommended and wait_exponential is rejected."),
        ("cd-xsrc-006", "GitHub #88 and PR #110 describe the idempotency key. Does the overlay implement what they describe, and is that what we want?",
         "Yes, the overlay matches them: the attempt is part of the key. That is not what we want. The key must be stable, header name Idempotency-Key.",
         "Pass if the code matches the stale PR and the desired behavior is a stable key."),
        ("cd-xsrc-007", "Which parts of the Notion retry spec still match tidepool_sync/retry_policy.py, and which parts are both wrong?",
         f"Both still have max {o['max']}, no jitter, and no idempotency header, from {o['meeting']}. The base of {o['base_s']}s matches and is still correct. The cap, jitter, and header are wrong together.",
         f"Pass if base {o['base_s']}s is the part that still holds and the cap of {o['max']} is wrong."),
        ("cd-xsrc-008", "Jonas confirmed a retry change in #eng. What does the overlay's USE_JITTER and MAX_ATTEMPTS say instead?",
         f"#eng says max {r['max']} with jitter. The overlay has USE_JITTER False and MAX_ATTEMPTS {o['max']}.",
         f"Pass if the Slack decision is {r['max']} with jitter and the code values are the old ones."),
    ]
    for i, (tid, prompt, gold, rubric) in enumerate(crosses):
        out.append(_llm(tid, "coding", "cross_source", 2 + (i % 2), prompt, gold, rubric, ["overlay", "mcp"], needs=["memory", "mcp", "code"]))

    controls = [
        ("cd-ctrl-001", "Using the release-notes skill in this workspace, what section headings does a customer note use, and are ticket ids allowed?",
         "Sections: New, Improved, Fixed. Customer language, no ticket ids.",
         "Pass if those three headings are named and ticket ids are excluded."),
        ("cd-ctrl-002", "From the team-conventions skill, what is the maximum length of a Linear title, and how many lines is a Slack update?",
         "Linear titles are imperative and under 70 characters. Slack updates are at most 3 lines: what changed, why, who to ask.",
         "Pass if both the 70-character title rule and the 3-line Slack rule are present."),
        ("cd-ctrl-003", "Summarise GitHub issue 88 in two sentences. Use the mock GitHub tools.",
         "Brightwave sees duplicate records after a failed sync. It points at LIN-155 and says the idempotency key includes the attempt.",
         "Pass if duplicates, Brightwave or the failed sync, and the attempt-in-key cause are present."),
        ("cd-ctrl-004", "What is the title of Linear ticket LIN-160, and what state is it in?",
         "Title: Update onboarding docs for webhooks. State: Backlog. Assignee priya.",
         "Pass if the title and the Backlog state are both correct."),
        ("cd-ctrl-005", "List the file paths changed by GitHub pull request 91.",
         "tidepool_sync/retry_policy.py and tests/test_retry.py.",
         "Pass if both paths are named."),
    ]
    for tid, prompt, gold, rubric in controls:
        needs = ["skill"] if tid in {"cd-ctrl-001", "cd-ctrl-002"} else ["mcp"]
        out.append(_llm(tid, "coding", "control", 1, prompt, gold, rubric, ["named"], needs=needs))

    multis = [
        ("cd-multi-001",
         ["Where in tenacity would we express 'exponential backoff with jitter' and a max attempt cap? Name the classes.",
          "Given the latest Fernhill decision, what arguments should those classes get for our sync path?"],
         f"wait_random_exponential or wait_exponential_jitter, plus stop_after_attempt({r['max']}). Base delay stays {r['base_s']}s. Jitter on. Not the stale cap of {o['max']}.",
         f"Judge the final turn. Pass if the cap is {r['max']}, jitter is on, and a jittering tenacity wait class is named."),
        ("cd-multi-002",
         ["How does idempotent_key in this repo relate to the Brightwave duplicate reports?",
          "Write the replacement behavior in one sentence, including the header name. Don't edit files yet."],
         f"The key must be stable per record (no attempt number) and the header is {IDEMPOTENCY['header']}.",
         f"Judge the final turn. Pass if the key is stable and the header is {IDEMPOTENCY['header']}."),
        ("cd-multi-003",
         ["What does PR #91 change, according to GitHub?",
          "Is that PR consistent with the latest decision? Answer yes or no and state the diff in the cap and jitter."],
         f"No. PR #91 is max {o['max']} without jitter. The decision is max {r['max']} with jitter.",
         f"Judge the final turn. Pass if the answer is no, PR cap {o['max']} without jitter, decision {r['max']} with jitter."),
    ]
    for tid, turns, gold, rubric in multis:
        out.append(_llm(tid, "coding", "multi_turn", 2, turns, gold, rubric, ["repo", "mcp"], needs=["memory", "mcp", "code"]))

    for spec in fix_tests:
        out.append(_task(
            spec["id"], "coding", "code_fix", spec["hops"], spec["prompt"], spec["gold"], None,
            ["memory", "mcp", "code"], spec["sources"],
            grader={"kind": "tests", "hidden_tests": f"tasks/coding/hidden/{spec['id']}",
                    "command": "python3 -m pytest -q tests/hidden --rootdir=. --override-ini=pythonpath=. -p no:cacheprovider"},
        ))
    return out


FIXES = [
    {"id": "cd-fix-001", "hops": 2,
     "prompt": "Update tidepool_sync/retry_policy.py so MAX_ATTEMPTS matches the latest retry decision. Do not change unrelated files.",
     "gold": "MAX_ATTEMPTS is 4.",
     "sources": ["MTG-0916", "retry_policy.py"],
     "test": "def test_max_attempts():\n    from tidepool_sync.retry_policy import MAX_ATTEMPTS\n    assert MAX_ATTEMPTS == 4\n"},
    {"id": "cd-fix-002", "hops": 2,
     "prompt": "Update tidepool_sync/retry_policy.py so jitter is enabled, matching the latest retry decision.",
     "gold": "USE_JITTER is True.",
     "sources": ["MTG-0916"],
     "test": "def test_jitter_enabled():\n    from tidepool_sync.retry_policy import USE_JITTER\n    assert USE_JITTER is True\n"},
    {"id": "cd-fix-003", "hops": 3,
     "prompt": "Fix idempotent_key in tidepool_sync/retry_policy.py so two attempts for the same record share one key. That is the Brightwave duplicate bug.",
     "gold": "idempotent_key(record_id, attempt) returns the record id only.",
     "sources": ["LIN-155", "GH-88"],
     "test": "def test_idempotent_key_stable():\n    from tidepool_sync.retry_policy import idempotent_key\n    assert idempotent_key('rec', 1) == idempotent_key('rec', 2) == 'rec'\n"},
    {"id": "cd-fix-004", "hops": 3,
     "prompt": "Update SIGNATURE_HEADER in tidepool_sync/retry_policy.py to the header the launch review confirmed.",
     "gold": "SIGNATURE_HEADER is X-Tidepool-Signature.",
     "sources": ["MTG-0923", "LIN-151"],
     "test": "def test_signature_header():\n    from tidepool_sync.retry_policy import SIGNATURE_HEADER\n    assert SIGNATURE_HEADER == 'X-Tidepool-Signature'\n"},
    {"id": "cd-fix-005", "hops": 2,
     "prompt": "Set IDEMPOTENCY_HEADER in tidepool_sync/retry_policy.py to the header name the latest eng sync required on POST /sync.",
     "gold": "IDEMPOTENCY_HEADER is Idempotency-Key.",
     "sources": ["MTG-0916"],
     "test": "def test_idempotency_header():\n    from tidepool_sync.retry_policy import IDEMPOTENCY_HEADER\n    assert IDEMPOTENCY_HEADER == 'Idempotency-Key'\n"},
    {"id": "cd-fix-006", "hops": 3,
     "prompt": "Update policy() in tidepool_sync/retry_policy.py so the returned dict matches every current decision: max 4, jitter on, base delay 2, Idempotency-Key, X-Tidepool-Signature, backoff 'exponential+jitter', decision source MTG-0916.",
     "gold": "policy() returns that bundle.",
     "sources": ["MTG-0916", "MTG-0923"],
     "test": "def test_policy_bundle():\n    from tidepool_sync.retry_policy import policy\n    assert policy() == {\n        'max_attempts': 4,\n        'jitter': True,\n        'base_delay_s': 2,\n        'idempotency_header': 'Idempotency-Key',\n        'signature_header': 'X-Tidepool-Signature',\n        'backoff': 'exponential+jitter',\n        'decision_source': 'MTG-0916',\n    }\n"},
    {"id": "cd-fix-007", "hops": 2,
     "prompt": "should_retry must follow the current cap of 4 attempts. Attempt numbers are 1-based counts of tries already started. Attempt 4 must not retry; attempt 3 must.",
     "gold": "should_retry(3) is True and should_retry(4) is False.",
     "sources": ["MTG-0916"],
     "test": "def test_should_retry_cap():\n    from tidepool_sync.retry_policy import should_retry\n    assert should_retry(3) is True\n    assert should_retry(4) is False\n"},
    {"id": "cd-fix-008", "hops": 2,
     "prompt": "Set BACKOFF in tidepool_sync/retry_policy.py to exponential+jitter, matching the latest decision rather than plain exponential.",
     "gold": "BACKOFF is exponential+jitter.",
     "sources": ["MTG-0916"],
     "test": "def test_backoff_name():\n    from tidepool_sync.retry_policy import BACKOFF\n    assert BACKOFF == 'exponential+jitter'\n"},
    {"id": "cd-fix-009", "hops": 2,
     "prompt": "Point DECISION_SOURCE in tidepool_sync/retry_policy.py at the meeting that set the current cap, not the original eng sync.",
     "gold": "DECISION_SOURCE is MTG-0916.",
     "sources": ["MTG-0916", "MTG-0902"],
     "test": "def test_decision_source():\n    from tidepool_sync.retry_policy import DECISION_SOURCE\n    assert DECISION_SOURCE == 'MTG-0916'\n"},
    {"id": "cd-fix-010", "hops": 3,
     "prompt": "Fix record_identity in tidepool_sync/retry_policy.py so the stored identity of a record does not change between attempts. Same bug class as the Brightwave duplicates.",
     "gold": "record_identity(record_id, attempt) returns the record id only.",
     "sources": ["LIN-155"],
     "test": "def test_record_identity_stable():\n    from tidepool_sync.retry_policy import record_identity\n    assert record_identity('rec', 1) == record_identity('rec', 2) == 'rec'\n"},
]


def write_hidden(spec):
    dest = ROOT / "tasks" / "coding" / "hidden" / spec["id"]
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob("test_*.py"):
        old.unlink()
    (dest / "test_fix.py").write_text(spec["test"])
    placeholder = dest / "test_placeholder.py"
    if placeholder.exists():
        placeholder.unlink()


def main():
    cfg = yaml.safe_load((ROOT / "config" / "experiment.yaml").read_text())
    tasks = project_ops() + meetings() + coding(FIXES)
    for spec in FIXES:
        write_hidden(spec)
    have = {}
    ids = []
    for t in tasks:
        have[(t["topic"], t["type"])] = have.get((t["topic"], t["type"]), 0) + 1
        ids.append(t["id"])
        path = ROOT / "tasks" / t["topic"] / f"{t['id']}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(t, sort_keys=False, allow_unicode=True, width=100))
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate ids in catalog")
    problems = []
    for topic, plan in cfg["sizing"].items():
        for typ, n in plan.items():
            got = have.get((topic, typ), 0)
            if got != n:
                problems.append(f"{topic}/{typ}: generated {got}, plan {n}")
    if problems:
        raise SystemExit("count mismatch:\n" + "\n".join(problems))
    # Drop task files the catalog no longer owns (keep templates and hidden tests).
    owned = {t["id"] for t in tasks}
    for path in (ROOT / "tasks").glob("*/*.yaml"):
        if "TEMPLATE" in path.name:
            continue
        if path.stem not in owned:
            path.unlink()
            print("removed", path)
    print(f"wrote {len(tasks)} tasks")


if __name__ == "__main__":
    main()
