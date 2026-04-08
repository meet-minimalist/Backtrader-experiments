import backtrader as bt


class XIRRAnalyzer(bt.Analyzer):
    """
    XIRR (Extended Internal Rate of Return) analyzer.

    Only tracks INITIAL and FINAL portfolio values.
    Internal trades are NOT external cash flows.
    """

    def __init__(self):
        self.initial_value = None
        self.final_value = None
        self.start_date = None
        self.end_date = None
        self.first_bar = True

    def start(self):
        # Record initial portfolio value
        self.initial_value = self.strategy.broker.getvalue()

    def prenext(self):
        if self.first_bar:
            self.start_date = bt.num2date(self.datas[0].datetime[0]).date()
            self.first_bar = False

    def next(self):
        if self.first_bar:
            self.start_date = bt.num2date(self.datas[0].datetime[0]).date()
            self.first_bar = False

        # Track latest date
        self.end_date = bt.num2date(self.datas[0].datetime[0]).date()

    def stop(self):
        self.final_value = self.strategy.broker.getvalue()

    def get_analysis(self):
        if (self.initial_value is None or
            self.final_value is None or
            self.start_date is None or
            self.end_date is None):
            return {
                'xirr': None,
                'initial_value': self.initial_value,
                'final_value': self.final_value,
                'days': None,
                'message': 'Insufficient data'
            }

        days = (self.end_date - self.start_date).days
        if days <= 0:
            return {
                'xirr': None,
                'initial_value': self.initial_value,
                'final_value': self.final_value,
                'days': days,
                'message': f'Invalid period: {days} days'
            }

        total_return = (self.final_value / self.initial_value) - 1
        years = days / 365.0
        xirr = ((1 + total_return) ** (1 / years)) - 1

        return {
            'xirr': xirr * 100,  # As percentage
            'initial_value': self.initial_value,
            'final_value': self.final_value,
            'days': days,
            'total_return': total_return * 100
        }
