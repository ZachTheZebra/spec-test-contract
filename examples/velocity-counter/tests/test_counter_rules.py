"""Python restatement of the VelocityCounter safety rules.

Each test is named in spec_coverage.yaml. The predicates match the TLA+
invariants in VelocityCounter.tla. A production repo points the same
contract at the tests that exercise the real counter.
"""

EVENT_IDS = {1, 2}
MAX_EVENTS = 2
RETENTION = 2
MAX_NOW = 4
KEYS = ("user", "ip", "api-client")
NONE = 0


def route(population):
    if population == "api":
        return {"api-client", "ip"}
    if population == "human":
        return {"user", "ip"}
    raise ValueError(population)


def in_window(event, now, window):
    return (now - window) < event <= now


def expired(event, now, retention=RETENTION):
    return event <= now - retention


def count(ticks, now, window):
    return sum(1 for event in ticks if in_window(event, now, window))


def type_ok(state):
    population = state["population"]
    if set(population) != EVENT_IDS:
        return False
    if any(population[event] not in {"human", "api"} for event in EVENT_IDS):
        return False
    now = state["now"]
    if not (MAX_EVENTS <= now <= MAX_NOW):
        return False
    for field in ("ticks", "recorded"):
        store = state[field]
        if set(store) != set(KEYS):
            return False
        for key in KEYS:
            if not set(store[key]) <= EVENT_IDS:
                return False
    inflight = state["inflight"]
    todo = state["todo"]
    if inflight != NONE and inflight not in EVENT_IDS:
        return False
    if not set(todo) <= set(KEYS):
        return False
    if inflight == NONE:
        return todo == set()
    return set(todo) <= route(population[inflight])


def valid_state():
    return {
        "population": {1: "human", 2: "api"},
        "now": 2,
        "ticks": {"user": set(), "ip": set(), "api-client": set()},
        "recorded": {"user": set(), "ip": set(), "api-client": set()},
        "inflight": NONE,
        "todo": set(),
    }


def test_type_ok():
    state = valid_state()
    assert type_ok(state), "initial state"
    state["todo"] = {"user"}
    assert not type_ok(state), "idle delivery must have an empty todo"
    state = valid_state()
    state["now"] = 1
    assert not type_ok(state), "now starts at MaxEvents"
    state = valid_state()
    state["inflight"] = 2
    state["todo"] = {"user"}
    assert not type_ok(state), "api inflight cannot name the user key"
    state["todo"] = {"api-client", "ip"}
    assert type_ok(state), "api inflight names its route"


def test_route_shape():
    for population in ("human", "api"):
        chosen = route(population)
        assert "ip" in chosen
        assert len(chosen) == 2
    assert route("api") == {"api-client", "ip"}
    assert "user" not in route("api")
    assert route("human") == {"user", "ip"}
    assert "api-client" not in route("human")


def test_only_routed():
    population = {1: "api", 2: "human"}
    stored = {
        "user": {2},
        "ip": {1, 2},
        "api-client": {1},
    }
    for key in KEYS:
        for event in stored[key]:
            assert key in route(population[event])
    assert "user" not in route(population[1])


def test_recorded_agrees():
    ticks = {"user": {1}, "ip": set(), "api-client": set()}
    recorded = {"user": {1, 2}, "ip": set(), "api-client": set()}
    for key in KEYS:
        assert ticks[key] <= recorded[key]
    assert not ({1} <= set())


def test_window_boundary():
    now = 4
    for event in EVENT_IDS | {3, 4}:
        if event <= now - RETENTION:
            for window in range(1, RETENTION + 1):
                assert not in_window(event, now, window)
        if event == now - RETENTION + 1:
            assert in_window(event, now, RETENTION)
    assert not in_window(2, 4, 1)
    assert not in_window(2, 4, 2)
    assert in_window(3, 4, 2)


def test_expired_not_counted():
    now = 4
    for event in range(0, 6):
        if expired(event, now):
            for window in range(1, RETENTION + 1):
                assert not in_window(event, now, window)


def test_count_matches():
    now = 4
    ticks = {1, 2, 3, 4}
    assert count(ticks, now, 1) == 1
    assert count(ticks, now, 2) == 2
    assert count(set(), now, 2) == 0
