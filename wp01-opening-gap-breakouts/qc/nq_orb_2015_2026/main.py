# Working Paper No. 01: the rule of replication version 4 with real orders over the full period
# 2015 to November 2026, test sample included. Orders go to E-mini Nasdaq-100 futures (NQ), because
# Micro futures (MNQ) start only in May 2019. Start capital 1 million USD, because one NQ contract
# is about 20 times an MNQ contract. Signals come from QQQ minute bars as in version 4. The random-
# direction test is computed virtually at the trigger price on NQ bars.
from AlgorithmImports import *
from collections import deque
import random, math

RISK = 0.01                           # share of equity at risk per trade
MAX_LEVERAGE = 4.0                    # notional at most 4 times equity
COST = 1e-4                           # as in the research model, only for the virtual null model
TRADE_FROM = datetime(2015, 1, 2)
SIGNAL = "QQQ"
OPEN_MIN = 570                        # 9:30 in minutes after midnight, New York time
LAST_ENTRY_MIN = 690                  # 11:30: an entry order not filled by then is cancelled
START_CAPITAL = 1000000


class OpeningRange:
    """Open, high, low and close of the first five minutes, and the volume of minutes 2 to 5."""
    def __init__(self):
        self.o = self.h = self.l = self.c = None
        self.vol_after_first = 0.0    # volume without the first minute
        self.n = 0

    def add(self, bar, minute):
        if self.o is None:
            self.o = bar.open
        self.h = bar.high if self.h is None else max(self.h, bar.high)
        self.l = bar.low if self.l is None else min(self.l, bar.low)
        self.c = bar.close
        if minute >= 1:
            self.vol_after_first += bar.volume
        self.n += 1


class VirtualTrade:
    """One trade at the trigger price, as in the research model: the stop counts in the entry second too."""
    def __init__(self, d, hi, lo):
        self.d, self.entry, self.stop = d, (hi if d == 1 else lo), (lo if d == 1 else hi)
        self.fill = self.exit = None

    def bar(self, b, may_enter):
        if self.exit is not None:
            return
        if self.fill is None:
            if not may_enter:
                return
            if self.d == 1 and b.high >= self.entry:
                self.fill = max(self.entry, b.open)
            elif self.d == -1 and b.low <= self.entry:
                self.fill = min(self.entry, b.open)
            else:
                return
        if self.d == 1 and b.low <= self.stop:
            self.exit = min(self.stop, b.open) if b.open < self.fill else self.stop
        elif self.d == -1 and b.high >= self.stop:
            self.exit = max(self.stop, b.open) if b.open > self.fill else self.stop
        self.last_close = b.close

    def result(self):
        if self.fill is None:
            return None
        exit_price = self.exit if self.exit is not None else self.last_close
        ret = self.d * (exit_price - self.fill) / self.fill
        stop_pct = abs(self.fill - self.stop) / self.fill
        r = self.d * (exit_price - self.fill) / abs(self.entry - self.stop)
        return ret, stop_pct, r


class OpeningRangeBreakoutNQ(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2014, 11, 14)
        self.set_end_date(2026, 11, 20)
        self.set_cash(START_CAPITAL)
        self.set_time_zone(TimeZones.NEW_YORK)
        self.sig = self.add_equity(SIGNAL, Resolution.MINUTE, extended_market_hours=False).symbol
        self.fut = self.add_future(Futures.Indices.NASDAQ_100_E_MINI, Resolution.SECOND,
                                   data_normalization_mode=DataNormalizationMode.RAW,
                                   data_mapping_mode=DataMappingMode.OPEN_INTEREST,
                                   contract_depth_offset=0, extended_market_hours=False)
        self.fut.set_filter(0, 120)
        self.vol_hist = deque(maxlen=14)
        self.count = {"Days evaluated": 0, "Signal days": 0, "Entries": 0, "Stopped out": 0,
                      "Closed at 15:55": 0, "Too small to trade": 0, "Incomplete opening range": 0,
                      "Not triggered by 11:30": 0, "Flat first candle": 0}
        self.virtual_days = []        # per signal day: (direction, result long, result short)
        self.days_evaluated = 0
        self.day = None
        self.new_day()

    def new_day(self):
        self.range_signal = OpeningRange()    # QQQ
        self.range_future = OpeningRange()    # traded future
        self.signal_done = False
        self.entry_ticket = self.stop_ticket = None
        self.contract = None
        self.direction = 0
        self.stop = None
        self.entered = self.closed = False
        self.virtual = None
        self.exit_min = None

    def exit_minute(self):
        # 5 minutes before the close of the cash session, shortened sessions included
        hours = self.securities[self.sig].exchange.hours
        close = hours.get_next_market_close(datetime.combine(self.day, time(9, 0)), False)
        if close.date() != self.day:
            return None
        return close.hour * 60 + close.minute - 5

    def on_data(self, data: Slice):
        if self.day != self.time.date():
            if self.day is not None:
                if self.portfolio.invested and not self.closed:
                    self.exit_position()
                self.close_virtual_day()
            self.day = self.time.date()
            self.new_day()
            self.exit_min = self.exit_minute()
        qb = data.bars.get(self.sig)
        if qb is not None:
            t0 = self.time - qb.period          # bar start in algorithm time (bar.time is exchange time)
            mq = t0.hour * 60 + t0.minute - OPEN_MIN
            if 0 <= mq <= 4:
                self.range_signal.add(qb, mq)
        fb = data.bars.get(self.fut.symbol)
        if fb is not None:
            t0 = self.time - fb.period
            mf = t0.hour * 60 + t0.minute - OPEN_MIN
            if 0 <= mf <= 4:
                self.range_future.add(fb, mf)

        m = self.time.hour * 60 + self.time.minute
        if not self.signal_done and m >= OPEN_MIN + 5:
            self.signal_done = True
            self.signal()

        # virtual trades for the null model
        if self.virtual is not None and fb is not None and self.exit_min is not None and m < self.exit_min:
            may_enter = m < LAST_ENTRY_MIN
            for v in self.virtual:
                v.bar(fb, may_enter)

        if self.entry_ticket is not None and not self.portfolio.invested and m >= LAST_ENTRY_MIN:
            if not self.entered:
                self.entry_ticket.cancel("entry window closed")
                self.count["Not triggered by 11:30"] += 1
            self.entry_ticket = None

        if self.exit_min is not None and m >= self.exit_min and self.portfolio.invested and not self.closed:
            self.closed = True
            self.exit_position()

    def signal(self):
        sig = self.range_signal
        if sig.o is None or self.range_future.h is None or self.exit_min is None:
            self.count["Incomplete opening range"] += 1
            return
        relvol = sig.vol_after_first / (sum(self.vol_hist) / len(self.vol_hist)) \
            if len(self.vol_hist) == 14 and sum(self.vol_hist) > 0 else None
        self.vol_hist.append(sig.vol_after_first)
        if relvol is None or self.time < TRADE_FROM:
            return
        self.count["Days evaluated"] += 1
        self.days_evaluated += 1
        d = 1 if sig.c > sig.o else (-1 if sig.c < sig.o else 0)
        if d == 0:
            self.count["Flat first candle"] += 1
            return
        if relvol < 1.0:
            return
        self.count["Signal days"] += 1
        hi, lo = self.range_future.h, self.range_future.l
        if hi - lo <= 0:
            return
        self.virtual = [VirtualTrade(1, hi, lo), VirtualTrade(-1, hi, lo)]
        self.virtual_direction = d
        entry = hi if d == 1 else lo
        stop = lo if d == 1 else hi
        sec = self.securities[self.fut.mapped] if self.fut.mapped else None
        if sec is None:
            return
        value_per_point = sec.symbol_properties.contract_multiplier * sec.quote_currency.conversion_rate
        equity = self.portfolio.total_portfolio_value
        leverage = min(RISK / ((hi - lo) / entry), MAX_LEVERAGE)
        quantity = int(leverage * equity / (entry * value_per_point))
        if quantity < 1:
            self.count["Too small to trade"] += 1
            return
        self.contract = self.fut.mapped
        self.direction = d
        self.stop = stop
        self.entry_ticket = self.stop_market_order(self.contract, d * quantity, entry, tag="entry")

    def close_virtual_day(self):
        if self.virtual is None:
            return
        self.virtual_days.append((self.virtual_direction, self.virtual[0].result(), self.virtual[1].result()))
        self.virtual = None

    def on_order_event(self, ev: OrderEvent):
        if ev.status != OrderStatus.FILLED:
            return
        if self.entry_ticket is not None and ev.order_id == self.entry_ticket.order_id:
            self.count["Entries"] += 1
            self.entered = True
            self.stop_ticket = self.stop_market_order(self.contract, -self.direction * abs(ev.fill_quantity),
                                                      self.stop, tag="stop")
        elif self.stop_ticket is not None and ev.order_id == self.stop_ticket.order_id:
            self.count["Stopped out"] += 1
            self.stop_ticket = None

    def exit_position(self):
        if self.stop_ticket is not None:
            self.stop_ticket.cancel("close")
            self.stop_ticket = None
        self.liquidate(self.contract, tag="close")
        self.count["Closed at 15:55"] += 1

    def null_model(self):
        def pnl(e):
            if e is None:
                return 0.0
            ret, sp, _ = e
            return min(RISK / sp, MAX_LEVERAGE) * (ret - COST) if sp > 0 else 0.0

        def sharpe(x):
            n = self.days_evaluated
            if n < 2:
                return float("nan")
            m = sum(x) / n
            v = (sum((a - m) ** 2 for a in x) + (n - len(x)) * m * m) / (n - 1)
            return m / math.sqrt(v) * math.sqrt(252) if v > 0 else float("nan")

        days = self.virtual_days
        actual = [pnl(l if d == 1 else s) for d, l, s in days]
        sr = sharpe(actual)
        rnd = random.Random(7)
        random_sr = []
        for _ in range(1000):
            random_sr.append(sharpe([pnl(l if rnd.random() < 0.5 else s) for d, l, s in days]))
        random_sr.sort()
        rs = [(l if d == 1 else s)[2] for d, l, s in days if (l if d == 1 else s) is not None]
        boot = []
        for _ in range(1000 if rs else 0):
            smp = [rs[rnd.randrange(len(rs))] for _ in rs]
            boot.append(sum(smp) / len(smp))
        boot.sort()
        return {"Sharpe at trigger price": sr,
                "Rank vs random direction": sum(1 for a in random_sr if a < sr) / len(random_sr),
                "Random direction 95th pct": random_sr[949],
                "Trades at trigger price": len(rs),
                "Mean R per trade": sum(rs) / len(rs) if rs else float("nan"),
                "Mean R bootstrap 5%": boot[49] if boot else float("nan"),
                "Days in random test": len(days)}

    def on_end_of_algorithm(self):
        self.close_virtual_day()
        for k, v in self.count.items():
            self.set_runtime_statistic(k, str(v))
        for k, v in self.null_model().items():
            self.set_runtime_statistic(k, f"{v:.4f}" if isinstance(v, float) else str(v))
