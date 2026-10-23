def test_should_retry_cap():
    from tidepool_sync.retry_policy import should_retry
    assert should_retry(3) is True
    assert should_retry(4) is False
