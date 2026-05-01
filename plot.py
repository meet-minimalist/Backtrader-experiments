"""
EMA 20/50/100/200 Plotter with EMA-200 Standard Deviation Bands
Usage: python ema_plot.py [TICKER] [PERIOD]
  TICKER: stock symbol (default: RELIANCE.NS)
  PERIOD: data period like 1y, 2y, 5y (default: 2y)

Examples:
  python ema_plot.py INFY.NS 2y
  python ema_plot.py TCS.NS 1y
  python ema_plot.py AAPL 2y
"""

import sys
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch

# ── Config ────────────────────────────────────────────────────────────────────
TICKER = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
PERIOD = sys.argv[2] if len(sys.argv) > 2 else "2y"

EMA_PERIODS   = [20, 50, 100, 200]
EMA_COLORS    = ["#00d4ff", "#f0c040", "#ff6b35", "#e055e0"]
STD_WINDOW    = 50          # rolling window used to compute σ of EMA-200
STD_UPPER_K   = 2.0         # upper band multiplier
STD_LOWER_K   = 2.0         # lower band multiplier

# ── Fetch Data ────────────────────────────────────────────────────────────────
print(f"Fetching {TICKER} ({PERIOD}) …")
df = yf.download(TICKER, period=PERIOD, auto_adjust=True, progress=False)
if df.empty:
    sys.exit(f"No data returned for '{TICKER}'. Check the ticker symbol.")

# Flatten MultiIndex columns if present (yfinance ≥ 0.2.x)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

close = df["Close"].squeeze()

# ── Compute EMAs ──────────────────────────────────────────────────────────────
emas = {p: close.ewm(span=p, adjust=False).mean() for p in EMA_PERIODS}

# ── Compute Rolling Std-Dev of EMA-200 and Bands ─────────────────────────────
ema200        = emas[200]
rolling_std   = ema200.rolling(window=STD_WINDOW, min_periods=STD_WINDOW // 2).std()

upper_band    = ema200 + STD_UPPER_K * rolling_std   # +2σ
lower_band    = ema200 - STD_LOWER_K * rolling_std   # -0.5σ

# ── Plot ──────────────────────────────────────────────────────────────────────
plt.style.use("dark_background")
fig, (ax_price, ax_std) = plt.subplots(
    2, 1,
    figsize=(16, 10),
    gridspec_kw={"height_ratios": [3, 1]},
    sharex=True,
)
fig.patch.set_facecolor("#0d0d0d")

# ── Top Panel: Price + EMAs + Bands ──────────────────────────────────────────
ax_price.set_facecolor("#0d0d0d")

# Shaded band between +2σ and -0.5σ
ax_price.fill_between(
    df.index, upper_band, lower_band,
    alpha=0.08, color="#e055e0", label="_nolegend_"
)

# Price candle-like line (OHLC range shading)
ax_price.fill_between(df.index, df["Low"].squeeze(), df["High"].squeeze(),
                       alpha=0.07, color="#aaaaaa")
ax_price.plot(df.index, close, color="#cccccc", linewidth=0.8,
              alpha=0.9, label="Close", zorder=2)

# EMAs
for p, col in zip(EMA_PERIODS, EMA_COLORS):
    ax_price.plot(df.index, emas[p], color=col, linewidth=1.4 if p < 200 else 2.0,
                  label=f"EMA {p}", zorder=3 + p // 50)

# Std-dev bands
ax_price.plot(df.index, upper_band, color="#ff4488", linewidth=1.2,
              linestyle="--", label=f"EMA200 +{STD_UPPER_K}σ", zorder=6)
ax_price.plot(df.index, lower_band, color="#44ff88", linewidth=1.2,
              linestyle="--", label=f"EMA200 −{STD_LOWER_K}σ", zorder=6)

# Annotate last values on the right axis
last_date = df.index[-1]
for p, col in zip(EMA_PERIODS, EMA_COLORS):
    val = emas[p].iloc[-1]
    ax_price.annotate(f"{val:.1f}", xy=(last_date, val),
                      xytext=(6, 0), textcoords="offset points",
                      color=col, fontsize=7.5, va="center",
                      clip_on=False)

ax_price.set_title(f"{TICKER}  —  EMA 20/50/100/200  with EMA-200 Std-Dev Bands",
                   color="white", fontsize=14, pad=10)
ax_price.set_ylabel("Price", color="#aaaaaa")
ax_price.tick_params(colors="#888888")
ax_price.yaxis.label.set_color("#aaaaaa")
ax_price.legend(loc="upper left", fontsize=8, framealpha=0.25,
                labelcolor="white", facecolor="#111111")
ax_price.grid(axis="y", color="#222222", linewidth=0.5)
ax_price.spines[:].set_visible(False)

# ── Bottom Panel: Rolling Std-Dev of EMA-200 ─────────────────────────────────
ax_std.set_facecolor("#0d0d0d")
ax_std.plot(df.index, rolling_std, color="#e055e0", linewidth=1.2,
            label=f"Rolling σ  (window={STD_WINDOW})")
ax_std.fill_between(df.index, 0, rolling_std, alpha=0.18, color="#e055e0")

# Reference lines for 2σ and 0.5σ of the overall std (static guide)
overall_std = rolling_std.mean()
ax_std.axhline(overall_std * 2,   color="#ff4488", linewidth=0.8, linestyle=":",
               label=f"Mean×2  ({overall_std*2:.2f})")
ax_std.axhline(overall_std * 0.5, color="#44ff88", linewidth=0.8, linestyle=":",
               label=f"Mean×0.5  ({overall_std*0.5:.2f})")

ax_std.set_ylabel("σ  (EMA 200)", color="#aaaaaa")
ax_std.tick_params(colors="#888888")
ax_std.yaxis.label.set_color("#aaaaaa")
ax_std.legend(loc="upper left", fontsize=7.5, framealpha=0.25,
              labelcolor="white", facecolor="#111111")
ax_std.grid(axis="y", color="#222222", linewidth=0.5)
ax_std.spines[:].set_visible(False)
ax_std.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
ax_std.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax_std.tick_params(axis="x", colors="#888888", rotation=30)

plt.tight_layout(h_pad=0.5)
import os
os.makedirs("./outputs", exist_ok=True)
out_path = f"./outputs/{TICKER.replace('.','_')}_ema_bands.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Chart saved → {out_path}")
plt.show()