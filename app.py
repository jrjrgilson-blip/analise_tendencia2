import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Rastreador de Tendências", layout="wide")
st.title("📈 Painel Avançado: MTF, Ichimoku e Oportunidades")

# Listas de Ativos
TOP_10_TICKERS = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'MGLU3.SA', 'WEGE3.SA', 'B3SA3.SA', 'GGBR4.SA', 'HAPV3.SA']
# Lista expandida para o Radar "caçar" oportunidades
RADAR_TICKERS = TOP_10_TICKERS + ['ABEV3.SA', 'RENT3.SA', 'EQTL3.SA', 'RADL3.SA', 'SUZB3.SA', 'VIVT3.SA', 'RAIL3.SA', 'CSNA3.SA', 'PRIO3.SA', 'CMIG4.SA', 'JBSS3.SA', 'ELET3.SA']

# --- PAINEL LATERAL ---
st.sidebar.header("⚙️ Painel de Controle")
modo = st.sidebar.radio("Selecione o Modo:", options=["Ação Individual", "Top 10 Maiores Volumes", "Radar de Oportunidades (Pullback)"])

periodo = st.sidebar.selectbox("Tempo Gráfico Principal:", options=['15m', '60m', '1d', '1wk'], index=2)

intervalos_validos = {'15m': '15m', '60m': '1h', '1d': '1d', '1wk': '1wk'}
intervalo_yf = intervalos_validos[periodo]

periodos_download = {'15m': '60d', '60m': '60d', '1d': '1y', '1wk': '2y'}
periodo_yf = periodos_download[periodo]

def carregar_mtf_unico(ticker):
    intervalos = [("60d", "30m"), ("60d", "60m"), ("6mo", "1d"), ("2y", "1wk")]
    sinais = []
    for p, i in intervalos:
        try:
            df = yf.download(ticker, period=p, interval=i, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if len(df) < 20:
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
    if isinstance(df_dados.columns, pd.MultiIndex):
        df_dados.columns = df_dados.columns.get_level_values(0)
    
    df_dados.ta.adx(length=14, append=True)
    df_dados.ta.rsi(length=14, append=True)
    df_dados.ta.ema(length=9, append=True)
    df_dados.ta.ema(length=20, append=True)
    
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
        "Divergência": sinal_divergencia
    }

# --- FLUXO PRINCIPAL ---
if modo == "Ação Individual":
    st.subheader("🔍 Análise de Ativo Específico")
    ticker_input = st.text_input("Digite o ticker do ativo (ex: PETR4, BOVA11):", value="PETR4").upper()
    
    if st.button("Executar Análise Individual"):
        if ticker_input.startswith("^") or "=" in ticker_input:
            ticker_busca = ticker_input
        else:
            ticker_busca = ticker_input if ticker_input.endswith(".SA") else f"{ticker_input}.SA"
            
        with st.spinner("Processando nuvens, blocos MTF e estruturas..."):
            dados = yf.download(ticker_busca, period=periodo_yf, interval=intervalo_yf, progress=False)
            if not dados.empty:
                resumo = processar_indicadores(dados)
                mtf_sinal = carregar_mtf_unico(ticker_busca)
                
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
                c8.metric("IFR", resumo['IFR'])
                
                st.info(f"Diagnóstico Estrutural: {resumo['Divergência']}")

elif modo == "Top 10 Maiores Volumes":
    st.subheader("📊 Top 10 B3: Mapa de Força, Nuvem e Níveis Críticos")
    if st.button("Atualizar Grade de Mercado"):
        with st.spinner("A rastrear limites de nuvem, suportes e estruturas. Aguarde..."):
            linhas = []
            dados_lote = yf.download(TOP_10_TICKERS, period=periodo_yf, interval=intervalo_yf, group_by="ticker", progress=False)
            
            for t in TOP_10_TICKERS:
                if t in dados_lote.columns.levels[0]:
                    df_t = dados_lote[t].dropna()
                    res = processar_indicadores(df_t)
                    if res:
                        res["Ativo"] = t.replace(".SA", "")
                        res["MTF (30m | 60m | 1D | 1S)"] = carregar_mtf_unico(t)
                        linhas.append(res)
            
            if linhas:
                df_final = pd.DataFrame(linhas)
                df_final = df_final[["Ativo", "Preço", "Ichimoku", "Suporte", "Resist.", "Tendência", "MTF (30m | 60m | 1D | 1S)", "Força (ADX)", "IFR", "Divergência"]]
                st.dataframe(df_final, use_container_width=True, hide_index=True)

elif modo == "Radar de Oportunidades (Pullback)":
    st.subheader("🎯 Radar Sniper: Caçador de Pullbacks")
    st.write("Filtro ativo: Tendência de Alta + Preço Acima da Nuvem + IFR Esfriando (< 50).")
    
    if st.button("Rodar Scanner de Oportunidades"):
        with st.spinner(f"A varrer {len(RADAR_TICKERS)} ativos em busca do setup ideal. Pode demorar uns 20 segundos..."):
            linhas_pullback = []
            dados_lote = yf.download(RADAR_TICKERS, period=periodo_yf, interval=intervalo_yf, group_by="ticker", progress=False)
            
            for t in RADAR_TICKERS:
                if t in dados_lote.columns.levels[0]:
                    df_t = dados_lote[t].dropna()
                    res = processar_indicadores(df_t)
                    if res:
                        # 🚨 A MATEMÁTICA DO PULLBACK ACONTECE AQUI 🚨
                        if res['Tendência'] == "Alta 🟢" and res['Ichimoku'] == "🌤️ Acima" and res['IFR'] <= 50:
                            res["Ativo"] = t.replace(".SA", "")
                            res["MTF (30m | 60m | 1D | 1S)"] = carregar_mtf_unico(t)
                            linhas_pullback.append(res)
            
            if linhas_pullback:
                df_final = pd.DataFrame(linhas_pullback)
                df_final = df_final[["Ativo", "Preço", "Ichimoku", "Suporte", "Resist.", "Tendência", "MTF (30m | 60m | 1D | 1S)", "Força (ADX)", "IFR"]]
                st.success(f"BINGO! Encontrámos {len(linhas_pullback)} ativo(s) alinhado(s) para um possível pullback.")
                st.dataframe(df_final, use_container_width=True, hide_index=True)
            else:
                st.warning("O Radar não encontrou nenhum ativo nas condições ideais de Pullback neste momento. O capital está protegido.")
