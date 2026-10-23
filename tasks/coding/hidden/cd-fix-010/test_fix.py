def test_record_identity_stable():
    from tidepool_sync.retry_policy import record_identity
    assert record_identity('rec', 1) == record_identity('rec', 2) == 'rec'
