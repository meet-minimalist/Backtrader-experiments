import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    Golden Cross + Day-1 Regime Init + Re-entry After Circuit Breaker

    Logic:
    - Entry: EMA(50) crosses above EMA(200) [golden cross]
      OR EMA(50) > EMA(200) AND price > EMA(200) on day 1 [initial regime load]
      OR EMA(50) > EMA(200) AND price recovers above EMA(200) [after circuit breaker]
    - Exit: death cross (EMA50 < EMA200) OR price drops >15% below EMA200
    - Position size: 10% of available cash per trade

    Rationale: Exp30 (golden cross only) misses stocks already in golden cross zone
    at backtest start (2015), and doesn't re-enter after circuit breaker fires
    during COVID crash while EMA50 still above EMA200.
    This version enters on: golden cross events + initial regime + post-stop recovery.
    """
    params = (
        ('slow_period', 200),
        ('fast_period', 50),
        ('crash_stop_pct', 0.15),
        ('position_size_pct', 0.10),
        ('symbol_names', []),
    )

    def __init__(self):
        self.ema_slow = {}
        self.ema_fast = {}
        self.golden_cross = {}
        self.price_ema_slow_cross = {}
        self.symbol_to_data = {d._name: d for d in self.datas}
        self._initialized = False

        for d in self.datas:
            symbol = d._name
            self.ema_slow[symbol] = bt.indicators.EMA(d.close, period=self.p.slow_period)
            self.ema_fast[symbol] = bt.indicators.EMA(d.close, period=self.p.fast_period)
            self.golden_cross[symbol] = bt.indicators.CrossOver(self.ema_fast[symbol], self.ema_slow[symbol])
            self.price_ema_slow_cross[symbol] = bt.indicators.CrossOver(d.close, self.ema_slow[symbol])

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            golden = self.golden_cross[symbol][0]
            price_cross = self.price_ema_slow_cross[symbol][0]
            price = d.close[0]
            ema_slow = self.ema_slow[symbol][0]
            ema_fast = self.ema_fast[symbol][0]
            in_regime = ema_fast > ema_slow

            if not pos:
                # Enter on: golden cross OR (in regime AND price recovers above EMA200)
                should_enter = (
                    golden > 0 or
                    (in_regime and price_cross > 0)
                )
                if should_enter:
                    cash = self.broker.getcash()
                    if cash > price:
                        size = self._calc_size(cash, price)
                        self.buy(data=d, size=size)
            else:
                hard_stop = ema_slow * (1 - self.p.crash_stop_pct)
                if golden < 0 or price < hard_stop:
                    self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
