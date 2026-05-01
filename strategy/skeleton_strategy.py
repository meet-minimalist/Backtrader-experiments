import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    params = (
        ('sma_period', 50),            # SMA look‑back period
        ('position_size_pct', 0.10),   # % of cash to allocate per trade
        ('symbol_names', []),          # required for multi‑stock support
    )

    def __init__(self):
        # One SMA per data feed (supports multi‑stock backtests)
        self.sma = {}
        for d in self.datas:
            symbol = d._name
            self.sma[symbol] = bt.indicators.SMA(d.close, period=self.p.sma_period)
        # Track the data feed for each symbol
        self.symbol_to_data = {d._name: d for d in self.datas}

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            price = d.close[0]
            sma_val = self.sma[symbol][0]
            pos = self.getposition(d)

            # ENTRY: price below SMA and no current position
            if not pos and price < sma_val:
                cash = self.broker.getcash()
                if cash > price:
                    size = self._calc_size(cash, price)
                    self.buy(data=d, size=size)
                    print(f"BUY {symbol} @ {price:.2f} (size={size})")
                continue

            # EXIT: price above SMA and we hold a position
            if pos and price > sma_val:
                self.close(data=d)
                print(f"SELL {symbol} @ {price:.2f}")

    def _calc_size(self, cash, price):
        """Calculate share count based on the configured cash percentage."""
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
