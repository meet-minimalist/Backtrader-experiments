import backtrader as bt


class SimpleSMAStrategy(bt.Strategy):
    """Simple SMA crossover strategy."""
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('symbol_names', []),  # Add this parameter
    )
    
    def __init__(self):
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
    
    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()
