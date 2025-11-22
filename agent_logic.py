from openai import OpenAI
import os
from dotenv import load_dotenv
from colorama import Fore, Style, init
import pandas as pd
from datetime import datetime
import json
import time

init(autoreset=True)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ ERROR: No se encontró la API Key en el archivo .env")

client = OpenAI(api_key=api_key)

def analyze_stock(ticker, data, model="gpt-5.1", reasoning_effort="none"):
    """
    Legacy wrapper for single stock analysis. Now redirects to the deep analysis function.
    """
    return analyze_individual_stock_deeply(ticker, data, model, reasoning_effort)

def analyze_individual_stock_deeply(ticker, data, model="gpt-5.1", reasoning_effort="none"):
    """
    Realiza un análisis profundo e INDIVIDUAL de un activo.
    NO ASUME TENDENCIAS. Analiza indicadores técnicos fríamente y noticias de largo/corto plazo.
    """
    start_time = time.time()
    
    # Extract data
    wk_data = data.get('weekly', {})
    dy_data = data.get('daily', {})
    news_data = data.get('news', []) # List of dicts
    
    # Fallback
    if not wk_data and not dy_data:
        dy_data = data
        wk_data = data
        
    # Format news for the prompt (distinguish recent vs older)
    news_text = ""
    if isinstance(news_data, list):
        news_text = "--- NOTICIAS RECIENTES (Últimos 60 días) ---\n"
        for n in news_data[:25]: # Top 25 news
            news_text += f"- [{n.get('published')}] {n.get('title')} ({n.get('source')})\n"
    else:
        news_text = f"Noticias: {str(news_data)[:500]}"

    system_prompt = f"""
    Eres un Analista Técnico y Fundamental Senior. Tu trabajo es analizar el activo {ticker} de forma INDIVIDUAL y OBJETIVA.
    
    ### TUS REGLAS DE ORO:
    1.  **NO ASUMAS NADA**: No des por hecho que la tendencia es alcista o bajista solo por el nombre del activo. Mira los datos.
    2.  **ANÁLISIS TÉCNICO PURO**:
        -   Usa los datos SEMANALES para el contexto macro (El Juez).
        -   Usa los datos DIARIOS para el timing preciso (El Francotirador).
        -   Si el precio está lejos de la EMA 200, dilo. Si el RSI está en 80, dilo.
    3.  **ANÁLISIS DE NOTICIAS (CRUCIAL)**:
        -   Analiza las noticias proporcionadas (que cubren hasta 60 días).
        -   **Largo Plazo (>30 días)**: ¿Qué dicen las noticias de hace un mes? ¿Hay una tendencia fundamental de fondo?
        -   **Corto Plazo (<7 días)**: ¿Hay noticias recientes que afecten el precio HOY?
    4.  **SALIDA ACCIONABLE**:
        -   Debes dar una recomendación clara: COMPRAR, VENDER, o ESPERAR.
        -   **TIMING**: Si recomiendas esperar, di CUÁNTO (ej: "Espera 3 días a que baje el RSI").
    
    ### DATOS TÉCNICOS:
    
    **MACRO (Semanal - 1W):**
    - Precio: ${wk_data.get('price')}
    - Tendencia Auto-Detectada: {wk_data.get('trend')}
    - EMA 200: {wk_data.get('ema_200')} (Posición: {"PRECIO ENCIMA" if wk_data.get('price', 0) > wk_data.get('ema_200', 0) else "PRECIO DEBAJO"})
    - RSI (1W): {wk_data.get('rsi')}
    
    **MICRO (Diario - 1D):**
    - Precio: ${dy_data.get('price')}
    - Tendencia Corto Plazo: {dy_data.get('trend')}
    - RSI (1D): {dy_data.get('rsi')}
    - MACD Histograma: {dy_data.get('macd_hist')}
    - ADX (Fuerza): {dy_data.get('adx')}
    
    {news_text}
    
    ### FORMATO DE RESPUESTA (MARKDOWN):
    
    #### 🔎 Análisis Individual: {ticker}
    
    **1. Diagnóstico Técnico (Sin Sesgos)**
    *   **Semanal (Macro)**: [Análisis objetivo. ¿Es alcista, bajista o lateral? ¿Por qué?]
    *   **Diario (Timing)**: [Análisis de entrada. ¿Está caro o barato hoy? ¿RSI sobrecomprado?]
    
    **2. Análisis de Noticias (Sentimiento)**
    *   **Tendencia Largo Plazo (>30d)**: [Resumen del sentimiento general de las noticias antiguas]
    *   **Eventos Corto Plazo**: [Noticias recientes clave y su impacto inmediato]
    
    **3. CONCLUSIÓN Y TIMING**
    *   **Veredicto**: [COMPRAR / VENDER / ESPERAR]
    *   **Instrucción de Tiempo**: [Ej: "Compra HOY", "Espera 3 días", "Espera a que toque $XXX"]
    *   **Razón**: [Justificación en 1 frase]
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analiza {ticker} ahora."}
            ],
            reasoning_effort=reasoning_effort if model == "gpt-5.1" else None
        )
        
        analysis = response.choices[0].message.content
        
        # Metrics
        end_time = time.time()
        metrics = {
            "execution_time": end_time - start_time,
            "token_usage": {
                "total_tokens": response.usage.total_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }
        
        return analysis, metrics

    except Exception as e:
        return f"❌ Error analizando {ticker}: {str(e)}", None

def recommend_capital_distribution(capital_amount, tickers_data, model="gpt-5.1", reasoning_effort="none"):
    """
    Genera una recomendación de distribución de capital basada en análisis individuales profundos.
    """
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    print(Fore.CYAN + f"\n🚀 Iniciando Análisis Profundo de {len(tickers_data)} activos...")
    
    # --- FASE 1: ANÁLISIS INDIVIDUAL (Iterativo) ---
    individual_reports = []
    total_tokens = 0
    
    # Prompt acumulativo para el debug
    debug_prompts = []
    
    for ticker, data in tickers_data.items():
        print(Fore.YELLOW + f"   [Agent] Analizando {ticker} individualmente...")
        report, metrics = analyze_individual_stock_deeply(ticker, data, model, reasoning_effort)
        
        if metrics:
            total_tokens += metrics['token_usage']['total_tokens']
            
        individual_reports.append(f"---\n{report}\n---")
        debug_prompts.append(f"ANÁLISIS {ticker}:\n{report}")

    # --- FASE 2: EL JEFE (Asignación de Capital) ---
    print(Fore.CYAN + "   [Agent] Generando decisión final de asignación (El Jefe)...")
    
    all_reports_text = "\n".join(individual_reports)
    
    boss_system_prompt = f"""
    Eres el CIO (Chief Investment Officer). Has recibido los reportes detallados de tus analistas sobre {len(tickers_data)} activos.
    
    Tu trabajo NO es re-analizar técnicamente (eso ya lo hicieron tus analistas), sino TOMAR DECISIONES DE DINERO.
    
    Tienes un capital de: ${capital_amount}.
    
    ### TUS INSTRUCCIONES:
    1.  Lee los reportes individuales adjuntos.
    2.  Identifica las MEJORES oportunidades (donde el analista dijo "COMPRAR").
    3.  Identifica dónde hay que ESPERAR (donde el analista dijo "Espera X días").
    4.  Asigna el capital de forma inteligente. NO pongas todo en una sola, pero tampoco diluyas demasiado.
    5.  Si un activo dice "ESPERAR", puedes asignar capital pero con la instrucción de "Reservar para comprar en X días".
    
    ### FORMATO DE REPORTE FINAL:
    
    # 🏛️ REPORTE DE ESTRATEGIA DE INVERSIÓN
    
    ## 1. RESUMEN EJECUTIVO
    *   **Sentimiento General del Portafolio**: [Alcista/Bajista/Mixto]
    *   **Mejor Oportunidad Hoy**: [Ticker]
    
    ## 2. ANÁLISIS INDIVIDUAL DETALLADO
    (Aquí resume brevemente lo más importante de cada reporte individual que recibiste, conservando el consejo de timing)
    
    *   **[TICKER]**: [Veredicto del Analista] -> [Instrucción de Timing: Ej. "Esperar 3 días"]
    *   ...
    
    ## 3. ASIGNACIÓN DE CAPITAL (${capital_amount})
    
    | Activo | Acción | Monto ($) | Instrucción Precisa |
    | :--- | :--- | :--- | :--- |
    | **AAPL** | COMPRAR | $100 | Entrar a mercado ahora. |
    | **TSLA** | ESPERAR | $50 | Reservar. Esperar 3 días a rebote en $200. |
    | **CASH** | MANTENER | $150 | No hay suficientes oportunidades claras hoy. |
    
    ## 4. PLAN DE ACCIÓN PARA LA SEMANA
    *   [Instrucciones finales para el inversor sobre qué monitorear]
    """
    
    boss_user_prompt = f"""
    Aquí están los reportes de tus analistas:
    
    {all_reports_text}
    
    DECIDE LA ASIGNACIÓN AHORA.
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": boss_system_prompt},
                {"role": "user", "content": boss_user_prompt}
            ],
            reasoning_effort=reasoning_effort if model == "gpt-5.1" else None
        )
        
        final_verdict = response.choices[0].message.content
        
        # Metrics Finales
        end_time = time.time()
        total_tokens += response.usage.total_tokens
        
        metrics = {
            "execution_time": end_time - start_time,
            "token_usage": {
                "total_tokens": total_tokens,
                "prompt_tokens": response.usage.prompt_tokens, # Solo del último call
                "completion_tokens": response.usage.completion_tokens # Solo del último call
            }
        }
        
        # --- Generación de Excel para Debugging ---
        filename = f"analysis_debug_{timestamp}.xlsx"
        
        # Sheet 1: Resumen
        df_resumen = pd.DataFrame({
            'Timestamp': [timestamp],
            'Capital': [capital_amount],
            'Modelo': [model]
        })
        
        # Sheet 2: Reportes Individuales (Raw Text)
        df_individual = pd.DataFrame({
            'Ticker': list(tickers_data.keys()),
            'Reporte_Analista': [r for r in individual_reports] # Simplificado, asumiendo orden
        })
        
        # Sheet 3: Respuesta Final
        df_response = pd.DataFrame({
            'Final_Verdict': [final_verdict]
        })
        
        # Sheet 4: Technical Data (Restored for App compatibility)
        tech_rows = []
        for t, d in tickers_data.items():
            dy = d.get('daily', {})
            tech_rows.append({
                'Ticker': t,
                'Price': dy.get('price'),
                'RSI': dy.get('rsi'),
                'ADX': dy.get('adx'),
                'Trend': dy.get('trend'),
                'EMA_200': dy.get('ema_200')
            })
        df_technical = pd.DataFrame(tech_rows)
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
            df_individual.to_excel(writer, sheet_name='Individual_Reports', index=False)
            df_response.to_excel(writer, sheet_name='Final_Verdict', index=False)
            df_technical.to_excel(writer, sheet_name='Technical_Data', index=False)
        print(Fore.RED + f"ERROR en recommend_capital_distribution: {e}")
        return f"Error: {str(e)}", None, None