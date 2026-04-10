# Backtrader Strategy Testing Framework

A modular backtesting framework for Indian stock markets using Backtrader, with comprehensive analytics and strategy comparison tools.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Project Structure

```
backtrader_experiements/
├── main.py                          # Core backtesting engine (reusable functions)
├── strategy_orchastrator.py         # Strategy tester & comparison tool
├── config.py                        # Global settings (dates, cash, commission)
│
├── strategy/                        # Strategy implementations
│   ├── shop_strategy.py             # Mean reversion strategy
│   ├── rsi_strategy.py              # RSI-based strategy
│   ├── macd_strategy.py             # MACD crossover strategy
│   ├── simple_sma_strategy.py       # SMA crossover strategy
│   ├── stop_loss_wrapper.py         # ATR trailing stop wrapper (reusable)
│   └── __init__.py
│
├── analyzers/                       # Custom analyzers
│   ├── sortino.py                   # Sortino Ratio analyzer
│   ├── xirr_analyzer.py             # XIRR calculator
│   ├── trade_logger.py              # Trade logging with strategy/stock context
│   └── ...
│
├── utils/                           # Helper utilities
│   ├── stock_helper.py              # Data loading helpers
│   └── ...
│
├── dataloader/                      # Data fetching utilities
└── utils/                           # Formatting & helpers
```

## Configuration

Edit `config.py` to set defaults:

```python
start_date = '2020-01-01'
end_date = '2025-08-31'
initial_cash = 1000000
commission = 0.002  # 0.2%
index_name = "NIFTY_MIDCAP_50"
riskfreerate = 0.06
```

## Usage

### 1. Run Default Backtest

```bash
python main.py
```

Uses the configured index and strategy with full analytics.

### 2. Use Strategy Orchestrator

```bash
python strategy_orchastrator.py
```

Compares multiple strategies side-by-side.

### 3. Programmatic Usage

#### Single Strategy on Index

```python
from main import run_backtest
from strategy import SkeletonStrategy

result = run_backtest(
    strategy_class=SkeletonStrategy,
    index_name='NIFTY_MIDCAP_50',
    start_date='2022-01-01',
    end_date='2024-01-01',
    strategy_params={},  # Strategy-specific params
    cash=1000000,
    log_trades=True      # Enable detailed trade logging
)
```

#### Custom List of Stocks

```python
from strategy_orchastrator import StrategyTester

tester = StrategyTester(cash=500000, commission_rate=0.001)

result = tester.test_multiple_stocks(
    strategy_class=ShopStrategy,
    symbols=['RELIANCE.NS', 'TCS.NS', 'INFY.NS'],
    start_date='2022-01-01',
    end_date='2024-01-01',
    log_trades=True
)
```

#### Compare Multiple Strategies

```python
from strategy_orchastrator import StrategyTester
from strategy import (
    SkeletonStrategy, SimpleSMAStrategy, RSIStrategy, MACDStrategy
)

tester = StrategyTester()

strategies = [
    {
        'name': 'SkeletonStrategy',
        'class': SkeletonStrategy,
        'params': {}
    },
    {
        'name': 'SMA_10_30',
        'class': SimpleSMAStrategy,
        'params': {'fast_period': 10, 'slow_period': 30}
    },
    {
        'name': 'RSI_14_30_70',
        'class': RSIStrategy,
        'params': {'rsi_period': 14, 'rsi_lower': 30, 'rsi_upper': 70}
    }
]

comparison = tester.compare_strategies(
    strategies_config=strategies,
    use_index='NIFTY_MIDCAP_50',
    start_date='2022-01-01',
    end_date='2024-01-01'
)
```

> **Note:** Trade logging is automatically disabled during strategy comparison for performance.

## Analytics

The framework provides comprehensive analytics:

| Metric | Description |
|--------|-------------|
| **Total Return** | Overall portfolio return % |
| **CAGR** | Compounded annual growth rate |
| **Sharpe Ratio** | Risk-adjusted return (volatility) |
| **Sortino Ratio** | Risk-adjusted return (downside only) |
| **XIRR** | Time-weighted annual return |
| **Max Drawdown** | Largest peak-to-trough decline |
| **Win Rate** | % of profitable trades |
| **Profit Factor** | Gross profit / Gross loss |
| **Expectancy** | Average profit per trade |

### Trade Logger

When `log_trades=True`, detailed trade logs are saved to:

```
trade_logs/
└── ShopStrategy_NIFTY_MIDCAP_50_20250407_143022/
    ├── trades.csv      # Machine-readable
    └── trades.log      # Human-readable
```

Each entry includes:
- Entry/exit dates and prices
- Position size and direction
- P&L and commission
- Trade duration

## ATR Trailing Stop Loss

Wrap any strategy with ATR-based trailing stop loss:

```python
from strategy import SkeletonStrategy, wrap_strategy_with_atr_stop

# Create wrapped strategy
SkeletonWithStop = wrap_strategy_with_atr_stop(
    SkeletonStrategy,
    atr_period=14,           # 14-day ATR
    atr_multiplier=2.0       # 2x ATR distance
)

result = run_backtest(
    strategy_class=SkeletonWithStop,
    index_name='NIFTY_MIDCAP_50'
)
```

**Example:** Entry ₹50, ATR=₹1.80, 2x ATR stop = ₹46.40

The stop trails upward as price increases, but never moves down.

## Core Components

### `main.py`

Reusable backtesting engine with:
- `setup_cerebro()` - Configure engine with data, strategy, analyzers
- `run_backtest()` - End-to-end backtest with full analytics
- `display_analyzer_results()` - Print comprehensive results
- `add_comprehensive_analyzers()` - Add all analyzers

### `strategy_orchastrator.py`

Strategy comparison tool with:
- `StrategyTester` class - Flexible testing framework
- `test_multiple_stocks()` - Test on custom stock list
- `test_index()` - Test on entire index
- `compare_strategies()` - Side-by-side strategy comparison

### Adding New Strategies

1. Copy `strategy/skeleton_strategy.py` as a template (or create new):

```python
# strategy/my_strategy.py
import backtrader as bt

class MyStrategy(bt.Strategy):
    """
    STRATEGY: My Custom Strategy
    DATE: 2025-04-07
    LOGIC: Brief description of strategy logic
    
    INDICATORS USED:
    - SMA(20): Trend filter
    
    ENTRY CONDITIONS:
    1. Price > SMA(20)
    2. RSI < 30
    """
    params = (('param1', 10), ('param2', 20))

    def __init__(self):
        for d in self.datas:
            self.sma = bt.indicators.SMA(d.close, period=self.p.param1)
        # Initialize tracking dicts

    def next(self):
        self.update_metrics()
        self.check_exits()
        self.check_entries()

    def update_metrics(self):
        # Calculate signals
        pass

    def check_exits(self):
        # Exit logic
        pass

    def check_entries(self):
        # Entry logic
        pass

    def calculate_position_size(self, cash, price):
        return int(cash * 0.10 / price)

    def record_buy_order(self, symbol, price, size):
        # Track buys
        pass

    def notify_order(self, order):
        if order.status == order.Completed:
            # Print executions
            pass
```

2. Register in `strategy/__init__.py`:

```python
from strategy.my_strategy import MyStrategy
```

3. Use it:

```python
from strategy import MyStrategy

result = run_backtest(
    strategy_class=MyStrategy,
    strategy_params={'param1': 15, 'param2': 30}
)
```

## Dependencies

See `requirements.txt`:
- `backtrader` - Core backtesting engine
- `numpy_financial` - Financial calculations
- `thematicnifty` - Indian stock index data
- `yfinance` - Stock data fetching

## Notes

- All stock symbols should include `.NS` suffix for NSE
- Trade logs use UTF-8 encoding (supports ₹ symbol)
- Strategy comparison automatically disables trade logging for performance
- XIRR requires at least 2 days of data to calculate
