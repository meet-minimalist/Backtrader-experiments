import sys
import logging
import backtrader as bt

# Set default logging level to WARNING (suppresses debug/info prints)
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

# Fix Windows console encoding for ₹ character
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import inspect
from strategy import SkeletonStrategy
from analyzers.sortino import SortinoRatio
from analyzers.trade_logger import TradeLogger
from analyzers.xirr_analyzer import XIRRAnalyzer
from config import initial_cash, riskfreerate
from utils.stock_helper import load_index_data, fetch_stock_data
from commission.zerodha import ZerodhaDeliveryCommission

def setup_cerebro(strategy_class, data_feeds, successful_symbols=None,
                  strategy_params=None, cash=None, log_trades=True, 
                  strategy_name=None, stock_name=None):
    """
    Create and configure Cerebro engine with data, strategy, and analyzers.

    Args:
        strategy_class: Backtrader strategy class
        data_feeds: List of backtrader data feeds
        successful_symbols: List of symbol names corresponding to data_feeds (optional)
        strategy_params: Dict of parameters to pass to strategy
        cash: Starting cash (defaults to config)
        log_trades: Whether to enable trade logging (default: True)
        strategy_name: Strategy name for trade logger
        stock_name: Stock/index name for trade logger

    Returns:
        Configured Cerebro instance
    """
    cerebro = bt.Cerebro()

    # Add data feeds
    for data_feed in data_feeds:
        name = data_feed._name if hasattr(data_feed, '_name') else None
        cerebro.adddata(data_feed, name=name)

    # Add strategy - only pass symbol_names if strategy accepts it
    all_params = {}
    if strategy_params:
        all_params.update(strategy_params)

    # Check if strategy accepts symbol_names parameter
    if successful_symbols:
        sig = inspect.signature(strategy_class.__init__)
        if 'symbol_names' in sig.parameters:
            all_params['symbol_names'] = successful_symbols

    if all_params:
        cerebro.addstrategy(strategy_class, **all_params)
    else:
        cerebro.addstrategy(strategy_class)
    
    # Set up broker
    cerebro.broker.setcash(cash if cash is not None else initial_cash)
    cerebro.broker.addcommissioninfo(ZerodhaDeliveryCommission())
    
    # Add comprehensive analyzers
    add_comprehensive_analyzers(cerebro, log_trades=log_trades, 
                                strategy_name=strategy_name, stock_name=stock_name)

    return cerebro


def add_comprehensive_analyzers(cerebro, log_trades=True, strategy_name=None, stock_name=None):
    """
    Add all comprehensive analyzers to cerebro.

    Args:
        cerebro: Backtrader Cerebro instance
        log_trades: Whether to enable trade logger
        strategy_name: Strategy name for trade logger
        stock_name: Stock/index name for trade logger
    """
    # Returns Analysis
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
    
    # Risk Analysis
    cerebro.addanalyzer(bt.analyzers.Calmar, _name='calmar')
    cerebro.addanalyzer(
        bt.analyzers.SharpeRatio,
        _name='sharpe',
        riskfreerate=riskfreerate,
        timeframe=bt.TimeFrame.Days,
        annualize=True
    )
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(SortinoRatio, _name='sortino', riskfreerate=riskfreerate, timeframe=bt.TimeFrame.Days)

    # XIRR Analysis
    cerebro.addanalyzer(XIRRAnalyzer, _name='xirr')

    # Trade Analysis
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Trade Logger (optional)
    if log_trades:
        cerebro.addanalyzer(TradeLogger, _name='trade_logger',
                           enabled=True,
                           strategy_name=strategy_name,
                           stock_name=stock_name)
    

def run_backtest(strategy_class=None, index_name=None,
                 start_date=None, end_date=None,
                 symbols=None, strategy_params=None,
                 cash=None, commission_rate=None,
                 log_trades=True, strategy_name=None, stock_name=None,
                 plot=False):
    """
    Run a complete backtest with comprehensive analytics.
    
    Args:
        strategy_class: Backtrader strategy class (default: ShopStrategy)
        index_name: Index name to load data from
        start_date: Start date string
        end_date: End date string
        symbols: List of symbols (alternative to index_name)
        strategy_params: Dict of strategy parameters
        cash: Starting cash
        plot: Whether to plot results
    
    Returns:
        Dict with strategy, cerebro, and results
    """
    from config import start_date as config_start, end_date as config_end, index_name as config_index
    
    # Use config defaults if not provided
    strategy_class = strategy_class or SkeletonStrategy
    start_date = start_date or config_start
    end_date = end_date or config_end
    index_name = index_name or symbols or config_index
    
    # Load data
    print("Fetching stock data...")
    if isinstance(index_name, str):
        data_feeds, successful_symbols = load_index_data(
            index_name=index_name,
            start_date=start_date,
            end_date=end_date
        )
    else:
        data_feeds, successful_symbols = fetch_stock_data(
            index_name,
            start_date=start_date,
            end_date=end_date,
        )
    
    # Setup cerebro
    # Derive strategy name if not provided
    if strategy_name is None:
        strategy_name = strategy_class.__name__
    
    # Derive stock/index name if not provided
    if stock_name is None:
        stock_name = index_name if isinstance(index_name, str) else (symbols[0] if symbols else 'Unknown')
    
    cerebro = setup_cerebro(
        strategy_class=strategy_class,
        data_feeds=data_feeds,
        successful_symbols=successful_symbols,
        strategy_params=strategy_params,
        cash=cash,
        log_trades=log_trades,
        strategy_name=strategy_name,
        stock_name=stock_name
    )
    
    # Print initial status
    print(f"\nStarting Backtest with {len(cerebro.datas)} stocks")
    print(f'Initial Capital: ₹{cerebro.broker.getvalue():,.2f}')
    
    # Run backtest
    print("\n🔄 Running Backtest...")
    results = cerebro.run()
    strategy = results[0]
    final_value = cerebro.broker.getvalue()
    
    # Calculate returns
    starting_cash = cash if cash is not None else initial_cash
    total_return = ((final_value - starting_cash) / starting_cash) * 100
    
    print(f"\nInitial Capital: ₹{starting_cash:,.2f}")
    print(f"Final Portfolio: ₹{final_value:,.2f}")
    print(f"Total Return: {total_return:+.2f}%")
    
    # Display comprehensive results
    print("\n" + "="*80)
    print("📈 COMPREHENSIVE PERFORMANCE ANALYSIS")
    print("="*80)
    display_analyzer_results(strategy)
    
    # Plot if requested
    if plot:
        cerebro.plot()
    
    return {
        'strategy': strategy,
        'cerebro': cerebro,
        'symbols': successful_symbols,
        'starting_value': starting_cash,
        'final_value': final_value,
        'total_return': total_return
    }


def display_analyzer_results(strategy):
    """Display results from all added analyzers"""
    
    # Returns Analysis
    returns = strategy.analyzers.returns.get_analysis()
    total_return = returns.get('rtot', 0) * 100
    average_return = returns.get('ravg', 0) * 100
    cagr = returns.get('rnorm100', 0)
    print(f"\n💰 RETURNS ANALYSIS:")
    print(f"   Total Return: {total_return:.2f}%")
    print(f"   Average Return: {average_return:.2f}%")
    print(f"   CAGR: {cagr:.2f}%")
    
    # XIRR Analysis
    xirr = strategy.analyzers.xirr.get_analysis()
    xirr_value = xirr.get('xirr', None)
    if xirr_value is not None:
        print(f"   XIRR: {xirr_value:.2f}%")
    else:
        print(f"   XIRR: N/A (insufficient data)")

    # Annual Returns
    annual_returns = strategy.analyzers.annual_return.get_analysis()
    print(f"   Annual Returns:")
    for year, ret in annual_returns.items():
        print(f"     {year}: {ret*100:.2f}%")
    
    # Risk Analysis
    sharpe = strategy.analyzers.sharpe.get_analysis()
    print(f"\n🎯 RISK ANALYSIS:")
    if sharpe.get("sharperatio") is not None:
        print(f"   Sharpe Ratio: {sharpe.get('sharperatio', 0):.2f} (Higher is better, >1 is good)")
        print(f"   Sharpe Ratio indicates how my returns are with respect to volatility of returns. A higher Sharpe Ratio means better risk-adjusted returns.")
    sortino = strategy.analyzers.sortino.get_analysis()
    print(f"   Sortino Ratio: {sortino.get('sortinoratio', 0):.2f} (Higher is better, >1 is good)")
    print(f"   Sortino Ratio indicates how my returns are with respect to downside volatility. A higher Sortino Ratio means better risk-adjusted returns.")
    
    drawdown = strategy.analyzers.drawdown.get_analysis()
    max_drawdown = drawdown.get('max', {}).get('drawdown', 0)
    drawdown_period = drawdown.get('max', {}).get('len', 0)
    print(f"   Max Drawdown: {max_drawdown:.2f}% (Usually it should be 15-20% or lower)")
    print(f"   Drawdown Period: {drawdown_period} days (Lower is better)")

    # Trade Analysis
    trades = strategy.analyzers.trades.get_analysis()
    print(f"\n📊 TRADING STATISTICS:")
    print(f"   Total Trades: {trades.get('total', {}).get('total', 0)}")
    print(f"   Winning Trades: {trades.get('won', {}).get('total', 0)}")
    print(f"   Losing Trades: {trades.get('lost', {}).get('total', 0)}")
    win_rate = trades.get('won', {}).get('total', 0) / max(trades.get('total', {}).get('total', 1), 1)
    print(f"   Win Rate: {win_rate * 100:.1f}%")
    
    if 'pnl' in trades.get('won', {}):
        avg_profit = trades.get('won', {}).get('pnl', {}).get('average', 0)
        avg_loss = trades.get('lost', {}).get('pnl', {}).get('average', 0)
        print(f"   Average Win: ₹{avg_profit:.2f}")
        print(f"   Average Loss: ₹{avg_loss:.2f}")
        print(f"   Risk/Reward Ratio: {abs(avg_profit/avg_loss) if avg_loss != 0 else float('inf'):.2f}")
        expectancy = win_rate * avg_profit - (1 - win_rate) * abs(avg_loss)
        print(f"   Expectancy: {expectancy:.2f}")
        total_won = trades.get('won', {}).get('pnl', {}).get('total', 0)
        total_lost = trades.get('lost', {}).get('pnl', {}).get('total', 0)
        profit_factor = abs(total_won / total_lost) if total_lost != 0 else float('inf')
        print(f"   Profit Factor: {profit_factor:.2f}")


if __name__ == '__main__':
    from config import start_date, end_date, index_name
    
    # Run default backtest
    run_backtest(
        index_name=index_name,
        start_date=start_date,
        end_date=end_date
    )
