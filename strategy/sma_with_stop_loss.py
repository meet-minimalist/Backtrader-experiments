"""
STRATEGY: SMA Mean Reversion
DATE: 2025-04-07
VERSION: 1.0

LOGIC SUMMARY:
- Entry: Buy when stock price drops below its 20-day SMA (mean reversion signal)
- Exit: Sell when price recovers to 6% above average entry price
- Position Sizing: 10% of available cash per trade
- Risk Management: Max 3 positions per stock (averaging down allowed)
- Ranking: Select top 5 stocks furthest below their SMA

INDICATORS USED:
- SMA(20): Simple moving average for mean reversion signal
- (Add more indicators below as needed)

ENTRY CONDITIONS:
1. Stock is not already in a position
2. Current price < SMA(20) (stock is below its average)
3. Available cash > stock price
4. Ranked by how far below SMA (buy biggest dips first)

EXIT CONDITIONS:
1. Current price >= average entry price * 1.06 (6% profit target)

AVERAGING DOWN:
- Allowed up to 3 times per stock
- Triggered when price drops 3% below last buy price
- Prioritizes stock with largest drawdown

MODIFICATION NOTES:
- [Log changes here with date and description]
- 2025-04-07: Initial skeleton - SMA mean reversion baseline
"""

import backtrader as bt
from datetime import time


class SMAWithStopLossStrategy(bt.Strategy):
    """
    SKELETON STRATEGY - Modify this file for your experiments.

    This is a template with all the common functions you'll need.
    Change the logic, add indicators, modify parameters freely.

    HOW TO MODIFY:
    1. Change parameters below to tune behavior
    2. Add indicators in __init__()
    3. Modify update_stock_metrics() for your signals
    4. Change check_entry_conditions() for your entry logic
    5. Change check_exit_conditions() for your exit logic
    6. Update the docstring above with your strategy logic
    """

    # ========================================================================
    # PARAMETERS - TUNE THESE
    # ========================================================================

    params = (
        # Position management
        ('max_positions_per_stock', 3),   # Max times to add to same stock
        ('position_size_pct', 0.10),      # 10% of cash per trade

        # Entry logic
        ('sma_period', 20),               # Period for SMA calculation
        ('ranking_count', 5),             # How many top stocks to consider

        # Exit logic
        ('exit_threshold', 0.06),         # 6% profit target from average entry

        # Averaging down
        ('averaging_down_threshold', 0.03),  # 3% drop triggers averaging

        # Timing (optional)
        ('end_of_day_time', time(15, 20)),   # Only trade after this time

        # DO NOT REMOVE: Required for multi-stock support
        ('symbol_names', []),
    )

    # ========================================================================
    # INITIALIZATION - Add your indicators here
    # ========================================================================

    def __init__(self):
        """
        Called once at the start. Initialize your indicators and trackers here.

        WHAT TO MODIFY:
        - Add new indicators for each data feed
        - Initialize tracking dictionaries for your signals
        """
        # --- Indicators (one per stock) ---
        self.sma = {}          # Simple moving average
        # self.rsi = {}        # Example: Relative Strength Index
        # self.atr = {}        # Example: Average True Range
        # self.ema = {}        # Example: Exponential Moving Average
        # self.bbands = {}     # Example: Bollinger Bands
        # self.macd = {}       # Example: MACD

        for d in self.datas:
            symbol = d._name
            self.sma[symbol] = bt.indicators.SMA(d.close, period=self.p.sma_period)
            # Add more indicators here:
            # self.rsi[symbol] = bt.indicators.RSI(d.close, period=14)
            # self.atr[symbol] = bt.indicators.ATR(d, period=14)

        # --- Position tracking ---
        self.symbol_to_data = {}      # symbol -> data feed
        self.buy_history = {}         # symbol -> list of {price, size, value}
        self.average_price = {}       # symbol -> average entry price
        self.current_prices = {}      # symbol -> latest price
        self.signals = {}             # symbol -> your custom signal values

        for d in self.datas:
            symbol = d._name
            self.symbol_to_data[symbol] = d
            self.buy_history[symbol] = []
            self.average_price[symbol] = 0.0
            self.current_prices[symbol] = d.close[0]
            self.signals[symbol] = 0.0

        # --- Metadata ---
        self.start_date = self.datas[0].datetime.date(0)
        self.start_value = self.broker.getvalue()
        print(f"🚀 Starting Backtest on {self.start_date}")

    # ========================================================================
    # MAIN LOOP - Called every bar
    # ========================================================================

    def next(self):
        """
        Called every bar (day) for all stocks. This is your main loop.

        WHAT TO MODIFY:
        - Add timing filters if needed
        - Call your update and check functions
        - Add any pre-trade logic
        """
        # Optional: Only trade at specific times
        # current_time = self.data.datetime.time()
        # if current_time < self.p.end_of_day_time:
        #     return

        # Update your metrics and signals
        self.update_stock_metrics()

        # Check if any positions should be closed
        self.check_exit_conditions()

        # Check if any new positions should be opened
        self.check_entry_conditions()

    # ========================================================================
    # METRICS UPDATE - Calculate your signals here
    # ========================================================================

    def update_stock_metrics(self):
        """
        Update prices and calculate your indicators/signals for all stocks.

        WHAT TO MODIFY:
        - Add your custom signal calculations
        - Update self.signals[symbol] with your entry/exit scores
        """
        for d in self.datas:
            symbol = d._name
            current_price = d.close[0]
            sma_value = self.sma[symbol][0]

            # Update trackers
            self.current_prices[symbol] = current_price

            # Example: Calculate how far below SMA (mean reversion signal)
            # Positive = below SMA (potential buy), Negative = above SMA
            if sma_value > 0:
                self.signals[symbol] = (sma_value - current_price) / sma_value
            else:
                self.signals[symbol] = 0.0

            # Add your custom calculations here:
            # self.signals[symbol] = your_custom_logic

    # ========================================================================
    # EXIT LOGIC - When to close positions
    # ========================================================================

    def check_exit_conditions(self):
        """
        Check all open positions for exit signals.

        WHAT TO MODIFY:
        - Change exit conditions (profit targets, stop losses, indicators)
        - Add trailing stops
        - Add time-based exits
        """
        for symbol in list(self.average_price.keys()):
            avg_price = self.average_price[symbol]
            current_price = self.current_prices[symbol]

            # Skip if no position
            if avg_price <= 0:
                continue

            # Exit: Price reached profit target
            if current_price >= avg_price * (1 + self.p.exit_threshold):
                d = self.symbol_to_data[symbol]
                position = self.getposition(d)
                if position.size > 0:
                    print(f"🎯 EXIT: {symbol} @ {current_price:.2f} (avg: {avg_price:.2f})")
                    self.close(data=d)
                    self.buy_history[symbol] = []
                    self.average_price[symbol] = 0.0

            # Add more exit conditions here:
            # if your_stop_loss_hit:
            #     self.close(data=d)

    # ========================================================================
    # ENTRY LOGIC - When to open positions
    # ========================================================================

    def check_entry_conditions(self):
        """
        Check for new entry opportunities.

        WHAT TO MODIFY:
        - Change entry signal logic
        - Add filters (volume, trend, market regime)
        - Modify ranking/scoring system
        """
        # Get ranked list of stocks based on your signals
        ranked_stocks = self.get_ranked_stocks()

        # Try to enter a new position
        new_stock_bought = self.try_new_stock_entry(ranked_stocks)

        # If no new entry, try averaging down on existing positions
        if not new_stock_bought:
            self.try_averaging_down()

    def get_ranked_stocks(self):
        """
        Rank stocks by your entry signal strength.

        WHAT TO MODIFY:
        - Change ranking logic (use different signals)
        - Add filters to exclude certain stocks
        - Return list of (symbol, score) sorted by preference
        """
        valid_stocks = []
        for symbol, signal in self.signals.items():
            # Example: Only consider stocks with positive signal (below SMA)
            if signal > 0:
                valid_stocks.append((symbol, signal))

        # Sort by signal strength (highest first = biggest dip)
        valid_stocks.sort(key=lambda x: x[1], reverse=True)

        # Return top N candidates
        return valid_stocks[:self.p.ranking_count]

    def try_new_stock_entry(self, ranked_stocks):
        """
        Try to open a new position in the best ranked stock.

        WHAT TO MODIFY:
        - Add entry filters (volume, sector, correlation)
        - Change position sizing logic
        - Add confirmation signals before entry
        """
        for symbol, signal in ranked_stocks:
            d = self.symbol_to_data[symbol]
            position = self.getposition(d)

            # Only enter if no existing position
            if position.size == 0:
                cash = self.broker.getcash()
                price = self.current_prices[symbol]

                if cash > price:
                    size = self.calculate_position_size(cash, price)
                    print(f"🛒 NEW ENTRY: {symbol} @ {price:.2f} (signal: {signal:.3f})")
                    self.buy(data=d, size=size)
                    self.record_buy_order(symbol, price, size)
                    return True  # One entry per bar

        return False

    # ========================================================================
    # AVERAGING DOWN - Add to losing positions
    # ========================================================================

    def try_averaging_down(self):
        """
        Add to existing positions that have dropped further.

        WHAT TO MODIFY:
        - Change averaging down logic or remove it entirely
        - Use different thresholds or criteria
        """
        candidates = []
        for symbol, avg_price in self.average_price.items():
            if avg_price <= 0:
                continue

            d = self.symbol_to_data[symbol]
            position = self.getposition(d)

            # Check if we can add more
            if (position.size > 0 and
                len(self.buy_history[symbol]) < self.p.max_positions_per_stock):

                current_price = self.current_prices[symbol]
                last_buy_price = self.get_last_buy_price(symbol)

                if last_buy_price > 0:
                    drawdown = (last_buy_price - current_price) / last_buy_price
                    if drawdown >= self.p.averaging_down_threshold:
                        candidates.append((symbol, drawdown))

        if not candidates:
            return False

        # Pick worst performer and add to position
        candidates.sort(key=lambda x: x[1], reverse=True)
        worst_symbol, drawdown = candidates[0]

        cash = self.broker.getcash()
        price = self.current_prices[worst_symbol]

        if cash > price:
            size = self.calculate_position_size(cash, price)
            d = self.symbol_to_data[worst_symbol]
            print(f"📉 AVERAGING DOWN: {worst_symbol} @ {price:.2f} (dd: {drawdown:.1%})")
            self.buy(data=d, size=size)
            self.record_buy_order(worst_symbol, price, size)
            return True

        return False

    # ========================================================================
    # POSITION SIZING - How much to buy
    # ========================================================================

    def calculate_position_size(self, cash, price):
        """
        Calculate how many shares to buy.

        WHAT TO MODIFY:
        - Change sizing logic (fixed size, volatility-based, Kelly, etc.)
        - Add risk-adjusted sizing
        """
        position_value = cash * self.p.position_size_pct
        size = int(position_value / price)
        return max(size, 1)

    # ========================================================================
    # ORDER TRACKING - Record your trades
    # ========================================================================

    def record_buy_order(self, symbol, price, size):
        """Record a buy order for tracking."""
        buy_info = {
            'price': price,
            'size': size,
            'value': price * size
        }
        self.buy_history[symbol].append(buy_info)

        # Update average entry price
        total_shares = sum(buy['size'] for buy in self.buy_history[symbol])
        total_value = sum(buy['value'] for buy in self.buy_history[symbol])
        if total_shares > 0:
            self.average_price[symbol] = total_value / total_shares

    def get_last_buy_price(self, symbol):
        """Get the most recent buy price for a stock."""
        if self.buy_history[symbol]:
            return self.buy_history[symbol][-1]['price']
        return 0

    # ========================================================================
    # ORDER NOTIFICATIONS - Track executions
    # ========================================================================

    def notify_order(self, order):
        """Called when an order is executed."""
        if order.status == order.Completed:
            symbol = order.data._name
            if order.isbuy():
                print(f"✅ BUY EXECUTED: {symbol} - {order.executed.size} shares @ ₹{order.executed.price:.2f}")
            else:
                print(f"💰 SELL EXECUTED: {symbol} - {order.executed.size} shares @ ₹{order.executed.price:.2f}")
                avg_price = self.average_price.get(symbol, 0)
                if avg_price > 0:
                    pnl_pct = (order.executed.price - avg_price) / avg_price * 100
                    print(f"   P&L: {pnl_pct:+.1f}%")

    # ========================================================================
    # STRATEGY END - Print summary
    # ========================================================================

    def stop(self):
        """Called when backtest ends."""
        final_value = self.broker.getvalue()
        total_return = (final_value - self.start_value) / self.start_value * 100

        print("\n" + "="*60)
        print("STRATEGY SUMMARY")
        print("="*60)
        print(f"Initial Capital: ₹{self.start_value:,.2f}")
        print(f"Final Portfolio: ₹{final_value:,.2f}")
        print(f"Total Return: {total_return:+.2f}%")
