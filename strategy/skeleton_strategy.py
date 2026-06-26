import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    Golden Cross + Breadth-Filtered Death Cross (30%) + 20% Circuit Breaker

    Logic:
    - Entry: EMA(50) crosses EMA(200) [golden cross]
      OR EMA(50) > EMA(200) AND price recovers above EMA(200) [regime re-entry]
    - Exit on death cross ONLY IF market breadth is very weak (< 30% stocks above EMA200)
      OR price drops >20% below EMA200 (circuit breaker - always fires)
    - Position size: 10% of available cash per trade

    Rationale: Exp56 (20% CB + 40% breadth) got 12.08% XIRR - new best.
    Lowering breadth threshold from 40% to 30% means death cross exits only in
    TRULY catastrophic crashes (70%+ of NIFTY stocks bearish).
    COVID 2020: breadth easily dropped below 30% → death cross exits still fire
    Normal corrections (2018, 2016): breadth likely stays 30-50% → no death cross exit
    This further reduces false exits in moderate corrections, capturing more recovery.
    Combined with 20% CB which handles individual deep crashes.
    """
    params = (
        ('slow_period', 200),
        ('fast_period', 50),
        ('crash_stop_pct', 0.20),
        ('position_size_pct', 0.10),
        ('breadth_threshold', 0.30),
        ('symbol_names', []),
    )

    def __init__(self):
        self.ema_slow = {}
        self.ema_fast = {}
        self.golden_cross = {}
        self.price_ema_slow_cross = {}
        self.symbol_to_data = {d._name: d for d in self.datas}

        for d in self.datas:
            symbol = d._name
            self.ema_slow[symbol] = bt.indicators.EMA(d.close, period=self.p.slow_period)
            self.ema_fast[symbol] = bt.indicators.EMA(d.close, period=self.p.fast_period)
            self.golden_cross[symbol] = bt.indicators.CrossOver(self.ema_fast[symbol], self.ema_slow[symbol])
            self.price_ema_slow_cross[symbol] = bt.indicators.CrossOver(d.close, self.ema_slow[symbol])

    def _market_breadth(self):
        total = len(self.datas)
        above_ema200 = sum(
            1 for d in self.datas
            if self.ema_fast[d._name][0] > self.ema_slow[d._name][0]
        )
        return above_ema200 / total if total > 0 else 0.5

    def next(self):
        breadth = self._market_breadth()
        weak_market = breadth < self.p.breadth_threshold

        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            golden = self.golden_cross[symbol][0]
            price_cross = self.price_ema_slow_cross[symbol][0]
            price = d.close[0]
            ema_slow = self.ema_slow[symbol][0]
            ema_fast = self.ema_fast[symbol][0]
            in_regime = ema_fast > ema_slow

            if not pos:
                signal = (golden > 0 or (in_regime and price_cross > 0))
                if signal:
                    cash = self.broker.getcash()
                    if cash > price:
                        size = self._calc_size(cash, price)
                        self.buy(data=d, size=size)
            else:
                hard_stop = ema_slow * (1 - self.p.crash_stop_pct)
                # Exit on death cross only during market-wide weakness
                # Circuit breaker always fires regardless of market state
                if (golden < 0 and weak_market) or price < hard_stop:
                    self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
