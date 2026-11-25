import pytest
from scripts.compare_validation_errors import measures


def test_confusion_counts_and_inclusive_threshold():
    result = measures([0, 0, 1, 1], [0.1, 0.5, 0.49, 0.9], 0.5)
    assert (result["tn"], result["fp"], result["fn"], result["tp"]) == (1, 1, 1, 1)
    assert result["precision"] == pytest.approx(0.5)
    assert result["recall"] == pytest.approx(0.5)
    assert result["false_alarms_per_1000_legitimate"] == pytest.approx(500)
