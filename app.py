import streamlit as st
import pandas as pd
from data_loader import get_market_data, get_multi_timeframe_data
from agent_logic import analyze_stock, recommend_capital_distribution
from colorama import Fore, Style, init
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

init(autoreset=True)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    layout="wide", 
    page_title="AI Finance Agent | Pro Terminal", 
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS (DARK PRO THEME) ---
st.markdown("""
<style>
    /* Fondo general y fuentes */
    .stApp {
        background-color: #0e1117;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Tarjetas de Métricas */
    div[data-testid="stMetric"] {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #00cc66;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        border-left-color: #00ff88;
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 255, 136, 0.1);
    }
    div[data-testid="stMetric"] label {
        font-size: 1.1rem !important;
        color: #8b949e !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #e6e6e6 !important;
    }
    
    /* Botones */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #238636 0%, #2ea043 100%);
        color: white;
        border: none;
        padding: 15px;
        font-weight: 600;
        font-size: 1.1rem;
        border-radius: 8px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(46, 160, 67, 0.4);
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #2ea043 0%, #3fb950 100%);
        box-shadow: 0 6px 18px rgba(46, 160, 67, 0.6);
        transform: scale(1.02);
    }

    /* Títulos y Headers */
    h1 {
        color: #e6e6e6;
        font-weight: 800;
        font-size: 3rem !important;
        letter-spacing: -1px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    h2, h3 {
        color: #c9d1d9;
        font-weight: 600;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        white-space: pre-wrap;
        background-color: #21262d;
        border-radius: 8px;
        padding: 10px 25px;
        color: #8b949e;
        font-weight: 500;
        border: 1px solid #30363d;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #30363d;
        color: #c9d1d9;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #238636;
        color: white;
        border-color: #2ea043;
        box-shadow: 0 4px 12px rgba(35, 134, 54, 0.3);
    }
    
    /* Status Container */
    .stStatus {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

def create_dashboard(df, ticker):
    """Crea un gráfico interactivo profesional con Plotly"""
    # Create copy to avoid mutating original data
    df = df.copy()
    
    # Aumentamos filas para nuevos indicadores
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        row_heights=[0.5, 0.15, 0.15, 0.2],
                        subplot_titles=(f'📊 Precio y Señales: {ticker}', '⚡ RSI (Momentum)', '🌊 Stochastic (Ciclos)', '📉 MACD & ADX (Tendencia)'))

    # --- PANEL 1: Candlestick y Bollinger ---
    # Velas
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'],
                                 name='Precio'), row=1, col=1)
    
    # Bandas de Bollinger
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='rgba(0, 255, 255, 0.3)', width=1), name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='rgba(0, 255, 255, 0.3)', width=1), name='BB Lower', fill='tonexty', fillcolor='rgba(0, 255, 255, 0.05)'), row=1, col=1)
    
    # EMAs
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='#ffaa00', width=1.5), name='EMA 50 (Medio Plazo)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='#ff3333', width=2.5), name='EMA 200 (Tendencia Mayor)'), row=1, col=1)

    # --- ESTRATEGIA "GOLDEN TREND MOMENTUM" ---
    # 1. Tendencia: Precio > EMA 200 (Alcista) / Precio < EMA 200 (Bajista)
    # 2. Momentum: Cruce de MACD
    # 3. Filtro: RSI no extremo
    
    # Detectar cruces de MACD
    df['MACD_Cross_Up'] = (df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1))
    df['MACD_Cross_Down'] = (df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1))
    
    # Señales de Compra (Trend Following)
    buy_signals = df[
        (df['Close'] > df['EMA_200']) &      # Tendencia Alcista
        (df['MACD_Cross_Up']) &              # Momentum Positivo
        (df['RSI'] < 70)                     # No sobrecomprado
    ]
    
    # Señales de Venta (Trend Following)
    sell_signals = df[
        (df['Close'] < df['EMA_200']) &      # Tendencia Bajista
        (df['MACD_Cross_Down']) &            # Momentum Negativo
        (df['RSI'] > 30)                     # No sobrevendido
    ]

    fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close']*0.98, mode='markers', 
                             marker=dict(symbol='triangle-up', size=16, color='#00ff00', line=dict(width=2, color='black')), name='🟢 BUY SIGNAL'), row=1, col=1)
    fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close']*1.02, mode='markers', 
                             marker=dict(symbol='triangle-down', size=16, color='#ff0000', line=dict(width=2, color='black')), name='🔴 SELL SIGNAL'), row=1, col=1)

    # --- PANEL 2: RSI ---
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#d2a8ff', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ff5555", row=2, col=1, annotation_text="Sobrecompra", annotation_position="top left")
    fig.add_hline(y=30, line_dash="dot", line_color="#55ff55", row=2, col=1, annotation_text="Sobreventa", annotation_position="bottom left")
    fig.add_shape(type="rect", x0=df.index[0], x1=df.index[-1], y0=30, y1=70, fillcolor="rgba(128, 128, 128, 0.1)", layer="below", line_width=0, row=2, col=1)

    # --- PANEL 3: Stochastic ---
    fig.add_trace(go.Scatter(x=df.index, y=df['Stoch_K'], line=dict(color='#58a6ff', width=1.5), name='Stoch %K'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Stoch_D'], line=dict(color='#ffa657', width=1.5, dash='dot'), name='Stoch %D'), row=3, col=1)
    fig.add_hline(y=80, line_dash="dot", line_color="#ff5555", row=3, col=1)
    fig.add_hline(y=20, line_dash="dot", line_color="#55ff55", row=3, col=1)
    fig.add_shape(type="rect", x0=df.index[0], x1=df.index[-1], y0=20, y1=80, fillcolor="rgba(128, 128, 128, 0.1)", layer="below", line_width=0, row=3, col=1)

    # --- PANEL 4: MACD & ADX ---
    # Usamos colores condicionales para el histograma
    colors = ['#238636' if v >= 0 else '#da3633' for v in df['MACD_Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=colors, name='MACD Hist'), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#58a6ff', width=1.5), name='MACD Line'), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='#ffa657', width=1.5), name='Signal Line'), row=4, col=1)
    
    # Layout Profesional
    fig.update_layout(
        height=1000, 
        xaxis_rangeslider_visible=False, 
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22, 27, 34, 0.5)',
        font=dict(family="Segoe UI, sans-serif", size=13, color="#c9d1d9"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    # Eliminar gridlines molestos pero mantener guías
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(48, 54, 61, 0.5)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(48, 54, 61, 0.5)')
    
    return fig

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_market_data(ticker):
    """Cached wrapper around get_multi_timeframe_data"""
    return get_multi_timeframe_data(ticker)

def main():
    # Header Principal
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        st.markdown("<div style='font-size: 4rem; text-align: center;'>🤖</div>", unsafe_allow_html=True)
    with col_title:
        st.title("AI Finance Agent v5.0")
        st.markdown("<h4 style='color: #00cc66;'>🚀 Advanced Technical Analysis & Portfolio Intelligence</h4>", unsafe_allow_html=True)
    
    st.divider()

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Panel de Control")
        ticker = st.text_input("Ticker Symbol", value="SPY", help="Ej: AAPL, BTC-USD, NVDA").upper()
        
        # Selector de Timeframe (Visual only now, as logic uses both)
        chart_interval = st.selectbox("Timeframe Gráfico", ["1d", "1wk", "1mo"], index=0)

        st.markdown("---")
        st.markdown("### 🧠 Configuración AI")
        model_info = st.selectbox("Modelo AI", ["GPT-5.1 (Latest)", "GPT-4o (Legacy)"], index=0)
        
        # Reasoning Effort Selector (Only for GPT-5.1)
        reasoning_effort = "none"
        if "GPT-5.1" in model_info:
            reasoning_effort = st.select_slider(
                "Esfuerzo de Razonamiento", 
                options=["none", "low", "medium", "high"], 
                value="none",
                help="None: Más rápido (Default) | High: Mayor profundidad de pensamiento"
            )
            

        
        st.markdown("---")
        analyze_btn = st.button("🚀 EJECUTAR ANÁLISIS", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 💰 Distribución de Capital")
        capital_amount = st.number_input("Monto a Invertir ($)", min_value=10.0, value=300.0, step=10.0, help="Ingresa cuánto dinero quieres invertir")
        
        # Tus acciones del portafolio (siempre incluidas)
        portfolio_tickers = ["AAPL", "NVDA", "TSLA", "BABA", "INTC", "MELI", "KO", "AMD", "NFLX"]
        
        st.caption(f"📊 Tu Portfolio: {', '.join(portfolio_tickers)}")
        
        # Campo opcional para agregar más tickers
        additional_tickers_input = st.text_input(
            "Agregar Tickers Adicionales (opcional)", 
            placeholder="Ej: MSFT, GOOGL, SPY",
            help="Separa los tickers con comas si quieres analizar activos adicionales"
        )
        
        # Combinar tickers
        if additional_tickers_input.strip():
            additional_tickers = [t.strip().upper() for t in additional_tickers_input.split(",") if t.strip()]
            selected_tickers = portfolio_tickers + additional_tickers
            st.caption(f"➕ Adicionales: {', '.join(additional_tickers)}")
        else:
            selected_tickers = portfolio_tickers
        
        distribute_btn = st.button("💡 RECOMENDAR DISTRIBUCIÓN", use_container_width=True)
        
        st.markdown("---")
        st.caption(f"Status: Online | Model: {model_info}")

    if analyze_btn:
        print(Fore.GREEN + Style.BRIGHT + f"\n=== 🚀 NUEVO ANÁLISIS SOLICITADO: {ticker} ===")
        
        # Container de Status Interactivo
        with st.status("🚀 Iniciando secuencia de análisis...", expanded=True) as status:
            
            try:
                status.write("📡 **Paso 1/3: Conectando con mercados (Semanal + Diario)...**")
                # 1. Obtener Datos Multi-Timeframe
                data_bundle, error = get_cached_market_data(ticker)
                
                if error:
                    status.update(label="❌ Error en la obtención de datos", state="error")
                    st.error(f"**Error Crítico**: {error}")
                    st.info("💡 **Sugerencias**: Verifica el ticker, tu conexión a internet, o prueba otro símbolo.")
                    return
                
                # Extract data for UI
                llm_data = data_bundle # Pass the whole bundle to LLM
                hist_data = data_bundle['daily_hist'] if chart_interval == '1d' else data_bundle['weekly_hist']
                raw_news = data_bundle['news']
                
                # Display key metrics from Daily data
                daily_price = data_bundle['daily'].get('price')
                daily_trend = data_bundle['daily'].get('trend')
                
                status.write(f"✅ Datos recibidos: Precio ${daily_price} | Tendencia {daily_trend}")
                
                # Map UI model names to actual API model names
                model_map = {
                    "GPT-5.1 (Latest)": "gpt-5.1",  # GPT-4o is the latest available
                    "GPT-4o (Legacy)": "gpt-4o"  # Use mini for legacy
                }
                selected_model = model_map.get(model_info, "gpt-5.1")
                
                status.write(f"🧠 **Paso 2/3: Analizando con {model_info}...**")
                
                # 2. Ejecutar Agente con modelo seleccionado
                analysis, metrics = analyze_stock(ticker, llm_data, model=selected_model, reasoning_effort=reasoning_effort)

                status.write("✅ Análisis de inteligencia generado.")
                status.update(label="✨ ¡Análisis Completado Exitosamente!", state="complete", expanded=False)

            except Exception as e:
                status.update(label="❌ Error Inesperado", state="error")
                st.error(f"Ocurrió un error: {e}")
                print(Fore.RED + f"ERROR: {e}")
                return

        # 3. Mostrar Resultados
        
        # KPIs Principales en Grid
        st.markdown("### 📊 Market Snapshot")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        last_price = llm_data['daily'].get('price')
        trend = llm_data['daily'].get('trend')
        rsi = llm_data['daily'].get('rsi')
        adx = llm_data['daily'].get('adx')
        
        # Determine metric color based on trend classification
        trend_color = "normal" if "Alcista" in trend else "inverse" if "Bajista" in trend else "off"
        
        kpi1.metric("Precio Actual", f"${last_price}", delta=f"{hist_data['Close'].diff().iloc[-1]:.2f}")
        kpi2.metric("Tendencia", trend, delta_color=trend_color, 
                   help=f"ADX: {adx} - {'✅ Tendencia fuerte' if adx > 25 else '⚠️ Tendencia débil' if adx > 20 else '❌ Mercado lateral (evitar seguir tendencia)'}")
        kpi3.metric("RSI (14)", rsi, delta="Sobrecompra" if rsi>70 else "Sobreventa" if rsi<30 else "Neutral", delta_color="off")
        kpi4.metric("ADX (Fuerza)", f"{adx}", help="ADX > 25 indica tendencia fuerte.")

        # Check for stale data
        last_updated_str = llm_data['daily'].get('last_updated', '')
        if last_updated_str:
            try:
                last_updated = datetime.strptime(last_updated_str, '%Y-%m-%d').date()
                today = datetime.now().date()
                
                if last_updated < today:
                    days_old = (today - last_updated).days
                    st.warning(f"⚠️ **Datos desactualizados**: Última actualización {last_updated_str} ({days_old} día(s) atrás). Los mercados pueden estar cerrados.")
            except ValueError:
                pass  # Skip if date parsing fails

        st.markdown("---")

        # Pestañas
        tab1, tab2, tab3 = st.tabs(["📈 GRÁFICO TÉCNICO", "🧠 ANÁLISIS INTELIGENTE", "📰 NOTICIAS EN TIEMPO REAL"])

        with tab1:
            st.plotly_chart(create_dashboard(hist_data, ticker), use_container_width=True)

        with tab2:
            st.markdown(f"""
            <div style="background-color: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
                <h3 style="margin-top: 0; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px;">📝 Reporte de Inteligencia: {ticker}</h3>
                <div style="font-size: 1.05em; line-height: 1.6; color: #c9d1d9;">
                    {analysis}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if metrics:
                st.caption(f"⏱️ Tiempo: {metrics['execution_time']:.2f}s | 🪙 Tokens: {metrics['token_usage']['total_tokens']} (Prompt: {metrics['token_usage']['prompt_tokens']}, Compl: {metrics['token_usage']['completion_tokens']})")
            
        with tab3:
            st.subheader("Últimas Noticias")
            if raw_news:
                for news in raw_news:
                    st.markdown(f"""
                    <div style="padding: 10px; border-bottom: 1px solid #333;">
                        <small style="color: #00cc66;">{news.get('published', 'Reciente')} | {news.get('source', 'Desconocido')}</small><br>
                        <a href="{news.get('link', '#')}" target="_blank" style="color: #e6e6e6; text-decoration: none; font-weight: bold; font-size: 1.1em;">{news.get('title', 'Sin Título')}</a>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No se encontraron noticias recientes.")
            
            with st.expander("Ver Datos Crudos (OHLCV)"):
                st.dataframe(hist_data.tail(20), width="stretch")
    
    # === NUEVA FUNCIONALIDAD: DISTRIBUCIÓN DE CAPITAL ===
    if distribute_btn:
        if not selected_tickers:
            st.error("⚠️ Debes seleccionar al menos un ticker para analizar.")
        else:
            print(Fore.CYAN + Style.BRIGHT + f"\n=== 💰 DISTRIBUCIÓN DE CAPITAL: ${capital_amount} entre {len(selected_tickers)} activos ===")
            
            with st.status(f"💰 Analizando distribución de ${capital_amount}...", expanded=True) as status:
                try:
                    status.write(f"📊 **Paso 1/3: Obteniendo datos de {len(selected_tickers)} activos...**")
                    
                    # Obtener datos de cada ticker
                    tickers_data = {}
                    failed_tickers = []
                    
                    for ticker_symbol in selected_tickers:
                        print(Fore.YELLOW + f"   [Debug] Procesando {ticker_symbol}...")
                        status.write(f"🔄 Procesando {ticker_symbol}...")
                        try:
                            # Use get_cached_market_data which now returns multi-timeframe bundle
                            data_bundle, error = get_cached_market_data(ticker_symbol)
                            
                            if error:
                                status.write(f"⚠️ Error obteniendo datos de {ticker_symbol}: {error}")
                                failed_tickers.append(ticker_symbol)
                            else:
                                tickers_data[ticker_symbol] = data_bundle
                                status.write(f"✅ {ticker_symbol}: ${data_bundle['daily'].get('price')} | Tendencia: {data_bundle['daily'].get('trend')}")
                        except Exception as e:
                            print(Fore.RED + f"   [Debug] Excepción en {ticker_symbol}: {str(e)}")
                            status.write(f"❌ Error con {ticker_symbol}: {str(e)}")
                            failed_tickers.append(ticker_symbol)
                    
                    if not tickers_data:
                        status.update(label="❌ No se pudo obtener datos de ningún ticker", state="error")
                        st.error("No se pudo obtener datos de mercado. Intenta con otros tickers.")
                        return
                    
                    if failed_tickers:
                        st.warning(f"⚠️ No se pudieron analizar: {', '.join(failed_tickers)}")
                    
                    # Map UI model names to actual API model names
                    model_map = {
                        "GPT-5.1 (Latest)": "gpt-5.1",
                        "GPT-4o (Legacy)": "gpt-4o"
                    }
                    selected_model = model_map.get(model_info, "gpt-5.1")
                    
                    status.write(f"🧠 **Paso 2/3: Invocando AI Portfolio Manager ({model_info})...**")
                    
                    # Generar recomendación
                    recommendation, excel_data, metrics = recommend_capital_distribution(
                        capital_amount=capital_amount,
                        tickers_data=tickers_data,
                        model=selected_model,
                        reasoning_effort=reasoning_effort
                    )
                    
                    status.write("✅ Recomendación generada.")
                    status.update(label="✨ ¡Distribución Completada!", state="complete", expanded=False)
                    
                except Exception as e:
                    status.update(label="❌ Error Inesperado", state="error")
                    st.error(f"Ocurrió un error: {e}")
                    print(Fore.RED + f"ERROR: {e}")
                    return
            
            # Mostrar resultados de distribución
            st.markdown("---")
            st.markdown(f"### 💰 Recomendación de Distribución para ${capital_amount}")
            
            st.markdown(f"""
            <div style="background-color: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
                <h3 style="margin-top: 0; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px;">📊 Análisis de Portfolio</h3>
                <div style="font-size: 1.05em; line-height: 1.6; color: #c9d1d9;">
                    {recommendation}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if metrics:
                st.caption(f"⏱️ Tiempo: {metrics['execution_time']:.2f}s | 🪙 Tokens: {metrics['token_usage']['total_tokens']} (Prompt: {metrics['token_usage']['prompt_tokens']}, Compl: {metrics['token_usage']['completion_tokens']})")
            
            # Mostrar resumen de señales técnicas
            with st.expander("🔍 Ver Detalles Técnicos de Cada Activo"):
                cols = st.columns(min(len(tickers_data), 3))
                for idx, (ticker_symbol, data) in enumerate(tickers_data.items()):
                    with cols[idx % 3]:
                        st.markdown(f"**{ticker_symbol}**")
                        st.metric("Precio", f"${data['daily'].get('price')}")
                        st.caption(f"Tendencia: {data['daily'].get('trend')}")
                        st.caption(f"RSI: {data['daily'].get('rsi')} | ADX: {data['daily'].get('adx')}")
                        st.caption(f"MACD: {data['daily'].get('macd_hist')}")
            
            # === NUEVA SECCIÓN: VISUALIZACIÓN DEL EXCEL EN STREAMLIT ===
            if excel_data:
                st.markdown("---")
                st.markdown("### 📊 Datos de Debugging (Excel)")
                
                # Botón de descarga del Excel
                try:
                    with open(excel_data['filename'], 'rb') as f:
                        excel_bytes = f.read()
                    st.download_button(
                        label="📥 Descargar Excel Completo",
                        data=excel_bytes,
                        file_name=excel_data['filename'],
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Descarga el análisis completo en formato Excel"
                    )
                except Exception as e:
                    st.warning(f"No se pudo preparar el archivo para descarga: {e}")
                
                # Tabs para mostrar cada hoja del Excel
                tab_debug1, tab_debug2, tab_debug3, tab_debug4, tab_debug5 = st.tabs([
                    "📋 Resumen", 
                    "📊 Datos Técnicos", 
                    "📰 Noticias", 
                    "💬 Prompt Enviado", 
                    "🤖 Respuesta LLM"
                ])
                
                with tab_debug1:
                    st.subheader("Resumen del Análisis")
                    st.dataframe(excel_data['df_resumen'], width="stretch", hide_index=True)
                
                with tab_debug2:
                    st.subheader("Indicadores Técnicos Completos")
                    st.dataframe(excel_data['df_technical'], width="stretch", hide_index=True)
                    
                    # Visualización adicional: Comparación de RSI
                    st.markdown("#### Comparación de Indicadores")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.bar_chart(excel_data['df_technical'].set_index('Ticker')['RSI'])
                        st.caption("RSI por Ticker (70+ sobrecompra, 30- sobreventa)")
                    with col2:
                        st.bar_chart(excel_data['df_technical'].set_index('Ticker')['ADX'])
                        st.caption("ADX por Ticker (25+ tendencia fuerte)")
                
                with tab_debug3:
                    st.subheader("Noticias Completas")
                    for idx, row in excel_data['df_news'].iterrows():
                        with st.expander(f"📰 {row['Ticker']}"):
                            st.write(row['Noticias'])
                
                with tab_debug4:
                    st.subheader("Prompt Enviado al LLM")
                    for idx, row in excel_data['df_prompt'].iterrows():
                        st.markdown(f"**{row['Tipo']}:**")
                        st.text_area(
                            label=f"{row['Tipo']}", 
                            value=row['Contenido'], 
                            height=200, 
                            key=f"prompt_{idx}",
                            label_visibility="collapsed"
                        )
                
                with tab_debug5:
                    st.subheader("Respuesta Completa del LLM")
                    st.info(f"**Modelo usado:** {excel_data['df_response'].iloc[0]['Valor']}")
                    st.markdown("**Recomendación:**")
                    st.text_area(
                        label="Respuesta", 
                        value=excel_data['df_response'].iloc[2]['Valor'], 
                        height=300,
                        label_visibility="collapsed"
                    )

if __name__ == "__main__":
    main()
