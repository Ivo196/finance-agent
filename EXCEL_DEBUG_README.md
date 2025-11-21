# 📊 Sistema de Debugging con Excel - IMPLEMENTADO ✅

## ¿Qué hace?

Cada vez que presionas **"💡 RECOMENDAR DISTRIBUCIÓN"**, automáticamente se genera un archivo Excel con toda la información del análisis.

## Nombre del archivo

```
analysis_debug_2025-11-20_21-08-31.xlsx
```

El nombre incluye fecha y hora exacta del análisis.

## Estructura del Excel (5 hojas)

### 📋 Hoja 1: "Resumen"
Información general del análisis:
- Timestamp del análisis
- Capital a invertir ($300, $500, etc.)
- Modelo AI usado (gpt-5.1, gpt-4o)
- Número de tickers analizados
- Lista de tickers

### 📊 Hoja 2: "Datos_Tecnicos"
**Todos los indicadores técnicos de cada ticker** en formato tabla:

| Ticker | Precio | Tendencia | RSI | MACD | MACD_Signal | MACD_Hist | ADX | ATR | Stoch_K | Stoch_D | OBV | Sector | Last_Updated |
|--------|--------|-----------|-----|------|-------------|-----------|-----|-----|---------|---------|-----|--------|--------------|
| AAPL   | 150.25 | Fuerte Alcista | 68.5 | 2.3 | 1.8 | 0.5 | 32.1 | 3.2 | 75.2 | 72.1 | 1.2M | Technology | 2025-11-20 |
| NVDA   | 485.60 | Alcista Débil  | 55.2 | -0.5 | -0.3 | -0.2 | 22.5 | 8.5 | 52.3 | 50.1 | 850K | Technology | 2025-11-20 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

### 📰 Hoja 3: "Noticias"
**Todas las noticias completas** de cada ticker (sin el límite de 200 caracteres):

| Ticker | Noticias |
|--------|----------|
| AAPL   | "Apple announces new iPhone 16... [texto completo de todas las noticias]" |
| NVDA   | "NVIDIA hits record high on AI demand... [texto completo]" |
| ... | ... |

### 💬 Hoja 4: "Prompt_Enviado"
**El prompt EXACTO que se envía al LLM**:

| Tipo | Contenido |
|------|-----------|
| System Prompt | "Eres un Portfolio Manager Cuantitativo de Élite..." [todo el system prompt] |
| User Prompt | "Tengo $300 para invertir HOY. Analiza estos activos..." [todo el user prompt con todos los datos] |

### 🤖 Hoja 5: "Respuesta_LLM"
**La respuesta completa del AI**:

| Campo | Valor |
|-------|-------|
| Modelo | gpt-5.1 |
| Timestamp | 2025-11-20_21-08-31 |
| Recomendación Completa | "De acuerdo a las señales de HOY, la mejor forma de gastar esos $300 es: $150 en TSLA..." [respuesta completa] |

## Ubicación del archivo

Se guarda en el directorio raíz del proyecto:
```
/Users/ivotonioni/Documents/Ivo/Repositories/ai-finance-agent/analysis_debug_YYYY-MM-DD_HH-MM-SS.xlsx
```

## Mejoras adicionales

También aumenté el límite de noticias de **200 a 500 caracteres** para que el LLM tenga más contexto en el análisis de distribución.

## Cómo usarlo para debugging

1. **Ejecuta un análisis** con distribución de capital
2. **Abre el Excel** generado
3. **Compara**:
   - ¿Qué datos técnicos recibió el LLM? (Hoja 2)
   - ¿Qué noticias vio? (Hoja 3)
   - ¿Qué prompt exacto se envió? (Hoja 4)
   - ¿Qué respondió? (Hoja 5)
4. **Identifica patrones**: Si el LLM no recomienda un ticker que tú esperabas, revisa sus señales técnicas y noticias

## Nota

La exportación es automática pero no bloqueante. Si falla, solo verás un warning amarillo en consola pero el análisis continuará normalmente.
