import numpy as np # Necesitamos numpy para cálculos vectoriales
import pandas as pd

def wilder_smoothing(data, period=14):
    """
    Implements Wilder's Smoothing (RMA/SMMA) - the correct method for ADX calculation.
    
    Wilder's formula: smoothed[i] = (smoothed[i-1] * (period - 1) + current_value) / period
    First value uses simple moving average as seed.
    
    This is different from EMA and produces values matching TradingView/Yahoo Finance.
    """
    result = pd.Series(index=data.index, dtype=float)
    
    # First value: simple moving average
    result.iloc[period - 1] = data.iloc[:period].mean()
    
    # Subsequent values: Wilder's smoothing
    for i in range(period, len(data)):
        result.iloc[i] = (result.iloc[i - 1] * (period - 1) + data.iloc[i]) / period
    
    return result

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
    # Use Wilder smoothing for ATR (industry standard)
    hist['ATR'] = wilder_smoothing(true_range, period=14)

    # --- NUEVO: ADX (Average Directional Index) ---
    # Wilder's ADX calculation (industry standard matching TradingView/Yahoo)
    plus_dm = hist['High'].diff()
    minus_dm = hist['Low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    # Smooth the directional movements and true range using Wilder's method
    smoothed_plus_dm = wilder_smoothing(plus_dm, period=14)
    smoothed_minus_dm = wilder_smoothing(minus_dm.abs(), period=14)
    smoothed_tr = wilder_smoothing(true_range, period=14)
    
    # Calculate +DI and -DI
    plus_di = 100 * (smoothed_plus_dm / smoothed_tr)
    minus_di = 100 * (smoothed_minus_dm / smoothed_tr)
    
    # Calculate DX
    dx = 100 * np.abs((plus_di - minus_di) / (plus_di + minus_di))
    
    # ADX is Wilder smoothing of DX
    hist['ADX'] = wilder_smoothing(dx, period=14)

    # --- NUEVO: Stochastic Oscillator ---
    low_min = hist['Low'].rolling(14).min()
    high_max = hist['High'].rolling(14).max()
    hist['Stoch_K'] = 100 * ((hist['Close'] - low_min) / (high_max - low_min))
    hist['Stoch_D'] = hist['Stoch_K'].rolling(3).mean()

    # --- NUEVO: OBV (On-Balance Volume) ---
    hist['OBV'] = (np.sign(hist['Close'].diff()) * hist['Volume']).fillna(0).cumsum()

    return hist