import backtrader as bt
import math


class TradeState:
    __slots__ = ['last_buy_price', 'avg_count']

    def __init__(self):
        self.last_buy_price = 0.0
        self.avg_count = 0


class NiftyShopStrategy(bt.Strategy):
    params = (
        ('printlog', True),
        ('ma_period', 20),
        ('avg_threshold_pct', 3.0),
        ('max_avg_count', 3),
        ('profit_target_pct', 8.0),
        ('position_sizing_mode', 'static'),
        ('fresh_static_amt', 10000),
        ('avg_static_amt', 10000),
        ('fresh_cash_pct', 0.04),
        ('avg_cash_pct', 0.04),
        ('fresh_trade_divisor', 50),
        ('avg_trade_divisor', 50),
        ('brokerage_per_order', 0),
    )

    def __init__(self):
        self.order = None
        self.trade_state = {}

        for data in self.datas:
            self.trade_state[data] = TradeState()

        self.moving_averages = {}
        for data in self.datas:
            self.moving_averages[data] = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.ma_period
            )

    def log(self, txt, dt=None):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, {order.data._name}, Price: {order.executed.price:.2f}, Size: {order.executed.size}'
                )
            elif order.issell():
                self.log(
                    f'SELL EXECUTED, {order.data._name}, Price: {order.executed.price:.2f}, Size: {order.executed.size}'
                )
                self.trade_state[order.data] = TradeState()

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Failed: {order.data._name} - Status: {order.getstatusname()}')

        self.order = None

    def get_underperformance_score(self, data):
        close = data.close[0]
        ma = self.moving_averages[data][0]

        if ma == 0 or close == 0:
            return -100

        pct_diff = ((ma - close) / ma) * 100
        return pct_diff

    def _alloc_amount_for_trade(self, trade_kind):
        if self.params.position_sizing_mode == "static":
            return float(self.params.fresh_static_amt) if trade_kind == "fresh" else float(self.params.avg_static_amt)
        elif self.params.position_sizing_mode == "dynamic":
            pct = float(self.params.fresh_cash_pct) if trade_kind == "fresh" else float(self.params.avg_cash_pct)
            return float(self.broker.getcash()) * pct
        else:
            divisor = self.params.fresh_trade_divisor if trade_kind == "fresh" else self.params.avg_trade_divisor
            portfolio_value = float(self.broker.getvalue())
            return portfolio_value / divisor

    def _determine_qty_for_buy(self, trade_kind, price):
        alloc_amount = self._alloc_amount_for_trade(trade_kind)

        if price <= 0 or alloc_amount <= 0:
            return 0

        qty_by_alloc = math.floor(alloc_amount / price)
        if qty_by_alloc <= 0:
            return 0

        available_cash = self.broker.getcash()
        brokerage = self.params.brokerage_per_order
        if available_cash <= brokerage:
            return 0

        max_qty_by_cash = math.floor((available_cash - brokerage) / price)
        if max_qty_by_cash <= 0:
            return 0

        return int(min(qty_by_alloc, max_qty_by_cash))

    def _execute_fresh_buy(self, data, current_price):
        state = self.trade_state[data]
        size = self._determine_qty_for_buy("fresh", current_price)

        if size > 0:
            self.log(f'FRESH BUY: {data._name} @ {current_price:.2f}')
            self.buy(data=data, size=size)
            state.last_buy_price = current_price
            state.avg_count = 0
        return size > 0

    def _execute_avg_buy(self, data, current_price, score):
        state = self.trade_state[data]
        size = self._determine_qty_for_buy("avg", current_price)

        if size > 0:
            self.log(f'AVG BUY: {data._name} @ {current_price:.2f} (Score: {score:.2f}%)')
            self.buy(data=data, size=size)
            state.last_buy_price = current_price
            state.avg_count += 1

    def next(self):
        if len(self.datas[0]) < self.params.ma_period:
            return

        for data in self.datas:
            position = self.getposition(data)
            if position.size > 0:
                avg_price = position.price
                if avg_price == 0:
                    continue

                target_price = avg_price * (1 + self.params.profit_target_pct / 100)
                if data.high[0] >= target_price:
                    self.log(f'EXIT TARGET HIT: {data._name}')
                    self.close(data=data)

        candidates = []
        for data in self.datas:
            score = self.get_underperformance_score(data)
            if score > 0:
                candidates.append((data, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top_5_candidates = candidates[:5]

        # Check if all top 5 are held - if so, process averaging across all holdings
        all_top5_held = all(
            self.getposition(data).size > 0 for data, _ in top_5_candidates
        )
        if all_top5_held and top_5_candidates:
            self._process_averaging_mode(top_5_candidates)
        else:
            # Process entries from top 5 (only fresh buys, skip already held)
            self._process_entries_for_top5(top_5_candidates)

    def _process_entries_for_top5(self, top_5_candidates):
        """Process fresh entries from top 5 candidates."""
        for data, score in top_5_candidates:
            position = self.getposition(data)
            current_price = data.close[0]

            if position.size == 0:
                bought_any = self._execute_fresh_buy(data, current_price)
                if bought_any:
                    break  # Only one fresh buy per day

    def _process_averaging_mode(self, top_5_candidates):
        """Process averaging for all holdings when all top 5 are already held."""
        for data in self.datas:
            if data not in [d for d, _ in top_5_candidates]:
                continue
            position = self.getposition(data)
            if position.size == 0:
                continue

            current_price = data.close[0]
            state = self.trade_state[data]
            last_buy_price = state.last_buy_price
            avg_count = state.avg_count

            if last_buy_price > 0 and avg_count < self.params.max_avg_count:
                drop_pct = ((last_buy_price - current_price) / last_buy_price) * 100

                if drop_pct >= self.params.avg_threshold_pct:
                    self._execute_avg_buy(data, current_price, 0)
                    # Continue scanning other holdings per reference implementation

    def stop(self):
        self.log(f'(Ending Value) {self.broker.getvalue():.2f}')