#!/usr/bin/env python3
"""Checks that the published result files hold no price data and have the expected size.

The price data behind this research are licensed. Result files may hold dates, directions, returns,
R multiples, slippage in index points, exposure ratios, account equity and summary statistics, but no
price levels. This check reads the header of every CSV under */results/ and fails on any column that
is not on the allow list, so a new column must be added here on purpose. It also checks the row counts
the README promises, and it names every file it read: "0 problems" from a check that read nothing
would look the same as a clean result.

Usage: python3 scripts/check_results.py [--root PATH]
Exit:  0 ok, 1 finding, 2 nothing to check
"""
import argparse
import csv
import sys
from pathlib import Path

ERLAUBT = {
    "tag", "dir", "rmult", "ret", "stop_pct", "art", "ein_min", "aus_min", "pnl",      # research model trades
    "name", "sr_r",                                                                    # research model Sharpe ratios
    "rm_q", "rm_q_ohne_schlupf", "schlupf_ein_pkt", "schlupf_stop_pkt", "ausstieg",    # QuantConnect trades
    "equity", "hebel",                                                                 # account equity, exposure
}
ZEILEN = {   # file -> number of non-empty lines (CSV files: header included)
    "wp01-opening-gap-breakouts/results/qc_variants/var_qc.txt": 51,
    "wp01-opening-gap-breakouts/results/qc_variants/q1_qc.txt": 24,
    "wp01-opening-gap-breakouts/results/qc_variants/daily_v51.txt": 1732,
    "wp01-opening-gap-breakouts/results/qc_test_sample/daily_v51_2015_2019.txt": 1258,
    "wp01-opening-gap-breakouts/results/research_model/variants_r.csv": 52,
    "wp01-opening-gap-breakouts/results/qc_mnq/trades_v4.csv": 650,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=Path(__file__).resolve().parents[1])
    root = Path(ap.parse_args().root)
    befunde, gelesen = [], 0
    for f in sorted(root.glob("*/results/**/*.csv")):
        gelesen += 1
        with open(f, newline="") as h:
            kopf = next(csv.reader(h), [])
        fremd = [k for k in kopf if k not in ERLAUBT]
        if fremd:
            befunde.append(f"{f.relative_to(root)}: columns not on the allow list: {', '.join(fremd)}")
    for rel, n in ZEILEN.items():
        f = root / rel
        if not f.exists():
            befunde.append(f"{rel}: missing")
            continue
        m = sum(1 for z in f.read_text().splitlines() if z.strip())
        if m != n:
            befunde.append(f"{rel}: {m} lines, expected {n}")
    if gelesen == 0:
        print("no CSV files found under */results/: nothing checked")
        return 2
    print(f"{gelesen} CSV files and {len(ZEILEN)} row counts checked, {len(befunde)} findings")
    for b in befunde:
        print("  " + b)
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
