"""
Momentum Rotation Strategy
==========================
Logic:
- Every `rebalance_days` bars, rank all stocks by their trailing
  `lookback`-day return (momentum).
- Hold the top `top_n` stocks, equal-weighted by portfolio value.
- Exit any held stock that drops out of the top ranks.
- Sells are submitted before buys so freed cash can fund new entries
  on the next bar.

Rationale: cross-sectional momentum is a persistent anomaly; Indian
large caps trended strongly 2015-2024, so rotating into recent winners
should beat the counter-trend skeleton baseline.
"""

import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    params = (
        ('lookback', 126),        # momentum look-back in bars (~6 months)
        ('top_n', 5),             # number of stocks to hold
        ('rebalance_days', 21),   # rebalance interval in bars (~1 month)
        ('reserve', 0.05),        # cash fraction kept unallocated
        ('symbol_names', []),     # required for multi-stock support
    )

    def __init__(self):
        self.days_since_rebalance = 0

    def next(self):
        self.days_since_rebalance += 1
        if self.days_since_rebalance < self.p.rebalance_days:
            return
        self.days_since_rebalance = 0
        self.rebalance()

    def rebalance(self):
        # Rank stocks with enough history by trailing return
        scores = {}
        for d in self.datas:
            if len(d) > self.p.lookback and d.close[-self.p.lookback] > 0:
                scores[d] = d.close[0] / d.close[-self.p.lookback] - 1.0

        if not scores:
            return

        ranked = sorted(scores, key=scores.get, reverse=True)
        targets = set(ranked[:self.p.top_n])

        # Sell first: anything held that is no longer a target
        for d in self.datas:
            pos = self.getposition(d)
            if pos.size and d not in targets:
                self.close(data=d)

        # Buy/adjust targets to equal weight
        total_value = self.broker.getvalue() * (1.0 - self.p.reserve)
        per_stock = total_value / self.p.top_n
        for d in targets:
            self.order_target_value(data=d, target=per_stock)
