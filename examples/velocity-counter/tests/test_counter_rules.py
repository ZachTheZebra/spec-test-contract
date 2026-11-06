"""Tests that call the example counter.

Each function is named in spec_coverage.yaml. The formulas stay in
VelocityCounter.tla. These tests fail when counter.py breaks.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from counter import Counter


def test_route_shape():
    counter = Counter(retention=2)
    counter.apply(1, 1, "api")
    assert 1 in counter.ticks["api-client"]
    assert 1 in counter.ticks["ip"]
    assert 1 not in counter.ticks["user"]
    counter.apply(2, 2, "human")
    assert 2 in counter.ticks["user"]
    assert 2 in counter.ticks["ip"]
    assert 2 not in counter.ticks["api-client"]


def test_only_routed():
    counter = Counter(retention=2)
    counter.apply(1, 1, "api")
    counter.apply(2, 2, "human")
    assert set(counter.ticks["user"]) == {2}
    assert set(counter.ticks["api-client"]) == {1}
    assert set(counter.ticks["ip"]) == {1, 2}


def test_recorded_agrees():
    counter = Counter(retention=2)
    counter.apply(1, 1, "human")
    for key in counter.ticks:
        assert set(counter.ticks[key]) <= counter.recorded[key]


def test_window_boundary():
    counter = Counter(retention=2)
    counter.advance(4)
    counter.apply(2, 2, "human")
    counter.apply(3, 3, "human")
    assert counter.count("user", 2) == 1
    assert counter.count("user", 1) == 0


def test_expired_not_counted():
    counter = Counter(retention=2)
    counter.advance(4)
    counter.apply(2, 2, "human")
    assert counter.count("user", 1) == 0
    assert counter.count("user", 2) == 0


def test_count_matches():
    counter = Counter(retention=2)
    counter.advance(4)
    for event_id, timestamp in ((1, 1), (2, 2), (3, 3), (4, 4)):
        counter.apply(event_id, timestamp, "human")
    assert counter.count("user", 1) == 1
    assert counter.count("user", 2) == 2
    counter.apply(4, 9, "human")
    assert counter.count("user", 1) == 1
