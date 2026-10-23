# Fernhill Labs

Fernhill Labs is a fictional company. Nothing here is a real customer, contract, or incident.

Tidepool is their data-sync product. The benchmark clock is late September 2026. People: Maya Chen (CEO, `maya`), Jonas Weber (Eng Lead, `jonas`), Priya Nair (PM, `priya`), Tom Okafor (Backend, `tom`), Lea Fischer (Support Lead, `lea`), Nora Berg (Legal, `nora`), Samir Haddad (Infra, `samir`), Hana Ito (Design, `hana`).

Machine-readable constants, fixture JSON, and task gold all come from `fixtures/story.py`. Edit that module and re-run `make fixtures`. This page is the narrative form of the same facts. Older documents in the fixtures disagree on purpose.

## Current decisions

- **Retries (MTG-0916, 2026-09-16).** Max 4 attempts, exponential backoff with jitter, base 2s. Brightwave was hitting rate limits. A cap of 3 (LIN-149) was rejected. `Idempotency-Key` is required on `POST /sync` and must not include the attempt number. Webhook signature header is `X-Tidepool-Signature`.
- **Earlier retry note (MTG-0902, 2026-09-02).** Max 5, no jitter. Still written on NP-1, LIN-142, and GitHub PR 91. The coding overlay `tidepool_sync/retry_policy.py` ships that stale policy until a code-fix task changes it.
- **Webhooks GA (MTG-0923, 2026-09-23).** General availability moved from Oct 15 to Nov 5 because LIN-151 (signature verification) has not started. Oct 1 was a private beta (LIN-158, Done), not GA. Flag `webhooks_v2` stays off, owner Tom, until Nov 5. NP-2 and a few tickets still say Oct 15.
- **Infra (MTG-0918, 2026-09-18).** One region, `eu-central-1`, with a warm standby in `eu-west-1`. Active-active writes were rejected. Redis stays on Render until 2026-11-30, then ElastiCache. NP-4 and PR 102 still describe the rejected design. MTG-0909 was a proposal only.
- **Brand (MTG-0911, 2026-09-11).** Values: Clear water, Honest sync, No dark patterns. Tagline: "Sync that stays in its lane." Rejected: "Move fast, sync faster" (still on NP-5).
- **Brightwave MSA (MTG-0919, 2026-09-19).** Customer Brightwave GmbH. Liability cap 12 months of fees. Renewal notice 90 days. Subprocessor notice 30 days. Residency EU. NP-6 still says 60 days and omits the subprocessor notice.
- **Northwind (MTG-0920, 2026-09-20).** $3100 per month, 5 connectors, approved by Maya. The 5 September pilot (MTG-0905) was $2400 and 3 connectors. NP-7 and LIN-168 still describe the pilot.
- **SOC 2 (MTG-0908, 2026-09-08).** Vanta, not Drata. Owner Samir. NP-8 still says the choice is open.
- **On-call (MTG-0912, 2026-09-12).** Tom on weekdays, Samir on weekends, escalate to Jonas. NP-9 still lists Jonas as the only primary.
- **Retention.** Sync logs are kept 30 days. NP-10 still says 90.
- **Hiring.** Rina Sol declined. Oleg Petrov is a contractor for 3 months from 2026-10-06. NP-11 and LIN-190 still say Rina accepted.
- **INC-19 (2026-09-14, SEV-2).** Brightwave retry storm. NP-12 matches the incident. The formal cap change was still open that day; it landed on 16 September.
- **Duplicates.** LIN-155 (assignee Jonas), GitHub #88, #support, and PR #110 put the attempt number in the idempotency key. That is the bug.

## Channels and stable pages

Slack: C01 `#eng`, C02 `#launch`, C03 `#support`, C04 `#product`, C05 `#infra`, C06 `#brand`, C07 `#legal`.

Pages that are current and safe to treat as controls: NP-3 Onboarding (5 steps), NP-13 Team Directory, NP-14 Glossary, NP-15 Incident Severity, NP-16 Support Macros, NP-17 Release Checklist (4 steps).

Distractors, not decisions: MTG-0820 (Q2 retro), MTG-0924 (Berlin offsite), a Slack aside from Tom about a fixed 30s sleep.

## Coding checkout

Coding tasks run against [tenacity](https://github.com/jd/tenacity) pinned at `32ac68f0941319c0d2f4fb927f96e4ee29bb46c6`, with `coding_overlay/tidepool_sync` copied on top. Hidden tests grade the overlay. Questions about tenacity itself are about that pin. The library is not vendored; dry-run uses `fixtures/coding_offline` plus the overlay and does not clone.
