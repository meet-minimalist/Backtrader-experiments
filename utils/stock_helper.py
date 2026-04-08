from thematicnifty import tn
import backtrader as bt
from yf_cache import YFinanceDataDownloader
from config import interval


def get_index_symbols(index_name: str):
    """Return list of 50 stocks based on given stock index"""
    # You need to replace these with actual Midcap 50 symbols
    stocks = tn.getThematicNiftyStocks(group_name='bmi_group', group_item=index_name, return_type='as_list_with_NS')
    return stocks

def fetch_stock_data(symbols, start_date, end_date):
    """Fetch data for multiple stocks"""
    data_feeds = []
    successful_symbols = []    

    downloader = YFinanceDataDownloader(log_level='WARNING')

    for symbol in symbols:
        try:
            print(f"Downloading data for {symbol}...")
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
                print(f"✅ Success: {symbol} - {len(data_df)} bars")
            else:
                print(f"❌ No data: {symbol}")
                
        except Exception as e:
            print(f"❌ Error downloading {symbol}: {e}")
    
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
    print(f"📊 Found {len(symbols)} symbols in {index_name}")
    
    data_feeds, successful_symbols = fetch_stock_data(
        symbols,
        start_date=start_date,
        end_date=end_date,
    )
    return data_feeds, successful_symbols
