import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    Golden Cross + Circuit Breaker (15% hard stop below EMA200)

    Logic:
    - Entry: EMA(50) crosses above EMA(200) — golden cross
    - Exit: death cross (EMA50 < EMA200) OR price drops >15% below EMA200
    - The circuit breaker exits during crashes before death cross fires
    - Position size: 10% of available cash per trade

    Rationale: Exp28 (golden cross/death cross) achieved 8.48% XIRR but 26.90% drawdown.
    The 26.90% drawdown occurs because in crashes (2020), price falls far below EMA200
    before EMA50 eventually crosses below EMA200. A 15% circuit breaker exits early
    during severe crashes, capping loss without disrupting normal trend holds.
    15% chosen to avoid triggering on normal market pullbacks (typically 5-10%).
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
        self.symbol_to_data = {d._name: d for d in self.datas}

        for d in self.datas:
            symbol = d._name
            self.ema_slow[symbol] = bt.indicators.EMA(d.close, period=self.p.slow_period)
            self.ema_fast[symbol] = bt.indicators.EMA(d.close, period=self.p.fast_period)
            self.golden_cross[symbol] = bt.indicators.CrossOver(self.ema_fast[symbol], self.ema_slow[symbol])

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            cross = self.golden_cross[symbol][0]
            price = d.close[0]
            ema_slow = self.ema_slow[symbol][0]

            if not pos:
                if cross > 0:
                    cash = self.broker.getcash()
                    if cash > price:
                        size = self._calc_size(cash, price)
                        self.buy(data=d, size=size)
            else:
                # Death cross OR price falls >15% below EMA200 (crash circuit breaker)
                hard_stop = ema_slow * (1 - self.p.crash_stop_pct)
                if cross < 0 or price < hard_stop:
                    self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
