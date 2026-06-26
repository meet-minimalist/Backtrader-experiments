import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    EMA Crossover Trend Following Strategy

    Logic:
    - Uses 12-period EMA (fast) and 26-period EMA (slow) per stock
    - Entry: fast EMA crosses above slow EMA (trend turning up)
    - Exit: fast EMA crosses below slow EMA (trend turning down)
    - Position size: 10% of available cash per trade
    - Supports multi-stock backtests (NIFTY_50 index)

    Rationale: The baseline mean-reversion (buy below SMA) was deeply negative.
    EMA crossover captures trend momentum which suits NIFTY stocks better.
    """
    params = (
        ('fast_period', 12),
        ('slow_period', 26),
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

            # ENTRY: fast crosses above slow (bullish crossover)
            if not pos and cross > 0:
                cash = self.broker.getcash()
                price = d.close[0]
                if cash > price:
                    size = self._calc_size(cash, price)
                    self.buy(data=d, size=size)

            # EXIT: fast crosses below slow (bearish crossover)
            elif pos and cross < 0:
                self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
