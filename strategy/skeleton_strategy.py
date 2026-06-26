import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    SMA(200) Trend Following with Hard Stop Loss

    Logic:
    - Entry: price crosses above SMA(200)
    - Exit: price drops below SMA(200) OR price falls 12% below entry price
    - Position size: 10% of available cash per trade

    Rationale: SMA200 baseline (3.09% XIRR, 18.16% drawdown) is best so far.
    Adding a 12% hard stop loss prevents individual positions from contributing
    to large drawdowns while keeping the trend-following core intact.
    This should improve Sharpe/Sortino without sacrificing much XIRR.
    """
    params = (
        ('trend_period', 200),
        ('stop_loss_pct', 0.12),
        ('position_size_pct', 0.10),
        ('symbol_names', []),
    )

    def __init__(self):
        self.sma200 = {}
        self.crossover = {}
        self.entry_price = {}
        self.symbol_to_data = {d._name: d for d in self.datas}

        for d in self.datas:
            symbol = d._name
            self.sma200[symbol] = bt.indicators.SMA(d.close, period=self.p.trend_period)
            self.crossover[symbol] = bt.indicators.CrossOver(d.close, self.sma200[symbol])
            self.entry_price[symbol] = 0.0

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            price = d.close[0]
            cross = self.crossover[symbol][0]

            if not pos:
                if cross > 0:
                    cash = self.broker.getcash()
                    if cash > price:
                        size = self._calc_size(cash, price)
                        self.buy(data=d, size=size)
                        self.entry_price[symbol] = price
            else:
                ep = self.entry_price[symbol]
                stop_hit = ep > 0 and price <= ep * (1 - self.p.stop_loss_pct)
                sma_break = cross < 0
                if stop_hit or sma_break:
                    self.close(data=d)
                    self.entry_price[symbol] = 0.0

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
