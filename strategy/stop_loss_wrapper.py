import backtrader as bt


def wrap_strategy_with_atr_stop(base_strategy_class, atr_period=14, atr_multiplier=2.0):
    """
    Dynamically wraps a strategy class with ATR-based trailing stop loss.
    Uses backtrader's built-in bt.Order.StopTrail (no manual tracking).

    Args:
        base_strategy_class: Original strategy class (unchanged)
        atr_period: ATR calculation period (default: 14)
        atr_multiplier: Multiplier for stop distance (default: 2.0x)

    Returns:
        New strategy class with trailing stop loss

    Usage:
        ShopWithStop = wrap_strategy_with_atr_stop(ShopStrategy, atr_multiplier=2.0)
        cerebro.addstrategy(ShopWithStop)
    """

    class StrategyWithStopLoss(base_strategy_class):
        params = (
            ('atr_period', atr_period),
            ('atr_multiplier', atr_multiplier),
        )

        def __init__(self):
            super().__init__()
            self.atr = {}
            self.active_stops = {}  # symbol -> order reference

            # Create ATR for each data feed
            for d in self.datas:
                self.atr[d._name] = bt.indicators.ATR(d, period=self.p.atr_period)

        def next(self):
            # Update/create trailing stops for open positions BEFORE original logic
            self._manage_trailing_stops()

            # Run original strategy logic
            super().next()

        def _manage_trailing_stops(self):
            """Create/update trailing stops for open positions."""
            for d in self.datas:
                symbol = d._name
                position = self.getposition(d)

                if position.size > 0 and symbol not in self.active_stops:
                    # New position opened - create trailing stop
                    atr_value = self.atr[symbol][0]
                    trail_distance = atr_value * self.p.atr_multiplier

                    # Create sell order with trailing stop
                    stop_order = self.sell(
                        data=d,
                        exectype=bt.Order.StopTrail,
                        trailamount=trail_distance
                    )

                    self.active_stops[symbol] = stop_order
                    print(f"🛡️ Trailing stop set: {symbol} (ATR: {atr_value:.2f}, Trail: {trail_distance:.2f})")

                elif position.size == 0 and symbol in self.active_stops:
                    # Position closed - remove stop
                    self.active_stops.pop(symbol, None)

        def notify_order(self, order):
            """Handle trailing stop execution."""
            if order.status == order.Completed:
                if order.exectype == bt.Order.StopTrail and not order.isbuy():
                    symbol = order.data._name
                    # Stop hit - position closed, remove from tracking
                    self.active_stops.pop(symbol, None)
                    print(f"🛑 Trailing stop executed: {symbol} @ {order.executed.price:.2f}")

            # Always call parent's notify_order
            super().notify_order(order)

    # Give it a meaningful name
    StrategyWithStopLoss.__name__ = f"{base_strategy_class.__name__}WithATRStop"
    return StrategyWithStopLoss
