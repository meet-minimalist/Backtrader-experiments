"""
Golden Cross Momentum Strategy
================================
Buy Rules:
  1. 50-day MA crosses above 200-day MA (Golden Cross)
  2. Stock is currently trading ABOVE its 50-day MA at crossover

Sell Rules:
  1. Emergency Stop Loss: Stock falls 15% from entry price → sell immediately
  2. Death Cross: 50-day MA closes BELOW 200-day MA → sell next open
  3. Profit Target: Stock rises 300% from entry price → sell immediately
"""

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as btanalyzers
import datetime


class GoldenCrossoverStrategy(bt.Strategy):
    params = (
        ('fast_period', 50),    # Fast (short) moving average period
        ('slow_period', 200),   # Slow (long) moving average period
        ('stop_loss_pct', 0.15),     # 15% stop loss below entry
        ('profit_target_pct', 3.00), # 300% profit target above entry
        ('printlog', True),          # Print trade logs
    )

    def __init__(self):
        # Moving averages for each data feed
        self.ma_fast = {}
        self.ma_slow = {}
        self.crossover = {}

        # Track entry prices and order refs per data
        self.entry_price = {}
        self.order = {}
        self.stop_order = {}

        for data in self.datas:
            self.ma_fast[data] = bt.indicators.SimpleMovingAverage(
                data.close, period=self.p.fast_period
            )
            self.ma_slow[data] = bt.indicators.SimpleMovingAverage(
                data.close, period=self.p.slow_period
            )
            # CrossOver: +1 when fast crosses above slow, -1 when fast crosses below slow
            self.crossover[data] = bt.indicators.CrossOver(
                self.ma_fast[data], self.ma_slow[data]
            )
            self.entry_price[data] = None
            self.order[data] = None
            self.stop_order[data] = None

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'[{dt}] {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return  # Order pending, nothing to do

        data = order.data

        if order.status == order.Completed:
            if order.isbuy():
                self.entry_price[data] = order.executed.price
                self.log(
                    f'BUY EXECUTED | {data._name} | '
                    f'Price: {order.executed.price:.2f} | '
                    f'Size: {order.executed.size} | '
                    f'Cost: {order.executed.value:.2f} | '
                    f'Comm: {order.executed.comm:.2f}'
                )
            elif order.issell():
                self.log(
                    f'SELL EXECUTED | {data._name} | '
                    f'Price: {order.executed.price:.2f} | '
                    f'Size: {order.executed.size} | '
                    f'PnL: {order.executed.pnl:.2f}'
                )
                self.entry_price[data] = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ORDER FAILED | {data._name} | Status: {order.getstatusname()}')

        # Clear the order reference
        if self.order[data] is order:
            self.order[data] = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(
            f'TRADE CLOSED | {trade.data._name} | '
            f'Gross PnL: {trade.pnl:.2f} | Net PnL: {trade.pnlcomm:.2f}'
        )

    def next(self):
        for data in self.datas:
            # Skip if there's a pending order for this data
            if self.order[data]:
                continue

            position = self.getposition(data)
            close = data.close[0]
            ma_fast_val = self.ma_fast[data][0]
            ma_slow_val = self.ma_slow[data][0]

            # ─── IN POSITION: Check exit conditions ───────────────────────
            if position:
                entry = self.entry_price[data]
                if entry is None:
                    continue

                pct_change = (close - entry) / entry

                # EXIT RULE 1: Emergency Stop Loss — stock fell 15% from entry
                if pct_change <= -self.p.stop_loss_pct:
                    self.log(
                        f'STOP LOSS TRIGGERED | {data._name} | '
                        f'Entry: {entry:.2f} | Current: {close:.2f} | '
                        f'Loss: {pct_change*100:.2f}%'
                    )
                    self.order[data] = self.close(data=data)
                    continue

                # EXIT RULE 2: Death Cross — 50MA closes BELOW 200MA → sell next open
                if self.crossover[data][0] == -1:
                    self.log(
                        f'DEATH CROSS | {data._name} | '
                        f'50MA: {ma_fast_val:.2f} crossed below 200MA: {ma_slow_val:.2f} | '
                        f'Sell at next open'
                    )
                    self.order[data] = self.close(data=data, exectype=bt.Order.Market)
                    continue

                # EXIT RULE 3: 300% Profit Target
                if pct_change >= self.p.profit_target_pct:
                    self.log(
                        f'PROFIT TARGET HIT | {data._name} | '
                        f'Entry: {entry:.2f} | Current: {close:.2f} | '
                        f'Gain: {pct_change*100:.2f}%'
                    )
                    self.order[data] = self.close(data=data)
                    continue

            # ─── NOT IN POSITION: Check entry conditions ──────────────────
            else:
                # ENTRY: Golden Cross AND price is above 50MA
                golden_cross = self.crossover[data][0] == 1
                price_above_fast_ma = close > ma_fast_val

                if golden_cross and price_above_fast_ma:
                    self.log(
                        f'BUY SIGNAL | {data._name} | '
                        f'50MA: {ma_fast_val:.2f} crossed above 200MA: {ma_slow_val:.2f} | '
                        f'Price {close:.2f} > 50MA {ma_fast_val:.2f} ✓ | '
                        f'Buying at next open'
                    )
                    # Buy at next market open
                    self.order[data] = self.buy(
                        data=data,
                        exectype=bt.Order.Market,
                    )

