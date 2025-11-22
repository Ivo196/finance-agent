import yfinance as yf
import pandas as pd
import numpy as np
from calculate_indicators import calculate_indicators
from colorama import Fore, Style, init

init(autoreset=True)

def classify_trend(hist):
    """
    Robust trend classification using ADX + EMA position + EMA slope.
    Returns: "Fuerte Alcista", "Alcista Débil", "Lateral", "Bajista Débil", "Fuerte Bajista"
    """
    last = hist.iloc[-1]
    
    # Get indicators
    close_price = last.get('Close', 0)
    ema_200 = last.get('EMA_200', 0)
    adx = last.get('ADX', 0)
    
    # Calculate EMA 200 slope (% change over last 20 periods)
    ema_200_series = hist['EMA_200'].tail(20)
    if len(ema_200_series) > 0 and ema_200_series.iloc[0] != 0:
        ema_slope = ((ema_200_series.iloc[-1] - ema_200_series.iloc[0]) / ema_200_series.iloc[0]) * 100
    else:
        ema_slope = 0  # Flat slope if insufficient data or starting from zero
    
    # 1. Check for sideways market (ADX filter)
    if adx < 20:
        return "Lateral (sin tendencia)"
    
    # 2. Determine direction (price vs EMA_200)
    is_above_ema = close_price > ema_200
    
    # 3. Determine strength (ADX + EMA slope confirmation)
    strong_trend = adx > 25 and abs(ema_slope) > 1.0  # EMA moving clearly
    
    # 4. Classify
    if is_above_ema:
        if strong_trend:
            return "Fuerte Alcista"
        else:
            return "Alcista Débil"
    else:
        if strong_trend:
            return "Fuerte Bajista"
        else:
            return "Bajista Débil"

def get_market_data(ticker, interval="1d"):
    try:
        print(Fore.CYAN + f"   [Data] 📡 Iniciando descarga de datos para {ticker} ({interval})...")
        stock = yf.Ticker(ticker)
        
        # --- 1. HISTORIAL Y TÉCNICO ---
        # Ajustamos el periodo según el intervalo para no traer demasiados datos innecesarios o muy pocos
        period = "5y" if interval == "1d" else "2y" if interval == "1wk" else "5y"
        
        # Download con timeout para evitar esperas largas en tickers inválidos
        try:
            hist = stock.history(period=period, interval=interval, timeout=10)
        except Exception as download_error:
            error_msg = f"Error al descargar datos para '{ticker}': {str(download_error)}"
            print(Fore.RED + f"   [Data] ❌ {error_msg}")
            return None, None, None, error_msg
        
        # Validación estricta de datos
        if hist is None or hist.empty:
            error_msg = f"No se encontraron datos para '{ticker}'. Verifica: 1) Ticker correcto (ej. AAPL, BTC-USD), 2) Mercado abierto, 3) Conexión a internet."
            print(Fore.RED + f"   [Data] ❌ {error_msg}")
            return None, None, None, error_msg
            
        print(Fore.CYAN + "   [Data] 📐 Calculando indicadores técnicos...")
        hist = calculate_indicators(hist)
        last = hist.iloc[-1]
        
        # --- 2. FUNDAMENTALES (Salud Financiera) ---
        # Solo intentamos buscar fundamentales si el ticker existe
        print(Fore.CYAN + "   [Data] 📊 Obteniendo fundamentales...")
        try:
            info = stock.info
            fundamentals = {
                "PER": info.get('forwardPE', 'N/A'),
                "PEG": info.get('pegRatio', 'N/A'),
                "Deuda/Equity": info.get('debtToEquity', 'N/A'),
                "Margen": info.get('profitMargins', 0)
            }
            sector = info.get('sector', 'Desconocido')
            industry = info.get('industry', 'Desconocido')
            fund_text = f"Sector: {sector} | Industria: {industry} | PER: {fundamentals['PER']} | PEG: {fundamentals['PEG']}"
        except Exception as e:
            print(Fore.YELLOW + f"   [Data] ⚠️ No se pudieron obtener fundamentales: {e}")
            fund_text = "Datos fundamentales no disponibles."
            sector = "Desconocido"

        # --- 3. NOTICIAS ---
        raw_news = []
        news_summary = []
        try:
            # Determine news timeframe based on analysis interval
            # User requested "maximum days possible", so we are being generous
            news_days = 7  # 1 week for daily analysis
            if interval == "1wk":
                news_days = 30 # 1 month for weekly analysis
            elif interval == "1mo":
                news_days = 90 # 3 months for monthly analysis
                
            print(Fore.YELLOW + f"   [News] 📰 Buscando noticias de {ticker} (últimos {news_days} días)...")
            from news_agents import NewsAggregator
            aggregator = NewsAggregator()
            raw_news = aggregator.get_consolidated_news(ticker, days=news_days)
            
            if raw_news:
                print(Fore.GREEN + f"   [News] ✅ Se encontraron {len(raw_news)} noticias relevantes.")
                for n in raw_news[:15]: # Increased summary limit to 15
                    date_str = n.get('published', 'Reciente')
                    title = n.get('title', 'Sin título')
                    source = n.get('source', 'Desconocido')
                    # Format: [YYYY-MM-DD HH:MM] (Source) Title
                    news_summary.append(f"- [{date_str}] ({source}) {title}")
            else:
                 print(Fore.RED + "   [News] ❌ No se encontraron noticias en ninguna fuente.")

        except Exception as e:
            print(Fore.RED + f"   [News] ⚠️ Fallo en noticias: {e}")
            news_summary.append("No se pudieron descargar noticias recientes.")

        # --- 4. EMPAQUETADO ---
        close_price = last.get('Close', 0)
        ema_200_val = last.get('EMA_200', 0)
        
        # Determine asset type for specialized analysis
        from datetime import datetime
        ticker_type = "CRYPTO" if "-USD" in ticker.upper() or "BTC" in ticker.upper() or "ETH" in ticker.upper() else "STOCK"
        
        llm_data = {
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),  # Critical: AI needs to know TODAY's date
            "ticker_type": ticker_type,  # Stocks vs Crypto behave differently
            "last_updated": str(hist.index[-1].date()),  # Date tracking
            "price": round(close_price, 2),
            "ema_20": round(last.get('EMA_20', 0), 2),
            "ema_50": round(last.get('EMA_50', 0), 2),
            "ema_200": round(ema_200_val, 2),
            "rsi": round(last.get('RSI', 50), 2),
            "macd": round(last.get('MACD', 0), 3),
            "macd_signal": round(last.get('MACD_Signal', 0), 3),
            "macd_hist": round(last.get('MACD_Hist', 0), 3),
            "atr": round(last.get('ATR', 0), 2),
            "adx": round(last.get('ADX', 0), 2),
            "stoch_k": round(last.get('Stoch_K', 0), 2),
            "stoch_d": round(last.get('Stoch_D', 0), 2),
            "obv": round(last.get('OBV', 0), 2),
            "sector": sector,
            "trend": classify_trend(hist),
            "fundamentals": fund_text,
            "news": "\n".join(news_summary) if news_summary else "Sin noticias."
        }
        
        return llm_data, hist, raw_news, None
        
    except Exception as e:
        return None, None, None, str(e)

def get_multi_timeframe_data(ticker):
    """
    Fetches both Weekly (The Judge) and Daily (The Sniper) data.
    Also fetches comprehensive news (Long Term + Short Term).
    """
    print(Fore.MAGENTA + f"   [Multi-TF] ⚖️ Obteniendo datos para estrategia Juez + Francotirador: {ticker}")
    
    # 1. The Judge (Weekly)
    # We don't need news from here, just technicals
    wk_data, wk_hist, _, wk_error = get_market_data(ticker, interval="1wk")
    if wk_error:
        return None, wk_error
        
    # 2. The Sniper (Daily)
    # We don't need news from here either, we will fetch it separately to control the range
    dy_data, dy_hist, _, dy_error = get_market_data(ticker, interval="1d")
    if dy_error:
        return None, dy_error

    # 3. Comprehensive News (60 Days for Long Term + Short Term)
    print(Fore.YELLOW + f"   [News] 📰 Buscando noticias extendidas de {ticker} (últimos 60 días)...")
    from news_agents import NewsAggregator
    aggregator = NewsAggregator()
    # Fetch 60 days to cover "beyond 30 days" requirement
    raw_news = aggregator.get_consolidated_news(ticker, days=60)
    
    news_summary = []
    if raw_news:
        print(Fore.GREEN + f"   [News] ✅ Se encontraron {len(raw_news)} noticias relevantes.")
        for n in raw_news[:20]: # Increased summary limit
            date_str = n.get('published', 'Reciente')
            title = n.get('title', 'Sin título')
            source = n.get('source', 'Desconocido')
            news_summary.append(f"- [{date_str}] ({source}) {title}")
    else:
         print(Fore.RED + "   [News] ❌ No se encontraron noticias en ninguna fuente.")
         news_summary.append("No se encontraron noticias recientes.")
         
    # Add news summary to daily data for the agent to see
    dy_data['news'] = "\n".join(news_summary)
        
    return {
        "weekly": wk_data,
        "daily": dy_data,
        "weekly_hist": wk_hist,
        "daily_hist": dy_hist,
        "news": raw_news # Raw list for UI
    }, None