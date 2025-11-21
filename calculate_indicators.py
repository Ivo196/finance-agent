import numpy as np # Necesitamos numpy para cálculos vectoriales
import pandas as pd

def calculate_indicators(hist):
    # 1. EMAs existentes
    hist['EMA_20'] = hist['Close'].ewm(span=20, adjust=False).mean()
    hist['EMA_50'] = hist['Close'].ewm(span=50, adjust=False).mean()
    hist['EMA_200'] = hist['Close'].ewm(span=200, adjust=False).mean()
    
    # 2. RSI existente
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    hist['RSI'] = 100 - (100 / (1 + rs))
    
    # 3. MACD existente
    ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
    ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
    hist['MACD'] = ema12 - ema26
    hist['MACD_Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
    hist['MACD_Hist'] = hist['MACD'] - hist['MACD_Signal']
    
    # --- NUEVO: BANDAS DE BOLLINGER (Volatilidad) ---
    # Media simple de 20 días
    sma_20 = hist['Close'].rolling(window=20).mean()
    # Desviación estándar
    rstd = hist['Close'].rolling(window=20).std()
    hist['BB_Upper'] = sma_20 + 2 * rstd
    hist['BB_Lower'] = sma_20 - 2 * rstd
    
    # --- NUEVO: ATR (Average True Range) para Riesgo ---
    high_low = hist['High'] - hist['Low']
    high_close = np.abs(hist['High'] - hist['Close'].shift())
    low_close = np.abs(hist['Low'] - hist['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    hist['ATR'] = true_range.rolling(14).mean()

    # --- NUEVO: ADX (Average Directional Index) ---
    plus_dm = hist['High'].diff()
    minus_dm = hist['Low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr14 = true_range.rolling(14).sum()
    plus_di14 = 100 * (plus_dm.ewm(alpha=1/14).mean() / tr14)
    minus_di14 = 100 * (minus_dm.abs().ewm(alpha=1/14).mean() / tr14)
    dx = 100 * np.abs((plus_di14 - minus_di14) / (plus_di14 + minus_di14))
    hist['ADX'] = dx.rolling(14).mean()

    # --- NUEVO: Stochastic Oscillator ---
    low_min = hist['Low'].rolling(14).min()
    high_max = hist['High'].rolling(14).max()
    hist['Stoch_K'] = 100 * ((hist['Close'] - low_min) / (high_max - low_min))
    hist['Stoch_D'] = hist['Stoch_K'].rolling(3).mean()

    # --- NUEVO: OBV (On-Balance Volume) ---
    hist['OBV'] = (np.sign(hist['Close'].diff()) * hist['Volume']).fillna(0).cumsum()

    return hist