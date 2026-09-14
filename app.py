import streamlit as st
import requests
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Rastreador de Tendências", layout="wide")
st.title("📈 Painel Avançado: MTF, Ichimoku e Oportunidades")

# O robô agora vai buscar a chave ao cofre fechado do Streamlit (Secrets)
BRAPI_TOKEN = st.secrets["BRAPI_TOKEN"]

# Ativos atualizados com os contratos vigentes do Mini Índice e Mini Dólar
TOP_10_TICKERS = ['WINV26', 'WDOV26', 'PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'MGLU3', 'WEGE3', 'GGBR4']
RADAR_TICKERS = TOP_10_TICKERS + ['ABEV3', 'RENT3', 'EQTL3', 'RADL3', 'SUZB3', 'VIVT3', 'RAIL3', 'CSNA3', 'PRIO3', 'CMIG4']

# --- PAINEL LATERAL ---
st.sidebar.header("⚙️ Painel de Controle")
modo = st.sidebar.radio("Selecione o Modo:", options=[
    "Ação Individual", 
    "Top 10 Maiores Volumes", 
    "Radar de Oportunidades (Pullback)",
    "Radar de Explosão (Fuga M6x16)"
])

# Tempo de 5m adicionado com sucesso. Index=3 mantém o Diário (1d) como padrão inicial
periodo = st.sidebar.selectbox("Tempo Gráfico Principal:", options=['5m', '15m', '60m', '1d', '1wk'], index=3)

# Tradutor de tempos gráficos para a linguagem da Brapi API
intervalos_validos = {'5m': '5m', '15m': '15m', '60m': '1h', '1d': '1d', '1wk': '1wk'}
periodos_download = {'5m': '1mo', '15m': '3mo', '60m': '3mo', '1d': '1y', '1wk': '2y'}

intervalo_api = intervalos_validos[periodo]
periodo_api = periodos_download[periodo]

def baixar_dados_brapi(tickers, range_val, interval_val, token):
    """Novo motor de download focado na API REST da Brapi com Header de Segurança"""
    tickers_str = ",".join(tickers) if isinstance(tickers, list) else tickers
    
    url = f"https://brapi.dev/api/quote/{tickers_str}?range={range_val}&interval={interval_val}"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        resp = requests.get(url, headers=headers)
        data = resp.json()
        dfs = {}
        
        if 'results' in data:
            for result in data['results']:
                symbol = result.get('symbol')
                hist = result.get('historicalDataPrice', [])
                if hist:
                    df = pd.DataFrame(hist)
                    df['Date'] = pd.to_datetime(df['date'], unit='s')
                    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                    df.set_index('Date', inplace=True)
                    dfs[symbol] = df
                    
        if isinstance(tickers, str):
            return list(dfs.values())[0] if dfs else pd.DataFrame()
        return dfs
    except:
        return pd.DataFrame() if isinstance(tickers, str) else {}

def carregar_mtf_unico(ticker, token):
    intervalos = [("1mo", "30m"), ("3mo", "1h"), ("1y", "1d"), ("2y", "1wk")]
    sinais = []
    for p, i in intervalos:
        try:
            df = baixar_dados_brapi(ticker, p, i, token)
            if df.empty or len(df) < 20:
                sinais.append("⚪")
            else:
                ema9 = df['Close'].ewm(span=9, adjust=False).mean()
                ema20 = df['Close'].ewm(span=20, adjust=False).mean()
                sinais.append("🟢" if ema9.iloc[-1] > ema20.iloc[-1] else "🔴")
        except:
            sinais.append("⚪")
    return " ".join(sinais)

def processar_indicadores(ticker_df):
    if ticker_df.empty or len(ticker_df) < 55: 
        return None
    df_dados = ticker_df.copy()
    
    df_dados.ta.adx(length=14, append=True)
    df_dados.ta.rsi(length=14, append=True)
    df_dados.ta.ema(length=9, append=True)
    df_dados.ta.ema(length=20, append=True)
    df_dados.ta.ema(length=6, append=True)
    df_dados.ta.ema(length=16, append=True)
    
    tenkan = (df_dados['High'].rolling(window=9).max() + df_dados['Low'].rolling(window=9).min()) / 2
    kijun = (df_dados['High'].rolling(window=26).max() + df_dados['Low'].rolling(window=26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((df_dados['High'].rolling(window=52).max() + df_dados['Low'].rolling(window=52).min()) / 2).shift(26)
    
    suporte = df_dados['Low'].iloc[-21:-1].min()
    resistencia = df_dados['High'].iloc[-21:-1].max()

    atual = df_dados.iloc[-1]
    anterior = df_dados.iloc[-2]
    
    adx_col = [col for col in df_dados.columns if col.startswith('ADX')][0]
    rsi_col = [col for col in df_dados.columns if col.startswith('RSI')][0]
    
    fechamento = float(atual['Close'])
    adx_atual = float(atual[adx_col])
    rsi_atual = float(atual[rsi_col])
    span_a_atual = float(senkou_a.iloc[-1])
    span_b_atual = float(senkou_b.iloc[-1])
    
    ema6_atual = atual['EMA_6']
    ema16_atual = atual['EMA_16']
    
    sinal_explosao = "Normal"
    if ema6_atual > ema16_atual and atual['Low'] > ema6_atual:
        sinal_explosao = "🚀 Fuga de Alta"
    elif ema6_atual < ema16_atual and atual['High'] < ema6_atual:
        sinal_explosao = "🩸 Queda Livre"
    
    if pd.isna(span_a_atual) or pd.isna(span_b_atual):
        estado_nuvem = "⚪ Sem Histórico"
    else:
        max_nuvem = max(span_a_atual, span_b_atual)
        min_nuvem = min(span_a_atual, span_b_atual)
        if fechamento > max_nuvem:
            estado_nuvem = "🌤️ Acima"
        elif fechamento < min_nuvem:
            estado_nuvem = "⛈️ Abaixo"
        else:
            estado_nuvem = "🌪️ Dentro"

    direcao = "Alta 🟢" if atual['EMA_9'] > atual['EMA_20'] else "Baixa 🔴"
    forca = f"{adx_atual:.1f} (Acelera)" if (adx_atual > 25 and adx_atual > anterior[adx_col]) else f"{adx_atual:.1f} (Perde Força)" if adx_atual > 25 else f"{adx_atual:.1f} (Lateral)"
    
    janela_recente = df_dados.iloc[-10:]
    janela_anterior = df_dados.iloc[-20:-10]
    max_preco_recente = janela_recente['High'].max()
    max_preco_anterior = janela_anterior['High'].max()
    max_rsi_recente = janela_recente[rsi_col].max()
    max_rsi_anterior = janela_anterior[rsi_col].max()
    min_preco_recente = janela_recente['Low'].min()
    min_preco_anterior = janela_anterior['Low'].min()
    min_rsi_recente = janela_recente[rsi_col].min()
    min_rsi_anterior = janela_anterior[rsi_col].min()

    sinal_divergencia = "Normal"
    if direcao.startswith("Alta") and max_preco_recente > max_preco_anterior and max_rsi_recente < max_rsi_anterior:
        sinal_divergencia = "⚠️ Div. Baixa"
    elif direcao.startswith("Baixa") and min_preco_recente < min_preco_anterior and min_rsi_recente > min_rsi_anterior:
        sinal_divergencia = "🚀 Div. Alta"
        
    return {
        "Preço": round(fechamento, 2),
        "Tendência": direcao,
        "MTF": "", 
        "Ichimoku": estado_nuvem,
        "Suporte": round(suporte, 2),
        "Resist.": round(resistencia, 2),
        "Força (ADX)": forca,
        "IFR": round(rsi_atual, 1),
        "Divergência": sinal_divergencia,
        "Sinal Explosão": sinal_explosao 
    }

# --- FLUXO PRINCIPAL ---
if modo == "Ação Individual":
    st.subheader("🔍 Análise de Ativo Específico")
    ticker_input = st.text_input("Digite o ticker (ex: PETR4, WINV26):", value="WINV26").upper()
    
    if st.button("Executar Análise Individual"):
        ticker_busca = ticker_input.replace(".SA", "") # Limpeza de segurança
            
        with st.spinner("Processando nuvens e estruturas institucionais..."):
            df = baixar_dados_brapi(ticker_busca, periodo_api, intervalo_api, BRAPI_TOKEN)
            
            if not df.empty:
                resumo = processar_indicadores(df)
                mtf_sinal = carregar_mtf_unico(ticker_busca, BRAPI_TOKEN)
                
                if resumo:
                    st.divider()
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Preço", f"R$ {resumo['Preço']:.2f}")
                    c2.metric("Nuvem Ichimoku", resumo['Ichimoku'])
                    c3.metric("Suporte", f"R$ {resumo['Suporte']:.2f}")
                    c4.metric("Resistência", f"R$ {resumo['Resist.']:.2f}")
                    
                    c5, c6, c7, c8 = st.columns(4)
                    c5.metric("Tendência", resumo['Tendência'])
                    c6.metric("MTF (30m | 60m | 1D | 1S)", mtf_sinal)
                    c7.metric("Força (ADX)", resumo['Força (ADX)'])
                    c8.metric("Status M6x16", resumo['Sinal Explosão'])
                    
                    st.info(f"Diagnóstico Estrutural: {resumo['Divergência']}")
                else:
                    st.warning("Dados insuficientes para calcular os indicadores neste tempo gráfico.")
            else:
                st.error("Ativo não encontrado ou erro na chave da API.")

elif modo == "Top 10 Maiores Volumes":
    st.subheader("📊 Top 10 B3: Mapa de Força, Nuvem e Níveis Críticos")
    if st.button("Atualizar Grade de Mercado"):
        with st.spinner("A rastrear fluxos e derivativos. Aguarde..."):
            linhas = []
            dfs = baixar_dados_brapi(TOP_10_TICKERS, periodo_api, intervalo_api, BRAPI_TOKEN)
            
            for t in TOP_10_TICKERS:
                if t in dfs and not dfs[t].empty:
                    res = processar_indicadores(dfs[t])
                    if res:
                        res["Ativo"] = t
                        res["MTF (30m | 60m | 1D | 1S)"] = carregar_mtf_unico(t, BRAPI_TOKEN)
                        linhas.append(res)
            
            if linhas:
                df_final = pd.DataFrame(linhas)
                df_final = df_final[["Ativo", "Preço", "Ichimoku", "Suporte", "Resist.", "Tendência", "MTF (30m | 60m | 1D | 1S)", "Força (ADX)", "IFR", "Divergência"]]
                st.dataframe(df_final, use_container_width=True, hide_index=True)

elif modo == "Radar de Oportunidades (Pullback)":
    st.subheader("🎯 Radar Sniper: Caçador de Pullbacks")
    st.write("Filtro ativo: Tendência de Alta + Preço Acima da Nuvem + IFR Esfriando (< 50).")
    
    if st.button("Rodar Scanner de Oportunidades"):
        with st.spinner(f"A varrer {len(RADAR_TICKERS)} ativos..."):
            linhas_pullback = []
            dfs = baixar_dados_brapi(RADAR_TICKERS, periodo_api, intervalo_api, BRAPI_TOKEN)
            
            for t in RADAR_TICKERS:
                if t in dfs and not dfs[t].empty:
                    res = processar_indicadores(dfs[t])
                    if res and res['Tendência'] == "Alta 🟢" and res['Ichimoku'] == "🌤️ Acima" and res['IFR'] <= 50:
                        res["Ativo"] = t
                        res["MTF (30m | 60m | 1D | 1S)"] = carregar_mtf_unico(t, BRAPI_TOKEN)
                        linhas_pullback.append(res)
            
            if linhas_pullback:
                df_final = pd.DataFrame(linhas_pullback)
                df_final = df_final[["Ativo", "Preço", "Ichimoku", "Suporte", "Resist.", "Tendência", "MTF (30m | 60m | 1D | 1S)", "Força (ADX)", "IFR"]]
                st.success(f"BINGO! {len(linhas_pullback)} ativo(s) alinhado(s) para um possível pullback.")
                st.dataframe(df_final, use_container_width=True, hide_index=True)
            else:
                st.warning("Sem ativos nas condições ideais de Pullback neste momento.")

elif modo == "Radar de Explosão (Fuga M6x16)":
    st.subheader("🚀 Radar de Explosão: Padrão de Fuga (M6 x M16)")
    st.write("Filtro ativo: Identifica ativos onde o preço descolou completamente da Média Móvel de 6 períodos.")
    
    if st.button("Rodar Scanner de Explosão"):
        with st.spinner(f"A analisar a estrutura de {len(RADAR_TICKERS)} ativos..."):
            linhas_explosao = []
            dfs = baixar_dados_brapi(RADAR_TICKERS, periodo_api, intervalo_api, BRAPI_TOKEN)
            
            for t in RADAR_TICKERS:
                if t in dfs and not dfs[t].empty:
                    res = processar_indicadores(dfs[t])
                    if res and res['Sinal Explosão'] in ["🚀 Fuga de Alta", "🩸 Queda Livre"]:
                        res["Ativo"] = t
                        res["MTF (30m | 60m | 1D | 1S)"] = carregar_mtf_unico(t, BRAPI_TOKEN)
                        linhas_explosao.append(res)
            
            if linhas_explosao:
                df_final = pd.DataFrame(linhas_explosao)
                df_final = df_final[["Ativo", "Preço", "Sinal Explosão", "MTF (30m | 60m | 1D | 1S)", "Força (ADX)", "Ichimoku", "Suporte", "Resist."]]
                st.success(f"ALERTA! Detetámos {len(linhas_explosao)} ativo(s) em descolamento absoluto.")
                st.dataframe(df_final, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum ativo apresenta o padrão de Fuga neste momento.")
