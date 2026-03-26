"""
Kaasb Load Test — Results Analyzer
=====================================
Parses k6 CSV output and Locust HTML/CSV reports.
Produces a clear pass/fail report against defined thresholds.

Usage:
  # Analyze k6 CSV output:
  python analyze_results.py --type k6 --file reports/baseline.csv --test baseline

  # Analyze Locust CSV:
  python analyze_results.py --type locust --file reports/results_stats.csv --test baseline

  # Compare two runs (regression check):
  python analyze_results.py --type k6 --file reports/current.csv --baseline reports/previous.csv

Requirements:
  pip install pandas tabulate
"""

import argparse
import sys
import os
import json
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("WARNING: pandas not installed. Install with: pip install pandas tabulate")

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# ── Acceptance thresholds (per test type) ────────────────────────────────────
THRESHOLDS = {
    "baseline": {
        "error_rate_pct":  1.0,    # < 1%
        "p50_ms":          500,
        "p95_ms":          2000,
        "p99_ms":          5000,
        "avg_ms":          800,
        "min_rps":         20,     # At least 20 requests/sec throughput
    },
    "stress": {
        "error_rate_pct":  5.0,    # < 5% under stress
        "p95_ms":          5000,
        "p99_ms":          10000,
        "avg_ms":          2000,
        "min_rps":         10,
    },
    "spike": {
        "error_rate_pct":  10.0,   # Up to 10% during spike
        "p95_ms":          10000,
        "p99_ms":          15000,
        "avg_ms":          5000,
        "min_rps":         5,
    },
    "soak": {
        "error_rate_pct":  1.0,    # Strict — must hold 4 hours
        "p95_ms":          2000,
        "p99_ms":          5000,
        "avg_ms":          800,
        "min_rps":         15,
        "max_p95_drift_pct": 20,   # p95 can't degrade > 20% over the test
    },
}

# ── Performance baseline (expected per-endpoint thresholds) ─────────────────
ENDPOINT_THRESHOLDS = {
    "search":          {"p95_ms": 1500, "error_rate_pct": 0.5},
    "job_detail":      {"p95_ms": 500,  "error_rate_pct": 0.1},
    "freelancers":     {"p95_ms": 1500, "error_rate_pct": 0.5},
    "register":        {"p95_ms": 3000, "error_rate_pct": 1.0},  # bcrypt is slow
    "login":           {"p95_ms": 1000, "error_rate_pct": 0.5},
    "me":              {"p95_ms": 200,  "error_rate_pct": 0.1},
    "post_job":        {"p95_ms": 1000, "error_rate_pct": 0.5},
    "health":          {"p95_ms": 100,  "error_rate_pct": 0.0},
    "notifications":   {"p95_ms": 300,  "error_rate_pct": 0.1},
    "my_proposals":    {"p95_ms": 500,  "error_rate_pct": 0.1},
    "contracts":       {"p95_ms": 500,  "error_rate_pct": 0.1},
    "transactions":    {"p95_ms": 800,  "error_rate_pct": 0.1},
}


def _pass_fail(condition: bool) -> str:
    return "✓ PASS" if condition else "✗ FAIL"


class K6Analyzer:
    """Analyzes k6 --out csv output."""

    def __init__(self, csv_path: str):
        if not HAS_PANDAS:
            raise ImportError("pandas required: pip install pandas tabulate")
        self.path = csv_path
        self.df   = pd.read_csv(csv_path)

    def overall_stats(self) -> dict:
        """Compute aggregate statistics across all HTTP requests."""
        http_reqs = self.df[
            (self.df["metric_name"] == "http_req_duration") &
            (self.df["metric_value"].notna())
        ]["metric_value"].astype(float)

        http_failed = self.df[
            self.df["metric_name"] == "http_req_failed"
        ]["metric_value"].astype(float)

        if http_reqs.empty:
            return {}

        return {
            "total_requests":   len(http_reqs),
            "avg_ms":           http_reqs.mean(),
            "p50_ms":           http_reqs.quantile(0.50),
            "p95_ms":           http_reqs.quantile(0.95),
            "p99_ms":           http_reqs.quantile(0.99),
            "max_ms":           http_reqs.max(),
            "min_ms":           http_reqs.min(),
            "error_rate_pct":   http_failed.mean() * 100 if not http_failed.empty else 0,
            "duration_s":       len(self.df) // 10,  # approximate
        }

    def per_endpoint_stats(self) -> list[dict]:
        """Group by endpoint tag and compute per-endpoint stats."""
        # k6 tags are encoded in the "extra_tags" or "tags" column
        results = []

        if "extra_tags" not in self.df.columns:
            return results

        duration_rows = self.df[
            (self.df["metric_name"] == "http_req_duration") &
            (self.df["metric_value"].notna())
        ].copy()

        duration_rows["endpoint"] = duration_rows["extra_tags"].str.extract(r'name:([^,}]+)')

        for endpoint, group in duration_rows.groupby("endpoint"):
            vals = group["metric_value"].astype(float)
            results.append({
                "endpoint":        endpoint,
                "requests":        len(vals),
                "avg_ms":          vals.mean(),
                "p95_ms":          vals.quantile(0.95),
                "p99_ms":          vals.quantile(0.99),
                "max_ms":          vals.max(),
            })

        return sorted(results, key=lambda x: x["p95_ms"], reverse=True)

    def soak_drift_analysis(self) -> dict | None:
        """For soak tests: check if p95 drifted over time."""
        http_rows = self.df[
            (self.df["metric_name"] == "http_req_duration") &
            (self.df["metric_value"].notna())
        ].copy()

        if "timestamp" not in self.df.columns:
            return None

        http_rows["ts"] = pd.to_datetime(http_rows["timestamp"], unit="s")
        http_rows["val"] = http_rows["metric_value"].astype(float)
        http_rows = http_rows.sort_values("ts")

        # Split into 4 quarters
        n = len(http_rows)
        q = n // 4
        if q == 0:
            return None

        quarters = {
            "Q1 (first 25%)":  http_rows.iloc[:q]["val"].quantile(0.95),
            "Q2 (25-50%)":     http_rows.iloc[q:q*2]["val"].quantile(0.95),
            "Q3 (50-75%)":     http_rows.iloc[q*2:q*3]["val"].quantile(0.95),
            "Q4 (last 25%)":   http_rows.iloc[q*3:]["val"].quantile(0.95),
        }

        first_p95 = list(quarters.values())[0]
        last_p95  = list(quarters.values())[-1]
        drift_pct = ((last_p95 - first_p95) / first_p95 * 100) if first_p95 > 0 else 0

        return {"quarters": quarters, "drift_pct": drift_pct, "first_p95": first_p95, "last_p95": last_p95}


class LocustAnalyzer:
    """Analyzes Locust --csv output (*_stats.csv)."""

    def __init__(self, stats_csv: str):
        if not HAS_PANDAS:
            raise ImportError("pandas required: pip install pandas")
        self.path = stats_csv
        self.df   = pd.read_csv(stats_csv)

    def overall_stats(self) -> dict:
        agg = self.df[self.df["Name"] == "Aggregated"]
        if agg.empty:
            agg = self.df.iloc[-1:]

        row = agg.iloc[0]
        total = row.get("Request Count", 0)
        fails = row.get("Failure Count", 0)

        return {
            "total_requests":  int(total),
            "failures":        int(fails),
            "error_rate_pct":  (fails / total * 100) if total > 0 else 0,
            "avg_ms":          float(row.get("Average Response Time", 0)),
            "p50_ms":          float(row.get("50%", 0)),
            "p95_ms":          float(row.get("95%", 0)),
            "p99_ms":          float(row.get("99%", 0)),
            "max_ms":          float(row.get("Max Response Time", 0)),
            "rps":             float(row.get("Requests/s", 0)),
        }

    def per_endpoint_stats(self) -> list[dict]:
        rows = self.df[self.df["Name"] != "Aggregated"]
        results = []
        for _, row in rows.iterrows():
            total = row.get("Request Count", 0)
            fails = row.get("Failure Count", 0)
            results.append({
                "endpoint":       row.get("Name", "unknown"),
                "requests":       int(total),
                "error_rate_pct": (fails / total * 100) if total > 0 else 0,
                "avg_ms":         float(row.get("Average Response Time", 0)),
                "p95_ms":         float(row.get("95%", 0)),
                "p99_ms":         float(row.get("99%", 0)),
                "max_ms":         float(row.get("Max Response Time", 0)),
                "rps":            float(row.get("Requests/s", 0)),
            })
        return sorted(results, key=lambda x: x["p95_ms"], reverse=True)


def check_thresholds(stats: dict, test_type: str) -> tuple[bool, list[str]]:
    """Returns (passed, list_of_violations)."""
    t = THRESHOLDS.get(test_type, THRESHOLDS["baseline"])
    violations = []

    checks = [
        ("error_rate_pct", stats.get("error_rate_pct", 0), t.get("error_rate_pct", 1.0), "<="),
        ("p95_ms",         stats.get("p95_ms", 0),         t.get("p95_ms", 2000),         "<="),
        ("p99_ms",         stats.get("p99_ms", 0),         t.get("p99_ms", 5000),         "<="),
        ("avg_ms",         stats.get("avg_ms", 0),         t.get("avg_ms", 800),          "<="),
    ]

    for metric, actual, threshold, op in checks:
        if op == "<=" and actual > threshold:
            violations.append(
                f"{metric} = {actual:.1f} exceeds threshold {threshold}"
            )

    return len(violations) == 0, violations


def print_report(stats: dict, per_endpoint: list[dict], test_type: str,
                 drift: dict | None = None):
    """Print a formatted pass/fail report."""
    passed, violations = check_thresholds(stats, test_type)

    print("\n" + "=" * 70)
    print(f"  KAASB LOAD TEST REPORT — {test_type.upper()}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Overall stats
    rows = [
        ["Total Requests",      f"{stats.get('total_requests', 0):,}"],
        ["Error Rate",          f"{stats.get('error_rate_pct', 0):.2f}%"],
        ["Avg Response Time",   f"{stats.get('avg_ms', 0):.0f}ms"],
        ["p50 Response Time",   f"{stats.get('p50_ms', 0):.0f}ms"],
        ["p95 Response Time",   f"{stats.get('p95_ms', 0):.0f}ms"],
        ["p99 Response Time",   f"{stats.get('p99_ms', 0):.0f}ms"],
        ["Max Response Time",   f"{stats.get('max_ms', 0):.0f}ms"],
        ["Throughput (RPS)",    f"{stats.get('rps', stats.get('min_rps', 0)):.1f}"],
    ]

    if HAS_TABULATE:
        print(tabulate(rows, headers=["Metric", "Value"], tablefmt="simple"))
    else:
        for r in rows:
            print(f"  {r[0]:<25} {r[1]}")

    # Threshold check
    t = THRESHOLDS.get(test_type, THRESHOLDS["baseline"])
    print(f"\n  Threshold Checks ({test_type}):")
    print(f"  {'Error rate':25} {stats.get('error_rate_pct', 0):.2f}% ≤ {t.get('error_rate_pct')}%  "
          f"  {_pass_fail(stats.get('error_rate_pct', 0) <= t.get('error_rate_pct', 1))}")
    print(f"  {'p95':25} {stats.get('p95_ms', 0):.0f}ms ≤ {t.get('p95_ms')}ms  "
          f"  {_pass_fail(stats.get('p95_ms', 0) <= t.get('p95_ms', 2000))}")
    print(f"  {'p99':25} {stats.get('p99_ms', 0):.0f}ms ≤ {t.get('p99_ms')}ms  "
          f"  {_pass_fail(stats.get('p99_ms', 0) <= t.get('p99_ms', 5000))}")

    # Soak drift
    if drift:
        print(f"\n  Soak Test p95 Drift Analysis:")
        for period, val in drift["quarters"].items():
            print(f"    {period}: {val:.0f}ms")
        drift_ok = abs(drift["drift_pct"]) <= t.get("max_p95_drift_pct", 20)
        print(f"  p95 drift: {drift['drift_pct']:+.1f}%  "
              f"{_pass_fail(drift_ok)} (threshold: ±{t.get('max_p95_drift_pct', 20)}%)")

    # Per-endpoint breakdown
    if per_endpoint:
        print(f"\n  Per-Endpoint Results (sorted by p95, slowest first):")
        ep_rows = []
        for ep in per_endpoint[:20]:
            name = ep["endpoint"]
            ep_t = ENDPOINT_THRESHOLDS.get(name, None)
            p95_ok = (ep["p95_ms"] <= ep_t["p95_ms"]) if ep_t else True
            err_ok = (ep.get("error_rate_pct", 0) <= ep_t["error_rate_pct"]) if ep_t else True
            status = _pass_fail(p95_ok and err_ok)
            ep_rows.append([
                name[:40],
                ep["requests"],
                f"{ep.get('error_rate_pct', 0):.1f}%",
                f"{ep.get('avg_ms', 0):.0f}",
                f"{ep['p95_ms']:.0f}",
                f"{ep['p99_ms']:.0f}",
                status,
            ])

        if HAS_TABULATE:
            print(tabulate(ep_rows,
                headers=["Endpoint", "Reqs", "Err%", "Avg(ms)", "p95(ms)", "p99(ms)", "Status"],
                tablefmt="simple"))
        else:
            for r in ep_rows:
                print(f"  {r[0]:<42} {r[1]:>6} {r[2]:>6} {r[3]:>8} {r[4]:>8} {r[5]:>8}  {r[6]}")

    # Final verdict
    print("\n" + "=" * 70)
    if passed:
        print(f"  OVERALL RESULT: ✓ PASSED — All thresholds met for {test_type}")
    else:
        print(f"  OVERALL RESULT: ✗ FAILED — {len(violations)} violation(s):")
        for v in violations:
            print(f"    ✗ {v}")

    # Recommendations
    if violations:
        print("\n  Recommendations:")
        if stats.get("p95_ms", 0) > 2000:
            print("    - p95 high: Check slow DB queries (pg_stat_statements)")
            print("      Run: scripts/db-monitoring.sql section 2 (slow queries)")
        if stats.get("error_rate_pct", 0) > 1:
            print("    - Errors: Check backend logs: ./deploy.sh --logs backend")
            print("      Likely: DB pool exhaustion or rate limiting")
        if stats.get("avg_ms", 0) > 1000:
            print("    - High avg latency: Consider increasing WEB_CONCURRENCY")
            print("      Or enable Redis caching for search results")
    print("=" * 70 + "\n")

    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description="Kaasb load test results analyzer")
    parser.add_argument("--type",     choices=["k6", "locust"], required=True)
    parser.add_argument("--file",     required=True, help="Path to CSV results file")
    parser.add_argument("--test",     choices=list(THRESHOLDS.keys()), default="baseline")
    parser.add_argument("--baseline", help="Previous run CSV for regression comparison")
    parser.add_argument("--output",   help="Save JSON report to file")
    args = parser.parse_args()

    if not HAS_PANDAS:
        print("ERROR: pandas required. Run: pip install pandas tabulate")
        sys.exit(1)

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    # Load and analyze
    if args.type == "k6":
        analyzer    = K6Analyzer(args.file)
        stats       = analyzer.overall_stats()
        per_ep      = analyzer.per_endpoint_stats()
        drift       = analyzer.soak_drift_analysis() if args.test == "soak" else None
    else:
        analyzer    = LocustAnalyzer(args.file)
        stats       = analyzer.overall_stats()
        per_ep      = analyzer.per_endpoint_stats()
        drift       = None

    if not stats:
        print("ERROR: No data found in the CSV file.")
        sys.exit(1)

    exit_code = print_report(stats, per_ep, args.test, drift)

    # Save JSON report
    if args.output:
        report = {
            "test_type":    args.test,
            "analyzer":     args.type,
            "file":         args.file,
            "timestamp":    datetime.now().isoformat(),
            "overall":      stats,
            "per_endpoint": per_ep,
            "passed":       exit_code == 0,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to: {args.output}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
