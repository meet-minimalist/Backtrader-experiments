"""
Momentum rotation strategy.

Logic:
- Universe: all stocks in the configured index (multi-feed).
- Every `rebalance_every` bars (weekly, 5), rank eligible stocks by
  dual-horizon momentum: 189-bar return + 63-bar return, both measured
  up to `momentum_skip` (10) bars ago to avoid short-term reversal noise.
- Hold the top `top_n` (20) stocks, roughly equal-weighted (0.98 of an
  equal slot of portfolio value).
- Re-entry cooldown: after any sell, the name cannot be rebought for
  `cooldown_bars` (10) bars.
- Eligibility: stock must have enough history and trade above its
  150-day SMA (trend filter).
- Rank hysteresis: buy only from the top N ranks, but keep holding
  until a stock falls out of the top `hold_buffer_mult` x N ranks.
  This cuts churn from rank jitter at fast rebalance cadences.
- Exits (explicit, realized):
  1. Rebalance exit: position falls out of the hold buffer -> close.
  2. Trend exit (checked daily): price closes below SMA150 -> close.
  3. Trailing stop (checked daily): close drops more than `trail_pct`
     below the highest close seen while holding -> close.
"""

import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    params = (
        ('momentum_period', 189),   # look-back for momentum ranking
        ('momentum_skip', 10),      # skip most recent bars (12-1 momentum)
        ('trend_period', 150),      # SMA trend filter / exit
        ('top_n', 20),               # number of positions to hold
        ('rebalance_every', 5),     # bars between rebalances
        ('hold_buffer_mult', 2),    # keep holdings while in top N*mult ranks
        ('trail_pct', 0.15),        # trailing stop below post-entry high close
        ('cooldown_bars', 10),      # bars to wait before re-buying after a daily exit
        ('symbol_names', []),       # required for multi-stock support
    )

    def __init__(self):
        self.sma = {}
        for d in self.datas:
            self.sma[d._name] = bt.indicators.SMA(d.close, period=self.p.trend_period)
        self.symbol_to_data = {d._name: d for d in self.datas}
        self.bar_count = 0
        self.high_water = {}  # symbol -> highest close while holding
        self.cooldown_until = {}  # symbol -> bar_count when re-entry allowed

    def _momentum(self, d):
        """Dual-horizon momentum: long (189-bar) + medium (63-bar) return,
        both measured up to -momentum_skip bars; None if too short."""
        if len(d) <= self.p.momentum_period:
            return None
        past = d.close[-self.p.momentum_period]
        mid = d.close[-63]
        recent = d.close[-self.p.momentum_skip]
        if past <= 0 or mid <= 0:
            return None
        return (recent / past - 1.0) + (recent / mid - 1.0)

    def _eligible(self, d):
        """Enough history and in an uptrend (above SMA200)."""
        if len(d) <= max(self.p.momentum_period, self.p.trend_period):
            return False
        return d.close[0] > self.sma[d._name][0]

    def next(self):
        self.bar_count += 1

        # Daily exits: trend break (below SMA150) or trailing stop
        for d in self.datas:
            pos = self.getposition(d)
            name = d._name
            if not pos:
                self.high_water.pop(name, None)
                continue
            hw = max(self.high_water.get(name, d.close[0]), d.close[0])
            self.high_water[name] = hw
            trend_break = len(d) > self.p.trend_period and d.close[0] < self.sma[name][0]
            stop_hit = d.close[0] < hw * (1.0 - self.p.trail_pct)
            if trend_break or stop_hit:
                self.close(data=d)
                self.cooldown_until[name] = self.bar_count + self.p.cooldown_bars

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
        names_sorted = [name for _, name in ranked]
        buy_list = names_sorted[:self.p.top_n]
        hold_buffer = set(names_sorted[:self.p.top_n * self.p.hold_buffer_mult])

        # Sell positions that fell out of the hold buffer
        kept = set()
        for d in self.datas:
            pos = self.getposition(d)
            if not pos:
                continue
            if d._name in hold_buffer:
                kept.add(d._name)
            else:
                self.close(data=d)
                self.cooldown_until[d._name] = self.bar_count + self.p.cooldown_bars

        # Fill free slots with top-ranked new entrants, roughly equal-weight
        slots = self.p.top_n - len(kept)
        to_buy = [name for name in buy_list
                  if name not in kept
                  and self.bar_count >= self.cooldown_until.get(name, 0)][:max(slots, 0)]
        if not to_buy:
            return
        slot_value = self.broker.getvalue() / self.p.top_n * 0.98
        cash = self.broker.getcash()
        for name in to_buy:
            d = self.symbol_to_data[name]
            price = d.close[0]
            value = min(slot_value, cash)
            size = int(value / price)
            if size > 0:
                self.buy(data=d, size=size)
                cash -= size * price
