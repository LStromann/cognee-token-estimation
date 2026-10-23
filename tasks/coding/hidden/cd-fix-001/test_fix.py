def test_max_attempts():
    from tidepool_sync.retry_policy import MAX_ATTEMPTS
    assert MAX_ATTEMPTS == 4
