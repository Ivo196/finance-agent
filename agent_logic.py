from openai import OpenAI
import os
from dotenv import load_dotenv
from colorama import Fore, Style, init
import pandas as pd
from datetime import datetime
import json

init(autoreset=True)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ ERROR: No se encontró la API Key en el archivo .env")

client = OpenAI(api_key=api_key)

def analyze_stock(ticker, data, model="gpt-5.1", risk_profile="Moderado"):
    """
    Análisis exhaustivo v3.0 (Técnico + Fundamental + Riesgo).
    """
    
    # Risk profile guidance for AI
    risk_guidance = {
        "Conservador": "Prioriza preservación de capital. Solo recomienda trades con ratio R:R > 1:3 y ADX > 30. Evita mercados laterales.",
        "Moderado": "Balance entre riesgo y retorno. Recomienda trades con ratio R:R > 1:2 en tendencias confirmadas.",
        "Agresivo": "Busca alta recompensa. Acepta mayor riesgo en tendencias débiles si el momentum es fuerte. Enfócate en oportunidades de alto potencial."
    }
    
    system_prompt = f"""
    Eres un Analista Financiero de Élite (GPT-5.1 Level). Tu objetivo es dar claridad inmediata.
    
    ESTILO DE RESPUESTA:
    - **Conciso y Directo**: Ve al grano. Usa bullet points.
    - **Visual**: Usa emojis para guiar la lectura (e.g., 🟢, 🔴, ⚠️, 🎯).
    - **Estructurado**: Sigue estrictamente el formato solicitado.
    
    TU MISIÓN:
    1. Determinar la tendencia dominante.
    2. Evaluar el riesgo vs recompensa.
    3. Dar una señal clara de acción.
    
    PERFIL DE RIESGO DEL USUARIO: {risk_profile}
    {risk_guidance.get(risk_profile, risk_guidance["Moderado"])}
    
    IMPORTANTE - CLASIFICACIÓN DE TENDENCIAS:
    - **"Fuerte Alcista/Bajista"**: ADX > 25, tendencia clara → Operaciones de seguimiento son viables.
    - **"Débil Alcista/Bajista"**: Tendencia presente pero débil → Precaución.
    - **"Lateral (sin tendencia)"**: ADX < 20 → ⚠️ ADVERTIR que estrategias de tendencia son RIESGOSAS aquí.
      En mercados laterales recomienda estrategias de rango (comprar soporte, vender resistencia) o esperar.
    """
    
    user_prompt = f"""
    📅 FECHA DEL ANÁLISIS: {data.get('analysis_date', 'N/A')}
    🏷️ TIPO DE ACTIVO: {data.get('ticker_type', 'STOCK')}
    
    {"⚠️ ADVERTENCIA: Este es un activo CRIPTO. Los indicadores técnicos estándar (RSI 14, BB 20) tienden a dar más señales falsas debido a la extrema volatilidad. Sé más exigente con las confirmaciones." if data.get('ticker_type') == 'CRYPTO' else ""}
    
    Analiza {ticker} con los siguientes datos:
    
    PRECIO: ${data.get('price')} | TENDENCIA: {data.get('trend')} (Fuerza ADX: {data.get('adx')})
    SECTOR: {data.get('sector', 'N/A')}
    RSI: {data.get('rsi')} | ADX: {data.get('adx')} | MACD: {data.get('macd_hist')}
    FUNDAMENTALES: {data.get('fundamentals')}
    NOTICIAS: {data.get('news')}
    
    --- FORMATO DE RESPUESTA REQUERIDO ---
    
    ### 🎯 VEREDICTO: [COMPRA FUERTE / COMPRA / MANTENER / VENTA / VENTA FUERTE] (Score: 0-100)
    
    **⚡ Resumen Ejecutivo**
    * [Punto clave 1]
    * [Punto clave 2]
    
    **📊 Análisis Técnico (Con Contexto)**
    * **Tendencia**: [Alcista/Bajista] (ADX: {data.get('adx')} - *Ref: >25 es tendencia fuerte*)
    * **RSI**: {data.get('rsi')} ([Sobrecompra/Neutral/Sobreventa] - *Ref: >70 Sobrecompra, <30 Sobreventa*)
    * **MACD**: {data.get('macd_hist')} ([Señal] - *Ref: >0 Alcista, <0 Bajista*)
    * **Niveles Clave**: Soporte: $X | Resistencia: $Y
    
    **🛡️ Gestión de Riesgo**
    * **Stop Loss**: $X (*Ref: Calculado con 2x ATR*)
    * **Take Profit**: $Y (*Ref: Ratio Riesgo/Beneficio 1:2*)
    * **Riesgo**: [Bajo/Medio/Alto]
    """

    try:
        print(Fore.MAGENTA + f"   [AI] 🧠 Enviando prompt a OpenAI ({model}) para {ticker}...")
        response = client.chat.completions.create(
            model=model, 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_completion_tokens=2000 
        )
        print(Fore.GREEN + "   [AI] ✅ Análisis recibido correctamente.")
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error OpenAI: {str(e)}"

def recommend_capital_distribution(capital_amount, tickers_data, model="gpt-5.1", export_to_excel=True):
    """
    Analiza múltiples tickers y recomienda cómo distribuir el capital basándose en señales técnicas.
    
    Args:
        capital_amount (float): Monto total a invertir en dólares
        tickers_data (dict): Diccionario {ticker: llm_data} con datos de mercado de cada ticker
        model (str): Modelo de OpenAI a utilizar
        export_to_excel (bool): Si True, exporta todos los datos a Excel para debugging
        
    Returns:
        str: Recomendación formateada de distribución de capital
    """
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    system_prompt = """
    Eres un Portfolio Manager Cuantitativo de Élite. Tu misión es MAXIMIZAR el retorno informado por riesgo.
    
    CRITERIOS DE ASIGNACIÓN:
    1. **Fuerza de Señal Técnica**: Prioriza activos con señales claras (ADX > 25, cruces MACD confirmados, RSI en zona óptima)
    2. **Momentum**: Favorece activos con momentum positivo y rupturas al alza
    3. **Gestión de Riesgo**: Evita activos en zonas de sobrecompra extrema o con señales contradictorias
    4. **Diversificación**: No pongas todo en un solo activo a menos que sea extraordinario
    
    FORMATO DE RESPUESTA:
    - Sé DIRECTO y CLARO
    - Especifica montos exactos en dólares para cada activo
    - Justifica BREVEMENTE cada asignación con razones técnicas concretas
    - Si un activo no es atractivo HOY, indícalo claramente
    - El total asignado debe ser cercano al capital disponible (no tienes que usar el 100% si no hay oportunidades)
    
    ESTILO:
    "De acuerdo a las señales de HOY, la mejor forma de gastar esos $XXX es:
    
    $YYY en TICKER1 (Razón técnica específica)
    $ZZZ en TICKER2 (Razón técnica específica)
    
    Ignora TICKER3 por hoy, [razón específica]."
    """
    
    # Construir resumen de datos de todos los tickers
    tickers_summary = []
    for ticker, data in tickers_data.items():
        summary = f"""
        {ticker}:
        - Precio: ${data.get('price')}
        - Tendencia: {data.get('trend')} (ADX: {data.get('adx')})
        - RSI: {data.get('rsi')}
        - MACD Hist: {data.get('macd_hist')}
        - Sector: {data.get('sector', 'N/A')}
        - Noticias: {data.get('news', 'Sin noticias relevantes')[:500]}...
        """
        tickers_summary.append(summary)
    
    user_prompt = f"""
    Tengo ${capital_amount} para invertir HOY.
    
    Analiza estos activos y recomiéndame cómo distribuir mi capital:
    
    {''.join(tickers_summary)}
    
    Recuerda: Busco las MEJORES oportunidades de HOY basadas en señales técnicas.
    Dame una recomendación clara y accionable.
    """
    
    try:
        print(Fore.MAGENTA + f"   [AI] 💰 Analizando distribución de ${capital_amount} entre {len(tickers_data)} activos...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_completion_tokens=1500
        )
        
        llm_response = response.choices[0].message.content
        print(Fore.GREEN + "   [AI] ✅ Recomendación de distribución generada.")
        
        # Exportar a Excel para debugging
        excel_data = None
        if export_to_excel:
            try:
                excel_data = export_analysis_to_excel(
                    timestamp=timestamp,
                    capital_amount=capital_amount,
                    model=model,
                    tickers_data=tickers_data,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    llm_response=llm_response
                )
                print(Fore.CYAN + f"   [Excel] 📊 Análisis exportado a: analysis_debug_{timestamp}.xlsx")
            except Exception as e:
                print(Fore.YELLOW + f"   [Excel] ⚠️ Error al exportar Excel: {e}")
        
        return llm_response, excel_data
        
    except Exception as e:
        return f"❌ Error al generar recomendación: {str(e)}", None

def export_analysis_to_excel(timestamp, capital_amount, model, tickers_data, system_prompt, user_prompt, llm_response):
    """
    Exporta todo el análisis a un archivo Excel para debugging y comparación.
    Retorna los DataFrames para mostrar en Streamlit.
    """
    filename = f"analysis_debug_{timestamp}.xlsx"
    
    # Sheet 1: Resumen General
    resumen_data = {
        'Parámetro': ['Timestamp', 'Capital a Invertir', 'Modelo AI', 'Num Tickers Analizados', 'Tickers'],
        'Valor': [
            str(timestamp),
            f"${capital_amount}",
            str(model),
            str(len(tickers_data)),
            ', '.join(tickers_data.keys())
        ]
    }
    df_resumen = pd.DataFrame(resumen_data)
    
    # Sheet 2: Datos Técnicos de Cada Ticker
    technical_data = []
    for ticker, data in tickers_data.items():
        technical_data.append({
            'Ticker': ticker,
            'Precio': data.get('price'),
            'Tendencia': data.get('trend'),
            'RSI': data.get('rsi'),
            'MACD': data.get('macd'),
            'MACD_Signal': data.get('macd_signal'),
            'MACD_Hist': data.get('macd_hist'),
            'ADX': data.get('adx'),
            'ATR': data.get('atr'),
            'Stoch_K': data.get('stoch_k'),
            'Stoch_D': data.get('stoch_d'),
            'OBV': data.get('obv'),
            'Sector': data.get('sector', 'N/A'),
            'Last_Updated': data.get('last_updated', 'N/A'),
            'Analysis_Date': data.get('analysis_date', 'N/A')
        })
    df_technical = pd.DataFrame(technical_data)
    
    # Sheet 3: Noticias Completas
    news_data = []
    for ticker, data in tickers_data.items():
        news_data.append({
            'Ticker': ticker,
            'Noticias': data.get('news', 'Sin noticias')
        })
    df_news = pd.DataFrame(news_data)
    
    # Sheet 4: Prompt Completo Enviado al LLM
    prompt_data = {
        'Tipo': ['System Prompt', 'User Prompt'],
        'Contenido': [system_prompt, user_prompt]
    }
    df_prompt = pd.DataFrame(prompt_data)
    
    # Sheet 5: Respuesta del LLM
    response_data = {
        'Campo': ['Modelo', 'Timestamp', 'Recomendación Completa'],
        'Valor': [model, timestamp, llm_response]
    }
    df_response = pd.DataFrame(response_data)
    
    # Guardar todo en Excel
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
        df_technical.to_excel(writer, sheet_name='Datos_Tecnicos', index=False)
        df_news.to_excel(writer, sheet_name='Noticias', index=False)
        df_prompt.to_excel(writer, sheet_name='Prompt_Enviado', index=False)
        df_response.to_excel(writer, sheet_name='Respuesta_LLM', index=False)
    
    print(Fore.GREEN + f"   [Excel] ✅ Archivo generado: {filename}")
    
    # Retornar DataFrames y filename para uso en Streamlit
    return {
        'filename': filename,
        'df_resumen': df_resumen,
        'df_technical': df_technical,
        'df_news': df_news,
        'df_prompt': df_prompt,
        'df_response': df_response
    }