import backtrader as bt
import pandas as pd

# TODO: Need to check the correctness of this implementation.

class XIRRAnalyzer(bt.Analyzer):
    """
    Custom XIRR (Extended Internal Rate of Return) analyzer.
    Calculates time-weighted return considering all cash flows:
    - Initial investment (outflow)
    - Stock purchases (outflows)
    - Stock sales (inflows)
    - Final portfolio value (inflow)
    """
    
    def __init__(self):
        self.cash_flows = []
        self.dates = []
        self.start_date = None
        self.start_cash = None
        
    def start(self):
        # Initial investment (negative cash flow - money going out)
        self.start_cash = self.strategy.broker.getvalue()
        self.start_date = self.strategy.datetime.date(0)
        self.cash_flows.append(-self.start_cash)
        self.dates.append(self.start_date)
    
    def notify_order(self, order):
        """Record cash flows when orders are executed."""
        if order.status in [order.Completed]:
            order_date = bt.num2date(order.executed.dt).date()
            
            # Calculate the cash flow from this order
            # Buy order: negative cash flow (money out)
            # Sell order: positive cash flow (money in)
            # executed.value includes price * size
            # executed.comm is the commission
            
            if order.isbuy():
                # Money going out (negative)
                cash_flow = -(order.executed.value + order.executed.comm)
            else:  # Sell order
                # Money coming in (positive)
                cash_flow = order.executed.value - order.executed.comm
            
            self.cash_flows.append(cash_flow)
            self.dates.append(order_date)
    
    def stop(self):
        # Final portfolio value (positive cash flow - money coming back)
        final_value = self.strategy.broker.getvalue()
        final_date = self.strategy.datetime.date(0)
        
        self.cash_flows.append(final_value)
        self.dates.append(final_date)
        
        # Calculate XIRR
        xirr = self._calculate_xirr(self.cash_flows, self.dates)
        self.rets['xirr'] = xirr
        self.rets['cash_flows'] = self.cash_flows.copy()
        self.rets['dates'] = [d.strftime('%Y-%m-%d') for d in self.dates]
        self.rets['num_cash_flows'] = len(self.cash_flows)
    
    def _calculate_xirr(self, cash_flows, dates):
        """Calculate XIRR using Newton-Raphson method."""
        if len(cash_flows) < 2:
            return None
        
        # Convert dates to days from first date
        days = [(d - dates[0]).days for d in dates]
        
        # Initial guess
        rate = 0.1
        
        # Newton-Raphson iteration
        max_iterations = 1000
        tolerance = 1e-6
        
        for iteration in range(max_iterations):
            npv = sum(cf / ((1 + rate) ** (day / 365.0)) for cf, day in zip(cash_flows, days))
            dnpv = sum(-cf * day / 365.0 / ((1 + rate) ** (day / 365.0 + 1)) for cf, day in zip(cash_flows, days))
            
            if abs(npv) < tolerance:  # Convergence
                break
            
            if abs(dnpv) < 1e-10:  # Avoid division by zero
                return None
            
            new_rate = rate - npv / dnpv
            
            # Prevent extreme values
            if new_rate < -0.99:
                new_rate = -0.99
            elif new_rate > 10:
                new_rate = 10
                
            rate = new_rate
        
        return rate * 100  # Return as percentage
