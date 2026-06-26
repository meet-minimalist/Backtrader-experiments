import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    EMA(200) + EMA(50) Dual Trend Confirmation

    Logic:
    - Entry: price crosses above EMA(200) AND EMA(50) > EMA(200)
      (medium-term AND long-term trend both aligned upward)
    - Exit: price drops below EMA(200)
    - Position size: 10% of available cash per trade

    Rationale: EMA(200) crossover gave 3.21% XIRR (best so far).
    Adding EMA(50) as dual confirmation filters false crossovers where
    price briefly touches EMA(200) but medium-term trend is still down.
    EMA(50) > EMA(200) means the stock is in a confirmed multi-period uptrend.
    """
    params = (
        ('slow_period', 200),
        ('fast_period', 50),
        ('position_size_pct', 0.10),
        ('symbol_names', []),
    )

    def __init__(self):
        self.ema_slow = {}
        self.ema_fast = {}
        self.crossover = {}
        self.symbol_to_data = {d._name: d for d in self.datas}

        for d in self.datas:
            symbol = d._name
            self.ema_slow[symbol] = bt.indicators.EMA(d.close, period=self.p.slow_period)
            self.ema_fast[symbol] = bt.indicators.EMA(d.close, period=self.p.fast_period)
            self.crossover[symbol] = bt.indicators.CrossOver(d.close, self.ema_slow[symbol])

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            price = d.close[0]
            cross = self.crossover[symbol][0]
            ema_slow = self.ema_slow[symbol][0]
            ema_fast = self.ema_fast[symbol][0]

            if not pos:
                # Enter only when price crosses EMA200 AND EMA50 > EMA200 (dual confirmation)
                if cross > 0 and ema_fast > ema_slow:
                    cash = self.broker.getcash()
                    if cash > price:
                        size = self._calc_size(cash, price)
                        self.buy(data=d, size=size)
            else:
                # Exit on EMA200 breach
                if cross < 0:
                    self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
