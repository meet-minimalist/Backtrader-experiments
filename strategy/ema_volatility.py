import backtrader as bt
import numpy as np

class EmaVolatilityStrategy(bt.Strategy):
    params = (
        ('ema_period', 200),
        ('std_dev_period', 50),
        ('avg_std_dev_period', 50),  # Lookback for the "average" of the rolling std dev
        ('buy_threshold', 0.3),
        ('sell_threshold', 2.0),
    )

    def __init__(self):
        # 1. Compute 200 EMA
        self.ema = bt.indicators.ExponentialMovingAverage(
            self.data.close, 
            period=self.params.ema_period
        )

        # 2. Compute Rolling 50-day Standard Deviation of the EMA
        # We use StdDev indicator on the EMA line
        self.rolling_std_dev = bt.indicators.StandardDeviation(
            self.ema, 
            period=self.params.std_dev_period
        )

        # 3. Compute Average Rolling Standard Deviation
        # This is the SMA of the rolling_std_dev over the last N periods
        self.avg_rolling_std_dev = bt.indicators.SimpleMovingAverage(
            self.rolling_std_dev, 
            period=self.params.avg_std_dev_period
        )

        # For debugging/logging
        self.buy_signal = False
        self.sell_signal = False

    def next(self):
        # Ensure we have enough data for all indicators
        if len(self) < self.params.ema_period + self.params.std_dev_period + self.params.avg_std_dev_period:
            return

        current_std = self.rolling_std_dev[0]
        avg_std = self.avg_rolling_std_dev[0]

        # Avoid division by zero or NaNs
        if avg_std <= 0 or np.isnan(avg_std) or np.isnan(current_std):
            return

        # Calculate thresholds
        lower_threshold = self.params.buy_threshold * avg_std
        upper_threshold = self.params.sell_threshold * avg_std

        # Reset signals
        self.buy_signal = False
        self.sell_signal = False

        # Check Conditions
        if current_std < lower_threshold:
            self.buy_signal = True
        elif current_std > upper_threshold:
            self.sell_signal = True

        # Execution Logic
        if self.position:
            if self.sell_signal:
                self.close()
                self.log(f'SELL EXECUTED: StdDev {current_std:.4f} > {upper_threshold:.4f}')
        else:
            if self.buy_signal:
                self.buy()
                self.log(f'BUY EXECUTED: StdDev {current_std:.4f} < {lower_threshold:.4f}')

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')