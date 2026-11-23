from app.services.risk_engine import RiskEngine


def test_velocity_rule_flags_fourth_transaction_in_one_minute():
    engine = RiskEngine(low_threshold=0.25)
    for timestamp in (0.0, 10.0, 20.0):
        result = engine.evaluate(
            entity_key="card-1",
            timestamp=timestamp,
            amount=10.0,
            ml_probability=0.01,
            ml_threshold=0.9,
        )
        assert result["route"] == "approve"

    result = engine.evaluate(
        entity_key="card-1",
        timestamp=30.0,
        amount=10.0,
        ml_probability=0.01,
        ml_threshold=0.9,
    )
    assert result["route"] == "flag"
    assert result["triggered_rules"][0]["code"] == "velocity_60s"


def test_ml_gray_zone_routes_to_step_up():
    result = RiskEngine(low_threshold=0.25).evaluate(
        entity_key="account-1",
        timestamp=100.0,
        amount=10.0,
        ml_probability=0.50,
        ml_threshold=0.90,
    )
    assert result["route"] == "step_up"
