import backtrader as bt
from strategy import MidcapMeanReversion
from analyzers.sortino_analyzer import SortinoRatio as Sortino
from config import commission, initial_cash, riskfreerate
from utils.stock_helper import load_index_data, fetch_stock_data


def setup_cerebro(strategy_class, data_feeds, successful_symbols, 
                  strategy_params=None, cash=None, commission_rate=None):
    """
    Create and configure Cerebro engine with data, strategy, and analyzers.
    
    Args:
        strategy_class: Backtrader strategy class
        data_feeds: List of backtrader data feeds
        successful_symbols: List of symbol names corresponding to data_feeds
        strategy_params: Dict of parameters to pass to strategy
        cash: Starting cash (defaults to config)
        commission_rate: Commission rate (defaults to config)
    
    Returns:
        Configured Cerebro instance
    """
    cerebro = bt.Cerebro()
    
    # Add data feeds
    for data_feed, symbol in zip(data_feeds, successful_symbols):
        cerebro.adddata(data_feed, name=symbol)
    
    # Add strategy
    if strategy_params:
        cerebro.addstrategy(strategy_class, symbol_names=successful_symbols, **strategy_params)
    else:
        cerebro.addstrategy(strategy_class, symbol_names=successful_symbols)
    
    # Set up broker
    cerebro.broker.setcash(cash if cash is not None else initial_cash)
    cerebro.broker.setcommission(commission=commission_rate if commission_rate is not None else commission)
    
    # Add comprehensive analyzers
    add_comprehensive_analyzers(cerebro)
    
    return cerebro


def add_comprehensive_analyzers(cerebro):
    """
    Add all comprehensive analyzers to cerebro.
    
    Args:
        cerebro: Backtrader Cerebro instance
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
    cerebro.addanalyzer(Sortino, _name='sortino', riskfreerate=riskfreerate, timeframe=bt.TimeFrame.Days)
    
    # Trade Analysis
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    

def run_backtest(strategy_class=None, index_name=None, 
                 start_date=None, end_date=None,
                 symbols=None, strategy_params=None,
                 cash=None, commission_rate=None,
                 plot=False):
    """
    Run a complete backtest with comprehensive analytics.
    
    Args:
        strategy_class: Backtrader strategy class (default: MidcapMeanReversion)
        index_name: Index name to load data from
        start_date: Start date string
        end_date: End date string
        symbols: List of symbols (alternative to index_name)
        strategy_params: Dict of strategy parameters
        cash: Starting cash
        commission_rate: Commission rate
        plot: Whether to plot results
    
    Returns:
        Dict with strategy, cerebro, and results
    """
    from config import start_date as config_start, end_date as config_end, index_name as config_index
    
    # Use config defaults if not provided
    strategy_class = strategy_class or MidcapMeanReversion
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
    cerebro = setup_cerebro(
        strategy_class=strategy_class,
        data_feeds=data_feeds,
        successful_symbols=successful_symbols,
        strategy_params=strategy_params,
        cash=cash,
        commission_rate=commission_rate
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
