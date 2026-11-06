"""In-memory counter the example tests call.

The rules live in VelocityCounter.tla. This module is the stand-in for an
implementation. A test fails when this module stops doing what it claims.
"""

KEYS = ("user", "ip", "api-client")


class Counter:
    def __init__(self, retention):
        self.retention = retention
        self.now = 0
        self.ticks = {key: {} for key in KEYS}
        self.recorded = {key: set() for key in KEYS}

    def route(self, population):
        if population == "api":
            return ("api-client", "ip")
        if population == "human":
            return ("user", "ip")
        raise ValueError(population)

    def apply(self, event_id, timestamp, population):
        for key in self.route(population):
            self.recorded[key].add(event_id)
            self.ticks[key].setdefault(event_id, timestamp)

    def advance(self, now):
        self.now = now

    def count(self, key, window):
        return sum(
            1
            for timestamp in self.ticks[key].values()
            if self.now - window < timestamp <= self.now
        )
