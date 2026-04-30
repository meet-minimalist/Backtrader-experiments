import backtrader as bt
import datetime
import math

class NiftyShopStrategy(bt.Strategy):
    params = (
        ('printlog', True),
        ('fresh_buy_amount', 10000),  # Static allocation for new entry
        ('avg_buy_amount', 5000),     # Static allocation for averaging
        ('ma_period', 20),            # 20-day Moving Average
        ('avg_threshold_pct', 3.0),   # Drop percentage to trigger average (positive value)
        ('max_avg_count', 3),         # Max 3 averaging trades per stock
        ('profit_target_pct', 15.0),   # Take profit at 8%
    )

    def __init__(self):
        # Keep track of pending orders
        self.order = None
        
        # Dictionary to store tracking info for each stock
        # Key: data reference, Value: dict with trading stats
        self.stock_tracker = {}
        
        # Initialize tracker for all datas
        for data in self.datas:
            self.stock_tracker[data] = {
                'last_buy_price': 0.0,
                'avg_count': 0,
            }

        # Calculate 20DMA for all stocks
        self.moving_averages = {}
        for data in self.datas:
            self.moving_averages[data] = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.ma_period
            )

    def log(self, txt, dt=None):
        '''Logging function'''
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
                # Reset tracker for this stock since we exited completely
                data = order.data
                self.stock_tracker[data]['last_buy_price'] = 0.0
                self.stock_tracker[data]['avg_count'] = 0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Failed: {order.data._name} - Status: {order.getstatusname()}')

        self.order = None

    def get_underperformance_score(self, data):
        """
        Calculates how far the price is below the 20DMA in percentage.
        Returns a positive number if Price < MA (Underperforming).
        Returns a negative number if Price > MA (Outperforming).
        """
        close = data.close[0]
        ma = self.moving_averages[data][0]
        
        if ma == 0 or close == 0:
            return -100 
        
        # Formula: ((MA - Close) / MA) * 100
        pct_diff = ((ma - close) / ma) * 100
        return pct_diff

    def next(self):
        # Wait until 20DMA is available for all stocks
        if len(self.datas[0]) < self.params.ma_period:
            return

        # ------------------------------------------------------------------
        # STEP 1: EXIT LOGIC (Process Exits First to Free Capital)
        # ------------------------------------------------------------------
        for data in self.datas:
            position = self.getposition(data)
            if position.size > 0:
                tracker = self.stock_tracker[data]
                last_buy_price = tracker['last_buy_price']
                
                # Only check exit if we have a valid reference buy price
                if last_buy_price > 0:
                    current_price = data.close[0]
                    profit_pct = ((current_price - last_buy_price) / last_buy_price) * 100
                    
                    if profit_pct >= self.params.profit_target_pct:
                        self.log(f'EXIT TARGET HIT: {data._name} (Profit: {profit_pct:.2f}%)')
                        self.close(data=data)

        # ------------------------------------------------------------------
        # STEP 2: RANKING & SELECTION (Find Top 5 Worst Performers)
        # ------------------------------------------------------------------
        candidates = []
        for data in self.datas:
            score = self.get_underperformance_score(data)
            # We only care about stocks trading BELOW their 20DMA (Score > 0)
            if score > 0:
                candidates.append((data, score))
        
        # Sort by highest score (Farthest below 20DMA)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Select Top 5
        top_5_candidates = candidates[:5]

        # ------------------------------------------------------------------
        # STEP 3: EXECUTION (Iterate through Top 5)
        # ------------------------------------------------------------------
        for data, score in top_5_candidates:
            position = self.getposition(data)
            tracker = self.stock_tracker[data]
            current_price = data.close[0]

            # CASE A: Stock is NOT in portfolio -> Fresh Buy
            if position.size == 0:
                if self.broker.get_cash() >= self.params.fresh_buy_amount:
                    size = math.floor(self.params.fresh_buy_amount / current_price)
                    if size > 0:
                        self.log(f'FRESH BUY: {data._name} (Score: {score:.2f}%)')
                        self.buy(data=data, size=size)
                        
                        # Update Tracker
                        tracker['last_buy_price'] = current_price
                        tracker['avg_count'] = 0
                else:
                    # Optional: Log if cash is insufficient for fresh buy
                    pass 

            # CASE B: Stock IS in portfolio -> Check Averaging Rule
            else:
                last_buy_price = tracker['last_buy_price']
                avg_count = tracker['avg_count']
                
                # Check if we can average down
                if last_buy_price > 0 and avg_count < self.params.max_avg_count:
                    # Calculate drop from last buy price
                    drop_pct = ((last_buy_price - current_price) / last_buy_price) * 100
                    
                    if drop_pct >= self.params.avg_threshold_pct:
                        if self.broker.get_cash() >= self.params.avg_buy_amount:
                            size = math.floor(self.params.avg_buy_amount / current_price)
                            if size > 0:
                                self.log(f'AVERAGE BUY: {data._name} (Drop: {drop_pct:.2f}%, Avg Count: {avg_count + 1})')
                                self.buy(data=data, size=size)
                                
                                # Update Tracker
                                # Note: Strategy says "3% below LAST BUY PRICE". 
                                # We update last_buy_price to current price to reset the baseline for next avg.
                                tracker['last_buy_price'] = current_price
                                tracker['avg_count'] += 1

    def stop(self):
        self.log('(Ending Value) %.2f' % self.broker.getvalue())