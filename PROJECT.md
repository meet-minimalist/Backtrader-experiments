# autoresearch — Trading Strategy

This is an experiment to have the LLM autonomously develop and iterate on trading strategies to optimize risk-adjusted returns (Sharpe, Sortino, XIRR) for a given index (e.g. NIFTY_MIDCAP_50, NIFTY50).

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `apr7`). The branch `autoresearch/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context and usage examples.
   - `config.py` — fixed constants (dates, cash, commission, index, risk-free rate). Do not modify.
   - `main.py` — backtesting engine (cerebro setup, analyzers, result display). Entry point for experiments.
   - `strategy_orchastrator.py` — strategy comparison tool. Do not modify.
   - `analyzers/` — metric calculators (Sortino, XIRR, TradeLogger). Do not modify.
   - `utils/stock_helper.py` — data loading helpers. Do not modify.
   - `strategy/skeleton_strategy.py` — **THE FILE YOU MODIFY**. This is your experimental canvas.
   - `strategy/__init__.py` — Register your strategy here when creating new files.
4. **Verify data access**: Confirm `thematicnifty` is configured and can fetch index data. If not, tell the human to verify their API key/setup.
5. **Run baseline**: Execute `python main.py` with `SkeletonStrategy` to establish baseline metrics.
6. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
7. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment is a backtest run that produces strategy performance metrics. You launch it as:

```bash
python strategy_orchastrator.py
```

Or programmatically:

```python
from main import run_backtest
result = run_backtest(strategy_class=YourStrategy, index_name='NIFTY_MIDCAP_50')
```

**What you CAN do:**
- Modify `strategy/skeleton_strategy.py` — this is your experimental canvas. Change anything: indicators, entry/exit logic, position sizing, risk management.
- Create new strategy files in `strategy/` (e.g. `strategy/momentum_strategy.py`). Register them in `strategy/__init__.py`.
- Modify `requirements.txt` — you can add new packages if needed.
- Use `wrap_strategy_with_atr_stop()` from `strategy/stop_loss_wrapper.py` to add trailing stops to any strategy.

**DOCUMENTATION REQUIREMENT**: When you modify strategy logic, you MUST update the docstring at the top of the file with:
- Strategy name and logic summary
- Indicators used and their parameters
- Entry conditions (list them clearly)
- Exit conditions (list them clearly)
- Any risk management rules
- Change log with date and description

Example docstring format:
```
STRATEGY: RSI Mean Reversion with ATR Stop
DATE: 2025-04-07
VERSION: 2.0

LOGIC SUMMARY:
- Entry: RSI < 30 AND price below SMA(50)
- Exit: RSI > 70 OR trailing stop hit
- Position Sizing: Volatility-weighted (1% risk per trade)
- Risk Management: ATR-based trailing stop (2x ATR)

INDICATORS USED:
- RSI(14): Entry/exit signal
- SMA(50): Trend filter
- ATR(14): Volatility-based stops

ENTRY CONDITIONS:
1. RSI(14) < 30 (oversold)
2. Price < SMA(50) (in downtrend)
3. Volume > 20-day average volume
4. Available cash > stock price

EXIT CONDITIONS:
1. RSI(14) > 70 (overbought) - profit taking
2. Price drops 2x ATR below highest since entry - trailing stop

MODIFICATION NOTES:
- 2025-04-07 v1.0: Baseline SMA mean reversion
- 2025-04-07 v2.0: Added RSI filter and ATR trailing stop
```

**What you CANNOT do:**
- Modify `main.py`, `strategy_orchastrator.py`, `config.py`. These are read-only.
- Modify analyzer files (`analyzers/`). The metrics are ground truth.
- Modify `utils/stock_helper.py`. Data loading is fixed.
- Change the evaluation harness. The analyzers (Sharpe, Sortino, XIRR) are the ground truth metrics.

**The goal is simple: maximize Sharpe Ratio, Sortino Ratio, and XIRR.** Since the backtest period is fixed, you don't need to worry about date ranges — it's always the same period from `config.py`. Everything is fair game: change the strategy logic, the indicators, the parameters, the position sizing, the exit conditions. The only constraint is that the code runs without crashing and produces valid results.

**Primary metric: Sharpe Ratio** (>1 is good, >1.5 is excellent).
**Secondary metrics: Sortino Ratio** (>1 is good), **XIRR** (positive, ideally >12%), **Max Drawdown** (<20%), **Win Rate** (>50%), **Profit Factor** (>1.5).

**Simplicity criterion**: All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Conversely, removing something and getting equal or better results is a great outcome — that's a simplification win. When evaluating whether to keep a change, weigh the complexity cost against the improvement magnitude. A 0.05 Sharpe improvement that adds 50 lines of hacky logic? Probably not worth it. A 0.05 Sharpe improvement from removing a redundant indicator? Definitely keep.

**The first run**: Your very first run should always be to establish the baseline, so you will run the ```main.py``` script as-is with `SkeletonStrategy`.

## Output format

When a strategy runs, it prints a summary like this:

```
💰 RETURNS ANALYSIS:
   Total Return: 45.23%
   Average Return: 0.02%
   CAGR: 12.45%
   Annual Returns:
     2023: 15.32%
     2024: 12.45%

🎯 RISK ANALYSIS:
   Sharpe Ratio: 1.25 (Higher is better, >1 is good)
   Sortino Ratio: 0.98 (Higher is better, >1 is good)
   Max Drawdown: 12.34% (Usually it should be 15-20% or lower)
   Drawdown Period: 45 days (Lower is better)

📈 XIRR ANALYSIS:
   XIRR: 15.67%
   Initial Value: ₹1,000,000.00
   Final Value: ₹1,452,300.00
   Days: 730
   Total Return: 45.23%

📊 TRADING STATISTICS:
   Total Trades: 125
   Winning Trades: 78
   Losing Trades: 47
   Win Rate: 62.4%
   Average Win: ₹2,340.50
   Average Loss: ₹-1,230.20
   Risk/Reward Ratio: 1.90
   Expectancy: 854.32
   Profit Factor: 1.65
```

You can extract key metrics from the output:

```
grep -A2 "Sharpe Ratio:" run.log
grep -A2 "Sortino Ratio:" run.log
grep "XIRR:" run.log
grep "Max Drawdown:" run.log
```

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated — commas break in descriptions).

The TSV has a header row and 6 columns:

```
commit	sharpe	sortino	xirr	drawdown	status	description
```

1. git commit hash (short, 7 chars)
2. Sharpe Ratio achieved (e.g. 1.25) — use 0.00 for crashes
3. Sortino Ratio achieved (e.g. 0.98) — use 0.00 for crashes
4. XIRR % achieved (e.g. 15.67) — use 0.00 for crashes
5. Max Drawdown % (e.g. 12.34) — use 0.00 for crashes
6. status: `keep`, `discard`, or `crash`
7. short text description of what this experiment tried

Example:

```
commit	sharpe	sortino	xirr	drawdown	status	description
a1b2c3d	0.85	0.72	14.20	18.50	keep	baseline (ShopStrategy)
b2c3d4e	1.12	0.95	16.80	14.20	keep	add RSI filter for entry
c3d4e5f	0.78	0.65	12.10	22.30	discard	switch to MACD crossover
d4e5f6g	0.00	0.00	0.00	0.00	crash	infinite loop in next()
```

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoresearch/apr7`).

LOOP FOREVER:

1. Look at the git state: the current branch/commit we're on.
2. Tune `strategy/skeleton_strategy.py` (or create a new strategy) with an experimental idea by directly hacking the code.
3. Update the docstring at the top of the file with your strategy logic summary.
4. git commit.
5. Run the experiment: `python main.py > run.log 2>&1` (redirect everything — do NOT use tee or let output flood your context).
6. Read out the results: `grep -A2 "Sharpe Ratio:\|Sortino Ratio:\|XIRR:\|Max Drawdown:" run.log`.
7. If the grep output is empty, the run crashed. Run `tail -n 50 run.log` to read the Python stack trace and attempt a fix. If you can't get things to work after more than a few attempts, give up.
8. Record the results in the TSV (NOTE: do not commit the results.tsv file, leave it untracked by git).
9. If Sharpe improved (higher), you "advance" the branch, keeping the git commit.
10. If Sharpe is equal or worse, you git reset back to where you started.

The idea is that you are a completely autonomous researcher trying things out. If they work, keep. If they don't, discard. And you're advancing the branch so that you can iterate. If you feel like you're getting stuck in some way, you can rewind but you should probably do this very very sparingly (if ever).

**Timeout**: Each experiment should take a few minutes (depending on data download and backtest complexity). If a run exceeds 10 minutes, kill it and treat it as a failure (discard and revert).

**Crashes**: If a run crashes (bug, data error, etc.), use your judgment: If it's something dumb and easy to fix (e.g. a typo, a missing import), fix it and re-run. If the idea itself is fundamentally broken, just skip it, log "crash" as the status in the TSV, and move on.

**NEVER STOP**: Once the experiment loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep, or gone from a computer and expects you to continue working *indefinitely* until you are manually stopped. You are autonomous. If you run out of ideas, think harder — read papers referenced in the code, re-read the in-scope files for new angles, try combining previous near-misses, try more radical architectural changes. The loop runs until the human interrupts you, period.

As an example use case, a user might leave you running while they sleep. If each experiment takes you ~5 minutes then you can run approx 12/hour, for a total of about 100 over the duration of the average human sleep. The user then wakes up to experimental results, all completed by you while they slept!

## Strategy Ideas to Explore

Start by modifying `strategy/skeleton_strategy.py` which has clear comments showing what to change in each function.

- **Indicator combinations**: SMA/EMA crossovers, RSI thresholds, MACD signals, Bollinger Band breakouts, ATR volatility filters
- **Entry filters**: Multiple confirmations (e.g., price above SMA + RSI oversold + volume spike)
- **Exit strategies**: Profit targets, trailing stops, time-based exits, indicator reversals
- **Position sizing**: Equal weight, volatility-weighted, risk-parity, Kelly criterion
- **Portfolio construction**: Top-N ranking, momentum scoring, sector diversification, correlation filtering
- **Risk management**: Per-trade risk limits, portfolio-level drawdown stops, correlation-adjusted sizing
- **Averaging strategies**: Scale-in on dips, grid trading, martingale (careful!), pyramiding
- **Market regime**: Trend-following in trends, mean-reversion in ranges, volatility-based strategy switching
- **Time-based**: Earnings avoidance, month-end rebalancing, seasonal patterns, day-of-week effects

## Progress Tracking

To review progress during a run:

```bash
# View results table
column -t results.tsv

# View recent commits and changes
git log --oneline -20

# Check current strategy changes
git diff HEAD~1 strategy/skeleton_strategy.py
```
