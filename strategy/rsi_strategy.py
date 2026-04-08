import backtrader as bt


class RSIStrategy(bt.Strategy):
    """RSI-based strategy."""
    params = (
        ('rsi_period', 14),
        ('rsi_upper', 70),
        ('rsi_lower', 30),
        ('symbol_names', []),  # Add this parameter
    )
    
    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
    
    def next(self):
        if not self.position:
            if self.rsi < self.params.rsi_lower:
                self.buy()
        elif self.rsi > self.params.rsi_upper:
            self.close()
