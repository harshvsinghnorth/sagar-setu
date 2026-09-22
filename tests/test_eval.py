"""The scoring in the evaluation harness is arithmetic; pin it with hand-built cases."""

from datetime import date

from marine.eval.backtest import Contingency, DayCase, score
from marine.risk.rules import RiskInputs
from marine.risk.thresholds import Level


def case(truth: Level, forecast: Level, hs_t: float = 1.0, hs_f: float = 1.0) -> DayCase:
    return DayCase(
        "x", date(2026, 9, 1), 1, RiskInputs(), RiskInputs(), truth, forecast, hs_t, hs_f
    )


def test_contingency_metrics():
    c = Contingency(hits=31, misses=2, false_alarms=1, correct_negatives=426)
    m = c.metrics()
    assert m["n"] == 460
    assert m["hit_rate_pod"] == round(31 / 33, 3)
    assert m["false_alarm_ratio"] == round(1 / 32, 3)
    assert m["critical_success_index"] == round(31 / 34, 3)
    assert m["accuracy"] == round(457 / 460, 3)


def test_contingency_handles_no_events():
    m = Contingency(correct_negatives=10).metrics()
    assert m["hit_rate_pod"] is None and m["false_alarm_ratio"] is None and m["accuracy"] == 1.0


def test_score_separates_miss_from_false_alarm_and_uses_both_event_definitions():
    cases = [
        case(Level.NO_GO, Level.NO_GO, 2.8, 2.7),  # hit for both events
        case(Level.NO_GO, Level.CAUTION, 2.6, 2.2),  # miss for NO-GO event, hit for CAUTION+ event
        case(
            Level.GO, Level.CAUTION, 1.0, 1.6
        ),  # false alarm for CAUTION+, correct negative for NO-GO
        case(Level.GO, Level.GO, 0.8, 0.9),  # correct negative
        case(Level.CAUTION, Level.GO, 1.7, 1.3),  # miss for CAUTION+
    ]
    m = score(cases)
    assert m.cases == 5
    assert (m.no_go.hits, m.no_go.misses, m.no_go.false_alarms, m.no_go.correct_negatives) == (
        1,
        1,
        0,
        3,
    )
    assert (m.not_go.hits, m.not_go.misses, m.not_go.false_alarms, m.not_go.correct_negatives) == (
        2,
        1,
        1,
        1,
    )
    assert m.three_class_agreement == 0.4
    assert m.confusion["NO_GO"]["CAUTION"] == 1 and m.confusion["GO"]["CAUTION"] == 1
    assert m.hs_mae == round((0.1 + 0.4 + 0.6 + 0.1 + 0.4) / 5, 3)
    assert m.hs_bias == round((-0.1 - 0.4 + 0.6 + 0.1 - 0.4) / 5, 3)


def test_score_empty():
    m = score([])
    assert m.cases == 0 and m.three_class_agreement is None
