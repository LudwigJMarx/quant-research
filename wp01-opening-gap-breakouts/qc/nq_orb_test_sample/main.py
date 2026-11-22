# Working Paper No. 01: the rule of replication version 4 with real orders in the test sample
# 2015 to 2019 only. Orders go to E-mini Nasdaq-100 futures (NQ), because Micro futures (MNQ) start
# only in May 2019. Start capital 1 million USD. Source of the real-order numbers for the test sample
# in the paper (−3.9% a year, largest loss −31.7%, Sharpe −0.33).
from AlgorithmImports import *
from collections import deque
import random, math

MARKT = "NQ"
RISIKO = 0.01
MAX_HEBEL = 4.0
KOSTEN = 1e-4                         # as in the research model, only for the virtual null model
HANDEL_AB = datetime(2015, 1, 2)
I = Futures.Indices
CFG = {
    "NQ":  dict(signal="QQQ", fut=lambda: I.NASDAQ_100_E_MINI, tz=TimeZones.NEW_YORK, auf=570, bis=690, ext=False, kapital=1000000),
}


class Spanne:
    def __init__(self):
        self.o = self.h = self.l = self.c = None
        self.v4 = 0.0                 # volume without the first minute
        self.n = 0

    def add(self, bar, minute):
        if self.o is None:
            self.o = bar.open
        self.h = bar.high if self.h is None else max(self.h, bar.high)
        self.l = bar.low if self.l is None else min(self.l, bar.low)
        self.c = bar.close
        if minute >= 1:
            self.v4 += bar.volume
        self.n += 1


class Virtuell:
    """One trade at the trigger price, as in the research model: the stop counts in the entry second too."""
    def __init__(self, d, hi, lo):
        self.d, self.ein, self.stop = d, (hi if d == 1 else lo), (lo if d == 1 else hi)
        self.fill = self.aus = None

    def bar(self, b, darf_einsteigen):
        if self.aus is not None:
            return
        if self.fill is None:
            if not darf_einsteigen:
                return
            if self.d == 1 and b.high >= self.ein:
                self.fill = max(self.ein, b.open)
            elif self.d == -1 and b.low <= self.ein:
                self.fill = min(self.ein, b.open)
            else:
                return
        if self.d == 1 and b.low <= self.stop:
            self.aus = min(self.stop, b.open) if b.open < self.fill else self.stop
        elif self.d == -1 and b.high >= self.stop:
            self.aus = max(self.stop, b.open) if b.open > self.fill else self.stop
        self.letzter = b.close

    def ergebnis(self):
        if self.fill is None:
            return None
        aus = self.aus if self.aus is not None else self.letzter
        ret = self.d * (aus - self.fill) / self.fill
        stop_pct = abs(self.fill - self.stop) / self.fill
        r = self.d * (aus - self.fill) / abs(self.ein - self.stop)
        return ret, stop_pct, r


class OrbMarkt(QCAlgorithm):

    def initialize(self):
        self.k = CFG[MARKT]
        self.set_start_date(2014, 11, 14)
        self.set_end_date(2019, 12, 31)
        self.set_cash(self.k.get("kapital", 100000))
        self.set_time_zone(self.k["tz"])
        self.sig = self.add_equity(self.k["signal"], Resolution.MINUTE, extended_market_hours=False).symbol \
            if self.k["signal"] else None
        self.fut = self.add_future(self.k["fut"](), Resolution.SECOND,
                                   data_normalization_mode=DataNormalizationMode.RAW,
                                   data_mapping_mode=DataMappingMode.OPEN_INTEREST,
                                   contract_depth_offset=0, extended_market_hours=self.k["ext"])
        self.fut.set_filter(0, 120)
        self.vol_hist = deque(maxlen=14)
        self.cnt = {"tage": 0, "signale": 0, "einstiege": 0, "stops": 0, "schluss": 0, "zu_klein": 0,
                    "spanne_unvollstaendig": 0, "nicht_ausgeloest": 0, "doji": 0}
        self.virt_tage = []           # per signal day: (direction, result long, result short)
        self.handelstage = 0
        self.tag = None
        self.neuer_tag()

    def neuer_tag(self):
        self.ss = Spanne()            # signal instrument
        self.sf = Spanne()            # traded instrument
        self.signal_fertig = False
        self.einstieg_ticket = self.stop_ticket = None
        self.vertrag = None
        self.richtung = 0
        self.stop = None
        self.eingestiegen = self.geschlossen = False
        self.virt = None
        self.aus_min = None

    def ausstieg_minute(self):
        # 5 minutes before the close of the cash session, shortened sessions included
        if self.sig is not None:
            h = self.securities[self.sig].exchange.hours
            start = datetime.combine(self.tag, time(9, 0))
            sc = h.get_next_market_close(start, False)
            if sc.date() != self.tag:
                return None
            return sc.hour * 60 + sc.minute - 5
        return None

    def on_data(self, data: Slice):
        if self.tag != self.time.date():
            if self.tag is not None:
                if self.portfolio.invested and not self.geschlossen:
                    self.ausstieg("schluss")
                self.virt_abschluss()
            self.tag = self.time.date()
            self.neuer_tag()
            self.aus_min = self.ausstieg_minute()
        auf = self.k["auf"]
        if self.sig is not None:
            qb = data.bars.get(self.sig)
            if qb is not None:
                t0 = self.time - qb.period          # bar start in algorithm time (bar.time is exchange time)
                mq = t0.hour * 60 + t0.minute - auf
                if 0 <= mq <= 4:
                    self.ss.add(qb, mq)
        fb = data.bars.get(self.fut.symbol)
        if fb is not None:
            t0 = self.time - fb.period
            mf = t0.hour * 60 + t0.minute - auf
            if 0 <= mf <= 4:
                self.sf.add(fb, mf)

        m = self.time.hour * 60 + self.time.minute
        if not self.signal_fertig and m >= auf + 5:
            self.signal_fertig = True
            self.signal()

        # virtual trades for the null model
        if self.virt is not None and fb is not None and self.aus_min is not None and m < self.aus_min:
            darf = m < self.k["bis"]
            for v in self.virt:
                v.bar(fb, darf)

        if self.einstieg_ticket is not None and not self.portfolio.invested and m >= self.k["bis"]:
            if not self.eingestiegen:
                self.einstieg_ticket.cancel("Einstiegsgrenze")
                self.cnt["nicht_ausgeloest"] += 1
            self.einstieg_ticket = None

        if self.aus_min is not None and m >= self.aus_min and self.portfolio.invested and not self.geschlossen:
            self.geschlossen = True
            self.ausstieg("schluss")

    def signal(self):
        sig = self.ss if self.sig is not None else self.sf
        if sig.o is None or self.sf.h is None or self.aus_min is None:
            self.cnt["spanne_unvollstaendig"] += 1
            return
        relvol = sig.v4 / (sum(self.vol_hist) / len(self.vol_hist)) \
            if len(self.vol_hist) == 14 and sum(self.vol_hist) > 0 else None
        self.vol_hist.append(sig.v4)
        if relvol is None or self.time < HANDEL_AB:
            return
        self.cnt["tage"] += 1
        self.handelstage += 1
        d = 1 if sig.c > sig.o else (-1 if sig.c < sig.o else 0)
        if d == 0:
            self.cnt["doji"] += 1
            return
        if relvol < 1.0:
            return
        self.cnt["signale"] += 1
        hi, lo = self.sf.h, self.sf.l
        if hi - lo <= 0:
            return
        self.virt = [Virtuell(1, hi, lo), Virtuell(-1, hi, lo)]
        self.virt_richtung = d
        einstieg = hi if d == 1 else lo
        stop = lo if d == 1 else hi
        sec = self.securities[self.fut.mapped] if self.fut.mapped else None
        if sec is None:
            return
        wert_je_punkt = sec.symbol_properties.contract_multiplier * sec.quote_currency.conversion_rate
        eq = self.portfolio.total_portfolio_value
        hebel = min(RISIKO / ((hi - lo) / einstieg), MAX_HEBEL)
        menge = int(hebel * eq / (einstieg * wert_je_punkt))
        if menge < 1:
            self.cnt["zu_klein"] += 1
            return
        self.vertrag = self.fut.mapped
        self.richtung = d
        self.stop = stop
        self.einstieg_ticket = self.stop_market_order(self.vertrag, d * menge, einstieg, tag="einstieg")

    def virt_abschluss(self):
        if self.virt is None:
            return
        self.virt_tage.append((self.virt_richtung, self.virt[0].ergebnis(), self.virt[1].ergebnis()))
        self.virt = None

    def on_order_event(self, ev: OrderEvent):
        if ev.status != OrderStatus.FILLED:
            return
        if self.einstieg_ticket is not None and ev.order_id == self.einstieg_ticket.order_id:
            self.cnt["einstiege"] += 1
            self.eingestiegen = True
            self.stop_ticket = self.stop_market_order(self.vertrag, -self.richtung * abs(ev.fill_quantity),
                                                      self.stop, tag="stop")
        elif self.stop_ticket is not None and ev.order_id == self.stop_ticket.order_id:
            self.cnt["stops"] += 1
            self.stop_ticket = None

    def ausstieg(self, art):
        if self.stop_ticket is not None:
            self.stop_ticket.cancel("Schluss")
            self.stop_ticket = None
        self.liquidate(self.vertrag, tag=art)
        self.cnt["schluss"] += 1

    def nullmodell(self):
        def pnl(e):
            if e is None:
                return 0.0
            ret, sp, _ = e
            return min(RISIKO / sp, MAX_HEBEL) * (ret - KOSTEN) if sp > 0 else 0.0

        def sharpe(x):
            n = self.handelstage
            if n < 2:
                return float("nan")
            m = sum(x) / n
            v = (sum((a - m) ** 2 for a in x) + (n - len(x)) * m * m) / (n - 1)
            return m / math.sqrt(v) * math.sqrt(252) if v > 0 else float("nan")

        tage = self.virt_tage
        echt = [pnl(l if d == 1 else s) for d, l, s in tage]
        sr = sharpe(echt)
        rnd = random.Random(7)
        z = []
        for _ in range(1000):
            z.append(sharpe([pnl(l if rnd.random() < 0.5 else s) for d, l, s in tage]))
        z.sort()
        rs = [(l if d == 1 else s)[2] for d, l, s in tage if (l if d == 1 else s) is not None]
        boot = []
        for _ in range(1000 if rs else 0):
            smp = [rs[rnd.randrange(len(rs))] for _ in rs]
            boot.append(sum(smp) / len(smp))
        boot.sort()
        return {"nm_sharpe": sr, "nm_rang": sum(1 for a in z if a < sr) / len(z), "nm_zufall95": z[949],
                "nm_trades": len(rs), "nm_r_mittel": sum(rs) / len(rs) if rs else float("nan"),
                "nm_r_unten": boot[49] if boot else float("nan"), "nm_signaltage": len(tage)}

    def on_end_of_algorithm(self):
        self.virt_abschluss()
        for k, v in self.cnt.items():
            self.set_runtime_statistic(k, str(v))
        for k, v in self.nullmodell().items():
            self.set_runtime_statistic(k, f"{v:.4f}" if isinstance(v, float) else str(v))
        self.set_runtime_statistic("markt", MARKT)
