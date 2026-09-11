from __future__ import annotations
import os
import io
import copy
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timedelta
import math
import requests
import pandas as pd
import numpy as np
import re
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / 'config' / 'config.env')
TIINGO_API_KEY = os.getenv('TIINGO_API_KEY', '').strip()
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '').strip()
_TTL_CACHE = {}

def _clone_cached(value):
    if isinstance(value, pd.DataFrame):
        return value.copy()
    return copy.deepcopy(value)

def _cache_get(key, ttl):
    item = _TTL_CACHE.get(key)
    if not item:
        return None
    ts, value = item
    if time.time() - ts > ttl:
        _TTL_CACHE.pop(key, None)
        return None
    return _clone_cached(value)

def _cache_set(key, value):
    _TTL_CACHE[key] = (time.time(), _clone_cached(value))
    return value

def round2(x):
    try:
        if x is None or pd.isna(x): return None
        return round(float(x), 2)
    except Exception: return None
def pct(a,b):
    try:
        if b in (0,None) or pd.isna(b): return None
        return round2((float(a)/float(b)-1)*100)
    except Exception: return None
def fmt_big(n):
    try:
        n=float(n)
        if abs(n)>=1e9: return f'{n/1e9:.2f}B'
        if abs(n)>=1e6: return f'{n/1e6:.2f}M'
        if abs(n)>=1e3: return f'{n/1e3:.2f}K'
        return str(round2(n))
    except Exception: return '--'

def _naive_ts(value):
    ts=pd.to_datetime(value)
    try:
        if getattr(ts, 'tzinfo', None) is not None:
            ts=ts.tz_convert(None)
    except Exception:
        try:
            ts=ts.tz_localize(None)
        except Exception:
            pass
    return ts

def fetch_daily(ticker: str, years: int=3) -> pd.DataFrame:
    key=('fetch_daily', ticker.upper(), years, datetime.utcnow().date().isoformat())
    cached=_cache_get(key, ttl=600)
    if cached is not None:
        return cached
    if not TIINGO_API_KEY: raise RuntimeError('Missing TIINGO_API_KEY in config/config.env')
    end=datetime.utcnow().date(); start=end-timedelta(days=365*years+60)
    url=f'https://api.tiingo.com/tiingo/daily/{ticker.upper()}/prices'
    r=requests.get(url, params={'token':TIINGO_API_KEY,'startDate':start.isoformat(),'endDate':end.isoformat(),'format':'json','resampleFreq':'daily'}, timeout=25, headers={'User-Agent':'MMF-v3'})
    r.raise_for_status(); data=r.json()
    if not isinstance(data,list) or not data: raise RuntimeError(f'No daily data returned for {ticker}')
    rows=[]
    for x in data:
        rows.append({'Date':_naive_ts(x['date']),'Open':x.get('adjOpen',x.get('open')),'High':x.get('adjHigh',x.get('high')),'Low':x.get('adjLow',x.get('low')),'Close':x.get('adjClose',x.get('close')),'Volume':x.get('volume',x.get('adjVolume',0))})
    return _cache_set(key, add_indicators(pd.DataFrame(rows).dropna(subset=['Open','High','Low','Close']).sort_values('Date').reset_index(drop=True)))

def fetch_live_quote(ticker: str):
    key=('fetch_live_quote', ticker.upper())
    cached=_cache_get(key, ttl=45)
    if cached is not None:
        return cached
    candidates=[]
    loaders=(fetch_tiingo_iex_quote, fetch_yahoo_extended_quote, fetch_alpha_vantage_quote)
    with ThreadPoolExecutor(max_workers=len(loaders)) as pool:
        futures=[pool.submit(loader, ticker) for loader in loaders]
        for future in as_completed(futures):
            try:
                value=future.result()
                if value and value.get('last') is not None:
                    candidates.append(value)
            except Exception:
                continue
    if not candidates:
        return _cache_set(key, None)
    def freshness(value):
        raw=value.get('latestTime') or value.get('latestTradingDay')
        try:
            return pd.to_datetime(raw, utc=True).timestamp()
        except Exception:
            return 0
    freshest=max(candidates, key=freshness)
    freshest['candidateSources']=[x.get('source') for x in candidates]
    return _cache_set(key, freshest)

def fetch_tiingo_iex_quote(ticker: str):
    key=('fetch_tiingo_iex_quote', ticker.upper())
    cached=_cache_get(key, ttl=45)
    if cached is not None:
        return cached
    if not TIINGO_API_KEY:
        return None
    end=datetime.utcnow().date()
    start=end-timedelta(days=7)
    url=f'https://api.tiingo.com/iex/{ticker.upper()}/prices'
    r=requests.get(url, params={'token':TIINGO_API_KEY,'startDate':start.isoformat(),'resampleFreq':'5min','columns':'open,high,low,close,volume'}, timeout=20, headers={'User-Agent':'MMF-v3'})
    r.raise_for_status(); data=r.json()
    if not isinstance(data,list) or not data:
        return None
    latest=data[-1]
    price=latest.get('close')
    if price is None:
        return None
    rows=[]
    for x in data:
        rows.append({'Date':_naive_ts(x.get('date')),'Open':x.get('open'),'High':x.get('high'),'Low':x.get('low'),'Close':x.get('close'),'Volume':x.get('volume',0)})
    idf=pd.DataFrame(rows).dropna(subset=['Date','Open','High','Low','Close']).sort_values('Date').reset_index(drop=True)
    for col in ['Open','High','Low','Close','Volume']:
        idf[col]=pd.to_numeric(idf[col], errors='coerce')
    idf=idf.dropna(subset=['Open','High','Low','Close']).reset_index(drop=True)
    day=None
    if not idf.empty:
        latest_day=pd.to_datetime(idf.iloc[-1].Date).date()
        day=idf[pd.to_datetime(idf.Date).dt.date == latest_day].copy().reset_index(drop=True)
    q_daily=None
    try:
        d=fetch_daily(ticker, years=1)
        q_daily=quote(d)
    except Exception:
        q_daily=None
    alpha_daily=None
    try:
        alpha_daily=fetch_alpha_vantage_quote(ticker)
    except Exception:
        alpha_daily=None
    yahoo_daily=None
    try:
        yahoo_daily=fetch_yahoo_chart_quote(ticker)
    except Exception:
        yahoo_daily=None
    day_open=day.iloc[0].Open if day is not None and not day.empty else latest.get('open')
    day_high=day.High.max() if day is not None and not day.empty else latest.get('high')
    day_low=day.Low.min() if day is not None and not day.empty else latest.get('low')
    day_volume=day.Volume.fillna(0).sum() if day is not None and not day.empty else latest.get('volume')
    latest_day=_naive_ts(latest.get('date')).date() if latest.get('date') else None
    alpha_date=None
    try:
        alpha_date=_naive_ts(alpha_daily.get('latestTradingDay')).date() if alpha_daily and alpha_daily.get('latestTradingDay') else None
    except Exception:
        alpha_date=None
    best_daily=None
    for candidate in [alpha_daily, yahoo_daily]:
        try:
            c_date=_naive_ts(candidate.get('latestTradingDay')).date() if candidate and candidate.get('latestTradingDay') else None
        except Exception:
            c_date=None
        c_vol=candidate.get('volumeRaw') if candidate else None
        if c_date == latest_day and isinstance(c_vol, (int, float, np.integer, np.floating)) and c_vol > float(day_volume or 0):
            if best_daily is None or c_vol > best_daily.get('volumeRaw', 0):
                best_daily=candidate
    if best_daily:
        day_open=best_daily.get('open') or day_open
        day_high=max([x for x in [day_high, best_daily.get('high')] if x is not None])
        day_low=min([x for x in [day_low, best_daily.get('low')] if x is not None])
        day_volume=best_daily.get('volumeRaw') or day_volume
        price=best_daily.get('last') or price
    prev=None
    try:
        if q_daily and not d.empty and latest.get('date'):
            latest_day=_naive_ts(latest.get('date')).date()
            prior=d[pd.to_datetime(d.Date).dt.date < latest_day]
            if not prior.empty:
                prev=prior.iloc[-1].Close
    except Exception:
        prev=None
    if prev is None:
        prev=(q_daily or {}).get('prevClose') or (q_daily or {}).get('close')
    return _cache_set(key, {
        'source':'Tiingo IEX 5min intraday',
        'open':round2(day_open),
        'high':round2(day_high),
        'low':round2(day_low),
        'close':round2(price),
        'last':round2(price),
        'prevClose':round2(prev),
        'changePct':pct(price,day_open),
        'openCloseChangePct':pct(price,day_open),
        'highLowChangePct':pct(day_low,day_high),
        'prevCloseChangePct':pct(price,prev),
        'volume':fmt_big(day_volume),
        'volumeRaw':day_volume or 0,
        'volumeSource':f"{best_daily.get('source')} daily volume preferred over partial Tiingo IEX volume" if best_daily else 'Tiingo IEX 5min cumulative volume',
        'latestTradingDay':str(_naive_ts(latest.get('date')).date()) if latest.get('date') else None,
        'latestTime':latest.get('date'),
    })

def fetch_intraday_5m(ticker: str, days: int=7) -> pd.DataFrame:
    key=('fetch_intraday_5m', ticker.upper(), days)
    cached=_cache_get(key, ttl=45)
    if cached is not None:
        return cached
    if not TIINGO_API_KEY:
        raise RuntimeError('Missing TIINGO_API_KEY in config/config.env')
    end=datetime.utcnow().date()
    start=end-timedelta(days=days)
    url=f'https://api.tiingo.com/iex/{ticker.upper()}/prices'
    r=requests.get(url, params={'token':TIINGO_API_KEY,'startDate':start.isoformat(),'resampleFreq':'5min','columns':'open,high,low,close,volume'}, timeout=20, headers={'User-Agent':'MMF-v3'})
    r.raise_for_status(); data=r.json()
    if not isinstance(data,list) or not data:
        raise RuntimeError(f'No intraday 5m data returned for {ticker}')
    rows=[]
    for x in data:
        rows.append({'Date':_naive_ts(x.get('date')),'Open':x.get('open'),'High':x.get('high'),'Low':x.get('low'),'Close':x.get('close'),'Volume':x.get('volume',0)})
    df=pd.DataFrame(rows).dropna(subset=['Date','Open','High','Low','Close']).sort_values('Date').reset_index(drop=True)
    for col in ['Open','High','Low','Close','Volume']:
        df[col]=pd.to_numeric(df[col], errors='coerce')
    df=df.dropna(subset=['Open','High','Low','Close']).reset_index(drop=True)
    if df.empty:
        raise RuntimeError(f'No usable intraday 5m data returned for {ticker}')
    latest_day=pd.to_datetime(df.iloc[-1].Date).date()
    df=df[pd.to_datetime(df.Date).dt.date == latest_day].copy().reset_index(drop=True)
    typical=(df['High']+df['Low']+df['Close'])/3
    volume=df['Volume'].fillna(0).clip(lower=0)
    cumulative_volume=volume.cumsum()
    df['VWAP']=np.where(cumulative_volume>0, (typical*volume).cumsum()/cumulative_volume, df['Close'].expanding().mean())
    df['EMA20']=df['Close'].ewm(span=20,adjust=False).mean()
    return _cache_set(key, df)

def fetch_alpha_vantage_quote(ticker: str):
    key=('fetch_alpha_vantage_quote', ticker.upper())
    cached=_cache_get(key, ttl=60)
    if cached is not None:
        return cached
    if not ALPHA_VANTAGE_API_KEY:
        return None
    url='https://www.alphavantage.co/query'
    r=requests.get(url, params={'function':'GLOBAL_QUOTE','symbol':ticker.upper(),'apikey':ALPHA_VANTAGE_API_KEY}, timeout=20, headers={'User-Agent':'MMF-v3'})
    r.raise_for_status(); data=r.json()
    g=data.get('Global Quote') or {}
    if not g or not g.get('05. price'):
        return None
    def f(key):
        try: return float(str(g.get(key,'')).replace('%',''))
        except Exception: return None
    price=f('05. price'); prev=f('08. previous close')
    volume_raw=f('06. volume')
    return _cache_set(key, {
        'source':'Alpha Vantage GLOBAL_QUOTE',
        'open':round2(f('02. open')),
        'high':round2(f('03. high')),
        'low':round2(f('04. low')),
        'close':round2(price),
        'last':round2(price),
        'prevClose':round2(prev),
        'changePct':round2(f('10. change percent')),
        'openCloseChangePct':pct(price, f('02. open')),
        'highLowChangePct':pct(f('04. low'), f('03. high')),
        'volume':fmt_big(volume_raw),
        'volumeRaw':volume_raw,
        'volumeSource':'Alpha Vantage daily volume',
        'latestTradingDay':g.get('07. latest trading day'),
    })

def fetch_yahoo_chart_quote(ticker: str):
    key=('fetch_yahoo_chart_quote', ticker.upper())
    cached=_cache_get(key, ttl=60)
    if cached is not None:
        return cached
    end_dt=datetime.utcnow()
    start_dt=end_dt-timedelta(days=7)
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}'
    r=requests.get(url, params={'period1':int(start_dt.timestamp()),'period2':int(end_dt.timestamp()),'interval':'1d','events':'history'}, timeout=15, headers={'User-Agent':'Mozilla/5.0 MMF-v3'})
    r.raise_for_status()
    result=((r.json().get('chart') or {}).get('result') or [None])[0]
    if not result:
        return None
    ts=result.get('timestamp') or []
    quote_rows=(((result.get('indicators') or {}).get('quote') or [{}])[0])
    if not ts or not quote_rows:
        return None
    idx=len(ts)-1
    def at(key):
        vals=quote_rows.get(key) or []
        return vals[idx] if idx < len(vals) else None
    close=at('close')
    if close is None:
        return None
    return _cache_set(key, {
        'source':'Yahoo Finance chart',
        'open':round2(at('open')),
        'high':round2(at('high')),
        'low':round2(at('low')),
        'close':round2(close),
        'last':round2(close),
        'prevClose':None,
        'changePct':None,
        'openCloseChangePct':pct(close, at('open')),
        'highLowChangePct':pct(at('low'), at('high')),
        'volume':fmt_big(at('volume')),
        'volumeRaw':float(at('volume') or 0),
        'volumeSource':'Yahoo Finance chart daily volume',
        'latestTradingDay':datetime.utcfromtimestamp(ts[idx]).date().isoformat(),
    })

def fetch_yahoo_extended_quote(ticker: str):
    """Fetch one shared 5m quote including pre/post-market and expose its timestamp."""
    key=('fetch_yahoo_extended_quote', ticker.upper())
    cached=_cache_get(key, ttl=45)
    if cached is not None:
        return cached
    end_dt=datetime.utcnow()
    start_dt=end_dt-timedelta(days=5)
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}'
    r=requests.get(url, params={
        'period1':int(start_dt.timestamp()),
        'period2':int(end_dt.timestamp())+300,
        'interval':'5m',
        'includePrePost':'true',
        'events':'history',
    }, timeout=15, headers={'User-Agent':'Mozilla/5.0 MMF-v3'})
    r.raise_for_status()
    result=((r.json().get('chart') or {}).get('result') or [None])[0]
    if not result:
        return None
    ts=result.get('timestamp') or []
    rows=(((result.get('indicators') or {}).get('quote') or [{}])[0])
    closes=rows.get('close') or []
    valid=[i for i,x in enumerate(closes) if x is not None and i < len(ts)]
    if not valid:
        return None
    idx=valid[-1]
    latest_ts=datetime.utcfromtimestamp(ts[idx])
    meta=result.get('meta') or {}
    market_price=meta.get('postMarketPrice') or meta.get('preMarketPrice') or meta.get('regularMarketPrice')
    market_ts=meta.get('postMarketTime') or meta.get('preMarketTime') or meta.get('regularMarketTime')
    if market_price is not None and market_ts and market_ts >= ts[idx]:
        price=float(market_price)
        latest_ts=datetime.utcfromtimestamp(market_ts)
    else:
        price=float(closes[idx])
    latest_date=latest_ts.date()
    prior_indices=[i for i in valid if datetime.utcfromtimestamp(ts[i]).date() < latest_date]
    previous=closes[prior_indices[-1]] if prior_indices else (meta.get('chartPreviousClose') or meta.get('previousClose'))
    day_indices=[i for i,t in enumerate(ts) if datetime.utcfromtimestamp(t).date()==latest_date]
    def values(name):
        source=rows.get(name) or []
        return [float(source[i]) for i in day_indices if i < len(source) and source[i] is not None]
    opens=values('open'); highs=values('high'); lows=values('low'); volumes=values('volume')
    day_open=opens[0] if opens else price
    return _cache_set(key, {
        'source':'Yahoo Finance 5m extended hours',
        'session':'extended' if meta.get('marketState') not in ('REGULAR','CLOSED') else str(meta.get('marketState') or 'unknown').lower(),
        'open':round2(day_open),
        'high':round2(max(highs+[price])),
        'low':round2(min(lows+[price])),
        'close':round2(price),
        'last':round2(price),
        'prevClose':round2(previous),
        'changePct':pct(price, previous),
        'openCloseChangePct':pct(price, day_open),
        'highLowChangePct':pct(min(lows+[price]), max(highs+[price])),
        'volume':fmt_big(sum(volumes)),
        'volumeRaw':sum(volumes),
        'volumeSource':'Yahoo Finance 5m extended-hours cumulative volume',
        'latestTradingDay':latest_date.isoformat(),
        'latestTime':latest_ts.isoformat()+'Z',
    })

def _norm_cdf(x):
    try:
        return 0.5 * (1 + math.erf(float(x) / math.sqrt(2)))
    except Exception:
        return None

def _norm_pdf(x):
    try:
        return math.exp(-0.5 * float(x) * float(x)) / math.sqrt(2 * math.pi)
    except Exception:
        return None

def _bs_gamma(spot, strike, years, iv, rate=0.045):
    try:
        spot=float(spot); strike=float(strike); years=float(years); iv=float(iv)
        if spot <= 0 or strike <= 0 or years <= 0 or iv <= 0:
            return None
        d1=(math.log(spot/strike)+(rate+0.5*iv*iv)*years)/(iv*math.sqrt(years))
        pdf=_norm_pdf(d1)
        return pdf/(spot*iv*math.sqrt(years)) if pdf is not None else None
    except Exception:
        return None

def fetch_yahoo_options(ticker: str, spot: float|None=None):
    symbol=ticker.upper()
    key=('fetch_yahoo_options', symbol, round2(spot) if spot is not None else None)
    cached=_cache_get(key, ttl=300)
    if cached is not None:
        return cached
    base=f'https://query2.finance.yahoo.com/v7/finance/options/{symbol}'
    headers={'User-Agent':'Mozilla/5.0 MMF-v3'}
    session=requests.Session()
    r=session.get(base, timeout=18, headers=headers)
    if r.status_code in (401, 403):
        try:
            crumb=session.get('https://query1.finance.yahoo.com/v1/test/getcrumb', timeout=12, headers=headers).text.strip()
            r=session.get(base, params={'crumb':crumb}, timeout=18, headers=headers)
        except Exception:
            pass
    if r.status_code in (401, 403):
        return fetch_cboe_options(symbol, spot=spot)
    r.raise_for_status()
    root=((r.json().get('optionChain') or {}).get('result') or [None])[0]
    if not root:
        raise RuntimeError(f'No option chain returned for {symbol}')
    expirations=root.get('expirationDates') or []
    if not expirations:
        raise RuntimeError(f'No option expirations returned for {symbol}')
    expiry=int(expirations[0])
    r=session.get(base, params={'date':expiry}, timeout=18, headers=headers)
    if r.status_code in (401, 403):
        try:
            crumb=session.get('https://query1.finance.yahoo.com/v1/test/getcrumb', timeout=12, headers=headers).text.strip()
            r=session.get(base, params={'date':expiry,'crumb':crumb}, timeout=18, headers=headers)
        except Exception:
            pass
    if r.status_code in (401, 403):
        return fetch_cboe_options(symbol, spot=spot)
    r.raise_for_status()
    root=((r.json().get('optionChain') or {}).get('result') or [None])[0]
    chain=((root.get('options') or [None])[0] or {})
    quote_obj=root.get('quote') or {}
    underlying=spot or quote_obj.get('regularMarketPrice') or quote_obj.get('postMarketPrice') or quote_obj.get('previousClose')
    calls=chain.get('calls') or []
    puts=chain.get('puts') or []
    expiry_dt=datetime.utcfromtimestamp(expiry)
    now=datetime.utcnow()
    years=max((expiry_dt-now).total_seconds()/(365.0*24*3600), 1/365)
    def rows(items):
        out=[]
        for x in items:
            strike=x.get('strike')
            iv=x.get('impliedVolatility')
            oi=x.get('openInterest') or 0
            vol=x.get('volume') or 0
            gamma=_bs_gamma(underlying, strike, years, iv)
            out.append({
                'contractSymbol':x.get('contractSymbol'),
                'strike':round2(strike),
                'lastPrice':round2(x.get('lastPrice')),
                'bid':round2(x.get('bid')),
                'ask':round2(x.get('ask')),
                'volume':float(vol or 0),
                'openInterest':float(oi or 0),
                'impliedVolatility':round2((iv or 0)*100) if iv is not None else None,
                'gamma':gamma,
                'inTheMoney':x.get('inTheMoney'),
            })
        return out
    call_rows=rows(calls)
    put_rows=rows(puts)
    call_volume=sum(x['volume'] for x in call_rows)
    put_volume=sum(x['volume'] for x in put_rows)
    call_oi=sum(x['openInterest'] for x in call_rows)
    put_oi=sum(x['openInterest'] for x in put_rows)
    contract_multiplier=100
    spot_val=float(underlying or 0)
    def gex(row):
        gamma=row.get('gamma')
        oi=row.get('openInterest') or 0
        if gamma is None or not spot_val:
            return 0
        return gamma*oi*contract_multiplier*spot_val*spot_val*0.01
    call_gex=sum(gex(x) for x in call_rows)
    put_gex=sum(gex(x) for x in put_rows)
    net_gex=call_gex-put_gex
    all_rows=call_rows+put_rows
    avg_iv=round2(np.mean([x['impliedVolatility'] for x in all_rows if isinstance(x.get('impliedVolatility'), (int, float))])) if all_rows else None
    return _cache_set(key, {
        'source':'Yahoo Finance option chain',
        'ticker':symbol,
        'underlying':round2(underlying),
        'expiration':expiry_dt.date().isoformat(),
        'daysToExpiry':max(0, (expiry_dt.date()-now.date()).days),
        'callVolume':round2(call_volume),
        'putVolume':round2(put_volume),
        'putCallVolumeRatio':round2(put_volume/call_volume) if call_volume else None,
        'callOpenInterest':round2(call_oi),
        'putOpenInterest':round2(put_oi),
        'putCallOpenInterestRatio':round2(put_oi/call_oi) if call_oi else None,
        'averageIVPct':avg_iv,
        'callGammaExposureProxy':round2(call_gex),
        'putGammaExposureProxy':round2(put_gex),
        'netGammaExposureProxy':round2(net_gex),
        'methodNote':'Gamma and dealer positioning are proxies from Yahoo option chain OI/IV, not live dealer books.',
        'topCalls':sorted(call_rows, key=lambda x: x.get('openInterest') or 0, reverse=True)[:5],
        'topPuts':sorted(put_rows, key=lambda x: x.get('openInterest') or 0, reverse=True)[:5],
    })

def fetch_cboe_options(ticker: str, spot: float|None=None):
    symbol=ticker.upper()
    key=('fetch_cboe_options', symbol, round2(spot) if spot is not None else None)
    cached=_cache_get(key, ttl=300)
    if cached is not None:
        return cached
    url=f'https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol}.json'
    r=requests.get(url, timeout=18, headers={'User-Agent':'Mozilla/5.0 MMF-v3'})
    r.raise_for_status()
    data=(r.json().get('data') or {})
    options=data.get('options') or []
    if not options:
        raise RuntimeError(f'No Cboe option data returned for {symbol}')
    underlying=spot or data.get('current_price') or data.get('price') or data.get('last')
    today=datetime.utcnow().date()
    parsed=[]
    for x in options:
        opt_symbol=str(x.get('option') or x.get('symbol') or x.get('option_symbol') or '')
        exp=x.get('expiration_date') or x.get('expiration') or x.get('expiry')
        typ=x.get('option_type') or x.get('type')
        strike=x.get('strike_price') or x.get('strike')
        if not exp:
            m=re.search(r'(\d{6})([CP])(\d{8})$', opt_symbol)
            if m:
                yy=int(m.group(1)[:2]); mm=int(m.group(1)[2:4]); dd=int(m.group(1)[4:6])
                exp=f'20{yy:02d}-{mm:02d}-{dd:02d}'
                typ='call' if m.group(2)=='C' else 'put'
                strike=float(m.group(3))/1000
        if typ in ('C','CALL','Call'):
            typ='call'
        elif typ in ('P','PUT','Put'):
            typ='put'
        try:
            exp_date=pd.to_datetime(exp).date()
        except Exception:
            exp_date=None
        if exp_date is None or exp_date < today or typ not in ('call','put'):
            continue
        parsed.append({**x, '_expiration':exp_date, '_type':typ, '_strike':strike})
    if not parsed:
        raise RuntimeError(f'No usable Cboe option rows returned for {symbol}')
    nearest=min({x['_expiration'] for x in parsed}, key=lambda d: (d-today).days)
    rows=[x for x in parsed if x['_expiration']==nearest]
    def num(x, *keys):
        for k in keys:
            try:
                v=x.get(k)
                if v not in (None, '', 'N/A'):
                    return float(v)
            except Exception:
                pass
        return 0.0
    def convert(x):
        iv=num(x, 'iv', 'implied_volatility', 'impliedVolatility')
        gamma=num(x, 'gamma')
        strike=num(x, '_strike', 'strike_price', 'strike')
        oi=num(x, 'open_interest', 'openInterest', 'oi')
        vol=num(x, 'volume')
        return {
            'contractSymbol':x.get('option') or x.get('symbol') or x.get('option_symbol'),
            'strike':round2(strike),
            'lastPrice':round2(num(x, 'last_trade_price', 'last', 'last_price')),
            'bid':round2(num(x, 'bid')),
            'ask':round2(num(x, 'ask')),
            'volume':vol,
            'openInterest':oi,
            'impliedVolatility':round2(iv*100 if iv and iv < 10 else iv),
            'gamma':gamma or None,
            'inTheMoney':None,
        }
    call_rows=[convert(x) for x in rows if x['_type']=='call']
    put_rows=[convert(x) for x in rows if x['_type']=='put']
    call_volume=sum(x['volume'] for x in call_rows)
    put_volume=sum(x['volume'] for x in put_rows)
    call_oi=sum(x['openInterest'] for x in call_rows)
    put_oi=sum(x['openInterest'] for x in put_rows)
    spot_val=float(underlying or 0)
    def gex(row):
        gamma=row.get('gamma')
        oi=row.get('openInterest') or 0
        if gamma is None or not spot_val:
            return 0
        return gamma*oi*100*spot_val*spot_val*0.01
    call_gex=sum(gex(x) for x in call_rows)
    put_gex=sum(gex(x) for x in put_rows)
    all_rows=call_rows+put_rows
    avg_iv=round2(np.mean([x['impliedVolatility'] for x in all_rows if isinstance(x.get('impliedVolatility'), (int, float))])) if all_rows else None
    return _cache_set(key, {
        'source':'Cboe delayed option quotes',
        'ticker':symbol,
        'underlying':round2(underlying),
        'expiration':nearest.isoformat(),
        'daysToExpiry':max(0, (nearest-today).days),
        'callVolume':round2(call_volume),
        'putVolume':round2(put_volume),
        'putCallVolumeRatio':round2(put_volume/call_volume) if call_volume else None,
        'callOpenInterest':round2(call_oi),
        'putOpenInterest':round2(put_oi),
        'putCallOpenInterestRatio':round2(put_oi/call_oi) if call_oi else None,
        'averageIVPct':avg_iv,
        'callGammaExposureProxy':round2(call_gex),
        'putGammaExposureProxy':round2(put_gex),
        'netGammaExposureProxy':round2(call_gex-put_gex),
        'methodNote':'Cboe delayed options. Gamma exposure is still a public-chain proxy, not live dealer inventory.',
        'topCalls':sorted(call_rows, key=lambda x: x.get('openInterest') or 0, reverse=True)[:5],
        'topPuts':sorted(put_rows, key=lambda x: x.get('openInterest') or 0, reverse=True)[:5],
    })

def fetch_yahoo_news(ticker: str, count: int=8):
    key=('fetch_yahoo_news', ticker.upper(), count)
    cached=_cache_get(key, ttl=300)
    if cached is not None:
        return cached
    url='https://query1.finance.yahoo.com/v1/finance/search'
    r=requests.get(url, params={'q':ticker.upper(),'quotesCount':0,'newsCount':count}, timeout=15, headers={'User-Agent':'Mozilla/5.0 MMF-v3'})
    r.raise_for_status()
    data=r.json()
    news=[]
    for item in data.get('news', [])[:count]:
        ts=item.get('providerPublishTime')
        news.append({
            'title':item.get('title'),
            'publisher':item.get('publisher'),
            'link':item.get('link'),
            'published':datetime.utcfromtimestamp(ts).isoformat()+'Z' if ts else None,
            'type':item.get('type'),
        })
    return _cache_set(key, {'source':'Yahoo Finance search news','ticker':ticker.upper(),'items':news})

def fetch_earnings_calendar(symbols=None, horizon: str='3month'):
    """Fetch one shared upcoming earnings calendar, then filter it locally.

    Alpha Vantage's calendar endpoint is intentionally called without a symbol so
    one request can serve every MMF section and every tracked ETF constituent.
    """
    normalized=tuple(sorted({str(x).upper() for x in (symbols or []) if str(x).strip()}))
    horizon=horizon if horizon in {'3month','6month','12month'} else '3month'
    key=('fetch_earnings_calendar', normalized, horizon, datetime.utcnow().date().isoformat())
    cached=_cache_get(key, ttl=21600)
    if cached is not None:
        return cached
    if not ALPHA_VANTAGE_API_KEY:
        return _cache_set(key, {'available':False,'source':'Alpha Vantage Earnings Calendar','events':[],'reason':'Alpha Vantage API key is not configured.'})
    try:
        r=requests.get(
            'https://www.alphavantage.co/query',
            params={'function':'EARNINGS_CALENDAR','horizon':horizon,'apikey':ALPHA_VANTAGE_API_KEY},
            timeout=30,
            headers={'User-Agent':'MMF-v3'},
        )
        if r.status_code >= 400:
            return _cache_set(key, {'available':False,'source':'Alpha Vantage Earnings Calendar','events':[],'reason':f'Calendar provider returned HTTP {r.status_code}.'})
        raw=r.text.strip()
        if not raw:
            return _cache_set(key, {'available':False,'source':'Alpha Vantage Earnings Calendar','events':[],'reason':'Calendar provider returned an empty response.'})
        if raw.startswith('{'):
            try:
                payload=r.json()
                reason=payload.get('Information') or payload.get('Note') or payload.get('Error Message') or 'Calendar provider did not return CSV data.'
            except Exception:
                reason='Calendar provider did not return CSV data.'
            return _cache_set(key, {'available':False,'source':'Alpha Vantage Earnings Calendar','events':[],'reason':str(reason)[:240]})
        frame=pd.read_csv(io.StringIO(raw), dtype=str).fillna('')
        columns={str(col).strip().lower():col for col in frame.columns}
        symbol_col=columns.get('symbol')
        date_col=columns.get('reportdate') or columns.get('report_date')
        if not symbol_col or not date_col:
            return _cache_set(key, {'available':False,'source':'Alpha Vantage Earnings Calendar','events':[],'reason':'Calendar response is missing symbol or reportDate.'})
        if normalized:
            frame=frame[frame[symbol_col].str.upper().isin(normalized)]
        name_col=columns.get('name')
        fiscal_col=columns.get('fiscaldateending') or columns.get('fiscal_date_ending')
        estimate_col=columns.get('estimate')
        currency_col=columns.get('currency')
        time_col=columns.get('reporttime') or columns.get('report_time') or columns.get('time')
        events=[]
        for _,row in frame.iterrows():
            report_date=pd.to_datetime(row.get(date_col), errors='coerce')
            if pd.isna(report_date):
                continue
            estimate=round2(row.get(estimate_col)) if estimate_col else None
            raw_time=str(row.get(time_col) or '').strip() if time_col else ''
            time_lower=raw_time.lower()
            session='PRE_MARKET' if any(x in time_lower for x in ('before','pre','bmo')) else 'AFTER_HOURS' if any(x in time_lower for x in ('after','post','amc')) else 'TIME_NOT_PROVIDED'
            events.append({
                'symbol':str(row.get(symbol_col) or '').upper(),
                'name':str(row.get(name_col) or '') if name_col else '',
                'reportDate':report_date.date().isoformat(),
                'fiscalDateEnding':str(row.get(fiscal_col) or '') if fiscal_col else '',
                'estimate':estimate,
                'currency':str(row.get(currency_col) or '') if currency_col else '',
                'reportSession':session,
                'rawReportTime':raw_time or None,
            })
        events.sort(key=lambda x:(x['reportDate'],x['symbol']))
        return _cache_set(key, {
            'available':True,
            'source':'Alpha Vantage Earnings Calendar',
            'asOf':datetime.utcnow().isoformat(timespec='seconds')+'Z',
            'horizon':horizon,
            'symbols':list(normalized),
            'events':events,
            'reason':None,
            'note':'The provider supplies expected report dates. Session timing remains unconfirmed unless explicitly supplied.',
        })
    except Exception as e:
        return _cache_set(key, {'available':False,'source':'Alpha Vantage Earnings Calendar','events':[],'reason':f'Calendar request failed: {type(e).__name__}.'})

def fetch_stooq_quote(symbol: str):
    key=('fetch_stooq_quote', symbol.upper())
    cached=_cache_get(key, ttl=60)
    if cached is not None:
        return cached
    mapped = {'VIX': '^vix', '^VIX': '^vix'}.get(symbol.upper(), symbol.lower())
    url='https://stooq.com/q/l/'
    r=requests.get(url, params={'s':mapped,'f':'sd2t2ohlcv','h':'','e':'csv'}, timeout=15, headers={'User-Agent':'MMF-v3'})
    r.raise_for_status()
    rows=[line.split(',') for line in r.text.strip().splitlines() if line.strip()]
    if len(rows)<2:
        return None
    header=rows[0]; vals=rows[1]
    data=dict(zip(header, vals))
    if data.get('Close') in (None, '', 'N/D'):
        return None
    def f(key):
        try: return float(str(data.get(key,'')).replace('%',''))
        except Exception: return None
    close=f('Close'); open_=f('Open')
    return _cache_set(key, {
        'source':'Stooq delayed quote',
        'open':round2(open_),
        'high':round2(f('High')),
        'low':round2(f('Low')),
        'close':round2(close),
        'last':round2(close),
        'prevClose':None,
        'changePct':pct(close, open_),
        'volume':data.get('Volume') or '--',
        'latestTradingDay':data.get('Date'),
        'latestTime':data.get('Time'),
    })

def fetch_cboe_vix_quote():
    key=('fetch_cboe_vix_quote', datetime.utcnow().date().isoformat())
    cached=_cache_get(key, ttl=300)
    if cached is not None:
        return cached
    url='https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv'
    r=requests.get(url, timeout=20, headers={'User-Agent':'MMF-v3'})
    r.raise_for_status()
    df=pd.read_csv(io.StringIO(r.text))
    if df.empty or 'CLOSE' not in df:
        return None
    df=df.dropna(subset=['CLOSE']).reset_index(drop=True)
    if df.empty:
        return None
    last=df.iloc[-1]
    prev=df.iloc[-2] if len(df)>1 else last
    close=last.get('CLOSE')
    return _cache_set(key, {
        'ticker':'VIX',
        'name':'VIX volatility index',
        'source':'CBOE VIX daily history',
        'open':round2(last.get('OPEN')),
        'high':round2(last.get('HIGH')),
        'low':round2(last.get('LOW')),
        'close':round2(close),
        'last':round2(close),
        'prevClose':round2(prev.get('CLOSE')),
        'changePct':pct(close, prev.get('CLOSE')),
        'volume':'--',
        'latestTradingDay':str(last.get('DATE')),
    })

def fetch_vix_quote():
    for symbol in ('^VIX', 'VIX'):
        try:
            q=fetch_alpha_vantage_quote(symbol)
            if q and q.get('last') is not None:
                q['ticker']='VIX'
                q['name']='VIX volatility index'
                return q
        except Exception:
            pass
    try:
        q=fetch_cboe_vix_quote()
        if q and q.get('last') is not None:
            return q
    except Exception:
        pass
    try:
        q=fetch_stooq_quote('^VIX')
        if q and q.get('last') is not None:
            q['ticker']='VIX'
            q['name']='VIX volatility index'
            return q
    except Exception:
        pass
    return {'ticker':'VIX','name':'VIX volatility index','source':'unavailable','last':None,'changePct':None,'volume':None}

def merge_live_quote(df, ticker: str) -> pd.DataFrame:
    try:
        live=fetch_live_quote(ticker)
    except Exception:
        live=None
    if not live or not live.get('latestTradingDay') or live.get('last') is None:
        return df
    out=df.copy()
    live_date=_naive_ts(live['latestTradingDay'])
    row={'Date':live_date,'Open':live.get('open') or live.get('last'),'High':live.get('high') or live.get('last'),'Low':live.get('low') or live.get('last'),'Close':live.get('last'),'Volume':live.get('volumeRaw') or 0}
    last_date=_naive_ts(out.iloc[-1].Date).normalize()
    if live_date.normalize() > last_date:
        out=pd.concat([out,pd.DataFrame([row])], ignore_index=True)
    elif live_date.normalize() == last_date:
        row['Volume']=max(float(row.get('Volume') or 0), float(out.iloc[-1].Volume or 0))
        out.loc[out.index[-1], ['Date','Open','High','Low','Close','Volume']] = [row['Date'],row['Open'],row['High'],row['Low'],row['Close'],row['Volume']]
    else:
        return out
    return add_indicators(out.sort_values('Date').reset_index(drop=True))
def add_indicators(df):
    df=df.copy(); df['EMA20']=df['Close'].ewm(span=20,adjust=False).mean(); df['EMA50']=df['Close'].ewm(span=50,adjust=False).mean(); df['SMA200']=df['Close'].rolling(200).mean()
    delta=df['Close'].diff()
    for window in (7,14):
        gain=delta.clip(lower=0).rolling(window).mean(); loss=(-delta.clip(upper=0)).rolling(window).mean(); rs=gain/loss.replace(0,np.nan)
        df[f'RSI{window}']=100-(100/(1+rs))
    df['VOL20']=df['Volume'].rolling(20).mean(); df['VOL_RATIO']=df['Volume']/df['VOL20'].replace(0,np.nan)
    ema12=df['Close'].ewm(span=12,adjust=False).mean(); ema26=df['Close'].ewm(span=26,adjust=False).mean(); df['MACD']=ema12-ema26; df['MACD_SIGNAL']=df['MACD'].ewm(span=9,adjust=False).mean()
    return df
def quote(df, ticker: str|None=None):
    if ticker:
        try:
            live=fetch_live_quote(ticker)
            if live:
                return live
        except Exception:
            pass
    last=df.iloc[-1]; prev=df.iloc[-2] if len(df)>1 else last
    return {'source':'Tiingo daily adjusted OHLCV','open':round2(last.Open),'high':round2(last.High),'low':round2(last.Low),'close':round2(last.Close),'last':round2(last.Close),'prevClose':round2(prev.Close),'changePct':pct(last.Close,prev.Close),'openCloseChangePct':pct(last.Close,last.Open),'highLowChangePct':pct(last.Low,last.High),'volume':fmt_big(last.Volume),'volumeRaw':float(last.Volume or 0),'volumeSource':'Tiingo daily adjusted OHLCV'}
def safe_quote(ticker):
    try:
        q=quote(fetch_daily(ticker, years=1))
        q['source']='Tiingo daily adjusted OHLCV (background quote)'
        return q
    except Exception as e: return {'source':f'unavailable: {str(e)[:80]}','last':None,'changePct':None,'volume':None}

def fetch_external_fear_greed():
    key=('fetch_external_fear_greed',)
    cached=_cache_get(key, ttl=300)
    if cached is not None:
        return cached
    url='https://feargreedmeter.com/'
    r=requests.get(url, timeout=15, headers={'User-Agent':'MMF-v3'})
    r.raise_for_status()
    text=r.text
    m=re.search(r'Fear and Greed Index:\s*(\d{1,3})\s*\(([^)]+)\)', text, re.I)
    if not m:
        m=re.search(r'<title>\s*Fear and Greed Index:\s*(\d{1,3})\s*\(([^)]+)\)', text, re.I)
    if not m:
        m=re.search(r'>\s*(\d{1,3})\s*</[^>]+>\s*<[^>]+>\s*(Extreme Fear|Fear|Neutral|Greed|Extreme Greed)\s*<', text, re.I)
    if not m:
        return None
    score=max(0,min(100,int(m.group(1))))
    label=m.group(2).strip()
    return _cache_set(key, {'score':score,'label':label,'source':'feargreedmeter.com','url':url})
