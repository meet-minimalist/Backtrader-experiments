import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    SMA(200) Trend Following - Long-Hold Strategy

    Logic:
    - Uses SMA(200) as the primary trend filter (long-term trend)
    - Entry: price crosses above SMA(200) for the first time (no existing position)
    - Also enter if price is already above SMA(200) and no position held
    - Exit: price drops below SMA(200)
    - Position size: 10% of available cash per trade

    Rationale: SMA(200) is the gold standard long-term trend indicator.
    On NIFTY_50 stocks during 2015-2024 bull market, most stocks spend the
    majority of time above SMA(200). Few signals = less commission drag.
    Captures major multi-year trends rather than short-term noise.
    """
    params = (
        ('trend_period', 200),
        ('position_size_pct', 0.10),
        ('symbol_names', []),
    )

    def __init__(self):
        self.sma200 = {}
        self.crossover = {}
        self.symbol_to_data = {d._name: d for d in self.datas}

        for d in self.datas:
            symbol = d._name
            self.sma200[symbol] = bt.indicators.SMA(d.close, period=self.p.trend_period)
            self.crossover[symbol] = bt.indicators.CrossOver(d.close, self.sma200[symbol])

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            price = d.close[0]
            sma = self.sma200[symbol][0]
            cross = self.crossover[symbol][0]

            # ENTRY: price just crossed above SMA200
            if not pos and cross > 0:
                cash = self.broker.getcash()
                if cash > price:
                    size = self._calc_size(cash, price)
                    self.buy(data=d, size=size)

            # EXIT: price dropped below SMA200
            elif pos and cross < 0:
                self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
