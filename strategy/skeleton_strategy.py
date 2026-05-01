"""
Strategy: SMA trend following with RSI momentum filter.
Buys when price > SMA(50) and RSI(14) > 50, sells when price < SMA(50).
"""
import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    params = (
        ('sma_period', 50),
        ('rsi_period', 14),
        ('rsi_threshold', 50),
        ('position_size_pct', 0.10),
        ('symbol_names', []),
    )

    def __init__(self):
        self.sma = {}
        self.rsi = {}
        for d in self.datas:
            self.sma[d._name] = bt.indicators.SMA(d.close, period=self.p.sma_period)
            self.rsi[d._name] = bt.indicators.RSI(d.close, period=self.p.rsi_period)
        self.symbol_to_data = {d._name: d for d in self.datas}
        self.entry_price = {}

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            price = d.close[0]
            sma_val = self.sma[symbol][0]
            rsi_val = self.rsi[symbol][0]
            pos = self.getposition(d)

            if not pos and price > sma_val and rsi_val > self.p.rsi_threshold:
                cash = self.broker.getcash()
                if cash > price:
                    size = self._calc_size(cash, price)
                    self.buy(data=d, size=size)
                    self.entry_price[symbol] = price
                    print(f"BUY {symbol} @ {price:.2f} (size={size})")
                continue

            if pos and price < sma_val:
                self.close(data=d)
                print(f"SELL {symbol} @ {price:.2f}")
                self.entry_price.pop(symbol, None)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
