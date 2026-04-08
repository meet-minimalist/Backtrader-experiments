import backtrader as bt
from datetime import time
import warnings
warnings.filterwarnings('ignore')

class ShopStrategy(bt.Strategy):
    params = (
        ('max_positions_per_stock', 3),
        ('averaging_down_threshold', 0.03),
        ('exit_threshold', 0.06),
        ('ranking_count', 5),
        ('end_of_day_time', time(15, 20)),
        ('symbol_names', []),  # Add this parameter
    )
    
    def __init__(self):
        # Initialize trackers
        self.buy_history = {}
        self.average_price = {}
        self.current_prices = {}
        self.below_sma_pct = {}
        self.symbol_to_data = {}
        self.sma20 = {}
    
        for d in self.datas:
            self.sma20[d._name] = bt.indicators.SMA(d, period=20)
            symbol = d._name
            self.symbol_to_data[symbol] = d
            self.buy_history[symbol] = []
            self.average_price[symbol] = 0.0
            self.current_prices[symbol] = d.close[0]
            self.below_sma_pct[symbol] = 0.0

        self.start_date = self.datas[0].datetime.date(1)
        self.start_value = self.broker.getvalue()
        print(f"🚀 Starting Backtest on {self.start_date}")

    def next(self):
        # Debug: Check if we have data
        current_date = self.data.datetime.date(0)
        print(f"\n📅 Processing {current_date} - Bar {len(self.data)}")
        
        # current_time = self.data.datetime.time()
        # if current_time < self.params.end_of_day_time:
        #     return
        self.update_stock_metrics()
        self.check_exit_conditions()
        self.check_entry_conditions()

    def update_stock_metrics(self):
        """Update current prices and SMA percentages"""
        
        for d in self.datas:
            symbol = d._name
            current_price = d.close[0]
            sma20 = self.sma20[symbol][0]
            # print(f"Updating metrics for {symbol}: Current Price = {current_price}, SMA20 = {sma20}")
            self.current_prices[symbol] = current_price
            self.below_sma_pct[symbol] = (sma20 - current_price) / sma20 if sma20 > 0 else 0.0

    # ... (keep all your existing trading methods unchanged)
    # def notify_order(self, order):
    #     if order.status == order.Completed:
    #         symbol = self.data_to_symbol[order.data]
    #         if order.isbuy():
    #             print(f"✅ BUY EXECUTED: {symbol} - {order.executed.size} shares @ ₹{order.executed.price:.2f}")
    #         else:
    #             print(f"💰 SELL EXECUTED: {symbol} - {order.executed.size} shares @ ₹{order.executed.price:.2f}")

    def check_exit_conditions(self):
        for symbol in list(self.average_price.keys()):
            avg_price = self.average_price[symbol]
            current_price = self.current_prices[symbol]
            if avg_price > 0 and current_price >= avg_price * (1 + self.params.exit_threshold):
                d = self.symbol_to_data[symbol]
                position = self.getposition(d)
                if position.size > 0:
                    print(f"🎯 EXIT: {symbol}")
                    self.close(data=d)
                    self.buy_history[symbol] = []
                    self.average_price[symbol] = 0.0

    def check_entry_conditions(self):
        ranked_stocks = self.get_ranked_stocks()
        new_stock_bought = self.try_new_stock_entry(ranked_stocks)
        if not new_stock_bought:
            self.try_averaging_down()

    def get_ranked_stocks(self):
        valid_stocks = []
        for symbol, below_sma in self.below_sma_pct.items():
            if below_sma > 0:
                valid_stocks.append((symbol, below_sma))
        valid_stocks.sort(key=lambda x: x[1], reverse=True)
        return valid_stocks[:self.params.ranking_count]

    def try_new_stock_entry(self, ranked_stocks):
        for symbol, below_sma in ranked_stocks:
            d = self.symbol_to_data[symbol]
            position = self.getposition(d)
            if position.size == 0:
                cash = self.broker.getcash()
                price = self.current_prices[symbol]
                if cash > price:
                    size = self.calculate_position_size(cash, price)
                    print(f"🛒 NEW ENTRY: {symbol}")
                    buy_order = self.buy(data=d, size=size)
                    self.record_buy_order(symbol, price, size)
                    return True
        return False

    def try_averaging_down(self):
        candidates = []
        for symbol, avg_price in self.average_price.items():
            if avg_price > 0:
                d = self.symbol_to_data[symbol]
                position = self.getposition(d)
                if position.size > 0 and len(self.buy_history[symbol]) < self.params.max_positions_per_stock:
                    current_price = self.current_prices[symbol]
                    last_buy_price = self.get_last_buy_price(symbol)
                    if last_buy_price > 0:
                        drawdown = (last_buy_price - current_price) / last_buy_price
                        if drawdown >= self.params.averaging_down_threshold:
                            candidates.append((symbol, drawdown))
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            worst_symbol, drawdown = candidates[0]
            cash = self.broker.getcash()
            price = self.current_prices[worst_symbol]
            if cash > price:
                size = self.calculate_position_size(cash, price)
                d = self.symbol_to_data[worst_symbol]
                print(f"📉 AVERAGING DOWN: {worst_symbol}")
                buy_order = self.buy(data=d, size=size)
                self.record_buy_order(worst_symbol, price, size)
                return True
        return False

    def record_buy_order(self, symbol, price, size):
        buy_info = {'price': price, 'size': size, 'value': price * size}
        self.buy_history[symbol].append(buy_info)
        total_shares = sum(buy['size'] for buy in self.buy_history[symbol])
        total_value = sum(buy['value'] for buy in self.buy_history[symbol])
        if total_shares > 0:
            self.average_price[symbol] = total_value / total_shares

    def get_last_buy_price(self, symbol):
        if self.buy_history[symbol]:
            return self.buy_history[symbol][-1]['price']
        return 0

    def calculate_position_size(self, cash, price):
        position_value = cash * 0.10
        size = int(position_value / price)
        return max(size, 1)

    def notify_order(self, order):
        if order.status == order.Completed:
            symbol = order.data._name  # Use the data feed name
            if order.isbuy():
                print(f"✅ BUY EXECUTED: {symbol} - {order.executed.size} shares @ ₹{order.executed.price:.2f}")
            else:
                print(f"💰 SELL EXECUTED: {symbol} - {order.executed.size} shares @ ₹{order.executed.price:.2f}")

                avg_price = self.average_price.get(symbol, 0)
                if avg_price > 0:
                    pnl_pct = (order.executed.price - avg_price) / avg_price * 100
                    print(f"   P&L: {pnl_pct:+.1f}%")


    # def compute_cagr(self, final_value):
    #     end_date = self.datas[0].datetime.date(0)
    #     days = (end_date - self.start_date).days
    #     years = days / 365.0
        
    #     # Handle very short periods to avoid division by zero or invalid calculations
    #     if days <= 0:
    #         return 0.0
        
    #     cagr = (pow((final_value / self.start_value), (1.0 / years)) - 1) * 100
    #     return cagr

    # def stop(self):
    #     """Called when backtest ends"""
    #     final_value = self.broker.getvalue()
    #     cagr = self.compute_cagr(final_value)
    #     total_return = (final_value - self.broker.startingcash) / self.broker.startingcash * 100

    #     print("\n" + "="*60)
    #     print("STRATEGY SUMMARY")
    #     print("="*60)
    #     print(f"Initial Capital: ₹{self.broker.startingcash:,.2f}")
    #     print(f"Final Portfolio: ₹{self.broker.getvalue():,.2f}")
    #     print(f"Total Return: {total_return:+.2f}%")
    #     print(f"CAGR: {cagr:+.2f}%")
                