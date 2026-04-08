import backtrader as bt
import numpy as np


class SortinoRatio(bt.Analyzer):
    """Custom Sortino Ratio Analyzer"""
    params = (('riskfreerate', 0.06), ('timeframe', bt.TimeFrame.Days),)

    def __init__(self):
        super(SortinoRatio, self).__init__()
        self.returns = []

    def start(self):
        self.start_value = self.strategy.broker.getvalue()

    def next(self):
        current_value = self.strategy.broker.getvalue()
        if hasattr(self, 'last_value') and self.last_value != 0:
            daily_return = (current_value - self.last_value) / self.last_value
            self.returns.append(daily_return)
        self.last_value = current_value

    def stop(self):
        if len(self.returns) == 0:
            self.ratio = 0
            return

        returns_array = np.array(self.returns)
        total_return = (self.strategy.broker.getvalue() - self.start_value) / self.start_value
        annualized_return = (1 + total_return) ** (252 / len(self.returns)) - 1
        
        negative_returns = returns_array[returns_array < 0]
        if len(negative_returns) == 0:
            self.ratio = 0
            return
            
        downside_deviation = np.std(negative_returns) * np.sqrt(252)
        excess_return = annualized_return - self.params.riskfreerate
        self.ratio = excess_return / downside_deviation if downside_deviation != 0 else 0

    def get_analysis(self):
        return {'sortinoratio': self.ratio}