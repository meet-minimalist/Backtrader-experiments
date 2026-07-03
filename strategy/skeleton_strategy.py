"""
Momentum rotation strategy.

Logic:
- Universe: all stocks in the configured index (multi-feed).
- Every `rebalance_every` bars (~monthly), rank eligible stocks by
  12-1 momentum: 12-month (252-bar) return skipping the most recent
  month (21 bars) to avoid short-term reversal noise.
- Hold the top `top_n` stocks, roughly equal-weighted.
- Eligibility: stock must have enough history and trade above its
  150-day SMA (trend filter).
- Exits (explicit, realized):
  1. Rebalance exit: position leaves the top-N momentum list -> close.
  2. Trend exit (checked daily): price closes below SMA150 -> close.
"""

import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    params = (
        ('momentum_period', 252),   # look-back for momentum ranking
        ('momentum_skip', 21),      # skip most recent bars (12-1 momentum)
        ('trend_period', 150),      # SMA trend filter / exit
        ('top_n', 7),               # number of positions to hold
        ('rebalance_every', 21),    # bars between rebalances (~1 month)
        ('symbol_names', []),       # required for multi-stock support
    )

    def __init__(self):
        self.sma = {}
        for d in self.datas:
            self.sma[d._name] = bt.indicators.SMA(d.close, period=self.p.trend_period)
        self.symbol_to_data = {d._name: d for d in self.datas}
        self.bar_count = 0

    def _momentum(self, d):
        """12-1 momentum: return from -252 to -21 bars; None if too short."""
        if len(d) <= self.p.momentum_period:
            return None
        past = d.close[-self.p.momentum_period]
        recent = d.close[-self.p.momentum_skip]
        if past <= 0:
            return None
        return recent / past - 1.0

    def _eligible(self, d):
        """Enough history and in an uptrend (above SMA200)."""
        if len(d) <= max(self.p.momentum_period, self.p.trend_period):
            return False
        return d.close[0] > self.sma[d._name][0]

    def next(self):
        self.bar_count += 1

        # Daily trend exit: close anything below its SMA200
        for d in self.datas:
            pos = self.getposition(d)
            if pos and len(d) > self.p.trend_period and d.close[0] < self.sma[d._name][0]:
                self.close(data=d)

        # Rebalance on schedule
        if self.bar_count % self.p.rebalance_every != 0:
            return

        # Rank eligible stocks by momentum
        ranked = []
        for d in self.datas:
            if not self._eligible(d):
                continue
            mom = self._momentum(d)
            if mom is not None and mom > 0:
                ranked.append((mom, d._name))
        ranked.sort(reverse=True)
        targets = {name for _, name in ranked[:self.p.top_n]}

        # Sell positions that dropped out of the target list
        for d in self.datas:
            pos = self.getposition(d)
            if pos and d._name not in targets:
                self.close(data=d)

        # Buy new entrants, roughly equal-weight
        current = {d._name for d in self.datas if self.getposition(d)}
        to_buy = [name for name in targets if name not in current]
        if not to_buy:
            return
        slot_value = self.broker.getvalue() / self.p.top_n * 0.95
        cash = self.broker.getcash()
        for name in to_buy:
            d = self.symbol_to_data[name]
            price = d.close[0]
            value = min(slot_value, cash)
            size = int(value / price)
            if size > 0:
                self.buy(data=d, size=size)
                cash -= size * price
