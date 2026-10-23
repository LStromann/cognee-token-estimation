def test_policy_bundle():
    from tidepool_sync.retry_policy import policy
    assert policy() == {
        'max_attempts': 4,
        'jitter': True,
        'base_delay_s': 2,
        'idempotency_header': 'Idempotency-Key',
        'signature_header': 'X-Tidepool-Signature',
        'backoff': 'exponential+jitter',
        'decision_source': 'MTG-0916',
    }
