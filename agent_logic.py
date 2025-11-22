from openai import OpenAI
import os
from dotenv import load_dotenv
from colorama import Fore, Style, init
import pandas as pd
from datetime import datetime, timedelta
import json
import time
import io
import traceback

init(autoreset=True)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ ERROR: No se encontró la API Key en el archivo .env")

client = OpenAI(api_key=api_key)

def _validate_model_name(model_name):
    """
    Maps UI model names to valid OpenAI API model names.
    """
    model_map = {
        "GPT-5.1 (Latest)": "gpt-5.1",
        "GPT-4o (Legacy)": "gpt-4o",
        "gpt-5.1": "gpt-5.1",
        "gpt-4o": "gpt-4o"
    }
    return model_map.get(model_name, "gpt-5.1")

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
    valid_model = _validate_model_name(model)
    
    # Extract data
    wk_data = data.get('weekly', {})
    dy_data = data.get('daily', {})
    news_data = data.get('news', []) # List of dicts
    
    # Fallback
    if not wk_data and not dy_data:
        dy_data = data
        wk_data = data
        
    # --- NEWS STRATEGY: EARNINGS CYCLE (90 Days vs 5 Days) ---
    catalyst_news = []
    context_news = []
    
    if isinstance(news_data, list):
        today = datetime.now()
        for n in news_data:
            try:
                # Parse date (assuming format YYYY-MM-DD or similar, handled by news agent)
                pub_date_str = n.get('published', '')
                # Simple heuristic: If it says "hours ago" or "days ago" or matches recent date
                # Assuming ISO YYYY-MM-DD for now as per data_loader.
                pub_date = datetime.strptime(pub_date_str[:10], "%Y-%m-%d")
                days_diff = (today - pub_date).days
                
                if days_diff <= 5:
                    catalyst_news.append(n)
                else:
                    context_news.append(n)
            except:
                # If date parsing fails, put in context to be safe unless it looks very recent
                context_news.append(n)
    
    # Format for Prompt
    catalyst_text = ""
    if catalyst_news:
        catalyst_text = "--- ⚡ CATALIZADORES (Últimos 5 días - ACCIÓN INMEDIATA) ---\n"
        for n in catalyst_news:
            catalyst_text += f"- [{n.get('published')}] {n.get('title')} ({n.get('source')})\n"
    else:
        catalyst_text = "No hay noticias de alto impacto en los últimos 5 días.\n"
        
    context_text = ""
    if context_news:
        context_text = "--- 🏗️ CONTEXTO (Últimos 90 días - SUELO FUNDAMENTAL / EARNINGS) ---\n"
        for n in context_news[:15]: # Limit context to top 15 relevant
            context_text += f"- [{n.get('published')}] {n.get('title')} ({n.get('source')})\n"
    else:
        context_text = "No hay noticias de contexto relevante.\n"

    system_prompt = f"""
    Eres un Analista Técnico y Fundamental Senior. Tu trabajo es analizar el activo {ticker} de forma INDIVIDUAL y OBJETIVA.
    
    ### TUS REGLAS DE ORO:
    1.  **NO ASUMAS NADA**: No des por hecho que la tendencia es alcista o bajista solo por el nombre del activo. Mira los datos.
    2.  **ANÁLISIS TÉCNICO PURO**:
        -   Usa los datos SEMANALES para el contexto macro (El Juez).
        -   Usa los datos DIARIOS para el timing preciso (El Francotirador).
        -   Si el precio está lejos de la EMA 200, dilo. Si el RSI está en 80, dilo.
    3.  **ANÁLISIS DE NOTICIAS (ESTRATEGIA EARNINGS CYCLE)**:
        -   **CONTEXTO (90 Días)**: Busca en las noticias antiguas. ¿Cómo fueron los últimos resultados (Earnings)? ¿La empresa crece o decrece? Este es el "Suelo Fundamental".
        -   **CATALIZADOR (5 Días)**: ¿Qué pasó ESTA SEMANA? ¿Hay algo que mueva el precio HOY? (Rumores, Upgrades, Datos Macro).
        -   *Diferencia claramente entre el ruido de hoy y la realidad de la empresa.*
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
    
    {catalyst_text}
    
    {context_text}
    
    ### FORMATO DE RESPUESTA (MARKDOWN):
    
    ### 🔎 Intelligence Report: {ticker}
    
    #### 1. Technical Diagnosis
    *   **Weekly (Macro)**: [Objective analysis. Bullish/Bearish/Neutral? Why?]
    *   **Daily (Timing)**: [Entry analysis. Cheap or Expensive today? RSI status?]
    
    #### 2. Fundamental & News Analysis
    *   **Fundamental Floor (90d Context)**: [Earnings/Growth trajectory?]
    *   **Immediate Catalyst (5d)**: [Any news driving price TODAY?]
    
    #### 3. Strategic Verdict
    *   **Action**: [BUY / SELL / HOLD]
    *   **Timing Instruction**: [e.g., "Buy NOW", "Wait 3 days", "Wait for $XXX"]
    *   **Rationale**: [One sentence justification]
    """

    try:
        # Prepare arguments
        kwargs = {
            "model": valid_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analiza {ticker} ahora."}
            ]
        }
        
        # GPT-5.1 supports reasoning_effort
        if valid_model == "gpt-5.1":
            kwargs["reasoning_effort"] = reasoning_effort

        response = client.chat.completions.create(**kwargs)
        
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
        traceback.print_exc()
        return f"❌ Error analizando {ticker}: {str(e)}", None

def recommend_capital_distribution(capital_amount, tickers_data, model="gpt-5.1", reasoning_effort="none", progress_callback=None):
    """
    Genera una recomendación de distribución de capital basada en análisis individuales profundos.
    """
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    valid_model = _validate_model_name(model)
    
    msg = f"🚀 Iniciando Análisis Profundo de {len(tickers_data)} activos..."
    print(Fore.CYAN + f"\n{msg}")
    if progress_callback: progress_callback(msg)
    
    # --- FASE 1: ANÁLISIS INDIVIDUAL (Iterativo) ---
    individual_reports = []
    total_tokens = 0
    
    # Prompt acumulativo para el debug
    debug_prompts = []
    
    for ticker, data in tickers_data.items():
        msg = f"   [Agent] Analizando {ticker} individualmente..."
        print(Fore.YELLOW + msg)
        if progress_callback: progress_callback(f"🕵️ Analizando {ticker}...")
        
        report, metrics = analyze_individual_stock_deeply(ticker, data, model, reasoning_effort)
        
        if metrics:
            total_tokens += metrics['token_usage']['total_tokens']
            
        individual_reports.append(f"---\n{report}\n---")
        debug_prompts.append(f"ANÁLISIS {ticker}:\n{report}")

    # --- FASE 2: EL JEFE (Asignación de Capital) ---
    msg = "   [Agent] Generando decisión final de asignación (El Jefe)..."
    print(Fore.CYAN + msg)
    if progress_callback: progress_callback("🧠 El Jefe está decidiendo la asignación de capital...")
    
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
    
    ## 🏛️ Investment Strategy Report
    
    ### 1. Executive Summary
    *   **Portfolio Sentiment**: [Bullish/Bearish/Mixed]
    *   **Top Pick Today**: [Ticker]
    
    ### 2. Asset Analysis Breakdown
    (Briefly summarize key points from individual reports, keeping timing advice)
    
    *   **[TICKER]**: [Verdict] -> [Timing Instruction]
    *   ...
    
    ### 3. Capital Allocation Strategy (${capital_amount})
    
    | Asset | Action | Amount ($) | Precise Instruction |
    | :--- | :--- | :--- | :--- |
    | **AAPL** | BUY | $100 | Enter market now. |
    | **TSLA** | HOLD | $50 | Reserve. Wait 3 days for bounce at $200. |
    | **CASH** | KEEP | $150 | Insufficient opportunities today. |
    
    ### 4. Weekly Action Plan
    *   [Final instructions for the investor]
    """
    
    boss_user_prompt = f"""
    Aquí están los reportes de tus analistas:
    
    {all_reports_text}
    
    DECIDE LA ASIGNACIÓN AHORA.
    """
    
    try:
        # Prepare arguments for Boss
        kwargs = {
            "model": valid_model,
            "messages": [
                {"role": "system", "content": boss_system_prompt},
                {"role": "user", "content": boss_user_prompt}
            ]
        }
        
        if valid_model == "gpt-5.1":
            kwargs["reasoning_effort"] = reasoning_effort

        response = client.chat.completions.create(**kwargs)
        
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
        
        # --- Generación de Excel para Debugging (IN MEMORY) ---
        filename = f"analysis_debug_{timestamp}.xlsx"
        output = io.BytesIO()
        
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
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
            df_individual.to_excel(writer, sheet_name='Individual_Reports', index=False)
            df_response.to_excel(writer, sheet_name='Final_Verdict', index=False)
            df_technical.to_excel(writer, sheet_name='Technical_Data', index=False)
            
        excel_data = {
            'filename': filename,
            'excel_bytes': output.getvalue(), # Return bytes directly
            'df_resumen': df_resumen,
            'df_technical': df_technical, 
            'df_news': df_individual, # Reusing this slot for reports in the UI
            'df_prompt': pd.DataFrame({'Tipo': ['System Prompt'], 'Contenido': [boss_system_prompt]}),
            'df_response': df_response
        }
        
        return final_verdict, excel_data, metrics

    except Exception as e:
        print(Fore.RED + f"ERROR en recommend_capital_distribution: {e}")
        traceback.print_exc()
        return f"Error: {str(e)}", None, None