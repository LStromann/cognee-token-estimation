def test_idempotent_key_stable():
    from tidepool_sync.retry_policy import idempotent_key
    assert idempotent_key('rec', 1) == idempotent_key('rec', 2) == 'rec'
