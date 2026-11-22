# Working Paper No. 01, replication version 3: rule as in version 2 (signal from QQQ, orders in MNQ),
# but MNQ in second resolution instead of minutes, so that stop orders fill at the price of the trigger
# second and not at the close of the trigger minute. Also one log line per day with relative volume,
# direction and the reason why no order was placed, for the comparison with the research model.
# Not a new variant: the rule is unchanged.
from AlgorithmImports import *
from collections import deque

RISIKO = 0.01
MAX_HEBEL = 4.0
PUNKTWERT = 2.0          # MNQ: 2 USD per index point
HANDEL_AB = datetime(2020, 1, 1)


class Spanne:
    def __init__(self):
        self.o = self.h = self.l = self.c = None
        self.v = 0.0
        self.n = 0

    def add(self, bar):
        if self.o is None:
            self.o = bar.open
        self.h = bar.high if self.h is None else max(self.h, bar.high)
        self.l = bar.low if self.l is None else min(self.l, bar.low)
        self.c = bar.close
        self.v += bar.volume
        self.n += 1


class MnqOrbQqqSek(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2019, 11, 15)
        self.set_end_date(2026, 11, 20)
        self.set_cash(100000)
        self.set_time_zone(TimeZones.NEW_YORK)
        self.qqq = self.add_equity("QQQ", Resolution.MINUTE, extended_market_hours=False).symbol
        self.fut = self.add_future(Futures.Indices.MICRO_NASDAQ_100_E_MINI, Resolution.SECOND,
                                   data_normalization_mode=DataNormalizationMode.RAW,
                                   data_mapping_mode=DataMappingMode.OPEN_INTEREST,
                                   contract_depth_offset=0, extended_market_hours=False)
        self.fut.set_filter(0, 120)
        self.vol5_hist = deque(maxlen=14)
        self.cnt = {"tage": 0, "signale": 0, "einstiege": 0, "stops": 0, "schluss": 0, "zu_klein": 0,
                    "spanne_unvollstaendig": 0, "nicht_ausgeloest": 0}
        self.tag = None
        self.neuer_tag()

    def neuer_tag(self):
        self.sq = Spanne()
        self.sf = Spanne()
        self.signal_fertig = False
        self.einstieg_ticket = None
        self.stop_ticket = None
        self.vertrag = None
        self.richtung = 0
        self.stop = None

    def on_data(self, data: Slice):
        if self.tag != self.time.date():
            if self.tag is not None and self.portfolio.invested:
                self.ausstieg("schluss")
            self.tag = self.time.date()
            self.neuer_tag()
        # range 9:30:00-9:34:59 by bar start time; the QQQ 9:34 minute bar arrives at 9:35:00
        qb = data.bars.get(self.qqq)
        if qb is not None and qb.time.hour == 9 and 30 <= qb.time.minute <= 34:
            self.sq.add(qb)
        fb = data.bars.get(self.fut.symbol)
        if fb is not None and fb.time.hour == 9 and 30 <= fb.time.minute <= 34:
            self.sf.add(fb)

        m = self.time.hour * 60 + self.time.minute
        if not self.signal_fertig and m >= 575:
            self.signal_fertig = True
            self.signal()

        if self.einstieg_ticket is not None and not self.portfolio.invested and m > 690:
            self.einstieg_ticket.cancel("nach 11:30")
            self.einstieg_ticket = None
            self.cnt["nicht_ausgeloest"] += 1

        if m >= 955 and self.portfolio.invested:
            self.ausstieg("schluss")

    def zeile(self, grund, relvol=None, d=None, r=None, menge=None):
        rv = "NA" if relvol is None else f"{relvol:.4f}"
        self.log(f"TAG {self.tag} grund={grund} rv={rv} d={d} qv={self.sq.v:.0f} qn={self.sq.n} "
                 f"fn={self.sf.n} r={r} menge={menge}")

    def signal(self):
        if self.sq.o is None or self.sf.h is None:
            self.cnt["spanne_unvollstaendig"] += 1
            if self.time >= HANDEL_AB:
                self.zeile("spanne_unvollstaendig")
            return
        relvol = self.sq.v / (sum(self.vol5_hist) / len(self.vol5_hist)) if len(self.vol5_hist) == 14 else None
        self.vol5_hist.append(self.sq.v)
        if relvol is None or self.time < HANDEL_AB:
            return
        self.cnt["tage"] += 1
        d = 1 if self.sq.c > self.sq.o else (-1 if self.sq.c < self.sq.o else 0)
        if d == 0:
            self.zeile("doji", relvol, d)
            return
        if relvol < 1.0:
            self.zeile("relvol", relvol, d)
            return
        self.cnt["signale"] += 1
        einstieg = self.sf.h if d == 1 else self.sf.l
        stop = self.sf.l if d == 1 else self.sf.h
        r = abs(einstieg - stop)
        if r <= 0:
            self.zeile("spanne_null", relvol, d, r)
            return
        eq = self.portfolio.total_portfolio_value
        hebel = min(RISIKO / (r / einstieg), MAX_HEBEL)
        menge = int(hebel * eq / (einstieg * PUNKTWERT))
        if menge < 1:
            self.cnt["zu_klein"] += 1
            self.zeile("zu_klein", relvol, d, r, menge)
            return
        self.vertrag = self.fut.mapped
        self.richtung = d
        self.stop = stop
        self.zeile("order", relvol, d, r, menge)
        self.einstieg_ticket = self.stop_market_order(self.vertrag, d * menge, einstieg, tag="einstieg")

    def on_order_event(self, ev: OrderEvent):
        if ev.status != OrderStatus.FILLED:
            return
        if self.einstieg_ticket is not None and ev.order_id == self.einstieg_ticket.order_id:
            self.cnt["einstiege"] += 1
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

    def on_end_of_algorithm(self):
        for k, v in self.cnt.items():
            self.set_runtime_statistic(k, str(v))
