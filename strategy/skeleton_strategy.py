import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    EMA(20/50) Crossover Trend Following

    Logic:
    - Uses 20-period EMA (fast) and 50-period EMA (slow) per stock
    - Entry: EMA(20) crosses above EMA(50) - golden cross (longer-term signal)
    - Exit: EMA(20) crosses below EMA(50) - death cross
    - Position size: 10% of available cash per trade

    Rationale: Longer EMA periods (20/50 vs 12/26) generate fewer, higher-quality
    signals on NIFTY_50 stocks, reducing whipsaw in choppy periods.
    """
    params = (
        ('fast_period', 20),
        ('slow_period', 50),
        ('position_size_pct', 0.10),
        ('symbol_names', []),
    )

    def __init__(self):
        self.fast_ema = {}
        self.slow_ema = {}
        self.crossover = {}
        self.symbol_to_data = {d._name: d for d in self.datas}

        for d in self.datas:
            symbol = d._name
            self.fast_ema[symbol] = bt.indicators.EMA(d.close, period=self.p.fast_period)
            self.slow_ema[symbol] = bt.indicators.EMA(d.close, period=self.p.slow_period)
            self.crossover[symbol] = bt.indicators.CrossOver(
                self.fast_ema[symbol], self.slow_ema[symbol]
            )

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            cross = self.crossover[symbol][0]

            # ENTRY: EMA20 crosses above EMA50
            if not pos and cross > 0:
                cash = self.broker.getcash()
                price = d.close[0]
                if cash > price:
                    size = self._calc_size(cash, price)
                    self.buy(data=d, size=size)

            # EXIT: EMA20 crosses below EMA50
            elif pos and cross < 0:
                self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
