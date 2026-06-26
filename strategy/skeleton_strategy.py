import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    EMA(200) Trend Following - Exponential vs Simple Moving Average

    Logic:
    - Entry: price crosses above EMA(200) (exponential, more responsive than SMA)
    - Exit: price drops below EMA(200)
    - Position size: 10% of available cash per trade

    Rationale: EMA(200) responds faster to recent price changes than SMA(200).
    In trend reversals (like COVID recovery), EMA200 would cross earlier than SMA200,
    potentially capturing more of the initial upswing. In downtrends, EMA200 also
    exits faster (better downside protection). This tests if faster response helps.
    """
    params = (
        ('trend_period', 200),
        ('position_size_pct', 0.10),
        ('symbol_names', []),
    )

    def __init__(self):
        self.ema200 = {}
        self.crossover = {}
        self.symbol_to_data = {d._name: d for d in self.datas}

        for d in self.datas:
            symbol = d._name
            self.ema200[symbol] = bt.indicators.EMA(d.close, period=self.p.trend_period)
            self.crossover[symbol] = bt.indicators.CrossOver(d.close, self.ema200[symbol])

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            price = d.close[0]
            cross = self.crossover[symbol][0]

            if not pos and cross > 0:
                cash = self.broker.getcash()
                if cash > price:
                    size = self._calc_size(cash, price)
                    self.buy(data=d, size=size)
            elif pos and cross < 0:
                self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
