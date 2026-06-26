import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    Golden Cross + Breadth-Filtered Exit + 15% Stop + Regime Re-entry

    Logic:
    - Entry: EMA(50) crosses EMA(200) [golden cross]
      OR EMA(50) > EMA(200) AND price recovers above EMA(200) [regime re-entry]
    - Exit on death cross ONLY IF market breadth is weak (< 40% stocks above EMA200)
      OR price drops >15% below EMA200 (circuit breaker - always fires)
    - If death cross fires but market is broadly bullish, hold (idiosyncratic correction)
    - Position size: 10% of available cash per trade

    Rationale: Exp37 (market breadth as ENTRY filter) hurt performance.
    New approach: use breadth as an EXIT filter only.
    Annual returns analysis showed Exp39 crushed in 2020 (COVID) because death cross
    exits freed capital at the WRONG time. But in strong bull years, death cross exits
    correctly recycle capital. Key distinction:
    - COVID 2020: market breadth collapsed (30-40% stocks above EMA200) → allow exit
    - Normal correction of one stock: breadth stays high (60-70%) → hold the position
    This preserves COVID-crash protection via circuit breaker while allowing
    single-stock death crosses to be ignored when the market is broadly healthy.
    """
    params = (
        ('slow_period', 200),
        ('fast_period', 50),
        ('crash_stop_pct', 0.15),
        ('position_size_pct', 0.10),
        ('breadth_threshold', 0.40),
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
