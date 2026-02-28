"""
Stock List for Indian Markets

Contains list of NSE stocks with metadata for search/autocomplete.
"""

# Popular NSE Stocks for search
NSE_STOCKS = [
    # Nifty 50 Stocks
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Oil & Gas"},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "sector": "IT"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking"},
    {"symbol": "INFY", "name": "Infosys Ltd", "sector": "IT"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Banking"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "sector": "FMCG"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecom"},
    {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd", "sector": "Banking"},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "sector": "Infrastructure"},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "sector": "Banking"},
    {"symbol": "ASIANPAINT", "name": "Asian Paints Ltd", "sector": "Paints"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "sector": "Automobile"},
    {"symbol": "TITAN", "name": "Titan Company Ltd", "sector": "Consumer Goods"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Ltd", "sector": "Pharma"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "sector": "Finance"},
    {"symbol": "WIPRO", "name": "Wipro Ltd", "sector": "IT"},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Ltd", "sector": "Cement"},
    {"symbol": "HCLTECH", "name": "HCL Technologies Ltd", "sector": "IT"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "sector": "Automobile"},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "sector": "Metals"},
    {"symbol": "NTPC", "name": "NTPC Ltd", "sector": "Power"},
    {"symbol": "POWERGRID", "name": "Power Grid Corporation of India Ltd", "sector": "Power"},
    {"symbol": "M&M", "name": "Mahindra & Mahindra Ltd", "sector": "Automobile"},
    {"symbol": "TECHM", "name": "Tech Mahindra Ltd", "sector": "IT"},
    {"symbol": "INDUSINDBK", "name": "IndusInd Bank Ltd", "sector": "Banking"},
    {"symbol": "DRREDDY", "name": "Dr Reddys Laboratories Ltd", "sector": "Pharma"},
    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Ltd", "sector": "Finance"},
    {"symbol": "NESTLEIND", "name": "Nestle India Ltd", "sector": "FMCG"},
    {"symbol": "ONGC", "name": "Oil and Natural Gas Corporation Ltd", "sector": "Oil & Gas"},
    {"symbol": "JSWSTEEL", "name": "JSW Steel Ltd", "sector": "Metals"},
    {"symbol": "GRASIM", "name": "Grasim Industries Ltd", "sector": "Cement"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd", "sector": "Diversified"},
    {"symbol": "ADANIPORTS", "name": "Adani Ports and SEZ Ltd", "sector": "Infrastructure"},
    {"symbol": "COALINDIA", "name": "Coal India Ltd", "sector": "Mining"},
    {"symbol": "BPCL", "name": "Bharat Petroleum Corporation Ltd", "sector": "Oil & Gas"},
    {"symbol": "CIPLA", "name": "Cipla Ltd", "sector": "Pharma"},
    {"symbol": "DIVISLAB", "name": "Divis Laboratories Ltd", "sector": "Pharma"},
    {"symbol": "EICHERMOT", "name": "Eicher Motors Ltd", "sector": "Automobile"},
    {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp Ltd", "sector": "Automobile"},
    {"symbol": "HINDALCO", "name": "Hindalco Industries Ltd", "sector": "Metals"},
    {"symbol": "TATACONSUM", "name": "Tata Consumer Products Ltd", "sector": "FMCG"},
    {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise Ltd", "sector": "Healthcare"},
    {"symbol": "SBILIFE", "name": "SBI Life Insurance Company Ltd", "sector": "Insurance"},
    {"symbol": "BRITANNIA", "name": "Britannia Industries Ltd", "sector": "FMCG"},
    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Ltd", "sector": "Automobile"},
    {"symbol": "UPL", "name": "UPL Ltd", "sector": "Chemicals"},
    {"symbol": "LTIM", "name": "LTIMindtree Ltd", "sector": "IT"},
    # Popular Mid-Caps
    {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance Co Ltd", "sector": "Insurance"},
    {"symbol": "VEDL", "name": "Vedanta Ltd", "sector": "Metals"},
    {"symbol": "BANKBARODA", "name": "Bank of Baroda", "sector": "Banking"},
    {"symbol": "PNB", "name": "Punjab National Bank", "sector": "Banking"},
    {"symbol": "ZOMATO", "name": "Zomato Ltd", "sector": "Internet"},
    {"symbol": "PAYTM", "name": "One 97 Communications Ltd", "sector": "Fintech"},
    {"symbol": "NYKAA", "name": "FSN E-Commerce Ventures Ltd", "sector": "E-Commerce"},
    {"symbol": "DMART", "name": "Avenue Supermarts Ltd", "sector": "Retail"},
    {"symbol": "TRENT", "name": "Trent Ltd", "sector": "Retail"},
    {"symbol": "PIDILITIND", "name": "Pidilite Industries Ltd", "sector": "Chemicals"},
    {"symbol": "HAVELLS", "name": "Havells India Ltd", "sector": "Electricals"},
    {"symbol": "GODREJCP", "name": "Godrej Consumer Products Ltd", "sector": "FMCG"},
    {"symbol": "DABUR", "name": "Dabur India Ltd", "sector": "FMCG"},
    {"symbol": "MARICO", "name": "Marico Ltd", "sector": "FMCG"},
    {"symbol": "COLPAL", "name": "Colgate-Palmolive India Ltd", "sector": "FMCG"},
    {"symbol": "TATAPOWER", "name": "Tata Power Company Ltd", "sector": "Power"},
    {"symbol": "ADANIGREEN", "name": "Adani Green Energy Ltd", "sector": "Power"},
    {"symbol": "JINDALSTEL", "name": "Jindal Steel & Power Ltd", "sector": "Metals"},
    {"symbol": "SAIL", "name": "Steel Authority of India Ltd", "sector": "Metals"},
    {"symbol": "NMDC", "name": "NMDC Ltd", "sector": "Mining"},
    {"symbol": "IOC", "name": "Indian Oil Corporation Ltd", "sector": "Oil & Gas"},
    {"symbol": "GAIL", "name": "GAIL India Ltd", "sector": "Oil & Gas"},
    {"symbol": "PETRONET", "name": "Petronet LNG Ltd", "sector": "Oil & Gas"},
    {"symbol": "INDIGO", "name": "InterGlobe Aviation Ltd", "sector": "Aviation"},
    {"symbol": "IRCTC", "name": "Indian Railway Catering and Tourism Corporation Ltd", "sector": "Travel"},
    {"symbol": "HDFCAMC", "name": "HDFC Asset Management Company Ltd", "sector": "Finance"},
    {"symbol": "MUTHOOTFIN", "name": "Muthoot Finance Ltd", "sector": "Finance"},
    {"symbol": "CHOLAFIN", "name": "Cholamandalam Investment and Finance Company Ltd", "sector": "Finance"},
    {"symbol": "SBICARD", "name": "SBI Cards and Payment Services Ltd", "sector": "Finance"},
    {"symbol": "ICICIPRULI", "name": "ICICI Prudential Life Insurance Company Ltd", "sector": "Insurance"},
    {"symbol": "ICICIGI", "name": "ICICI Lombard General Insurance Company Ltd", "sector": "Insurance"},
    {"symbol": "PAGEIND", "name": "Page Industries Ltd", "sector": "Textiles"},
    {"symbol": "VOLTAS", "name": "Voltas Ltd", "sector": "Consumer Durables"},
    {"symbol": "WHIRLPOOL", "name": "Whirlpool of India Ltd", "sector": "Consumer Durables"},
    {"symbol": "BLUEDART", "name": "Blue Dart Express Ltd", "sector": "Logistics"},
    {"symbol": "DLF", "name": "DLF Ltd", "sector": "Real Estate"},
    {"symbol": "GODREJPROP", "name": "Godrej Properties Ltd", "sector": "Real Estate"},
    {"symbol": "OBEROIRLTY", "name": "Oberoi Realty Ltd", "sector": "Real Estate"},
    {"symbol": "PRESTIGE", "name": "Prestige Estates Projects Ltd", "sector": "Real Estate"},
    # Indices (for reference)
    {"symbol": "NIFTY", "name": "Nifty 50 Index", "sector": "Index"},
    {"symbol": "BANKNIFTY", "name": "Nifty Bank Index", "sector": "Index"},
]


def search_stocks(query: str, limit: int = 10) -> list[dict]:
    """
    Search stocks by symbol or name.

    Args:
        query: Search query (partial match)
        limit: Maximum results to return

    Returns:
        List of matching stocks
    """
    query = query.upper().strip()

    if not query:
        return []

    results = []

    # Exact symbol match first
    for stock in NSE_STOCKS:
        if stock["symbol"] == query:
            results.append(stock)
            break

    # Partial symbol match
    for stock in NSE_STOCKS:
        if stock["symbol"].startswith(query) and stock not in results:
            results.append(stock)

    # Name contains query
    for stock in NSE_STOCKS:
        if query.lower() in stock["name"].lower() and stock not in results:
            results.append(stock)

    return results[:limit]


def get_popular_stocks(count: int = 10) -> list[dict]:
    """Get most popular stocks for default display."""
    # Return top Nifty 50 stocks
    popular = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "SBIN", "BHARTIARTL", "TATASTEEL", "TATAMOTORS", "ITC"
    ]
    return [s for s in NSE_STOCKS if s["symbol"] in popular][:count]


def get_stocks_by_sector(sector: str) -> list[dict]:
    """Get stocks by sector."""
    return [s for s in NSE_STOCKS if s["sector"].lower() == sector.lower()]


def get_nifty50_stocks() -> list[str]:
    """Get list of Nifty 50 stock symbols."""
    nifty50 = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
        "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
        "SUNPHARMA", "BAJFINANCE", "WIPRO", "ULTRACEMCO", "HCLTECH",
        "TATAMOTORS", "TATASTEEL", "NTPC", "POWERGRID", "M&M",
        "TECHM", "INDUSINDBK", "DRREDDY", "BAJAJFINSV", "NESTLEIND",
        "ONGC", "JSWSTEEL", "GRASIM", "ADANIENT", "ADANIPORTS",
        "COALINDIA", "BPCL", "CIPLA", "DIVISLAB", "EICHERMOT",
        "HEROMOTOCO", "HINDALCO", "TATACONSUM", "APOLLOHOSP", "SBILIFE",
        "BRITANNIA", "BAJAJ-AUTO", "UPL", "LTIM", "HDFCLIFE"
    ]
    return nifty50


def get_all_stocks() -> list[str]:
    """Get list of all available stock symbols."""
    return [s["symbol"] for s in NSE_STOCKS if s["sector"] != "Index"]
