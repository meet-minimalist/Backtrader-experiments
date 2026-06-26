import backtrader as bt
import datetime

class TradePerformanceAnalyzer(bt.Analyzer):
    """
    Calculates strategy efficiency metrics:
    1. Total Net Profit
    2. Total Invested Capital (Sum of all buy values)
    3. Average Holding Period
    4. Annualized Return on Capital (Simple Approximation)
    """

    def __init__(self):
        self.trades = []
        self.total_profit = 0
        self.total_invested = 0
        self.total_holding_days = 0
        self.num_trades = 0

    def notify_trade(self, trade):
        if trade.isclosed:
            # Calculate holding period
            dt_open = bt.num2date(trade.dtopen)
            dt_close = bt.num2date(trade.dtclose)
            holding_days = (dt_close - dt_open).days
            if holding_days < 1: holding_days = 1 # Avoid division by zero

            profit = trade.pnlcomm # Profit after commission
            
            self.total_profit += profit
            self.total_invested += abs(trade.value) # Value of the trade at entry
            self.total_holding_days += holding_days
            self.num_trades += 1

    def get_analysis(self):
        if self.num_trades == 0:
            return {
                'total_profit': 0,
                'num_trades': 0,
                'avg_holding_days': 0,
                'annualized_roce': 0
            }

        avg_holding_days = self.total_holding_days / self.num_trades
        
        # Simple Annualized Return on Capital Employed (ROCE)
        # Formula: (Total Profit / Total Invested) * (365 / Avg Holding Days)
        # This tells you: "For every dollar I put into a trade, how much did I make annualized?"
        
        if self.total_invested > 0:
            total_return_on_capital = self.total_profit / self.total_invested
            # Annualize based on average trade duration
            annualized_roce = total_return_on_capital * (365 / avg_holding_days)
        else:
            annualized_roce = 0

        return {
            'total_profit': self.total_profit,
            'num_trades': self.num_trades,
            'total_invested_volume': self.total_invested,
            'avg_holding_days': avg_holding_days,
            'annualized_roce_pct': annualized_roce * 100,
            'total_return_on_capital_pct': (self.total_profit / self.total_invested * 100) if self.total_invested > 0 else 0
        }