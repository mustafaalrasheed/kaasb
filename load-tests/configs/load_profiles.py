"""
Kaasb Load Test Profiles
=========================
Defines load profiles for each test type.
Import this in Locust for consistent configuration across runs.

Iraqi traffic patterns:
  - Peak hours: 19:00–23:00 Baghdad time (UTC+3) Thursday/Friday
  - Weekend: Thursday evening is highest traffic
  - Off-peak: 08:00–12:00 is lowest traffic
  - Average daily users: ~500 active sessions
  - Peak concurrent users: ~150–200
  - Normal concurrent users: ~30–50
"""

from dataclasses import dataclass, field


@dataclass
class LoadProfile:
    name:             str
    description:      str
    target_users:     int        # Peak concurrent virtual users
    spawn_rate:       int        # Users spawned per second
    duration_minutes: int
    stages:           list       = field(default_factory=list)

    # Acceptance thresholds
    max_error_rate_pct:  float = 1.0
    max_p95_ms:          int   = 2000
    max_p99_ms:          int   = 5000
    max_avg_ms:          int   = 800

    def to_locust_args(self) -> list[str]:
        return [
            f"--users={self.target_users}",
            f"--spawn-rate={self.spawn_rate}",
            f"--run-time={self.duration_minutes}m",
        ]


# ── Test profiles ─────────────────────────────────────────────────────────────

PROFILES = {

    "smoke": LoadProfile(
        name             = "smoke",
        description      = "Quick sanity check — 2 users, 2 minutes. Run after every deploy.",
        target_users     = 2,
        spawn_rate       = 1,
        duration_minutes = 2,
        max_error_rate_pct = 0.0,   # Zero tolerance in smoke test
        max_p95_ms       = 2000,
        max_p99_ms       = 5000,
    ),

    "baseline": LoadProfile(
        name             = "baseline",
        description      = "Normal Iraqi daily load: ~50 concurrent users, 30 minutes.",
        target_users     = 50,
        spawn_rate       = 5,
        duration_minutes = 30,
        stages = [
            {"duration": "5m",  "target": 50},   # ramp up
            {"duration": "20m", "target": 50},   # hold
            {"duration": "5m",  "target": 0},    # ramp down
        ],
        max_error_rate_pct = 1.0,
        max_p95_ms         = 2000,
        max_p99_ms         = 5000,
        max_avg_ms         = 800,
    ),

    "stress": LoadProfile(
        name             = "stress",
        description      = "3× normal load. Finds performance degradation point.",
        target_users     = 150,
        spawn_rate       = 10,
        duration_minutes = 35,
        stages = [
            {"duration": "2m",  "target": 50},   # 1× baseline
            {"duration": "5m",  "target": 100},  # 2× stress
            {"duration": "5m",  "target": 150},  # 3× stress
            {"duration": "5m",  "target": 200},  # 4× — find breaking point
            {"duration": "5m",  "target": 100},  # recovery
            {"duration": "3m",  "target": 0},    # cooldown
        ],
        max_error_rate_pct = 5.0,    # Allow up to 5% under stress
        max_p95_ms         = 5000,
        max_p99_ms         = 10000,
        max_avg_ms         = 2000,
    ),

    "spike": LoadProfile(
        name             = "spike",
        description      = "10× sudden spike for 2 min. Tests recovery time.",
        target_users     = 500,
        spawn_rate       = 100,      # Very fast ramp
        duration_minutes = 12,
        stages = [
            {"duration": "2m",  "target": 50},   # baseline
            {"duration": "30s", "target": 500},  # SPIKE — 10× in 30s
            {"duration": "2m",  "target": 500},  # hold spike
            {"duration": "1m",  "target": 50},   # drop
            {"duration": "3m",  "target": 50},   # recovery observation
            {"duration": "1m",  "target": 0},    # cooldown
        ],
        max_error_rate_pct = 10.0,   # Up to 10% during spike is acceptable
        max_p95_ms         = 10000,
        max_p99_ms         = 15000,
        max_avg_ms         = 5000,
    ),

    "soak": LoadProfile(
        name             = "soak",
        description      = "4-hour sustained load. Detects memory leaks + connection exhaustion.",
        target_users     = 30,
        spawn_rate       = 3,
        duration_minutes = 240,      # 4 hours
        stages = [
            {"duration": "5m",  "target": 30},
            {"duration": "230m", "target": 30},  # 3h50m hold
            {"duration": "5m",  "target": 0},
        ],
        max_error_rate_pct = 1.0,    # STRICT — must hold all 4 hours
        max_p95_ms         = 2000,
        max_p99_ms         = 5000,
        max_avg_ms         = 800,
    ),

    "breakpoint": LoadProfile(
        name             = "breakpoint",
        description      = "Ramp until system breaks. Documents breaking point VU count.",
        target_users     = 1000,     # Upper bound — system will break before this
        spawn_rate       = 10,
        duration_minutes = 40,
        stages = [
            {"duration": "2m", "target": 10},
            {"duration": "2m", "target": 20},
            {"duration": "2m", "target": 40},
            {"duration": "2m", "target": 80},
            {"duration": "2m", "target": 120},
            {"duration": "2m", "target": 160},
            {"duration": "2m", "target": 200},
            {"duration": "2m", "target": 300},
            {"duration": "2m", "target": 400},
            {"duration": "2m", "target": 500},
            {"duration": "5m", "target": 50},   # recovery
            {"duration": "3m", "target": 0},
        ],
        max_error_rate_pct = 100.0,  # No threshold — documenting, not passing
        max_p95_ms         = 999999,
    ),

    "peak_iraqi": LoadProfile(
        name             = "peak_iraqi",
        description      = "Thursday 7-9PM Baghdad peak simulation: 120 concurrent users.",
        target_users     = 120,
        spawn_rate       = 15,
        duration_minutes = 25,
        stages = [
            {"duration": "5m",  "target": 50},   # 7:00 PM — building up
            {"duration": "5m",  "target": 120},  # 7:30 PM — peak hits
            {"duration": "10m", "target": 120},  # 8:00-9:00 PM — sustained peak
            {"duration": "5m",  "target": 30},   # 9:00 PM — winding down
        ],
        max_error_rate_pct = 2.0,
        max_p95_ms         = 3000,
        max_p99_ms         = 7000,
        max_avg_ms         = 1000,
    ),
}


def get_profile(name: str) -> LoadProfile:
    if name not in PROFILES:
        raise ValueError(f"Unknown profile: {name}. Available: {list(PROFILES.keys())}")
    return PROFILES[name]


if __name__ == "__main__":
    print("Available load profiles:\n")
    for name, p in PROFILES.items():
        print(f"  {name:<15} — {p.description}")
        print(f"              {'Users':10}: {p.target_users}")
        print(f"              {'Duration':10}: {p.duration_minutes}m")
        print(f"              {'p95 SLA':10}: {p.max_p95_ms}ms")
        print(f"              {'Error SLA':10}: {p.max_error_rate_pct}%")
        print()
