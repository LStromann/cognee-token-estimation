# Fernhill Labs — company story (source of truth for all fixtures)

Fernhill Labs is a 25-person startup building **Tidepool**, a data-sync SaaS. The current time is late September 2026.

**People:** Maya Chen (CEO, `maya`), Jonas Weber (Eng Lead, `jonas`), Priya Nair (PM, `priya`), Tom Okafor (Backend, `tom`), Lea Fischer (Support Lead, `lea`).

## Storylines
Each storyline is spread across tools and contains deliberate stale sources.

1. **Retry policy**
   - On 2026-09-02, the eng sync (MTG-0902) decides on exponential backoff with a 2s base and a maximum of 5 retries.
   - Priya writes the Notion spec "Sync Retry Policy v2". Tom opens LIN-142 and later PR #91 with `max_retries=5`.
   - On 2026-09-16, the eng sync (MTG-0916) reduces the maximum to **4 retries with jitter**, because customer Brightwave was hitting rate limits. Jonas confirms this in #eng on Slack.
   - **Stale sources:** the Notion spec, LIN-142 and PR #91 still say 5.
2. **Webhooks GA date**
   - The launch review on 2026-09-23 (MTG-0923) moves GA from Oct 15 to **Nov 5**, because signature verification (LIN-151) hasn't started. Priya posts this in #launch.
   - **Stale source:** the Notion launch plan still says Oct 15.
3. **Brightwave duplicates**
   - Lea reports duplicate records after a failed sync (#support, LIN-155, GitHub #88). The root cause is that retries aren't idempotent.

Use `python -m mcp_mocks.generate_fixtures` to expand the story with more storylines, filler noise and distractors, up to the sizes in docs/test-plan.md.
