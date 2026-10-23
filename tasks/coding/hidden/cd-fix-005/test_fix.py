def test_idempotency_header():
    from tidepool_sync.retry_policy import IDEMPOTENCY_HEADER
    assert IDEMPOTENCY_HEADER == 'Idempotency-Key'
