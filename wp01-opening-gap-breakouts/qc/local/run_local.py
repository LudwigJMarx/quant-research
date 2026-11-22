"""Run qc/variants/main.py or qc/test_sample/main.py locally on a CSV of minute bars.

The CSV needs the columns tag,min,open,high,low,close,volume: tag is the trading day (YYYY-MM-DD,
New York time), min is the minute of the day of the bar start (9:30 = 570), one row per regular-session
minute (570 to 959), sorted by day and minute. The log lines the algorithm writes on QuantConnect are
written to the output file instead.

Usage:
    python3 -I run_local.py <algorithm_dir> <bars.csv> <output.txt> [--start YYYY-MM-DD]

--start overrides the first day of the evaluated sample (ENTW in the algorithm). Days before it are
used only as warm-up for the 14-day volume and ATR averages. Without it the algorithm's own value applies.
"""
import argparse
import csv
import importlib.util
import sys
from datetime import date
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("algorithm_dir")
    ap.add_argument("csv")
    ap.add_argument("output")
    ap.add_argument("--start")
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))        # AlgorithmImports stand-in
    spec = importlib.util.spec_from_file_location("algo", Path(a.algorithm_dir) / "main.py")
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    if a.start:
        M.ENTW = date.fromisoformat(a.start)
    cls = [c for c in vars(M).values() if isinstance(c, type) and issubclass(c, M.QCAlgorithm) and c is not M.QCAlgorithm]
    if len(cls) != 1:
        sys.exit(f"expected one algorithm class in {a.algorithm_dir}, found {len(cls)}")
    alg = cls[0].__new__(cls[0])
    lines = []
    alg.log = lines.append
    alg.set_runtime_statistic = lambda k, v: lines.append(f"STAT {k} {v}")
    alg.init_zustand()
    n_rows = 0
    with open(a.csv, newline="") as f:
        for row in csv.DictReader(f):
            d = date.fromisoformat(row["tag"])
            if alg.tag is not None and d != alg.tag:
                alg.tag_auswerten()
                alg.bars = []
            alg.tag = d
            alg.bars.append((int(row["min"]), float(row["open"]), float(row["high"]), float(row["low"]),
                             float(row["close"]), float(row["volume"])))
            n_rows += 1
    if n_rows == 0:
        sys.exit("no rows in " + a.csv)
    alg.on_end_of_algorithm()
    Path(a.output).write_text("\n".join(lines) + "\n")
    print(f"{n_rows} bars read, {len(alg.tage)} days evaluated, {len(lines)} lines written to {a.output}")


if __name__ == "__main__":
    main()
