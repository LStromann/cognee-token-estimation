def test_backoff_name():
    from tidepool_sync.retry_policy import BACKOFF
    assert BACKOFF == 'exponential+jitter'
