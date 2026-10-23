"""Corrected Fernhill sync retry policy (2026-09-16 decision, MTG-0916)."""

MAX_ATTEMPTS = 4
USE_JITTER = True
BASE_DELAY_S = 2
IDEMPOTENCY_HEADER = "Idempotency-Key"
SIGNATURE_HEADER = "X-Tidepool-Signature"
DECISION_SOURCE = "MTG-0916"
BACKOFF = "exponential+jitter"


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
    return str(record_id)


def should_retry(attempt_number):
    return attempt_number < MAX_ATTEMPTS


def record_identity(record_id, attempt):
    return str(record_id)
