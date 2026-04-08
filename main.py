from thematicnifty import tn
import yfinance as yf
import backtrader as bt
from strategy.midcap_shop_strategy import MidcapMeanReversionWithAnalyzers
from analyzers.sortino_analyzer import SortinoRatio as Sortino
from config import start_date, end_date, commission, initial_cash, index_name, riskfreerate
from utils.stock_helper import get_index_symbols, fetch_stock_data


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
    
    # System Quality
    # sqn = strategy.analyzers.sqn.get_analysis()
    # print(f"   System Quality Number (SQN): {sqn.get('sqn', 0):.2f}")
    
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
    
def run_backtest():
    """Run the complete backtest"""
    # Initialize Cerebro engine
    cerebro = bt.Cerebro()
    
    # Get symbols for the specified index
    symbols = get_index_symbols(index_name=index_name)
    
    # Fetch data
    print("Fetching stock data...")
    data_feeds, successful_symbols = fetch_stock_data(
        symbols, 
        start_date=start_date, 
        end_date=end_date,
    )
    
    # Add data to cerebro
    for data_feed, symbol in zip(data_feeds, successful_symbols):
        cerebro.adddata(data_feed, name=symbol)
        print(f"📊 Added: {symbol}")
    
    # Add strategy
    cerebro.addstrategy(MidcapMeanReversionWithAnalyzers, symbol_names=successful_symbols)
    
    # Set up broker
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=commission)
    
    # 🔥 ADD ALL BUILT-IN ANALYZERS HERE 🔥
    
    # Returns Analysis
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
    
    # Risk Analysis
    cerebro.addanalyzer(bt.analyzers.Calmar, _name='calmar')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=riskfreerate, timeframe=bt.TimeFrame.Days, annualize=True)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(Sortino, _name='sortino', riskfreerate=riskfreerate, timeframe=bt.TimeFrame.Days)
    
    # Trade Analysis
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    # cerebro.addanalyzer(bt.analyzers.Transactions, _name='transactions')
    # cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='time_return')
    
    print(f"\nStarting Backtest with {len(cerebro.datas)} stocks")
    
    # Run backtest
    print("\n🔄 Running Backtest...")
    results = cerebro.run()
    strategy = results[0]
    
    # Print results
    end_value = cerebro.broker.getvalue()
    total_return = (end_value - initial_cash) / initial_cash * 100
    print(f"Initial Capital: ₹{initial_cash:,.2f}")
    print(f"Final Portfolio: ₹{end_value:,.2f}")
    print(f"Total Return: {total_return:+.2f}%")
    
    # 📊 DISPLAY ALL ANALYZER RESULTS
    print("\n" + "="*80)
    print("📈 COMPREHENSIVE PERFORMANCE ANALYSIS")
    print("="*80)
    
    display_analyzer_results(strategy)
    
    # Plot results
    # cerebro.plot()
    
    
if __name__ == '__main__':
    run_backtest()