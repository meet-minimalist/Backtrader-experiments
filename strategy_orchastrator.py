import pandas as pd
from main import (
    setup_cerebro,
    load_index_data,
    run_backtest,
    display_analyzer_results
)
import numpy as np

from utils.formatter import indian_rupee
from strategy import wrap_strategy_with_atr_stop

class StrategyTester:
    """
    A lightweight orchestrator for testing strategies using main_v2 components.
    """

    def __init__(self, cash=None):
        """
        Initialize the strategy tester.

        Args:
            cash: Starting cash amount (defaults to config value)
        """
        from config import initial_cash
        self.cash = cash if cash is not None else initial_cash


    def test_multiple_stocks(self, strategy_class, symbols, strategy_params=None,
                             start_date=None, end_date=None, log_trades=True):
        """Test a strategy on custom list of stocks."""
        from utils.stock_helper import fetch_stock_data

        # Load data
        data_feeds, successful_symbols = fetch_stock_data(
            symbols,
            start_date=start_date,
            end_date=end_date,
        )

        # Use main's setup_cerebro
        cerebro = setup_cerebro(
            strategy_class=strategy_class,
            data_feeds=data_feeds,
            successful_symbols=successful_symbols,
            strategy_params=strategy_params,
            cash=self.cash,
            log_trades=log_trades,
            strategy_name=strategy_class.__name__,
            stock_name='_'.join(symbols) if len(symbols) <= 3 else f'{len(symbols)}_stocks'
        )

        print(f"\nStarting Backtest with {len(cerebro.datas)} stocks")
        results = cerebro.run()
        strategy = results[0]
        final_value = cerebro.broker.getvalue()

        print(f"\nInitial Capital: ₹{self.cash:,.2f}")
        print(f"\nFinal Portfolio: ₹{final_value:,.2f}")
        display_analyzer_results(strategy)

        return {
            'strategy': strategy,
            'cerebro': cerebro,
            'symbols': successful_symbols,
            'final_value': final_value
        }

    def test_index(self, strategy_class, index_name, strategy_params=None,
                   start_date=None, end_date=None, log_trades=True):
        """Test a strategy on an entire index."""
        # Load index data using main
        data_feeds, successful_symbols = load_index_data(
            index_name=index_name,
            start_date=start_date,
            end_date=end_date
        )

        cerebro = setup_cerebro(
            strategy_class=strategy_class,
            data_feeds=data_feeds,
            successful_symbols=successful_symbols,
            strategy_params=strategy_params,
            cash=self.cash,
            log_trades=log_trades,
            strategy_name=strategy_class.__name__,
            stock_name=index_name
        )

        print(f"\nStarting Backtest with {len(cerebro.datas)} stocks")
        results = cerebro.run()
        strategy = results[0]
        final_value = cerebro.broker.getvalue()

        print(f"\nFinal Portfolio: ₹{final_value:,.2f}")
        display_analyzer_results(strategy)

        return {
            'strategy': strategy,
            'cerebro': cerebro,
            'symbols': successful_symbols,
            'final_value': final_value
        }

    def compare_strategies(self, strategies_config, use_index=None, symbols=None,
                           start_date=None, end_date=None):
        """
        Compare multiple strategies.

        Args:
            strategies_config: List of dicts with 'name', 'class', and 'params'
            use_index: Index name to test on
            symbols: List of symbols (alternative to use_index)
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with comparison results
        """
        results = []

        for config in strategies_config:
            print(f"\n{'='*80}")
            print(f"Testing: {config['name']}")
            print('='*80)

            # Use full backtest from main (DISABLE trade logging for comparison)
            result = run_backtest(
                strategy_class=config['class'],
                index_name=use_index,
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                strategy_params=config.get('params'),
                cash=self.cash,
                log_trades=False,  # Disable for comparison
                strategy_name=config['name'],
                plot=False
            )

            analytics = result.copy()
            analytics['strategy_name'] = config['name']
            results.append(analytics)

        # Create comparison DataFrame
        df = pd.DataFrame(results)
        cols = ['strategy_name', 'starting_value', 'final_value', 'total_return']
        available_cols = [col for col in cols if col in df.columns]
        df = df[available_cols]

        print("\n" + "="*80)
        print("STRATEGY COMPARISON")
        print("="*80)

        # Build formatters dict: rupee for cols 1 & 2, plain float for rest
        formatters = {}
        for i, col in enumerate(df.columns):
            if i in (1, 2):
                formatters[col] = indian_rupee
            elif df[col].dtype in [np.float32, np.float64]:
                formatters[col] = lambda x: f"{x:.2f}"

        # TODO: Also, add logging of sharpe, sortino, drawdown etc for each strategy in the comparison table
        print(df.to_string(index=False, formatters=formatters))
        return df


# Example usage
if __name__ == "__main__":
    from strategy import ShopStrategy, SimpleSMAStrategy, RSIStrategy, MACDStrategy, GoldenCrossoverStrategy, EmaVolatilityStrategy, NiftyShopStrategy

    print("="*80)
    print("Strategy Tester - Lightweight Orchestrator")
    print("="*80)

    # Initialize tester
    tester = StrategyTester()

    # Example 1: Quick single stock test
    # result = tester.test_multiple_stocks(
    #     strategy_class=SimpleSMAStrategy,
    #     symbols=['RELIANCE.NS'],
    #     strategy_params={'fast_period': 10, 'slow_period': 30},
    #     start_date='2020-01-01',
    #     end_date='2025-01-01'
    # )

    # Example 2: Test on index
    # result = tester.test_index(
    #     strategy_class=NiftyShopStrategy,
    #     index_name='NIFTY_MIDCAP_50',
    #     start_date='2020-01-01',
    #     end_date='2025-12-31'
    # )

    # Example 3: Compare strategies
    strategies = [
        {
            'name': 'ShopStrategy',
            'class': ShopStrategy,
            'params': {}
        },
        {
            'name': 'NiftyShopStrategy',
            'class': NiftyShopStrategy,
            'params': {'printlog': False}
        },
        # {
        #     'name': 'SimpleSMAStrategy',
        #     'class': SimpleSMAStrategy,
        #     'params': {'fast_period': 10, 'slow_period': 30}
        # },
        # {
        #     'name': 'RSIStrategy',
        #     'class': RSIStrategy,
        #     'params': {'rsi_period': 14, 'rsi_lower': 30, 'rsi_upper': 70}
        # },
        # {
        #     'name': 'MACDStrategy',
        #     'class': MACDStrategy,
        #     'params': {'fast_ema': 12, 'slow_ema': 26, 'signal': 9}
        # }
    ]

    comparison = tester.compare_strategies(
        strategies_config=strategies,
        # use_index='NIFTY_MIDCAP_50',
        use_index='^RUT',
        start_date='2020-01-01',
        end_date='2025-12-31'
    )
