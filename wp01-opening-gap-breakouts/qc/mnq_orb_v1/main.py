# Working Paper No. 01, replication version 1: candidate rule on MNQ (Micro E-mini Nasdaq-100).
# Rule: direction of the first 5-minute candle (9:30-9:34 ET), taken here from the future itself.
# Trade only if the volume of these 5 minutes is >= the mean of the 14 previous sessions.
# Entry with a stop order at the edge of the 5-minute range until 11:30, stop at the opposite edge,
# not trailed, exit at 15:55. Risk 1% per trade, leverage <= 4. MNQ in minute resolution.
from AlgorithmImports import *
from collections import deque

RISIKO = 0.01
MAX_HEBEL = 4.0
PUNKTWERT = 2.0          # MNQ: 2 USD per index point
HANDEL_AB = datetime(2020, 1, 1)


class MnqOrb(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2019, 11, 15)          # warm-up for the volume of the 14 previous sessions
        self.set_end_date(2026, 11, 20)
        self.set_cash(100000)
        self.set_time_zone(TimeZones.NEW_YORK)
        self.fut = self.add_future(Futures.Indices.MICRO_NASDAQ_100_E_MINI, Resolution.MINUTE,
                                   data_normalization_mode=DataNormalizationMode.RAW,
                                   data_mapping_mode=DataMappingMode.OPEN_INTEREST,
                                   contract_depth_offset=0, extended_market_hours=False)
        self.fut.set_filter(0, 120)
        self.vol5_hist = deque(maxlen=14)
        self.trades = []
        self.cnt = {"tage": 0, "signale": 0, "einstiege": 0, "stops": 0, "schluss": 0, "zu_klein": 0}
        self.neuer_tag()

    def neuer_tag(self):
        self.tag = None
        self.or_h = self.or_l = self.or_o = self.or_c = None
        self.vol5 = 0.0
        self.richtung = 0
        self.einstieg_ticket = None
        self.stop_ticket = None
        self.vertrag = None
        self.offen = None

    def on_data(self, data: Slice):
        bar = data.bars.get(self.fut.symbol)
        if bar is None:
            return
        t = bar.time                              # start of the minute, ET
        m = t.hour * 60 + t.minute
        if self.tag != t.date():
            if self.tag is not None and self.portfolio.invested:
                self.ausstieg("schluss")          # safety net, should not happen
            self.neuer_tag()
            self.tag = t.date()

        if 570 <= m <= 574:                       # opening range 9:30-9:34
            if m == 570:
                self.or_o = bar.open
            self.or_h = bar.high if self.or_h is None else max(self.or_h, bar.high)
            self.or_l = bar.low if self.or_l is None else min(self.or_l, bar.low)
            self.vol5 += bar.volume
            self.or_c = bar.close
            if m == 574:
                self.spanne_fertig()
            return

        if self.einstieg_ticket is not None and not self.portfolio.invested and m > 690:
            self.einstieg_ticket.cancel("nach 11:30")
            self.einstieg_ticket = None

        if m >= 955 and self.portfolio.invested:
            self.ausstieg("schluss")

    def spanne_fertig(self):
        if self.or_o is None:
            return
        relvol = self.vol5 / (sum(self.vol5_hist) / len(self.vol5_hist)) if len(self.vol5_hist) == 14 else None
        self.vol5_hist.append(self.vol5)
        if relvol is None or self.time < HANDEL_AB:
            return
        self.cnt["tage"] += 1
        d = 1 if self.or_c > self.or_o else (-1 if self.or_c < self.or_o else 0)
        if d == 0 or relvol < 1.0:
            return
        self.cnt["signale"] += 1
        einstieg = self.or_h if d == 1 else self.or_l
        stop = self.or_l if d == 1 else self.or_h
        r = abs(einstieg - stop)
        if r <= 0:
            return
        eq = self.portfolio.total_portfolio_value
        hebel = min(RISIKO / (r / einstieg), MAX_HEBEL)
        menge = int(hebel * eq / (einstieg * PUNKTWERT))
        if menge < 1:
            self.cnt["zu_klein"] += 1
            return
        self.vertrag = self.fut.mapped
        self.richtung = d
        self.offen = {"tag": str(self.tag), "dir": d, "orh": self.or_h, "orl": self.or_l, "menge": menge,
                      "relvol": round(relvol, 3), "stop": stop}
        self.einstieg_ticket = self.stop_market_order(self.vertrag, d * menge, einstieg, tag="einstieg")

    def on_order_event(self, ev: OrderEvent):
        if ev.status != OrderStatus.FILLED or self.offen is None:
            return
        if self.einstieg_ticket is not None and ev.order_id == self.einstieg_ticket.order_id:
            self.cnt["einstiege"] += 1
            self.offen.update({"ein_zeit": str(self.time), "fill": float(ev.fill_price)})
            self.stop_ticket = self.stop_market_order(self.vertrag, -self.richtung * abs(ev.fill_quantity),
                                                      self.offen["stop"], tag="stop")
        elif self.stop_ticket is not None and ev.order_id == self.stop_ticket.order_id:
            self.cnt["stops"] += 1
            self.trade_ende(float(ev.fill_price), "stop")

    def ausstieg(self, art):
        if self.stop_ticket is not None:
            self.stop_ticket.cancel("Schluss")
        tickets = self.liquidate(self.vertrag, tag=art)
        self.cnt["schluss"] += 1
        px = None
        for tk in tickets or []:
            px = float(tk.average_fill_price) if tk.average_fill_price else px
        self.trade_ende(px if px else float(self.securities[self.vertrag].price), art)

    def trade_ende(self, px, art):
        o = self.offen
        if o is None or "fill" not in o:
            return
        o.update({"aus_zeit": str(self.time), "exit": px, "art": art,
                  "rmult": o["dir"] * (px - o["fill"]) / abs(o["fill"] - o["stop"])})
        self.trades.append(o)
        self.offen = None
        self.stop_ticket = None

    def on_end_of_algorithm(self):
        kopf = "tag,dir,ein_zeit,aus_zeit,fill,exit,stop,orh,orl,menge,relvol,art,rmult"
        zeilen = [kopf] + [",".join(str(t.get(k, "")) for k in kopf.split(",")) for t in self.trades]
        self.object_store.save("mnq_orb_v1_trades.csv", "\n".join(zeilen))
        for k, v in self.cnt.items():
            self.set_runtime_statistic(k, str(v))
        rm = [t["rmult"] for t in self.trades]
        if rm:
            self.set_runtime_statistic("r_mittel", f"{sum(rm) / len(rm):.3f}")
        self.log(f"counters {self.cnt}, trades {len(self.trades)}")
