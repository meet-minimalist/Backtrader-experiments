import pickle
import logging
import backtrader as bt
from pathlib import Path
from thematicnifty import tn
from yf_cache import YFinanceDataDownloader
from config import interval, reuse_data


logger = logging.getLogger(__name__)

CACHE_DIR = Path("data_cache")
CACHE_DIR.mkdir(exist_ok=True)


def _get_cache_path(index_name, start_date, end_date):
    """Generate cache file path based on index and date range."""
    safe_index = index_name.replace(" ", "_").replace("/", "_")
    filename = f"{safe_index}_{start_date}_{end_date}.pkl"
    return CACHE_DIR / filename


def _save_to_cache(cache_path, data_feeds, successful_symbols):
    """Save data feeds and symbols to cache file."""
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump({
                'data_feeds': data_feeds,
                'successful_symbols': successful_symbols
            }, f)
        logger.info("Cached data for %s (%d symbols)", cache_path.name, len(successful_symbols))
    except Exception as e:
        logger.warning("Failed to cache data: %s", e)


def _load_from_cache(cache_path):
    """Load data feeds from cache file. Returns None if cache miss."""
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'rb') as f:
            cached = pickle.load(f)
        logger.info("Loaded cached data for %s (%d symbols)", cache_path.name, len(cached['successful_symbols']))
        return cached['data_feeds'], cached['successful_symbols']
    except Exception as e:
        logger.warning("Failed to load cache, will download fresh: %s", e)
        return None


def fetch_stock_data(symbols, start_date, end_date):
    """Fetch data for multiple stocks"""
    data_feeds = []
    successful_symbols = []

    downloader = YFinanceDataDownloader(log_level='WARNING')

    for symbol in symbols:
        try:
            logger.debug("Downloading data for %s...", symbol)
            data_df = downloader.get_data(symbol, start_date=start_date, end_date=end_date, interval=interval, validate_date_range=True)

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
    Load stock data for an index with optional caching.

    Args:
        index_name: Index name (e.g., 'NIFTY_MIDCAP_50')
        start_date: Start date string
        end_date: End date string

    Returns:
        Tuple of (data_feeds, successful_symbols)
    """
    cache_path = _get_cache_path(index_name, start_date, end_date)
    
    # Try to load from cache if enabled
    if reuse_data:
        cached = _load_from_cache(cache_path)
        if cached is not None:
            return cached
    
    # Download fresh data
    symbols = get_index_symbols(index_name=index_name)
    logger.info("Found %d symbols in %s", len(symbols), index_name)

    data_feeds, successful_symbols = fetch_stock_data(
        symbols,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Save to cache if we got data
    if reuse_data and data_feeds:
        _save_to_cache(cache_path, data_feeds, successful_symbols)
    
    return data_feeds, successful_symbols


def get_index_symbols(index_name: str):
    """Return list of stocks based on given stock index"""
    return tn.getThematicNiftyStocks(group_name='bmi_group', group_item=index_name, return_type='as_list_with_NS')
