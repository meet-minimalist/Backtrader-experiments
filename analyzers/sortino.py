import backtrader as bt
import numpy as np


class SortinoRatio(bt.Analyzer):
    """
    Sortino Ratio analyzer for downside risk assessment.

    Correctly handles risk-free rate conversion from annual to daily.
    """
    params = (
        ('riskfreerate', 0.06),
        ('timeframe', bt.TimeFrame.Days),
    )

    def __init__(self):
        self.returns = []
        self.start_value = None
        self.last_value = None
        self.trading_days_per_year = 252

    def start(self):
        self.start_value = self.strategy.broker.getvalue()
        self.last_value = self.start_value

    def next(self):
        current_value = self.strategy.broker.getvalue()
        if self.last_value != 0:
            daily_return = (current_value - self.last_value) / self.last_value
            self.returns.append(daily_return)
        self.last_value = current_value

    def stop(self):
        if len(self.returns) == 0:
            self._analysis = {
                'sortinoratio': None,
                'annualized_return': 0,
                'downside_deviation': 0,
                'total_return': 0
            }
            return

        returns_array = np.array(self.returns)

        # Convert annual risk-free rate to daily rate
        daily_riskfree = (1 + self.params.riskfreerate) ** (1 / self.trading_days_per_year) - 1

        # Calculate downside deviation (returns below risk-free rate)
        downside_returns = returns_array[returns_array < daily_riskfree]
        if len(downside_returns) == 0:
            # No downside - infinite Sortino
            self._analysis = {
                'sortinoratio': float('inf'),
                'annualized_return': 0,
                'downside_deviation': 0,
                'total_return': 0,
                'message': 'No downside deviation'
            }
            return

        # Downside deviation (annualized)
        downside_deviation = np.sqrt(np.mean(downside_returns ** 2)) * np.sqrt(self.trading_days_per_year)

        # Calculate annualized return
        total_return = (self.last_value / self.start_value) - 1
        years = len(self.returns) / self.trading_days_per_year
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # Sortino Ratio = (Annualized Return - Annual Risk-Free Rate) / Annualized Downside Deviation
        excess_return = annualized_return - self.params.riskfreerate
        sortino = excess_return / downside_deviation if downside_deviation > 0 else float('inf')

        self._analysis = {
            'sortinoratio': sortino,
            'annualized_return': annualized_return * 100,
            'annual_riskfree': self.params.riskfreerate * 100,
            'downside_deviation': downside_deviation * 100,
            'total_return': total_return * 100,
            'trading_days': len(self.returns)
        }

    def get_analysis(self):
        return getattr(self, '_analysis', {'sortinoratio': None})
