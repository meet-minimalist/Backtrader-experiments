# Backtrader Internal Working & Execution Flow

This document explains how Backtrader works under the hood, the order of method calls, and how different components interact. Understanding this flow will help you debug, extend, and optimize your backtesting strategies.

---

## Table of Contents

1. [Core Architecture Overview](#core-architecture-overview)
2. [The Cerebro Engine](#the-cerebro-engine)
3. [Execution Lifecycle](#execution-lifecycle)
4. [Method Call Order During `cerebro.run()`](#method-call-order-during-cerebrorun)
5. [Strategy Lifecycle Methods](#strategy-lifecycle-methods)
6. [Data Feed Processing](#data-feed-processing)
7. [Order Execution Flow](#order-execution-flow)
8. [Analyzer Execution Timeline](#analyzer-execution-timeline)
9. [Broker & Commission Processing](#broker--commission-processing)
10. [Multi-Data Strategy Handling](#multi-data-strategy-handling)
11. [Visual Flow Diagram](#visual-flow-diagram)
12. [Practical Examples from Your Code](#practical-examples-from-your-code)

---

## Core Architecture Overview

Backtrader's architecture follows an **event-driven** model with these key components:

```
┌─────────────────────────────────────────────────────────────┐
│                        Cerebro                               │
│                  (Orchestration Engine)                      │
└───────────────┬──────────────────────────────┬──────────────┘
                │                              │
    ┌───────────▼──────────┐      ┌────────────▼────────────┐
    │       Broker         │      │      Data Feeds         │
    │  (Order Management)  │      │  (Market Data Source)   │
    └───────────┬──────────┘      └────────────┬────────────┘
                │                              │
                │         ┌────────────────────┘
                │         │
    ┌───────────▼─────────▼────────────────────┐
    │           Strategy Instance              │
    │  (Indicators, Logic, Orders)             │
    └──────────────────────────────────────────┘
                │
    ┌───────────▼──────────────────────────────┐
    │           Analyzers                      │
    │  (Performance Metrics, Logging)          │
    └──────────────────────────────────────────┘
```

### Key Classes

| Component | Purpose |
|-----------|---------|
| `bt.Cerebro` | Main engine that orchestrates everything |
| `bt.Strategy` | Your trading logic (entry/exit rules) |
| `bt.AbstractDataBase` | Market data wrapper (yfinance, CSV, etc.) |
| `bt.BrokerBase` | Order execution, position tracking |
| `bt.Analyzer` | Performance metrics (Sharpe, Drawdown, etc.) |
| `bt.CommInfoBase` | Commission/slippage calculations |

---

## The Cerebro Engine

`Cerebro` is the central orchestrator. When you call methods like `addstrategy()`, `adddata()`, and `addanalyzer()`, you're registering components that will be executed in a specific order during `cerebro.run()`.

### What Happens During Setup

```python
cerebro = bt.Cerebro()
cerebro.adddata(data_feed)        # Registers data feeds
cerebro.addstrategy(ShopStrategy) # Registers strategy
cerebro.broker.setcash(1000000)   # Sets initial capital
cerebro.addanalyzer(SharpeRatio)  # Registers analyzers
```

Internally, Cerebro stores these in collections:
- `self.strats` - List of strategy instances
- `self.datas` - List of data feeds
- `self.analyzers` - List of analyzer instances
- `self.observers` - Observers for charting

---

## Execution Lifecycle

When you call `results = cerebro.run()`, Backtrader goes through these phases:

### Phase 1: Initialization
1. **Clone broker** for each strategy
2. **Instantiate strategies** with parameters
3. **Instantiate analyzers** and attach to strategies
4. **Initialize indicators** (strategy `__init__()` is called)
5. **Determine run range** (min/max bar lengths across all data feeds)

### Phase 2: Main Loop
Iterates through each bar (time step) and calls strategy methods in order.

### Phase 3: Finalization
1. Calls `stop()` on strategies
2. Collects analyzer results
3. Returns strategy instances with results

---

## Method Call Order During `cerebro.run()`

This is the **exact sequence** of method calls:

### Pre-Loop Phase

```
1. Cerebro.run() starts
   │
   ├─► For each data feed:
   │    └─► data.reset()  # Reset data pointers
   │
   ├─► For each strategy:
   │    ├─► Strategy.__init__()
   │    │    └─► Indicators are created (SMA, RSI, etc.)
   │    │    └─► self.datas, self.data0, self.data1 are available
   │    │
   │    └─► Strategy.start()  # Optional, rarely overridden
   │
   └─► For each analyzer:
        └─► Analyzer.__init__()
        └─► Analyzer.start()  # Optional setup
```

### Main Loop (Executed for EVERY Bar)

```
For bar_index in range(min_bar_length, max_bar_length):
   │
   ├─► 1. Strategy.nextstart()  # Called ONLY on first bar
   │
   ├─► 2. Strategy.next()       # Called on EVERY subsequent bar
   │      │
   │      ├─► Access current data: self.data.close[0], self.data.high[0]
   │      ├─► Access previous data: self.data.close[-1], self.data.close[-2]
   │      ├─► Check indicators: self.sma[0]
   │      ├─► Place orders: self.buy(), self.sell(), self.close()
   │      └─► Your logic runs here (entry/exit checks)
   │
   ├─► 3. Broker processes orders
   │      ├─► Check for order execution
   │      ├─► Apply commissions
   │      ├─► Update positions
   │      └─► Update cash/portfolio value
   │
   ├─► 4. Strategy.notify_order()  # Called when order status changes
   │      ├─► order.Created
   │      ├─► order.Submitted
   │      ├─► order.Accepted
   │      ├─► order.Completed  # Most important
   │      ├─► order.Canceled
   │      └─► order.Rejected
   │
   ├─► 5. Strategy.notify_trade()  # Called when trade opens/closes
   │      ├─► trade.isopen
   │      └─► trade.isclosed
   │
   └─► 6. Analyzers record data
          ├─► Analyzer.next()  # Called every bar
          └─► Record metrics, P&L, etc.
```

### Post-Loop Phase

```
1. For each strategy:
   │
   ├─► Strategy.stop()  # Cleanup, final calculations
   │
   └─► For each analyzer:
        └─► Analyzer.stop()  # Finalize results
        └─► Analyzer.get_analysis()  # Retrieve results
        └─► Results attached to strategy.analyzers.<name>

2. Cerebro.run() returns list of strategy instances
3. Access results via strategy.analyzers.<name>.get_analysis()
```

---

## Strategy Lifecycle Methods

### `__init__()` - Setup Phase

**Called**: Once, before the loop starts  
**Purpose**: Initialize indicators, trackers, data structures  
**Available**:
- `self.datas` - All data feeds
- `self.data` or `self.data0` - Primary data feed
- `self.data1`, `self.data2`, etc. - Additional data feeds
- `self.broker` - Broker instance
- `self.position` - Position in primary data

**Example from your ShopStrategy**:
```python
def __init__(self):
    self.buy_history = {}
    self.average_price = {}
    self.sma20 = {}
    
    for d in self.datas:
        self.sma20[d._name] = bt.indicators.SMA(d, period=20)
        self.symbol_to_data[d._name] = d
```

**Important**: 
- Indicators declared here are computed automatically during the loop
- `[0]` = current value, `[-1]` = previous bar, `[-2]` = two bars ago
- You **cannot** access `[0]` values in `__init__()` (data not loaded yet)

---

### `next()` - Main Processing

**Called**: Every bar after `nextstart()`  
**Purpose**: Your core trading logic  
**Available**: Everything from `__init__()`, plus:
- Current indicator values: `self.sma[0]`
- Current prices: `self.data.close[0]`, `self.data.open[0]`
- Broker state: `self.broker.getcash()`, `self.broker.getvalue()`
- Positions: `self.getposition(data)`

**Example from your ShopStrategy**:
```python
def next(self):
    current_date = self.data.datetime.date(0)
    self.update_stock_metrics()      # Check current prices
    self.check_exit_conditions()     # Close positions if needed
    self.check_entry_conditions()    # Open new positions
```

**Execution order matters**:
1. Exit conditions checked first (close losing positions)
2. Entry conditions checked second (open new positions)
3. This prevents using cash from just-closed positions on same bar

---

### `nextstart()` - First Bar Handler

**Called**: ONLY on the first bar of the loop  
**Default behavior**: Calls `next()`  
**Override when**: You need special handling for the first bar

```python
def nextstart(self):
    # Special logic for first bar
    print("First bar processing")
    self.next()  # Usually call next() afterward
```

---

### `stop()` - Cleanup Phase

**Called**: Once, after the loop ends  
**Purpose**: Final calculations, cleanup, summary output  

```python
def stop(self):
    final_value = self.broker.getvalue()
    print(f"Final Portfolio Value: ₹{final_value:,.2f}")
```

**Note**: Rarely overridden; analyzers handle most post-processing.

---

### `notify_order(order)` - Order Status Updates

**Called**: Whenever an order changes status  
**Triggered by**: `self.buy()`, `self.sell()`, `self.close()`  

**Order status flow**:
```
Created → Submitted → Accepted → Completed (success)
                                  ↓
                            Canceled / Rejected (failure)
```

**Example from your ShopStrategy**:
```python
def notify_order(self, order):
    if order.status == order.Completed:
        symbol = order.data._name
        if order.isbuy():
            print(f"✅ BUY: {symbol} @ ₹{order.executed.price:.2f}")
        else:
            print(f"💰 SELL: {symbol} @ ₹{order.executed.price:.2f}")
```

**Important attributes**:
- `order.executed.price` - Fill price
- `order.executed.size` - Executed quantity
- `order.executed.value` - Total value
- `order.executed.comm` - Commission charged
- `order.isbuy()` / `order.issell()` - Order direction

---

### `notify_trade(trade)` - Trade Lifecycle

**Called**: When a trade opens or closes  
**Difference from orders**: A trade can involve multiple orders (entry + exit)

```python
def notify_trade(self, trade):
    if trade.isclosed:
        print(f"Trade closed: P&L Gross={trade.pnl:.2f}, Net={trade.pnlcomm:.2f}")
```

**Trade states**:
- `trade.isopen` - Trade just opened
- `trade.isclosed` - Trade just closed (P&L available)

---

## Data Feed Processing

### How Data Feeds Work

When you call `cerebro.adddata(data_feed)`, Backtrader:

1. **Stores** the data feed in `cerebro.datas`
2. **Assigns** it to strategies via `self.datas[i]`
3. **Synchronizes** all data feeds by date
4. **Handles** missing data (holidays, suspensions)

### Data Access Patterns

```python
# Current bar values
self.data.close[0]      # Close price
self.data.open[0]       # Open price
self.data.high[0]       # High price
self.data.low[0]        # Low price
self.data.volume[0]     # Volume
self.data.datetime[0]   # Date/time

# Previous bars
self.data.close[-1]     # Previous close
self.data.close[-2]     # Close 2 bars ago

# Slicing (indicator-style)
self.data.close(0, 1)   # Current close
self.data.close(-1, 1)  # Previous close
self.data.close(-2, 3)  # Average of last 3 closes
```

### Multi-Data Strategies

In your code, you load multiple stocks:

```python
for data_feed in data_feeds:
    cerebro.adddata(data_feed, name=symbol)
```

Inside strategy:
```python
def __init__(self):
    for d in self.datas:
        symbol = d._name  # Get symbol name from data feed
        self.sma20[symbol] = bt.indicators.SMA(d, period=20)

def next(self):
    for d in self.datas:
        symbol = d._name
        current_price = d.close[0]  # Current price of this stock
```

**Important**: `self.data` or `self.data0` always refers to the **first** data feed. Use `self.data1`, `self.data2`, etc., or iterate `self.datas`.

---

## Order Execution Flow

### Order Types

| Type | Description | Example |
|------|-------------|---------|
| `Market` | Execute immediately at next available price | `self.buy()` |
| `Limit` | Execute only at specified price or better | `self.buy(exectype=bt.Order.Limit, price=100)` |
| `Stop` | Execute when price crosses threshold | `self.sell(exectype=bt.Order.Stop, price=95)` |
| `StopLimit` | Stop + Limit combined | `self.buy(exectype=bt.Order.StopLimit, price=100, plimit=102)` |

### Order Execution Timeline

```
Bar N:
  └─► Strategy.next() calls self.buy()
       │
       └─► Order created with status: Created
       └─► notify_order() NOT called yet

Bar N+1:
  └─► Broker processes order
       ├─► Order status: Submitted → Accepted
       ├─► notify_order() called for each status change
       │
       ├─► IF market price allows execution:
       │    ├─► Order status: Completed
       │    ├─► Position updated
       │    ├─► Commission deducted
       │    ├─► Cash reduced
       │    └─► notify_order(order) called with Completed status
       │
       └─► IF order cannot execute:
            ├─► Order status: Canceled / Rejected
            └─► notify_order() called with failure status
```

### Default Behavior (Market Orders)

In your strategies, you use:
```python
self.buy(data=d, size=size)
```

This creates a **Market Order**:
1. Order placed in current bar
2. Executed in **next bar** at opening price
3. Commission applied
4. Position updated
5. `notify_order()` called with `Completed` status

**Critical**: Orders don't execute instantly! There's always a 1-bar delay.

---

## Analyzer Execution Timeline

Analyzers run **in parallel** with strategies and record data at each step.

### Analyzer Lifecycle

```
1. Cerebro.addanalyzer(AnalyzerClass, _name='my_analyzer')
   │
   ├─► Analyzer.__init__(strategy, params)
   │
2. cerebro.run() starts
   │
   ├─► Analyzer.start()
   │
3. For each bar:
   │
   ├─► Analyzer.next()  # Called after strategy.next()
   │    └─► Record metrics, trades, portfolio values
   │
4. cerebro.run() ends
   │
   ├─► Analyzer.stop()
   └─► Analyzer.get_analysis() → Returns dict of results
```

### Accessing Analyzer Results

```python
results = cerebro.run()
strategy = results[0]

# Access by _name
sharpe = strategy.analyzers.sharpe.get_analysis()
drawdown = strategy.analyzers.drawdown.get_analysis()
returns = strategy.analyzers.returns.get_analysis()

# Results are dictionaries
print(sharpe['sharperatio'])
print(drawdown['max']['drawdown'])
print(returns['rnorm100'])  # CAGR
```

### Your Custom Analyzers

In your code:
```python
cerebro.addanalyzer(TradeLogger, _name='trade_logger',
                   enabled=True,
                   strategy_name=strategy_name,
                   stock_name=stock_name)
```

Custom analyzers work the same way but can have custom methods:
```python
class TradeLogger(bt.Analyzer):
    def next(self):
        # Called every bar - log trades, positions, etc.
        pass
    
    def get_analysis(self):
        return self.trade_log
```

---

## Broker & Commission Processing

### Broker Role

The broker:
1. **Manages cash** - Tracks available capital
2. **Tracks positions** - What you own/owe
3. **Executes orders** - Fills buys/sells
4. **Applies commissions** - Transaction costs
5. **Calculates portfolio value** - Cash + positions

### Commission Processing

When you add custom commission:
```python
cerebro.broker.addcommissioninfo(ZerodhaDeliveryCommission())
```

This commission info is used for **every order**. The `ZerodhaDeliveryCommission` class (inheriting from `bt.CommInfoBase`) defines:
- Commission percentage
- Stamp duty
- STT (Securities Transaction Tax)
- Exchange charges

**Commission is applied when**:
- Order reaches `Completed` status
- Deducted from cash immediately
- Visible in `order.executed.comm`

### Portfolio Valuation

```python
# Available in strategy
cash = self.broker.getcash()          # Available cash
value = self.broker.getvalue()        # Cash + positions value
position_value = value - cash         # Just position value
```

---

## Multi-Data Strategy Handling

Your code loads multiple stocks simultaneously. Here's how Backtrader handles this:

### Data Synchronization

```python
data_feeds, symbols = load_index_data('NIFTY_MIDCAP_50', ...)
for data_feed in data_feeds:
    cerebro.adddata(data_feed)
```

Backtrader:
1. **Aligns** all data feeds by date
2. **Skips** bars where any data is missing
3. **Ensures** all `self.datas` have valid `[0]` values in `next()`

### Strategy Processing with Multiple Data

```python
def next(self):
    # Called once per bar, but ALL data feeds are available
    for d in self.datas:
        symbol = d._name
        price = d.close[0]  # Current price of THIS stock
        
    # All data feeds advance together
    # You can't have data0 at day 10 and data1 at day 5
```

**Key insight**: `next()` is called **once per bar**, not once per data feed. Inside that single call, you have access to ALL data feeds at the current timestamp.

### Position Management

```python
# Get position for specific data feed
position = self.getposition(d)  # Position in data feed d
position.size  # Number of shares (positive=long, negative=short)
position.price  # Average entry price

# Close position
self.close(data=d)  # Closes position in data feed d
```

---

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    cerebro.run() starts                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │  INITIALIZATION PHASE           │
          │  ─────────────────────          │
          │  • Reset data feeds             │
          │  • Clone broker                 │
          │  • Create strategy instance     │
          │  • Call Strategy.__init__()     │
          │  • Create analyzer instances    │
          │  • Call Analyzer.start()        │
          │  • Call Strategy.start()        │
          └───────────────┬────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │  MAIN LOOP (for each bar)       │
          │  ─────────────────────          │
          │                                 │
          │  1. nextstart() [first bar only]│
          │         ↓                       │
          │  2. next() [every bar]          │
          │     • Read indicators           │
          │     • Check entry/exit logic    │
          │     • Place orders (buy/sell)   │
          │         ↓                       │
          │  3. Broker processes orders     │
          │     • Execute fills             │
          │     • Apply commissions         │
          │     • Update positions          │
          │         ↓                       │
          │  4. notify_order()              │
          │     • Called for status changes │
          │         ↓                       │
          │  5. notify_trade()              │
          │     • Called on trade open/close│
          │         ↓                       │
          │  6. Analyzer.next()             │
          │     • Record metrics            │
          │     • Log trades                │
          └───────────────┬────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │  FINALIZATION PHASE             │
          │  ─────────────────────          │
          │  • Call Strategy.stop()         │
          │  • Call Analyzer.stop()         │
          │  • Collect analyzer results     │
          │  • Return strategy instances    │
          └───────────────┬────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │  ACCESS RESULTS                 │
          │  ─────────────────────          │
          │  strategy.analyzers.sharpe      │
          │  strategy.analyzers.drawdown    │
          │  strategy.analyzers.returns     │
          └─────────────────────────────────┘
```

---

## Practical Examples from Your Code

### Example 1: ShopStrategy Execution Flow

```python
class ShopStrategy(bt.Strategy):
    def __init__(self):
        # CALLED ONCE during initialization
        self.sma20 = {}
        for d in self.datas:
            # Create 20-period SMA for each stock
            self.sma20[d._name] = bt.indicators.SMA(d, period=20)
    
    def next(self):
        # CALLED EVERY BAR for all stocks simultaneously
        
        # Step 1: Update current metrics
        self.update_stock_metrics()
        # For each stock: store current price, calculate % below SMA
        
        # Step 2: Check if any positions should be closed
        self.check_exit_conditions()
        # Loop through holdings, close if profit > 6%
        
        # Step 3: Check for new entries or averaging down
        self.check_entry_conditions()
        # Rank stocks by how far below SMA they are
        # Buy new stock OR average down on existing position
```

**What happens internally**:

```
Bar 1: __init__() → Create SMA indicators
Bar 2: next() → update_stock_metrics() → check_exit_conditions() → check_entry_conditions()
       ↓
       If entry condition met:
       self.buy(data=d, size=10) → Order Created
       ↓
Bar 3: Broker executes order → notify_order() called with Completed
       ↓
       next() → ... (same logic repeats)
```

---

### Example 2: Order Lifecycle in Your Code

```python
# In ShopStrategy.try_new_stock_entry()
buy_order = self.buy(data=d, size=size)

# Internally, this triggers:
# 1. Order object created (status: Created)
# 2. Sent to broker (status: Submitted)
# 3. Broker accepts (status: Accepted)
# 4. next() bar: Broker executes (status: Completed)
# 5. notify_order() called automatically
```

```python
def notify_order(self, order):
    if order.status == order.Completed:
        symbol = order.data._name
        if order.isbuy():
            print(f"✅ BUY: {symbol} @ ₹{order.executed.price:.2f}")
            # This is where you could update trackers
            self.record_buy_order(symbol, order.executed.price, order.executed.size)
```

---

### Example 3: Analyzer Integration

```python
# In main.py
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', 
                   riskfreerate=0.06)

# Internally:
# 1. SharpeRatio analyzer instantiated
# 2. Every bar: analyzer.next() records portfolio returns
# 3. After run(): analyzer.stop() calculates final Sharpe
# 4. Results attached to strategy

# Access results:
results = cerebro.run()
strategy = results[0]
sharpe_data = strategy.analyzers.sharpe.get_analysis()
print(sharpe_data['sharperatio'])
```

---

## Key Concepts & Gotchas

### 1. **Order Execution Delay**

```python
def next(self):
    self.buy()  # Order placed NOW
    # But executes in NEXT bar at opening price
```

**Implication**: You can't buy and sell the same stock on the same bar.

### 2. **Data Indexing**

```python
self.data.close[0]   # Current bar (in next())
self.data.close[-1]  # Previous bar
self.data.close[-2]  # Two bars ago
```

**Warning**: In `__init__()`, you **cannot** use `[0]` indexing (data not loaded).

### 3. **Position Sizing**

```python
# Get available cash
cash = self.broker.getcash()

# Get current position
position = self.getposition(data)
print(position.size)  # 0 = no position, >0 = long
```

### 4. **Multiple Data Feeds**

```python
# All data feeds advance together
def next(self):
    for d in self.datas:
        # d.close[0] is valid for ALL d
        pass
```

### 5. **Commission Impact**

```python
# Commission is applied on EVERY trade
order.executed.comm  # Commission for this order

# Reduces your cash automatically
cash_after = self.broker.getcash()  # Already includes commission deduction
```

---

## Debugging Tips

### 1. **Print Statement Strategy**

```python
def next(self):
    current_date = self.data.datetime.date(0)
    print(f"\n📅 {current_date} | Bar {len(self.data)}")
    print(f"   Cash: ₹{self.broker.getcash():,.2f}")
    print(f"   Value: ₹{self.broker.getvalue():,.2f}")
```

### 2. **Track Order Flow**

```python
def notify_order(self, order):
    print(f"Order Status: {order.getstatusname(order.status)}")
    if order.status == order.Completed:
        print(f"   Executed: {order.executed.size} @ ₹{order.executed.price}")
        print(f"   Commission: ₹{order.executed.comm:.2f}")
```

### 3. **Monitor Analyzer Calls**

```python
class DebugAnalyzer(bt.Analyzer):
    def next(self):
        print(f"Analyzer recording bar {len(self.strategy.data)}")
        print(f"   Portfolio value: {self.strategy.broker.getvalue()}")
```

---

## Performance Optimization Tips

### 1. **Minimize `next()` Work**

Heavy computations in `next()` slow down backtests. Pre-calculate in `__init__()` where possible.

```python
# GOOD: Indicator created once
def __init__(self):
    self.sma = bt.indicators.SMA(self.data, period=20)

def next(self):
    if self.data.close[0] > self.sma[0]:  # Fast lookup
        self.buy()
```

### 2. **Use Built-in Indicators**

Backtrader's indicators are optimized in C. Prefer them over manual calculations.

```python
# GOOD
self.rsi = bt.indicators.RSI(self.data, period=14)

# SLOWER
def next(self):
    rsi = manual_rsi_calculation(self.data.close.get(size=14))
```

### 3. **Batch Data Processing**

When using multiple data feeds, avoid redundant loops:

```python
# Efficient
def next(self):
    for d in self.datas:
        symbol = d._name
        # Process each stock once per bar
```

---

## Common Patterns

### Pattern 1: Signal Generation

```python
def next(self):
    # Generate signal
    if self.rsi[0] < 30:
        self.buy_signal = True
    elif self.rsi[0] > 70:
        self.sell_signal = True
    
    # Execute signal
    if self.buy_signal and not self.position:
        self.buy()
```

### Pattern 2: Trailing Stop

```python
def next(self):
    if self.position:
        highest = max(self.data.high.get(size=20))
        stop_price = highest * 0.95
        
        if self.data.close[0] < stop_price:
            self.close()
```

### Pattern 3: Portfolio Rebalancing

```python
def next(self):
    # Check if it's rebalance day
    if self.data.datetime.date(0).day == 1:  # First of month
        # Close all positions
        for d in self.datas:
            if self.getposition(d).size > 0:
                self.close(data=d)
        
        # Rebalance
        for d in self.datas:
            if some_condition(d):
                self.buy(data=d)
```

---

## Summary: Method Call Order Cheat Sheet

```
1. cerebro.adddata()        → Register data feeds
2. cerebro.addstrategy()    → Register strategy class
3. cerebro.addanalyzer()    → Register analyzers
4. cerebro.run()            → START EXECUTION
   │
   ├─► Data feeds reset
   ├─► Strategy.__init__()
   ├─► Strategy.start()
   ├─► Analyzer.start()
   │
   ├─► FOR EACH BAR:
   │    ├─► nextstart() [first bar only]
   │    ├─► next() [every bar]
   │    │    └─► self.buy() / self.sell() / self.close()
   │    ├─► Broker processes orders
   │    ├─► notify_order() [if order status changed]
   │    ├─► notify_trade() [if trade opened/closed]
   │    └─► Analyzer.next()
   │
   ├─► Strategy.stop()
   ├─► Analyzer.stop()
   └─► Return strategy instances
```

---

## Further Resources

- **Official Docs**: https://www.backtrader.com/docu/
- **Community**: https://community.backtrader.com/
- **Source Code**: https://github.com/mementum/backtrader

---

**Last Updated**: 2025-04-10  
**Applicable to**: Backtrader 1.9.x+
