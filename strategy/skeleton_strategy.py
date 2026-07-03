"""
Equal-weight buy-and-hold strategy.

Logic:
- On the first bar, split available cash equally across all stocks that
  have data and buy them. Hold to the end of the backtest.
- Stocks whose data starts later (e.g. later listings) are bought when
  their feed comes alive, using an equal share of remaining cash spread
  over the remaining unbought names.
- No exits: the XIRR analyzer marks open positions to market at the end.
"""

import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    params = (
        ('symbol_names', []),   # required for multi-stock support
    )

    def __init__(self):
        self.symbol_to_data = {d._name: d for d in self.datas}
        self.bought = set()

    def next(self):
        unbought = [
            (symbol, d) for symbol, d in self.symbol_to_data.items()
            if symbol not in self.bought
        ]
        if not unbought:
            return

        live = [(symbol, d) for symbol, d in unbought if len(d) > 0]
        if not live:
            return

        # Equal share of current cash over all remaining unbought names,
        # so late-starting feeds keep a comparable allocation.
        cash = self.broker.getcash() * 0.98
        slot = cash / len(unbought)
        for symbol, d in live:
            price = d.close[0]
            size = int(slot / price)
            if size > 0:
                self.buy(data=d, size=size)
            self.bought.add(symbol)
