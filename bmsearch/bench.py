"""Benchmark harness.  Usage:
    python -m bmsearch.bench                # full suite, tables to stdout
    python -m bmsearch.bench --quick        # small sizes
    python -m bmsearch.bench --csv out.csv  # also write raw results
    python -m bmsearch.bench --algos naive horspool BM-full
"""
import argparse
import csv
import random
import time

from .algorithms import ALGORITHMS
from .datasets import TEXT_GENERATORS, adversarial, sample_patterns


def run_case(text, pat, algos, reps):
    ref = None
    row = {}
    for name in algos:
        f, best = ALGORITHMS[name], float("inf")
        for _ in range(reps):
            t0 = time.perf_counter()
            res = f(text, pat)
            best = min(best, time.perf_counter() - t0)
        if ref is None:
            ref = res.matches
        assert res.matches == ref, f"{name} disagrees with {algos[0]}"
        row[name] = (res.comparisons / len(text), best * 1000, len(res.matches))
    return row


def print_table(title, n, rows, algos):
    print(f"\n== {title} (n={n}) ==   cells: cmp/char  ms")
    print(f"{'m':>4} {'hits':>6} | " + " | ".join(f"{a:>14}" for a in algos))
    for m, row in rows:
        hits = next(iter(row.values()))[2]
        print(f"{m:>4} {hits:>6} | " + " | ".join(
            f"{row[a][0]:>6.3f} {row[a][1]:>7.1f}" for a in algos))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--csv")
    ap.add_argument("--algos", nargs="+", default=["naive", "horspool", "BM-bc",
                    "BM-gs", "BM-full", "BM-full-ext", "BM-galil"])
    a = ap.parse_args()
    n = a.n or (20_000 if a.quick else 200_000)
    lengths = [2, 4, 8, 16, 32, 64] if not a.quick else [4, 16, 64]
    rnd = random.Random(a.seed)
    log = []

    def record(scenario, m, row):
        for alg, (cpc, ms, hits) in row.items():
            log.append(dict(scenario=scenario, m=m, algo=alg, cmp_per_char=cpc, ms=ms, hits=hits))

    for name, gen in TEXT_GENERATORS.items():
        text = gen(n, rnd)
        rows = []
        for pat in sample_patterns(text, lengths, rnd):
            row = run_case(text, pat, a.algos, a.reps)
            rows.append((len(pat), row)); record(name, len(pat), row)
        print_table(f"{name} text", len(text), rows, a.algos)

    an = n // 4  # adversarial cases are O(nm) for non-Galil variants
    for m in ([8, 32] if not a.quick else [8]):
        for name, (t, p) in adversarial(an, m).items():
            row = run_case(t, p, a.algos, 1)
            print_table(f"adversarial: {name}", len(t), [(len(p), row)], a.algos)
            record("adv:" + name, len(p), row)

    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=log[0].keys()); w.writeheader(); w.writerows(log)
        print(f"\nwrote {len(log)} rows to {a.csv}")


if __name__ == "__main__":
    main()
