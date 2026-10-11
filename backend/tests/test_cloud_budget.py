import pytest
from backend import cloud_budget, storage

def test_paid_inference_requires_verified_rates(monkeypatch):
    monkeypatch.setenv('ATMOS_BEDROCK_INPUT_USD_PER_MILLION','0')
    monkeypatch.setenv('ATMOS_BEDROCK_OUTPUT_USD_PER_MILLION','0')
    with pytest.raises(ValueError,match='pricing'):
        cloud_budget.inference_reservation(100)
    monkeypatch.setenv('ATMOS_BEDROCK_INPUT_USD_PER_MILLION','1')
    monkeypatch.setenv('ATMOS_BEDROCK_OUTPUT_USD_PER_MILLION','2')
    assert cloud_budget.inference_reservation(100)==pytest.approx((125+2048+1024)/1000000)
    with pytest.raises(ValueError,match='request limit'):
        cloud_budget.inference_reservation(50001)
    monkeypatch.setenv('ATMOS_BEDROCK_INPUT_USD_PER_MILLION','nan')
    with pytest.raises(ValueError,match='pricing'):
        cloud_budget.inference_reservation(100)

def test_reservations_enforce_lifetime_limits(monkeypatch):
    cloud_budget.status()
    with storage.connect() as db:
        db.execute('DELETE FROM cloud_reservations')
    monkeypatch.setenv('ATMOS_BEDROCK_RESERVATION_LIMIT_USD','25')
    cloud_budget.reserve('bedrock',4.99)
    with pytest.raises(ValueError,match='limit reached'):
        cloud_budget.reserve('bedrock',.02)
    cloud_budget.reserve('s3',units=1000)
    with pytest.raises(ValueError,match='limit reached'):
        cloud_budget.reserve('sqs')
    with pytest.raises(ValueError,match='Invalid'):
        cloud_budget.reserve('bedrock',float('nan'))
    with storage.connect() as db:
        db.execute('DELETE FROM cloud_reservations')
