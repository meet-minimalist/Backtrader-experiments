import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    EMA Crossover + SMA(50) Trend Filter

    Logic:
    - Uses 12-period EMA (fast), 26-period EMA (slow), and SMA(50) as trend filter
    - Entry: fast EMA crosses above slow EMA AND price is above SMA(50)
    - Exit: fast EMA crosses below slow EMA OR price drops below SMA(50)
    - Position size: 10% of available cash per trade

    Rationale: Adding a long-term trend filter (SMA50) to the EMA crossover reduces
    false signals in downtrending stocks, keeping us on the right side of the trend.
    """
    params = (
        ('fast_period', 12),
        ('slow_period', 26),
        ('trend_period', 50),
        ('position_size_pct', 0.10),
        ('symbol_names', []),
    )

    def __init__(self):
        self.fast_ema = {}
        self.slow_ema = {}
        self.trend_sma = {}
        self.crossover = {}
        self.symbol_to_data = {d._name: d for d in self.datas}

        for d in self.datas:
            symbol = d._name
            self.fast_ema[symbol] = bt.indicators.EMA(d.close, period=self.p.fast_period)
            self.slow_ema[symbol] = bt.indicators.EMA(d.close, period=self.p.slow_period)
            self.trend_sma[symbol] = bt.indicators.SMA(d.close, period=self.p.trend_period)
            self.crossover[symbol] = bt.indicators.CrossOver(
                self.fast_ema[symbol], self.slow_ema[symbol]
            )

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            cross = self.crossover[symbol][0]
            price = d.close[0]
            trend = self.trend_sma[symbol][0]

            # ENTRY: bullish crossover AND price in uptrend (above SMA50)
            if not pos and cross > 0 and price > trend:
                cash = self.broker.getcash()
                if cash > price:
                    size = self._calc_size(cash, price)
                    self.buy(data=d, size=size)

            # EXIT: bearish crossover OR price breaks below trend filter
            elif pos and (cross < 0 or price < trend):
                self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
