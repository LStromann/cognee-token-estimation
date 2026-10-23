def test_jitter_enabled():
    from tidepool_sync.retry_policy import USE_JITTER
    assert USE_JITTER is True
