# Auto Strategy Development

This is an experiment to have an LLM develop and improve a trading strategy iteratively.

## Setup
To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar5`). The branch `autostratdev/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autostratdev/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context.
   - `main.py` — backtesting engine (cerebro setup, analyzers, result display). Entry point for experiments. DO NOT MODIFY.
   - `config.py` — fixed constants (dates, cash, commission, index, risk-free rate). DO NOT MODIFY.
   - `analyzers/` — metric calculators (Sortino, XIRR, TradeLogger). DO NOT MODIFY.
   - `utils/` — data loading helpers. DO NOT MODIFY.
   - `commission/` — Broker commission calculation utility. DO NOT MODIFY.
   - `strategy/skeleton_strategy.py` — the file you modify. Strategy logic, timeframe, what indicators you'd like to use etc.
4. **Initialize `results.tsv`**: Create results.tsv with just the header row. The baseline will be recorded after the first run.
5. **Confirm and go**: Confirm setup looks good.
Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs on a backtest. You launch it simply as: `uv run python -m main`

**What you CAN do:**

   - Modify `strategy/skeleton_strategy.py` — this is the only file you edit. Everything is fair game: strategy logic, timeframe, what indicators to use, etc.

**What you CANNOT do:**

   - Modify `main.py`. It is read-only. It contains core logic for loading data, and ensuring trades are placed and executed fairly.
   - Modify the evaluation metrics. The analyzers present in `./analyzers` directory. 
   - Modify `config.py`. It is read-only and contains start and end date of backtest, interval of the data available, initial cash available, index name etc.

The goal: maximize **risk-adjusted return**. The selection metric is **Calmar = XIRR / Max Drawdown** — a strategy making 20% XIRR with a 20% max drawdown (Calmar 1.0) beats one making 30% with a 50% drawdown (Calmar 0.6). Everything is fair game: change the strategy, the indicators, the windows, the timeframe. The only constraint is that the code runs without crashing and output print_metrics to stdout.

Selection rules (ALL must hold to keep a change):

1. **Calmar improves**: keep a change if XIRR / MaxDrawdown beats the current champion. All else being equal, simpler is better.
2. **Sharpe must not degrade materially**: a Sharpe drop of more than ~0.05 needs a large Calmar win to justify it. Conversely, a change with ~equal Calmar but better Sharpe or lower drawdown is a keep — that's a volatility win.
3. **XIRR floor**: XIRR must stay above 12% (beat fixed deposits). A tiny-drawdown strategy earning less than that is uninteresting — discard regardless of Calmar.
4. **Realized trades requirement**: every position must have an explicit exit rule (signal, stop, target, or time-based). Pure buy-and-hold — where the return engine is open positions marked to market at the end of the backtest — is ineligible. Measurable check: the run must show closed winning trades (Winning Trades > 0 and Average Win > 0), and the trade statistics must reflect the strategy's actual return engine, not just its discarded losers. A strategy that only ever realizes losses while its winners stay open forever converges to buy-and-hold; discard it even if Calmar improves.

The first run: Your very first run should always be to establish the baseline, so you will run the backtesting script as is.

## Output format

When a strategy runs, it prints a summary like this:

```
💰 RETURNS ANALYSIS:
   Total Return: 45.23%
   Average Return: 0.02%
   CAGR: 12.45%
   XIRR: 12.83%
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
commit	xirr  sharpe	sortino  drawdown status   description
```

1. git commit hash (short, 7 chars)
2. XIRR % achieved (e.g. 15.67) — use 0.00 for crashes
3. Sharpe Ratio achieved (e.g. 1.25) — use 0.00 for crashes
4. Sortino Ratio achieved (e.g. 0.98) — use 0.00 for crashes
5. Max Drawdown % (e.g. 12.34) — use 0.00 for crashes
6. status: `keep`, `discard`, or `crash`
7. short text description of what this experiment tried

Example:

```
commit	xirr  sharpe   sortino	drawdown	status	description
a1b2c3d	18.50 0.85	   0.72	   14.20	   keep	   baseline (ShopStrategy)
b2c3d4e	14.20 1.12	   0.95	   16.80	   keep	   add RSI filter for entry
c3d4e5f	22.30 0.78	   0.65	   12.10	   discard	switch to MACD crossover
d4e5f6g	0.00  0.00	   0.00	   0.00	   crash	   infinite loop in next()
```

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoresearch/apr7`).

LOOP FOREVER:

1. Look at the git state: the current branch/commit we're on.
2. Tune `strategy/skeleton_strategy.py` with an experimental idea by directly hacking the code.
3. Update the docstring at the top of the file with your strategy logic summary.
4. git commit.
5. Run the experiment: `uv run python -m main > run.log 2>&1` (redirect everything — do NOT use tee or let output flood your context).
6. Read out the results: `grep -A2 "Sharpe Ratio:\|Sortino Ratio:\|XIRR:\|Max Drawdown:" run.log`.
7. If the grep output is empty, the run crashed. Run `tail -n 50 run.log` to read the Python stack trace and attempt a fix. If you can't get things to work after more than a few attempts, give up.
8. If the risk-adjusted result improved (Calmar = XIRR/MaxDD higher AND the Selection rules hold), you "advance" the branch, keeping the git commit
9. If Calmar is equal or worse, or any Selection rule fails (Sharpe degraded, XIRR below floor, no realized winning trades), you git reset back to where you started
10. For marginal changes use the `Selection rules` to decide.

You are a completely autonomous quant developer trying things out. If they work, keep. If they don't, discard. And you're advancing the branch so that you can iterate. If you feel like you're getting stuck in some way, you can rewind but you should probably do this very very sparingly (if ever).

**Crashes**: If a run crashes (OOM, or a bug, or etc.), use your judgment: If it's something dumb and easy to fix (e.g. a typo, a missing import), fix it and re-run. If the idea itself is fundamentally broken, just skip it, log "crash" as the status in the tsv, and move on.

**NEVER STOP**: Once the development loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep, or gone from a computer and expects you to continue working indefinitely until you are manually stopped. You are autonomous. If you run out of ideas, think harder — read papers, read famous quant blogs, re-read the in-scope files for new angles, try combining previous near-misses, try more radical architectural changes. The loop runs until the human interrupts you, period.

As an example use case, a user might leave you running while they sleep. If each development cycle takes you ~2 minutes then you can run approx 30/hour, for a total of about 240 over the duration of the average human sleep. The user then wakes up to experimental results, all completed by you while they slept!