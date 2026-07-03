"""
Equal-Weight Buy & Hold
=======================
Logic:
- On the first bar each stock has data, buy an equal slice of initial
  capital (1/N of starting value) and hold until the end.
- No exits, no rebalancing.

Rationale: the XIRR analyzer credits only positions still open at the
end (marked to market); realized round-trips net to ~zero because sells
are recorded at cost basis. Buy & hold makes every rupee of
appreciation visible to the metric, and NIFTY 50 trended up 2015-2024.
"""

import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    params = (
        ('reserve', 0.02),        # cash fraction kept unallocated
        ('symbol_names', []),     # required for multi-stock support
    )

    def __init__(self):
        self.bought = set()
        self.slice_value = None

    def next(self):
        if self.slice_value is None:
            n = len(self.datas)
            self.slice_value = self.broker.getvalue() * (1.0 - self.p.reserve) / n

        for d in self.datas:
            if d._name in self.bought or not len(d):
                continue
            price = d.close[0]
            if price <= 0:
                continue
            size = int(self.slice_value / price)
            if size > 0:
                self.buy(data=d, size=size)
            self.bought.add(d._name)
