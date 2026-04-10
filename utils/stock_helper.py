import logging
import backtrader as bt
from thematicnifty import tn
from yf_cache import YFinanceDataDownloader
from config import interval


logger = logging.getLogger(__name__)


def get_index_symbols(index_name: str):
    """Return list of stocks based on given stock index"""
    return tn.getThematicNiftyStocks(group_name='bmi_group', group_item=index_name, return_type='as_list_with_NS')


def fetch_stock_data(symbols, start_date, end_date):
    """Fetch data for multiple stocks"""
    data_feeds = []
    successful_symbols = []

    downloader = YFinanceDataDownloader(log_level='WARNING')

    for symbol in symbols:
        try:
            logger.debug("Downloading data for %s...", symbol)
            data_df = downloader.get_data(symbol, start_date=start_date, end_date=end_date, interval=interval)

            if len(data_df) > 0:
                data_feed = bt.feeds.PandasData(
                    dataname=data_df,
                    open='Open',
                    high='High',
                    low='Low',
                    close='Close',
                    volume='Volume',
                    openinterest=None,
                    name=symbol
                )
                data_feeds.append(data_feed)
                successful_symbols.append(symbol)
                logger.debug("Success: %s - %d bars", symbol, len(data_df))
            else:
                logger.warning("No data: %s", symbol)

        except Exception as e:
            logger.error("Error downloading %s: %s", symbol, e)

    return data_feeds, successful_symbols


def load_index_data(index_name, start_date, end_date):
    """
    Load stock data for an index.

    Args:
        index_name: Index name (e.g., 'NIFTY_MIDCAP_50')
        start_date: Start date string
        end_date: End date string

    Returns:
        Tuple of (data_feeds, successful_symbols)
    """
    symbols = get_index_symbols(index_name=index_name)
    logger.info("Found %d symbols in %s", len(symbols), index_name)

    data_feeds, successful_symbols = fetch_stock_data(
        symbols,
        start_date=start_date,
        end_date=end_date,
    )
    return data_feeds, successful_symbols
