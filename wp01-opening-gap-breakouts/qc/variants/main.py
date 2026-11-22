# Working Paper No. 01: all registered variants on QuantConnect's QQQ minute bars, side by side, at the
# trigger price. Output as log lines with a prefix:
#   VAR  one line per variant: Sharpe, CAGR, max drawdown, trades, mean R, median R, hit rate,
#        rank against 1,000 random-direction runs, 95% quantile of the random runs, Sharpe of "first break"
#   DSR  deflated Sharpe ratio of the candidate V51 over all 51 registered variants
#   Q1   mean daily result of the 24 base variants by fifth of days, sorted by the day's range / ATR
#   MERK day features: mean daily result (bp) of two reference rules by feature level
#   TAG  daily return series of the candidate V51
# The same code runs locally on any minute-bar CSV (qc/local/run_local.py).
#
# Two of the 51 registered variants (S_S1_T3 and S_S2_T3) use an unpublished in-house smoothed line
# and are not part of this code. Their results are in results/qc_variants/var_qc.txt. To keep the
# published output identical, the program consumes the random numbers of these two variants without
# using them, and the DSR uses their Sharpe ratios from the QuantConnect run (UNPUBLISHED_SR).
#
# Identifiers are German. Glossary: tag = day, luecke = gap, kerze = candle, spanne = range,
# einstieg = entry, schluss = close, gegen = opposite edge, mitte = middle of the range,
# richtung = direction, erster = first break of either side, zufall = random, rang = rank.
from AlgorithmImports import *
from collections import deque
import numpy as np
import math

START, LETZTER_EIN, SCHLUSS = 570, 690, 955
KOSTEN, RISIKO, MAX_HEBEL = 1e-4, 0.01, 4.0
ENTW = date(2020, 1, 1)
FOMC = set(date.fromisoformat(s) for s in (
    "2019-12-11,2020-01-29,2020-03-03,2020-03-15,2020-04-29,2020-06-10,2020-07-29,2020-09-16,2020-11-05,"
    "2020-12-16,2021-01-27,2021-03-17,2021-04-28,2021-06-16,2021-07-28,2021-09-22,2021-11-03,2021-12-15,"
    "2022-01-26,2022-03-16,2022-05-04,2022-06-15,2022-07-27,2022-09-21,2022-11-02,2022-12-14,2023-02-01,"
    "2023-03-22,2023-05-03,2023-06-14,2023-07-26,2023-09-20,2023-11-01,2023-12-13,2024-01-31,2024-03-20,"
    "2024-05-01,2024-06-12,2024-07-31,2024-09-18,2024-11-07,2024-12-18,2025-01-29,2025-03-19,2025-05-07,"
    "2025-06-18,2025-07-30,2025-09-17,2025-10-29,2025-12-10,2026-01-28,2026-03-18,2026-04-29,2026-06-17,"
    "2026-07-29,2026-09-16,2026-10-28").split(","))
T830 = set(date.fromisoformat(s) for s in "2019-11-01,2019-11-13,2019-11-27,2019-12-06,2019-12-11,2019-12-20,2020-01-10,2020-01-14,2020-01-31,2020-02-07,2020-02-13,2020-02-28,2020-03-06,2020-03-11,2020-03-26,2020-03-27,2020-04-03,2020-04-10,2020-04-30,2020-05-08,2020-05-12,2020-05-29,2020-06-05,2020-06-10,2020-06-25,2020-06-26,2020-07-02,2020-07-14,2020-07-30,2020-07-31,2020-08-07,2020-08-12,2020-08-28,2020-09-04,2020-09-11,2020-10-01,2020-10-02,2020-10-13,2020-10-30,2020-11-06,2020-11-12,2020-11-25,2020-12-04,2020-12-10,2020-12-23,2021-01-08,2021-01-13,2021-01-29,2021-02-05,2021-02-10,2021-02-26,2021-03-05,2021-03-10,2021-03-25,2021-03-26,2021-04-02,2021-04-13,2021-04-30,2021-05-07,2021-05-12,2021-05-27,2021-05-28,2021-06-04,2021-06-10,2021-06-25,2021-07-02,2021-07-13,2021-07-30,2021-08-06,2021-08-11,2021-08-26,2021-08-27,2021-09-03,2021-09-14,2021-10-01,2021-10-08,2021-10-13,2021-10-29,2021-11-05,2021-11-10,2021-11-24,2021-12-03,2021-12-10,2021-12-23,2022-01-07,2022-01-12,2022-01-28,2022-02-04,2022-02-10,2022-02-24,2022-02-25,2022-03-04,2022-03-10,2022-03-31,2022-04-01,2022-04-12,2022-04-29,2022-05-06,2022-05-11,2022-05-27,2022-06-03,2022-06-10,2022-06-29,2022-06-30,2022-07-08,2022-07-13,2022-07-28,2022-07-29,2022-08-05,2022-08-10,2022-08-26,2022-09-02,2022-09-13,2022-09-30,2022-10-07,2022-10-13,2022-10-27,2022-10-28,2022-11-04,2022-11-10,2022-12-01,2022-12-02,2022-12-13,2022-12-23,2023-01-06,2023-01-12,2023-01-27,2023-02-03,2023-02-14,2023-02-24,2023-03-10,2023-03-14,2023-03-30,2023-03-31,2023-04-07,2023-04-12,2023-04-28,2023-05-05,2023-05-10,2023-05-26,2023-06-02,2023-06-13,2023-06-29,2023-06-30,2023-07-07,2023-07-12,2023-07-28,2023-08-04,2023-08-10,2023-08-31,2023-09-01,2023-09-13,2023-09-28,2023-09-29,2023-10-06,2023-10-12,2023-10-27,2023-11-03,2023-11-14,2023-11-29,2023-11-30,2023-12-08,2023-12-12,2023-12-22,2024-01-05,2024-01-11,2024-01-25,2024-01-26,2024-02-02,2024-02-13,2024-02-29,2024-03-08,2024-03-12,2024-03-29,2024-04-05,2024-04-10,2024-04-25,2024-04-26,2024-05-03,2024-05-15,2024-05-31,2024-06-07,2024-06-12,2024-06-28,2024-07-05,2024-07-11,2024-07-26,2024-08-02,2024-08-14,2024-08-21,2024-08-29,2024-08-30,2024-09-06,2024-09-11,2024-09-27,2024-10-04,2024-10-10,2024-10-31,2024-11-01,2024-11-13,2024-11-27,2024-12-06,2024-12-11,2024-12-20,2025-01-10,2025-01-15,2025-01-31,2025-02-07,2025-02-12,2025-02-27,2025-02-28,2025-03-07,2025-03-12,2025-03-28,2025-04-04,2025-04-10,2025-04-30,2025-05-02,2025-05-13,2025-05-29,2025-05-30,2025-06-06,2025-06-11,2025-06-27,2025-07-03,2025-07-15,2025-07-31,2025-08-01,2025-08-12,2025-08-29,2025-09-05,2025-09-11,2025-09-25,2025-09-26,2025-10-24,2025-11-13,2025-11-20,2025-12-05,2025-12-16,2025-12-18,2025-12-23,2026-01-09,2026-01-13,2026-01-22,2026-02-11,2026-02-13,2026-02-20,2026-03-06,2026-03-11,2026-03-13,2026-04-03,2026-04-09,2026-04-10,2026-04-30,2026-05-08,2026-05-12,2026-05-28,2026-06-05,2026-06-10,2026-06-25,2026-07-02,2026-07-14,2026-07-30,2026-08-07,2026-08-12,2026-08-26,2026-09-04,2026-09-11,2026-09-30,2026-10-02,2026-10-14,2026-10-29,2026-11-06,2026-11-10".split(","))

BASIS = [(k, e, s, be) for k in (5, 15, 30) for e in ("schluss5", "stop") for s in ("gegen", "mitte") for be in (False, True)]
RICHT = ("D1_luecke", "D2_kerze", "D3_erster")
FILT = ("F0_keiner", "F1_kerze_wie_luecke", "F2_relvol", "F3_luecke", "F4_kein_fed", "F5_kombi")
# Initial stop S1 = opposite edge of the 5-minute range, S2 = 0.15 x ATR14.
# Trail T0 = none, T1 = break-even after +1 R, T2 = 1 R behind each 5-minute close after +1 R.
STOPS = [(s, t) for s in ("S1", "S2") for t in ("T0", "T1", "T2")]
# Registered but not published (see header). Sharpe ratios from the QuantConnect run, used only in the DSR.
UNPUBLISHED_SR = {"S_S1_T3": 0.7259, "S_S2_T3": 0.6041}


def spiegeln(x):
    """Mirror prices (sign flip) so that a short trade runs through the long logic."""
    return {"min": x["min"], "open": -x["open"], "close": -x["close"], "high": -x["low"], "low": -x["high"]}


def trade_long(x, k, einstieg, stop, be):
    """Port of trade_long from R/bt_intraday.R. Returns (ret, stop_pct, rmult, entry_min, fill, r) or None."""
    mi, op, hi, lo, cl = x["min"], x["open"], x["high"], x["low"], x["close"]
    orm = mi < START + k
    if orm.sum() < k * 0.8:
        return None
    orh, orl = hi[orm].max(), lo[orm].min()
    if einstieg == "stop":
        kand = np.nonzero(~orm & (mi <= LETZTER_EIN) & (hi >= orh))[0]
        if len(kand) == 0:
            return None
        i = kand[0]
        fill = max(orh, op[i])
    else:
        e5 = np.nonzero(~orm & ((mi - START) % 5 == 4) & (mi <= LETZTER_EIN) & (cl > orh))[0]
        if len(e5) == 0 or e5[0] == len(mi) - 1:
            return None
        i = e5[0] + 1
        fill = op[i]
    stop0 = orl if stop == "gegen" else (orh + orl) / 2
    if fill <= stop0:
        return None
    r = fill - stop0
    idx = np.nonzero(mi <= SCHLUSS)[0]
    ende = idx[-1]
    if i > ende:
        return None
    lo_j, hi_j, op_j = lo[i:ende + 1], hi[i:ende + 1], op[i:ende + 1]
    ts = np.nonzero(lo_j <= stop0)[0]
    t_stop = ts[0] if len(ts) else None
    t_be = None
    if be:
        tb = np.nonzero(hi_j >= fill + r)[0]
        t_be = tb[0] if len(tb) else None
    exit_px = None
    if t_be is not None and (t_stop is None or t_be < t_stop):
        nach = np.nonzero(lo_j[t_be + 1:] <= fill)[0]
        if len(nach):
            s = t_be + 1 + nach[0]
            exit_px = min(fill, op_j[s])
    elif t_stop is not None:
        exit_px = stop0 if t_stop == 0 else min(stop0, op_j[t_stop])
    if exit_px is None:
        exit_px = cl[ende]
    return ((exit_px - fill) / abs(fill), r / abs(fill), (exit_px - fill) / r, mi[i], fill, r)


def trade_stop(x, stop_art, trail, atr):
    """Port of trade_tag/einstieg_long/ausstieg_long from R/bt_stop.R (long logic)."""
    mi, op, hi, lo, cl = x["min"], x["open"], x["high"], x["low"], x["close"]
    orm = mi < START + 5
    if orm.sum() < 4:
        return None
    orh, orl = hi[orm].max(), lo[orm].min()
    kand = np.nonzero(~orm & (mi <= LETZTER_EIN) & (hi >= orh))[0]
    if len(kand) == 0:
        return None
    i = kand[0]
    fill = max(orh, op[i])
    stop0 = orl if stop_art == "S1" else fill - 0.15 * atr * abs(fill)
    ende = np.nonzero(mi <= SCHLUSS)[0][-1]
    if i > ende or fill <= stop0:
        return None
    r = fill - stop0
    st = stop0
    erreicht = False
    for j in range(i, ende + 1):
        if lo[j] <= st:
            px = st if j == i else min(st, op[j])
            return ((px - fill) / abs(fill), r / abs(fill), (px - fill) / r)
        if hi[j] >= fill + r:
            erreicht = True
        if trail == "T1" and erreicht:
            st = max(st, fill)
        if (mi[j] - START) % 5 == 4:
            if trail == "T2" and erreicht:
                st = max(st, cl[j] - r)
    return ((cl[ende] - fill) / abs(fill), r / abs(fill), (cl[ende] - fill) / r)


def pnl(t):
    """Daily return of a trade: risk 1% of the account to the stop, leverage capped, costs per round trip."""
    if t is None:
        return 0.0
    return min(RISIKO / t[1], MAX_HEBEL) * (t[0] - KOSTEN)


def sharpe_np(r):
    r = np.asarray(r, dtype=float)
    s = r.std(ddof=1)
    return r.mean() / s * math.sqrt(252) if s > 0 else float("nan")


def kennz(r):
    r = np.asarray(r, dtype=float)
    w = np.cumprod(1 + r)
    return sharpe_np(r), w[-1] ** (252 / len(r)) - 1, (w / np.maximum.accumulate(w) - 1).min()


class Belege(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2019, 6, 1)
        self.set_end_date(2026, 11, 20)
        self.set_cash(100000)
        self.set_time_zone(TimeZones.NEW_YORK)
        self.qqq = self.add_equity("QQQ", Resolution.MINUTE, extended_market_hours=False).symbol
        self.init_zustand()

    def init_zustand(self):
        self.tag = None
        self.bars = []
        self.vc = None
        self.tr_hist = deque(maxlen=14)
        self.v5_hist = deque(maxlen=14)
        self.v4_hist = deque(maxlen=14)
        self.tage = []                  # one dict of day features per development day
        self.v = {}                     # variant -> dict of lists

    def on_data(self, data: Slice):
        b = data.bars.get(self.qqq)
        if b is None:
            return
        t0 = self.time - b.period
        if self.tag is not None and t0.date() != self.tag:
            self.tag_auswerten()
            self.bars = []
        self.tag = t0.date()
        self.bars.append((t0.hour * 60 + t0.minute, b.open, b.high, b.low, b.close, b.volume))

    def tag_auswerten(self):
        a = np.array(self.bars, dtype=float)
        a = a[np.argsort(a[:, 0], kind="stable")]
        mi = a[:, 0].astype(int)
        x = {"min": mi, "open": a[:, 1], "high": a[:, 2], "low": a[:, 3], "close": a[:, 4]}
        vol = a[:, 5]
        d = self.tag
        o, h, l, c = x["open"][0], x["high"].max(), x["low"].min(), x["close"][-1]
        vc = self.vc
        luecke = (o / vc - 1) if vc else float("nan")
        atr14 = (sum(self.tr_hist) / 14) if len(self.tr_hist) == 14 else float("nan")
        orm5 = mi < START + 5
        o5, c5 = (x["open"][orm5][0], x["close"][orm5][-1]) if orm5.any() else (float("nan"), float("nan"))
        orm15 = mi < START + 15
        or15 = (x["high"][orm15].max() - x["low"][orm15].min()) / x["open"][orm15][0] if orm15.any() else float("nan")
        v5 = vol[orm5].sum()
        v4 = vol[(mi >= START + 1) & (mi < START + 5)].sum()
        rv5 = v5 / (sum(self.v5_hist) / 14) if len(self.v5_hist) == 14 and sum(self.v5_hist) > 0 else float("nan")
        rv4 = v4 / (sum(self.v4_hist) / 14) if len(self.v4_hist) == 14 and sum(self.v4_hist) > 0 else float("nan")
        if vc:
            self.tr_hist.append((max(h, vc) - min(l, vc)) / vc)
        self.v5_hist.append(v5)
        self.v4_hist.append(v4)
        self.vc = c
        if d < ENTW or vc is None:
            return
        self.rechnen(x, luecke, atr14, o5, c5, rv5, rv4, d, (h - l) / o, or15)

    def var(self, name):
        if name not in self.v:
            self.v[name] = {"r": [], "pl": [], "ps": [], "tage": [], "rm": [], "erster": []}
        return self.v[name]

    def rechnen(self, x, luecke, atr14, o5, c5, rv5, rv4, d, spanne, or15):
        xs = spiegeln(x)
        g = 0 if (luecke != luecke or luecke == 0) else (1 if luecke > 0 else -1)
        kr = 0 if c5 == o5 or c5 != c5 else (1 if c5 > o5 else -1)
        # 24 base variants, direction = gap; random direction on all days
        r5 = None
        for (k, e, s, be) in BASIS:
            tl = trade_long(x, k, e, s, be)
            ts = trade_long(xs, k, e, s, be)
            z = self.var(f"B_{k}_{e}_{s}_{'T' if be else 'F'}")
            z["pl"].append(pnl(tl)); z["ps"].append(pnl(ts))
            z["r"].append(pnl(tl) if g == 1 else (pnl(ts) if g == -1 else 0.0))
            z["tage"].append(True)
            t = tl if g == 1 else (ts if g == -1 else None)
            if t is not None:
                z["rm"].append(t[2])
            ers = 0.0
            if tl is not None or ts is not None:
                ers = pnl(tl) if (ts is None or (tl is not None and tl[3] <= ts[3])) else pnl(ts)
            z["erster"].append(ers)
            if (k, e, s, be) == (5, "stop", "gegen", False):
                r5 = (tl, ts, ers)
        tl, ts, erster = r5
        # 18 filter variants: 3 directions x 6 day filters on the OR5 stop-order rule
        fl = {"F0_keiner": True, "F1_kerze_wie_luecke": kr == g, "F2_relvol": rv5 >= 1,
              "F3_luecke": (abs(luecke) / atr14) >= 0.1 if atr14 == atr14 and luecke == luecke else False,
              "F4_kein_fed": d not in FOMC}
        fl["F5_kombi"] = fl["F1_kerze_wie_luecke"] and fl["F2_relvol"] and fl["F4_kein_fed"]
        for rn in RICHT:
            for fn in FILT:
                z = self.var(f"F_{rn}_{fn}")
                z["pl"].append(pnl(tl)); z["ps"].append(pnl(ts)); z["tage"].append(fl[fn])
                t = None
                if not fl[fn]:
                    v = 0.0
                elif rn == "D3_erster":
                    v = erster
                    if tl is not None or ts is not None:
                        t = tl if (ts is None or (tl is not None and tl[3] <= ts[3])) else ts
                else:
                    dd = g if rn == "D1_luecke" else kr
                    t = tl if dd == 1 else (ts if dd == -1 else None)
                    v = pnl(t)
                z["r"].append(v)
                if t is not None:
                    z["rm"].append(t[2])
        # stop variants on the selected filter (first candle, opening volume >= 14-day mean)
        f2 = rv5 >= 1 and kr != 0
        for (sa, tr) in STOPS:
            z = self.var(f"S_{sa}_{tr}")
            l_ = s_ = None
            if f2:
                l_ = trade_stop(x, sa, tr, atr14)
                s_ = trade_stop(xs, sa, tr, atr14)
            z["pl"].append(pnl(l_)); z["ps"].append(pnl(s_)); z["tage"].append(f2)
            t = (l_ if kr == 1 else s_) if f2 else None
            z["r"].append(pnl(t))
            if t is not None:
                z["rm"].append(t[2])
        # V51: data correction, opening volume from the bars 9:31-9:34 only (the candidate)
        f51 = rv4 >= 1 and kr != 0
        z = self.var("V51_relvol4")
        z["pl"].append(pnl(tl)); z["ps"].append(pnl(ts)); z["tage"].append(f51)
        t = (tl if kr == 1 else ts) if f51 else None
        z["r"].append(pnl(t))
        if t is not None:
            z["rm"].append(t[2])
        self.tage.append({"tag": d, "g": g, "kr": kr, "rv5": rv5, "fomc": d in FOMC, "t830": d in T830,
                          "or15_atr": or15 / atr14 if atr14 == atr14 else float("nan"),
                          "spanne_atr": spanne / atr14 if atr14 == atr14 else float("nan"),
                          "r5_l": pnl(tl) if g == 1 else (pnl(ts) if g == -1 else 0.0), "r5_e": erster})

    # ---------------- evaluation at the end ----------------
    def zufall_rang(self, z, rng, B=1000):
        pl, ps, tg = np.array(z["pl"]), np.array(z["ps"]), np.array(z["tage"])
        echt = sharpe_np(z["r"])
        d = rng.integers(0, 2, size=(B, len(pl)))
        m = np.where(d == 1, pl, ps) * tg
        mu = m.mean(axis=1); sd = m.std(axis=1, ddof=1)
        srz = mu / sd * math.sqrt(252)
        return float((srz < echt).mean()), float(np.quantile(srz, 0.95))

    def varianten_ausgeben(self):
        rng = np.random.default_rng(20261121)
        sr_alle = {}
        n_tage = len(self.tage)
        for name in sorted(list(self.v) + list(UNPUBLISHED_SR)):
            if name in UNPUBLISHED_SR:
                rng.integers(0, 2, size=(1000, n_tage))     # same draws as in the full run, not used
                continue
            z = self.v[name]
            sr, cg, dd = kennz(z["r"])
            sr_alle[name] = sr
            rang, p95 = self.zufall_rang(z, rng)
            rm = np.array(z["rm"]) if z["rm"] else np.array([np.nan])
            se = sharpe_np(z["erster"]) if z["erster"] else float("nan")
            self.log(f"VAR {name} {sr:.4f} {cg:.4f} {dd:.4f} {len(z['rm'])} {np.nanmean(rm):.4f} "
                     f"{np.nanmedian(rm):.4f} {np.nanmean(rm > 0):.4f} {rang:.4f} {p95:.4f} {se:.4f}")
        return sr_alle

    def dsr_ausgeben(self, sr):
        from statistics import NormalDist
        N = NormalDist()
        sr = dict(sr, **UNPUBLISHED_SR)
        namen = sorted(sr)
        srd = np.array([sr[k] for k in namen]) / math.sqrt(252)
        nv = len(srd); var = srd.var(ddof=1)
        g = 0.5772156649
        sr0 = math.sqrt(var) * ((1 - g) * N.inv_cdf(1 - 1 / nv) + g * N.inv_cdf(1 - 1 / (nv * math.e)))
        r = np.array(self.v["V51_relvol4"]["r"]); n = len(r)
        s = sr["V51_relvol4"] / math.sqrt(252)
        sd = r.std(); sk = (((r - r.mean()) / sd) ** 3).mean(); ku = (((r - r.mean()) / sd) ** 4).mean()
        dsr = N.cdf((s - sr0) * math.sqrt(n - 1) / math.sqrt(1 + (3 - 1) / 4 * s * s))
        dsr_sk = N.cdf((s - sr0) * math.sqrt(n - 1) / math.sqrt(1 - sk * s + (ku - 1) / 4 * s * s))
        # state at the filter step: 42 variants (24 base + 18 filter)
        n42 = [k for k in namen if k.startswith("B_") or k.startswith("F_")]
        srd42 = np.array([sr[k] for k in n42]) / math.sqrt(252)
        sr0_42 = math.sqrt(srd42.var(ddof=1)) * ((1 - g) * N.inv_cdf(1 - 1 / 42) + g * N.inv_cdf(1 - 1 / (42 * math.e)))
        s42 = sr["F_D2_kerze_F2_relvol"] / math.sqrt(252)
        dsr42 = N.cdf((s42 - sr0_42) * math.sqrt(n - 1) / math.sqrt(1 + 0.5 * s42 * s42))
        self.log(f"DSR V51 {dsr:.4f} {dsr_sk:.4f} {sk:.3f} {ku:.3f} {nv} {n} D2F2_bei42 {dsr42:.4f}")

    def spanne_ausgeben(self):
        sp = np.array([t["spanne_atr"] for t in self.tage])
        q = np.quantile(sp, [0.2, 0.4, 0.6, 0.8])
        fu = np.searchsorted(q, sp, side="left") + 1
        for name in sorted(k for k in self.v if k.startswith("B_")):
            r = np.array(self.v[name]["r"])
            self.log("Q1 " + name + " " + " ".join(f"{1e4 * r[fu == i].mean():.3f}" for i in range(1, 6)))

    def merkmale_ausgeben(self):
        # columns: feature, level, days, bp/day gap rule (OR5 stop order), bp/day first break of either side
        T = self.tage
        r5l = np.array([t["r5_l"] for t in T]); r5e = np.array([t["r5_e"] for t in T])
        def aus(name, stufen):
            for st in sorted(set(stufen)):
                s = np.array([a == st for a in stufen])
                self.log(f"MERK {name} {st} {s.sum()} {1e4 * r5l[s].mean():.2f} {1e4 * r5e[s].mean():.2f}")
        def fuenftel(v):
            v = np.array(v, dtype=float); q = np.nanquantile(v, [0.2, 0.4, 0.6, 0.8])
            return list(np.searchsorted(q, v, side="left") + 1)
        aus("kerze_wie_luecke", [t["kr"] == t["g"] for t in T])
        aus("relvol5", fuenftel([t["rv5"] for t in T]))
        aus("termin_0830", [t["t830"] for t in T])
        aus("fomc", [t["fomc"] for t in T])
        aus("or15_atr", fuenftel([t["or15_atr"] for t in T]))

    def tagesreihe_ausgeben(self):
        r = self.v["V51_relvol4"]["r"]
        for t, x in zip(self.tage, r):
            self.log(f"TAG {t['tag']} {x:.6f}")

    def on_end_of_algorithm(self):
        if self.bars:
            self.tag_auswerten()
        sr = self.varianten_ausgeben()
        self.dsr_ausgeben(sr)
        self.spanne_ausgeben()
        self.merkmale_ausgeben()
        self.tagesreihe_ausgeben()
        self.set_runtime_statistic("tage", str(len(self.tage)))
