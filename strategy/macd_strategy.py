import backtrader as bt


class MACDStrategy(bt.Strategy):
    """MACD crossover strategy."""
    params = (
        ('fast_ema', 12),
        ('slow_ema', 26),
        ('signal', 9),
        ('symbol_names', []),  # Add this parameter
    )
    
    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_ema,
            period_me2=self.params.slow_ema,
            period_signal=self.params.signal
        )
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
    
    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()

