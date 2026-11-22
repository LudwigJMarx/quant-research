"""Tests for the QuantConnect variant program (qc/variants/main.py) and the local runner.

The hand-computed cases mirror R/test_bt.R and R/test_stop.R, so the Python port and the R research
model are checked against the same numbers. The last test runs the program end to end through
qc/local/run_local.py on synthetic minute bars, so the wiring of the output is tested as well.
Run from the folder wp01-opening-gap-breakouts: python3 -m pytest tests
"""
import csv
import importlib.util
import runpy
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

ORDNER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ORDNER / "qc" / "local"))           # AlgorithmImports stand-in
_spec = importlib.util.spec_from_file_location("variants", ORDNER / "qc" / "variants" / "main.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def flach():
    """Flat day 9:30-15:59 at 100, opening range (first 5 minutes) 99..101."""
    mi = np.arange(570, 960)
    x = {"min": mi, "open": np.full(len(mi), 100.0), "high": np.full(len(mi), 100.2),
         "low": np.full(len(mi), 99.8), "close": np.full(len(mi), 100.0)}
    x["high"][mi < 575] = 101
    x["low"][mi < 575] = 99
    return x


def setze(x, maske, **werte):
    for k, v in werte.items():
        x[k][maske] = v


def test_long_held_to_close():
    x = flach(); mi = x["min"]
    setze(x, mi == 580, high=101.5)
    setze(x, mi >= 600, open=103, high=103, low=102.9, close=103)
    ret, stop_pct, rm, ein, fill, r = V.trade_long(x, 5, "stop", "gegen", False)
    assert (ein, fill, r) == (580, 101, 2)
    assert rm == pytest.approx(1.0)


def test_stop_at_opposite_edge_and_gap_through_stop():
    x = flach(); mi = x["min"]
    setze(x, mi == 580, high=101.5)
    setze(x, mi == 600, low=98.5)
    assert V.trade_long(x, 5, "stop", "gegen", False)[2] == pytest.approx(-1.0)
    x = flach(); mi = x["min"]
    setze(x, mi == 580, high=101.5)
    setze(x, mi == 600, open=98, low=97.5)
    assert V.trade_long(x, 5, "stop", "gegen", False)[2] == pytest.approx((98 - 101) / 2)


def test_break_even_after_one_r():
    x = flach(); mi = x["min"]
    setze(x, mi == 580, high=101.5)
    setze(x, mi > 580, open=102, close=102, high=102.2, low=101.8)
    setze(x, mi == 590, high=103.5)
    setze(x, mi == 600, low=100.8)
    assert V.trade_long(x, 5, "stop", "gegen", True)[2] == pytest.approx(0.0)
    assert V.trade_long(x, 5, "stop", "gegen", False)[2] > 0


def test_short_via_mirror_and_no_entry_after_1130():
    x = flach(); mi = x["min"]
    setze(x, mi == 580, low=98.5)
    setze(x, mi >= 600, open=97, high=97.1, low=97, close=97)
    assert V.trade_long(V.spiegeln(x), 5, "stop", "gegen", False)[2] == pytest.approx(1.0)
    x = flach(); mi = x["min"]
    setze(x, mi == 700, high=102)
    assert V.trade_long(x, 5, "stop", "gegen", False) is None


def test_entry_after_five_minute_close():
    x = flach(); mi = x["min"]
    setze(x, mi == 584, high=101.6, close=101.5)
    setze(x, mi == 585, open=101.4)
    t = V.trade_long(x, 5, "schluss5", "gegen", False)
    assert (t[3], t[4]) == (585, 101.4)


def stop_tag():
    """Breakout 9:40 at 101, rise to 105 by 10:30, fall to 102.5 at 11:00 (as in R/test_stop.R)."""
    mi = np.arange(570, 960)
    px = np.full(len(mi), 100.0)
    px[mi >= 580] = 101
    steig = (mi >= 581) & (mi <= 630)
    px[steig] = np.linspace(101, 105, steig.sum())
    px[(mi > 630) & (mi < 660)] = 105
    px[mi >= 660] = 102.5
    x = {"min": mi, "open": px.copy(), "high": px + 0.05, "low": px - 0.05, "close": px.copy()}
    x["high"][mi < 575] = 101
    x["low"][mi < 575] = 99
    x["high"][mi == 580] = 101.2
    return x


def test_stop_rules():
    x = stop_tag()
    assert V.trade_stop(x, "S1", "T0", 0.01)[2] == pytest.approx(0.75)
    assert V.trade_stop(x, "S1", "T1", 0.01)[2] == pytest.approx(0.75)
    assert V.trade_stop(x, "S1", "T2", 0.01)[2] == pytest.approx((102.5 - 101) / 2)
    assert V.trade_stop(x, "S2", "T0", 0.01)[1] == pytest.approx(0.0015)


def test_unpublished_stop_rule_is_not_accepted_as_a_trail():
    # A trail name the program does not know must behave like no trail, never like a hidden rule.
    x = stop_tag()
    assert V.trade_stop(x, "S1", "T3", 0.01) == V.trade_stop(x, "S1", "T0", 0.01)
    assert ("S1", "T3") not in V.STOPS and ("S2", "T3") not in V.STOPS


def synthetisch(pfad, n_tage=60, seed=3):
    rng = np.random.default_rng(seed)
    tag, px = date(2020, 1, 2), 100.0
    with open(pfad, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "min", "open", "high", "low", "close", "volume"])
        for _ in range(n_tage):
            while tag.weekday() >= 5:
                tag += timedelta(days=1)
            px *= 1 + rng.normal(0, 0.005)
            for m in range(570, 960):
                o = px
                px *= 1 + rng.normal(0, 0.0008)
                w.writerow([tag.isoformat(), m, round(o, 4), round(max(o, px) * 1.0002, 4),
                            round(min(o, px) * 0.9998, 4), round(px, 4), int(rng.integers(1e4, 1e5))])
            tag += timedelta(days=1)


@pytest.mark.parametrize("prozess", [False, True])
def test_local_run_end_to_end(tmp_path, monkeypatch, prozess):
    # once in this process (counted by the coverage measurement), once as the documented command
    synthetisch(tmp_path / "bars.csv")
    aus = tmp_path / "out.txt"
    arg = [str(ORDNER / "qc" / "local" / "run_local.py"), str(ORDNER / "qc" / "variants"), str(tmp_path / "bars.csv"), str(aus)]
    if prozess:
        subprocess.run([sys.executable, "-I"] + arg, check=True, capture_output=True)
    else:
        monkeypatch.setattr(sys, "argv", arg)
        runpy.run_path(arg[0], run_name="__main__")
    z = aus.read_text().splitlines()
    var = [l.split()[1] for l in z if l.startswith("VAR ")]
    assert len(var) == 49 and "V51_relvol4" in var and not any(v.endswith("_T3") for v in var)
    assert sum(l.startswith("DSR V51 ") for l in z) == 1
    assert sum(l.startswith("Q1 ") for l in z) == 24
    assert sum(l.startswith("TAG ") for l in z) == 59          # first day has no prior close
