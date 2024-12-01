import finnhub
import helpercode

#TODO: Create your own API key by going to https://finnhub.io/
finnhub_client = finnhub.Client(api_key="cstluhpr01qj0ou20db0cstluhpr01qj0ou20dbg")

def symbol_lookup(params):
    return finnhub_client.symbol_lookup(params['company_name'])

def get_quote(params):
    return finnhub_client.quote(params['symbol'])

def company_news(params):
    return finnhub_client.company_news(params['symbol'], _from=params['from_date'], to=params['to_date'])

def news_sentiment(params):
    return finnhub_client.news_sentiment(params['symbol'])

def company_peers(params):
    return finnhub_client.company_peers(params['symbol'])

def insider_sentiment(params):
    return finnhub_client.stock_insider_sentiment(params['symbol'], params['from_date'], params['to_date'])

def company_basic_financials(params):
    return finnhub_client.company_basic_financials(params['symbol'],'all')

def financials_reported(params):
    return finnhub_client.financials_reported(symbol=params['symbol'], _from=params['from_date'], to=params['to_date'] )

def sec_filings(params):
    #Since this function has links to the actual file we are downloading the file from the link and processing it
    
    secfilings = finnhub_client.filings(symbol=params['symbol'], _from=params['from_date'], to=params['to_date'])
    parsed_filings = []
    for filing in secfilings:
        if filing['form'] in ['10-Q', '8-K']:
            parsed_filings.append({"accessNumber":filing['accessNumber'], 
                                   "symbol": params['symbol'], 
                                   "filedDate": filing['filedDate'],
                                   "report": helpercode.get_text_from_url(filing['reportUrl'])})
    
    return parsed_filings

def company_profile(params):
    return finnhub_client.company_profile2(symbol=params['symbol'])




#######################################################





function_handler = {
    "symbol_lookup": symbol_lookup,
    "get_quote": get_quote,
    "company_news": company_news,
    "company_profile": company_profile,
    "company_basic_financials": company_basic_financials,
    "company_peers": company_peers,
    "insider_sentiment": insider_sentiment,
    "financials_reported": financials_reported,
    "sec_filings": sec_filings,
}