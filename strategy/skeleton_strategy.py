"""
Strategy: EMA(10/20) crossover + SMA(20) trend + volume filter + RSI filter + ATR volatility sizing.
Buy when price > SMA(20), EMA10 > EMA20, volume > 1.3x volume SMA(20), 50 < RSI(14) < 70.
Position size scaled by 1/ATR (larger when volatility is low).
Sell when price < SMA(20).
"""
import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    # Updated strategy: added RSI filter (50 < RSI < 70) and tighter volume multiplier

    params = (
        ('sma_period', 20),
        ('ema_fast', 10),
        ('ema_slow', 20),
        ('vol_period', 20),
        ('vol_multiplier', 1.3),
        ('atr_period', 14),
        ('rsi_period', 14),
        ('position_size_pct', 0.15),
        ('symbol_names', []),
    )

    def __init__(self):
        self.sma = {}
        self.ema_fast = {}
        self.ema_slow = {}
        self.vol_sma = {}
        self.atr = {}
        self.rsi = {}
        for d in self.datas:
            self.sma[d._name] = bt.indicators.SMA(d.close, period=self.p.sma_period)
            self.ema_fast[d._name] = bt.indicators.EMA(d.close, period=self.p.ema_fast)
            self.ema_slow[d._name] = bt.indicators.EMA(d.close, period=self.p.ema_slow)
            self.vol_sma[d._name] = bt.indicators.SMA(d.volume, period=self.p.vol_period)
            self.atr[d._name] = bt.indicators.ATR(d, period=self.p.atr_period)
            self.rsi[d._name] = bt.indicators.RSI(d.close, period=self.p.rsi_period)
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

            if not pos and price > sma_val and ema_fast_val > ema_slow_val and vol_val > self.p.vol_multiplier * vol_sma_val:
                rsi_val = self.rsi[symbol][0]
                if not (50 < rsi_val < 70):
                    continue
                cash = self.broker.getcash()
                if cash > price:
                    size = self._calc_size(cash, price, self.atr[symbol][0])
                    self.buy(data=d, size=size)
                    self.entry_price[symbol] = price
                    print(f"BUY {symbol} @ {price:.2f} (size={size})")
                continue

            if pos and price < sma_val:
                self.close(data=d)
                print(f"SELL {symbol} @ {price:.2f}")
                self.entry_price.pop(symbol, None)

    def _calc_size(self, cash, price, atr_val):
        base_value = cash * self.p.position_size_pct
        if atr_val > 0:
            vol_factor = 1.0 / (atr_val / price)
            vol_factor = min(max(vol_factor, 0.5), 3.0)
        else:
            vol_factor = 1.0
        value = base_value * vol_factor
        size = int(value / price)
        return max(size, 1)
