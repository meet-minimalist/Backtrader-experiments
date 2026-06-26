import backtrader as bt


class SkeletonStrategy(bt.Strategy):
    """
    Golden Cross / Death Cross: EMA50 vs EMA200

    Logic:
    - Entry: EMA(50) crosses above EMA(200) — golden cross
    - Exit: EMA(50) drops below EMA(200) — death cross
    - Hold through normal price volatility; only trade on major trend changes
    - Position size: 10% of available cash per trade

    Rationale: Instead of waiting for price to cross EMA200, we enter when the
    medium-term (EMA50) definitively exceeds the long-term (EMA200). This golden
    cross fires once per trend, not every time price bounces off EMA200.
    Death cross exit means we stay invested through pullbacks that don't break
    the medium-term trend. Classic institutional signal for major trend changes.
    """
    params = (
        ('slow_period', 200),
        ('fast_period', 50),
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
            # Cross of EMA50 vs EMA200 (not price vs EMA)
            self.golden_cross[symbol] = bt.indicators.CrossOver(self.ema_fast[symbol], self.ema_slow[symbol])

    def next(self):
        for symbol, d in self.symbol_to_data.items():
            pos = self.getposition(d)
            cross = self.golden_cross[symbol][0]

            if not pos:
                # Golden cross: EMA50 crosses above EMA200
                if cross > 0:
                    cash = self.broker.getcash()
                    price = d.close[0]
                    if cash > price:
                        size = self._calc_size(cash, price)
                        self.buy(data=d, size=size)
            else:
                # Death cross: EMA50 drops below EMA200
                if cross < 0:
                    self.close(data=d)

    def _calc_size(self, cash, price):
        value = cash * self.p.position_size_pct
        size = int(value / price)
        return max(size, 1)
