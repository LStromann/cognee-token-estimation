"""Fernhill sync retry policy.

This overlay is copied onto the pinned tenacity checkout. The constants below
match the 2026-09-02 decision and are stale relative to later meetings.
Hidden tests check the corrected behavior; they are not in this tree.
"""

MAX_ATTEMPTS = 5
USE_JITTER = False
BASE_DELAY_S = 2
IDEMPOTENCY_HEADER = ""
SIGNATURE_HEADER = "X-Hub-Signature"
DECISION_SOURCE = "MTG-0902"
BACKOFF = "exponential"


def policy():
    return {
        "max_attempts": MAX_ATTEMPTS,
        "jitter": USE_JITTER,
        "base_delay_s": BASE_DELAY_S,
        "idempotency_header": IDEMPOTENCY_HEADER,
        "signature_header": SIGNATURE_HEADER,
        "backoff": BACKOFF,
        "decision_source": DECISION_SOURCE,
    }


def idempotent_key(record_id, attempt):
    """Bug: the attempt number is part of the key, so a retry is a new write."""
    return f"{record_id}:{attempt}"


def should_retry(attempt_number):
    return attempt_number < MAX_ATTEMPTS


def record_identity(record_id, attempt):
    return f"{record_id}#{attempt}"
