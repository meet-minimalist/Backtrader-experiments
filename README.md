# Backtrader Strategy Testing Framework

One day, strategy research used to be done by humans in between eating, sleeping, and synchronizing in the ritual of "weekly review meetings". That era is ending. Research is now the domain of autonomous AI agents iterating on strategy code overnight. You wake up in the morning to a log of experiments and (hopefully) better Sharpe ratios. This repo is the story of how it all began.

**The idea:** Give an AI agent a small but real backtesting setup and let it experiment autonomously. It modifies the strategy, runs a backtest, checks if the metrics improved, keeps or discards, and repeats.

## How It Works

The repo is deliberately kept small with clear boundaries:

- **`config.py`** — fixed constants (dates, cash, index, commission). Not modified by agent.
- **`main.py`** — backtesting engine, analyzers, result display. Not modified by agent.
- **`strategy_orchastrator.py`** — strategy comparison tool. Not modified by agent.
- **`strategy/skeleton_strategy.py`** — **THE FILE THE AGENT EDITS**. Contains the full strategy template. Everything is fair game: indicators, entry/exit logic, position sizing, risk management.
- **`PROJECT.md`** — agent instructions for autonomous research. **This file is edited by the human** to refine the research process.

By design, backtest runs use a **fixed time period** (from `config.py`), regardless of strategy complexity. The primary metric is **Sharpe Ratio** (higher is better, >1 is good, >1.5 is excellent) — it's risk-adjusted so strategies are fairly compared regardless of their risk profile.

If you are new to algorithmic trading or backtesting, the skeleton strategy is intentionally well-commented to help you understand the flow.

## Quick Start

**Requirements:** Python 3.10+, access to Indian stock data via `thematicnifty` API.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify data access works (one-time check)
python -c "from thematicnifty import tn; print('Data access OK')"

# 3. First run will download the stock data and cache it. Subsequent runs will skip the download and use the cached data. Manually run a single backtest experiment
python main.py
```

If the above commands all work ok, your setup is working and you can go into autonomous research mode.

## Running the Agent

Simply spin up your AI agent (Claude, Codex, Qwen, etc.) in this repo, then you can prompt something like:

```
Hi have a look at PROJECT.md and let's kick off a new experiment! Let's do the setup first.
```

The `PROJECT.md` file is essentially a lightweight "skill" that guides autonomous experimentation.

## Design Choices

- **Single file to modify.** The agent only touches `strategy/skeleton_strategy.py`. This keeps the scope manageable and diffs reviewable.
- **Fixed backtest period.** Experiments always use the same date range from `config.py`, making results directly comparable regardless of what the agent changes (indicators, logic, parameters).
- **Fixed index.** All experiments run on the same index (e.g., NIFTY_MIDCAP_50) for fair comparison.
- **Self-contained.** No external dependencies beyond what's in `requirements.txt`. No complex configs. One index, one metric, one file.
- **Skeleton as template.** The skeleton strategy is intentionally over-commented with "WHAT TO MODIFY" markers so the agent knows exactly where to experiment.

## Project Structure

```
backtrader_experiements/
├── main.py                          # Core backtesting engine (read-only)
├── strategy_orchastrator.py         # Strategy comparison tool (read-only)
├── config.py                        # Global settings (read-only)
├── PROJECT.md                       # Agent instructions for autonomous research
├── README.md                        # This file
│
├── strategy/                        # Strategy implementations
│   ├── skeleton_strategy.py         # THE FILE TO MODIFY - well-commented template
│   ├── stop_loss_wrapper.py         # ATR trailing stop wrapper (reusable)
│   ├── shop_strategy.py             # Reference: existing strategy
│   ├── rsi_strategy.py              # Reference: RSI-based strategy
│   ├── macd_strategy.py             # Reference: MACD crossover strategy
│   ├── simple_sma_strategy.py       # Reference: SMA crossover strategy
│   └── __init__.py                  # Strategy registry
│
├── analyzers/                       # Custom analyzers (read-only)
│   ├── sortino.py                   # Sortino Ratio analyzer
│   ├── xirr_analyzer.py             # XIRR calculator
│   ├── trade_logger.py              # Trade logging with strategy/stock context
│   └── ...
│
├── utils/                           # Helper utilities (read-only)
│   ├── stock_helper.py              # Data loading helpers
│   └── formatter.py                 # Output formatting
│
└── commission/                      # Commission models (read-only)
    └── zerodha.py                   # Zerodha delivery commission
```

## Configuration

Edit `config.py` to set defaults before starting experiments:

```python
start_date = '2020-01-01'
end_date = '2025-08-31'
initial_cash = 1000000
index_name = "NIFTY_MIDCAP_50"
riskfreerate = 0.06
```

## Experiment Loop

The agent runs experiments on a dedicated branch (e.g., `autoresearch/apr7`).

**LOOP:**

1. Read `PROJECT.md` for experiment guidelines
2. Modify `strategy/skeleton_strategy.py` with a new idea
3. Update the strategy docstring at the top (logic, indicators, conditions)
4. git commit
5. Run: `python main.py > run.log 2>&1`
6. Extract results: `grep -A2 "Sharpe Ratio:\|Sortino Ratio:\|XIRR:" run.log`
7. If results improved → keep the commit and advance
8. If results unchanged/worse → git reset and try something else
9. Log results to `results.tsv` (tab-separated)

Each experiment takes a few minutes. You can expect ~12 experiments/hour, or ~100 experiments overnight.

## Analytics

The framework provides comprehensive analytics:

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| **Sharpe Ratio** | Risk-adjusted return (total volatility) | >1.0, ideally >1.5 |
| **Sortino Ratio** | Risk-adjusted return (downside only) | >1.0 |
| **XIRR** | Time-weighted annual return | >12% (beat FDs) |
| **Max Drawdown** | Largest peak-to-trough decline | <20% |
| **Win Rate** | % of profitable trades | >50% |
| **Profit Factor** | Gross profit / Gross loss | >1.5 |
| **Expectancy** | Average profit per trade | Positive |
| **CAGR** | Compounded annual growth rate | >15% |

**Primary metric: Sharpe Ratio** — it's the fairest comparison across strategies since it accounts for risk. A strategy that makes 50% returns with 60% volatility is worse than one that makes 30% with 15% volatility.

### Trade Logger

When `log_trades=True`, detailed trade logs are saved to:

```
trade_logs/
└── SkeletonStrategy_NIFTY_MIDCAP_50_20250407_143022/
    ├── trades.csv      # Machine-readable (for analysis)
    └── trades.log      # Human-readable (for debugging)
```

Each entry includes:
- Entry/exit dates and prices
- Position size and direction
- P&L and commission
- Trade duration

## Strategy Experiment Ideas

Here are concrete experiments to try, roughly ordered from simple to advanced. All experiments work within a single index (e.g., NIFTY_50) using only OHLCV data available per stock.

### Level 1: Parameter Tuning
- Change `sma_period` from 20 → 10, 30, 50
- Adjust `exit_threshold` from 6% → 4%, 8%, 10%
- Modify `position_size_pct` from 10% → 5%, 15%, 20%
- Change `averaging_down_threshold` from 3% → 2%, 5%

### Level 2: Price-Based Indicators
- Add RSI(14) — only buy when RSI < 30 (oversold confirmation)
- Add EMA(12, 26) — faster/slower trend signals
- Add MACD — enter when MACD line crosses above signal
- Add Bollinger Bands(20, 2) — buy at lower band, exit at upper
- Add Stochastic Oscillator(14, 3) — overbought/oversold timing
- Add CCI(20) — commodity channel index for cycle detection
- Add Williams %R — momentum reversal signal
- Add ADX(14) — trend strength filter (only trade when ADX > 25)

### Level 3: Volume-Based Indicators
- **Volume SMA** — only trade stocks with volume > 1.5x average volume
- **OBV (On-Balance Volume)** — confirm price moves with volume
- **Volume Rate of Change** — spot unusual volume spikes
- **Chaikin Money Flow(20)** — accumulation/distribution signal
- **Volume-Weighted Average Price (VWAP)** — institutional price level
- **Volume + Price Breakout** — only enter when BOTH price and volume break out
- **Volume Divergence** — price making new low but volume declining (reversal signal)

### Level 4: Volatility Indicators
- **ATR(14)** — volatility-based position sizing and stops
- **Keltner Channels** — ATR-based bands for entry/exit
- **Donchian Channels(20)** — breakout at N-day high/low
- **Standard Deviation Bands** — volatility expansion/contraction
- **Historical Volatility** — only trade low-volatility stocks
- **Volatility Contraction** — enter when ATR is at N-day low (breakout coming)

### Level 5: Entry Filter Combinations
- Price < SMA(20) AND RSI < 30 AND volume > volume_sma
- Price crosses above EMA(12) AND MACD histogram turning positive
- Price below lower Bollinger Band AND RSI showing bullish divergence
- ADX > 25 (strong trend) AND EMA(12) > EMA(26) AND volume spike
- ATR contracting (low volatility) + Donchian breakout (new 20-day high)

### Level 6: Exit Strategy Variations
- Replace fixed 6% target with ATR trailing stop (use wrapper)
- Exit when RSI > 70 (overbought) instead of fixed target
- Time-based exit: close positions older than 20/30/60 days
- Exit when price crosses back below SMA(20)
- Exit when volume spikes on down day (distribution signal)
- Scale out: sell 50% at 4% profit, rest at 8%

### Level 7: Position Sizing Experiments
- **Volatility-weighted**: larger positions in less volatile stocks (1/ATR)
- **Equal risk**: size positions so each has same ATR-based dollar risk
- **Volume-weighted**: larger positions in higher liquidity stocks
- **Kelly criterion**: optimal bet size based on win rate and R:R ratio
- **Risk parity**: allocate based on inverse volatility ranking

### Level 8: Portfolio Construction (Within Index Only)
- Change `ranking_count` from 5 → 3, 10, 20
- Rank by momentum: buy top N performers over last 20 days
- Rank by mean reversion: buy biggest losers expecting bounce
- Rank by volume strength: trade stocks with highest volume confirmation
- Rank by volatility: prefer low-volatility stocks for stability
- Rank by composite score: weighted combination of multiple signals

### Level 9: Advanced Signal Combinations
- **RSI + Volume**: RSI < 30 AND volume > 2x average (oversold with conviction)
- **MACD + ATR**: MACD crossover AND ATR expanding (trend + volatility breakout)
- **Bollinger + OBV**: Price at lower band AND OBV making higher low (accumulation at support)
- **Stochastic + ADX**: Stochastic oversold AND ADX rising (strong trend reversal)
- **Volume Profile + VWAP**: Price bounces off VWAP with volume confirmation

### Level 10: Multi-Timeframe Analysis
- Use daily data but check weekly SMA(20) for trend filter
- Check if stock is above/below both short-term (10) and long-term (50) MAs
- Rate of change: compare 5-day vs 20-day momentum
- Dual timeframe confirmation: daily RSI oversold + weekly RSI turning up

### High-Impact Combinations to Try First
1. **RSI + SMA + Volume** — RSI < 30 AND price < SMA(20) AND volume > 1.5x avg
2. **ATR Trailing Stop** — wrap with `wrap_strategy_with_atr_stop(skeleton, atr_multiplier=2.0)`
3. **Momentum + Volume** — rank by 20-day return, only trade with volume confirmation
4. **Bollinger Mean Reversion** — buy at lower band, exit at middle band
5. **MACD + RSI Filter** — MACD crossover only when RSI < 40
6. **Volume Breakout** — enter when price breaks 20-day high with 2x volume
7. **Low Volatility Portfolio** — rank by lowest ATR, trade top 10 stable stocks
8. **OBV Divergence** — buy when price makes lower low but OBV makes higher low

## Using the ATR Trailing Stop Wrapper

Wrap any strategy with ATR-based trailing stop loss (no code changes needed):

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

**Example:** Entry ₹50, ATR=₹1.80, 2x ATR stop = ₹46.40. The stop trails upward as price increases, but never moves down.

## Usage Patterns

### Quick Backtest (Default)

```bash
python main.py
```

### Compare Multiple Strategies

```python
from strategy_orchastrator import StrategyTester
from strategy import SkeletonStrategy, SimpleSMAStrategy, RSIStrategy

tester = StrategyTester()

strategies = [
    {'name': 'Skeleton', 'class': SkeletonStrategy, 'params': {}},
    {'name': 'SMA_10_30', 'class': SimpleSMAStrategy, 'params': {'fast_period': 10, 'slow_period': 30}},
    {'name': 'RSI', 'class': RSIStrategy, 'params': {'rsi_period': 14}},
]

comparison = tester.compare_strategies(strategies, use_index='NIFTY_MIDCAP_50')
```

### Custom Stock List

```python
from strategy_orchastrator import StrategyTester

tester = StrategyTester(cash=500000, commission_rate=0.001)
result = tester.test_multiple_stocks(
    strategy_class=SkeletonStrategy,
    symbols=['RELIANCE.NS', 'TCS.NS', 'INFY.NS'],
    log_trades=True
)
```

## Adding New Strategies

1. Copy `strategy/skeleton_strategy.py` as a template (recommended) or create new file
2. Update the docstring at the top with your strategy logic (required!)
3. Register in `strategy/__init__.py`:

```python
from strategy.my_strategy import MyStrategy
```

4. Use it in experiments

## Progress Tracking

During an autonomous run:

```bash
# View experiment log
column -t results.tsv

# View recent changes
git log --oneline -20

# See what changed in latest experiment
git diff HEAD~1 strategy/skeleton_strategy.py

# Check current results
tail -f results.tsv
```

## Dependencies

See `requirements.txt`:
- `backtrader` - Core backtesting engine
- `numpy_financial` - Financial calculations (XIRR)
- `thematicnifty` - Indian stock index data
- `yfinance` - Stock data fetching
- `numpy` - Numerical operations

## Notes

- All stock symbols should include `.NS` suffix for NSE
- Trade logs use UTF-8 encoding (supports ₹ symbol)
- Strategy comparison automatically disables trade logging for performance
- XIRR requires at least 2 days of data to calculate
- The skeleton strategy is intentionally simple — a basic mean reversion baseline that the agent should improve upon
