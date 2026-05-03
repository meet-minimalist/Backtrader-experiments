import backtrader as bt


class XIRRAnalyzer(bt.Analyzer):
    """
    Calculates XIRR based on individual trade cash flows.
    This measures the efficiency of deployed capital, ignoring idle cash.
    """

    def __init__(self):
        self.cash_flows = []
        self.open_trades = {}  # Track open positions to handle final valuation

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                # Cash outflow (negative)
                # Note: order.executed.value is positive, so we negate it
                date = bt.num2date(order.executed.dt).date()
                amount = -order.executed.value
                self.cash_flows.append((date, amount))

            elif order.issell():
                # Cash inflow (positive)
                date = bt.num2date(order.executed.dt).date()
                amount = order.executed.value
                self.cash_flows.append((date, amount))

    def stop(self):
        # Handle any OPEN positions at the end of the backtest
        # We treat them as if they were sold at the current market price
        position_values = 0
        for data in self.strategy.datas:
            pos = self.strategy.getposition(data)
            if pos.size != 0:
                # Mark to market
                value = pos.size * data.close[0]
                position_values += value

        if position_values > 0:
            end_date = bt.num2date(self.datas[0].datetime[0]).date()
            # Treat final portfolio value of open trades as an inflow
            self.cash_flows.append((end_date, position_values))

    def _calculate_xirr(self, cash_flows):
        # Same Newton-Raphson implementation as before
        if not cash_flows:
            return None
        cash_flows.sort(key=lambda x: x[0])
        d0 = cash_flows[0][0]

        def npv(rate):
            total = 0.0
            for date, amount in cash_flows:
                days = (date - d0).days
                if days < 0:
                    continue
                total += amount / ((1 + rate) ** (days / 365.0))
            return total

        def npv_derivative(rate):
            total = 0.0
            for date, amount in cash_flows:
                days = (date - d0).days
                if days < 0:
                    continue
                total -= (days / 365.0) * amount / ((1 + rate) ** ((days / 365.0) + 1))
            return total

        rate = 0.1
        for _ in range(100):
            f_val = npv(rate)
            f_deriv = npv_derivative(rate)
            if abs(f_deriv) < 1e-10:
                break
            new_rate = rate - f_val / f_deriv
            if abs(new_rate - rate) < 1e-7:
                return new_rate
            rate = new_rate
        return rate

    def get_analysis(self):
        if not self.cash_flows:
            return {"xirr": None, "message": "No trades executed"}

        xirr_val = self._calculate_xirr(self.cash_flows)

        return {
            "xirr": xirr_val * 100 if xirr_val else None,
            "num_trades": len(
                [f for f in self.cash_flows if f[1] < 0]
            ),  # Approx count of buys
            "total_invested": sum([-f[1] for f in self.cash_flows if f[1] < 0]),
            "total_returned": sum([f[1] for f in self.cash_flows if f[1] > 0]),
        }
