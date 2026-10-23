def test_signature_header():
    from tidepool_sync.retry_policy import SIGNATURE_HEADER
    assert SIGNATURE_HEADER == 'X-Tidepool-Signature'
