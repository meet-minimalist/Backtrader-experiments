"""
Buy & Hold Winners, Cut Losers Fast, Redeploy into Risk-Adjusted Momentum
=========================================================================
Logic:
- Start with an equal-weight buy of every stock as its data appears.
- Every `check_days` (5) bars:
  - SELL any position more than `loss_pct` (5%) below its average entry
    price AND below its 200-day SMA (confirmed downtrend).
  - REDEPLOY available cash equally into the top `top_n` (3) stocks ranked
    by risk-adjusted momentum: 126-day return divided by 63-day daily
    volatility. Only stocks above their 200-day SMA are eligible.
- Winners are never sold; they compound until the end of the backtest.

Rationale: fast loss-cutting recycles dead capital quickly; dividing
momentum by volatility steers redeploys toward steadier trends.
"""

import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    params = (
        ('reserve', 0.02),        # cash fraction kept unallocated
        ('check_days', 5),        # bars between maintenance checks
        ('loss_pct', 0.05),       # loss threshold to cut a position
        ('trend_period', 200),    # SMA period for downtrend confirmation
        ('lookback', 126),        # momentum look-back for redeploys
        ('vol_period', 63),       # look-back for daily-return volatility
        ('top_n', 2),             # number of momentum leaders to add to
        ('symbol_names', []),     # required for multi-stock support
    )

    def __init__(self):
        self.bought = set()
        self.slice_value = None
        self.days_since_check = 0
        self.sma = {}
        self.vol = {}
        for d in self.datas:
            self.sma[d._name] = bt.indicators.SMA(d.close, period=self.p.trend_period)
            daily_ret = bt.indicators.ROC(d.close, period=1)
            self.vol[d._name] = bt.indicators.StdDev(daily_ret, period=self.p.vol_period)

    def next(self):
        # Initial equal-weight deployment
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

        # Periodic maintenance: cut losers, redeploy into leaders
        self.days_since_check += 1
        if self.days_since_check < self.p.check_days:
            return
        self.days_since_check = 0
        self.maintain()

    def maintain(self):
        # Cut losers: in a loss beyond threshold AND below long-term trend
        for d in self.datas:
            pos = self.getposition(d)
            if not pos.size or not len(d):
                continue
            price = d.close[0]
            sma = self.sma[d._name][0]
            if price < pos.price * (1.0 - self.p.loss_pct) and price < sma:
                self.close(data=d)

        # Redeploy free cash into top risk-adjusted momentum stocks
        cash = self.broker.getcash() * (1.0 - self.p.reserve)
        if cash < self.broker.getvalue() * 0.01:
            return

        scores = {}
        for d in self.datas:
            if len(d) > self.p.lookback and d.close[-self.p.lookback] > 0:
                vol = self.vol[d._name][0]
                if d.close[0] > self.sma[d._name][0] and vol > 0:
                    mom = d.close[0] / d.close[-self.p.lookback] - 1.0
                    scores[d] = mom / vol

        if not scores:
            return

        ranked = sorted(scores, key=scores.get, reverse=True)[:self.p.top_n]
        per_stock = cash / len(ranked)
        for d in ranked:
            size = int(per_stock / d.close[0])
            if size > 0:
                self.buy(data=d, size=size)
