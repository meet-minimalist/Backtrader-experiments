import backtrader as bt
import os
import pandas as pd
from pathlib import Path
from datetime import datetime


class TradeLogger(bt.Analyzer):
    """
    Logs trades with strategy and stock context.
    Can be enabled/disabled per backtest run.
    """
    params = (
        ('log_dir', 'trade_logs'),
        ('enabled', True),
        ('strategy_name', None),
        ('stock_name', None),
    )

    def __init__(self):
        self.trades = []
        self.trade_num = 0

        # Skip if disabled (useful for strategy comparison)
        if not self.params.enabled:
            return

        # Create log directory with strategy context
        strat = self.params.strategy_name or 'UnknownStrategy'
        stock = self.params.stock_name or 'UnknownStock'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        self.folder_name = f"{strat}_{stock}_{timestamp}"
        self.log_dir = os.path.join(self.params.log_dir, self.folder_name)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

        self.csv_path = os.path.join(self.log_dir, 'trades.csv')
        self.log_path = os.path.join(self.log_dir, 'trades.log')

        # Initialize log file
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write("="*100 + "\n")
            f.write(f"STRATEGY: {strat}\n")
            f.write(f"STOCK:    {stock}\n")
            f.write(f"LOGGED:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*100 + "\n\n")

    def notify_trade(self, trade):
        if not self.params.enabled:
            return

        if trade.isclosed:
            self.trade_num += 1

            # Calculate trade metrics
            pnl = trade.pnlcomm  # Use Net P&L (after commission) instead of Gross
            pnl_pct = (pnl / trade.value) * 100 if trade.value != 0 else 0
            duration = (trade.dtclose - trade.dtopen)

            # Calculate exit price
            entry_price = trade.price
            exit_price = entry_price + (pnl / trade.size) if trade.size != 0 else entry_price

            trade_info = {
                'trade_num': self.trade_num,
                'stock': trade.data._name if hasattr(trade.data, '_name') else 'Unknown',
                'entry_date': bt.num2date(trade.dtopen).strftime('%Y-%m-%d'),
                'exit_date': bt.num2date(trade.dtclose).strftime('%Y-%m-%d'),
                'direction': 'LONG' if trade.size > 0 else 'SHORT',
                'size': abs(trade.size),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'duration_days': duration,
                'commission': trade.commission,
                'status': 'WIN' if pnl > 0 else 'LOSS'
            }

            self.trades.append(trade_info)
            self._write_log_entry(trade_info)

    def _write_log_entry(self, trade):
        """Write formatted trade entry to log file."""
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f"{'='*100}\n")
            f.write(f"Trade #{trade['trade_num']} - {trade['stock']} - {trade['status']}\n")
            f.write(f"{'='*100}\n")
            f.write(f"Direction:        {trade['direction']}\n")
            f.write(f"Entry Date:       {trade['entry_date']}\n")
            f.write(f"Exit Date:        {trade['exit_date']}\n")
            f.write(f"Duration:         {trade['duration_days']} days\n")
            f.write(f"Size:             {trade['size']}\n")
            f.write(f"Entry Price:      ₹{trade['entry_price']:.2f}\n")
            f.write(f"Exit Price:       ₹{trade['exit_price']:.2f}\n")
            f.write(f"P&L:              ₹{trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)\n")
            f.write(f"Commission:       ₹{trade['commission']:.2f}\n")
            f.write(f"\n")

    def stop(self):
        """Save trades to CSV and write summary."""
        if not self.params.enabled:
            return

        if self.trades:
            df = pd.DataFrame(self.trades)
            df.to_csv(self.csv_path, index=False)

            # Write summary
            wins = sum(1 for t in self.trades if t['status'] == 'WIN')
            losses = sum(1 for t in self.trades if t['status'] == 'LOSS')
            total_pnl = sum(t['pnl'] for t in self.trades)

            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write("\n" + "="*100 + "\n")
                f.write("SUMMARY\n")
                f.write("="*100 + "\n")
                f.write(f"Total Trades:     {len(self.trades)}\n")
                f.write(f"Winning Trades:   {wins}\n")
                f.write(f"Losing Trades:    {losses}\n")
                f.write(f"Win Rate:         {(wins/len(self.trades)*100):.1f}%\n")
                f.write(f"Total P&L:        ₹{total_pnl:.2f}\n")
                f.write(f"\nCSV saved to:     {self.csv_path}\n")
                f.write(f"Log saved to:     {self.log_path}\n")
                f.write("="*100 + "\n")

    def get_analysis(self):
        """Return trade analysis."""
        if not self.params.enabled:
            return {'enabled': False}
        
        return {
            'enabled': True,
            'trades': self.trades,
            'csv_path': getattr(self, 'csv_path', None),
            'log_path': getattr(self, 'log_path', None),
            'total_trades': len(self.trades),
            'wins': sum(1 for t in self.trades if t['status'] == 'WIN'),
            'losses': sum(1 for t in self.trades if t['status'] == 'LOSS'),
            'total_pnl': sum(t['pnl'] for t in self.trades)
        }
