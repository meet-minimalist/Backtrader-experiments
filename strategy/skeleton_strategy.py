"""
Strategy: EMA crossover + SMA trend + volume filter.
Buy when price > SMA(50), EMA12 > EMA26, and volume > 1.5× volume SMA(20).
Sell when price < SMA(50).
"""
import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    params = (
        ('sma_period', 50),
        ('ema_fast', 12),
        ('ema_slow', 26),
        ('vol_period', 20),
        ('vol_multiplier', 1.5),
        ('position_size_pct', 0.10),
        ('symbol_names', []),
    )

    def __init__(self):
        self.sma = {}
        self.ema_fast = {}
        self.ema_slow = {}
        self.vol_sma = {}
        for d in self.datas:
            self.sma[d._name] = bt.indicators.SMA(d.close, period=self.p.sma_period)
            self.ema_fast[d._name] = bt.indicators.EMA(d.close, period=self.p.ema_fast)
            self.ema_slow[d._name] = bt.indicators.EMA(d.close, period=self.p.ema_slow)
            self.vol_sma[d._name] = bt.indicators.SMA(d.volume, period=self.p.vol_period)
        self.symbol_to_data = {d._name: d for d in self.datas}
        self.entry_price = {}

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            price = d.close[0]
            sma_val = self.sma[symbol][0]
            ema_fast_val = self.ema_fast[symbol][0]
            ema_slow_val = self.ema_slow[symbol][0]
            vol_val = d.volume[0]
            vol_sma_val = self.vol_sma[symbol][0]
            pos = self.getposition(d)

            # Entry conditions
            if not pos and price > sma_val and ema_fast_val > ema_slow_val and vol_val > self.p.vol_multiplier * vol_sma_val:
                cash = self.broker.getcash()
                if cash > price:
                    size = self._calc_size(cash, price)
                    self.buy(data=d, size=size)
                    self.entry_price[symbol] = price
                    print(f"BUY {symbol} @ {price:.2f} (size={size})")
                continue

            # Exit condition
            if pos and price < sma_val:
                self.close(data=d)
                print(f"SELL {symbol} @ {price:.2f}")
                self.entry_price.pop(symbol, None)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
