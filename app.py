import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Rastreador de Tendências", layout="wide")
st.title("📈 Painel Avançado de Tendências e Divergências")

TOP_10_TICKERS = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'MGLU3.SA', 'WEGE3.SA', 'B3SA3.SA', 'GGBR4.SA', 'HAPV3.SA']

st.sidebar.header("⚙️ Painel de Controle")
modo = st.sidebar.radio("Selecione o Modo:", options=["Ação Individual", "Top 10 Maiores Volumes"])
periodo = st.sidebar.selectbox("Tempo Gráfico Principal:", options=['15m', '60m', '1d'], index=2)

intervalos_validos = {'15m': '15m', '60m': '1h', '1d': '1d'}
intervalo_yf = intervalos_validos[periodo]

# Removi o cache para obrigar o sistema a procurar o MTF em tempo real sempre
def carregar_mtf_unico(ticker):
    """Lê os 4 tempos gráficos de um ativo e devolve as 4 setas de tendência"""
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
    if ticker_df.empty or len(ticker_df) < 25: return None
    df_dados = ticker_df.copy()
    if isinstance(df_dados.columns, pd.MultiIndex):
        df_dados.columns = df_dados.columns.get_level_values(0)
    
    df_dados.ta.adx(length=14, append=True)
    df_dados.ta.rsi(length=14, append=True)
    df_dados.ta.ema(length=9, append=True)
    df_dados.ta.ema(length=20, append=True)
    
    atual = df_dados.iloc[-1]
    anterior = df_dados.iloc[-2]
    
    adx_col = [col for col in df_dados.columns if col.startswith('ADX')][0]
    rsi_col = [col for col in df_dados.columns if col.startswith('RSI')][0]
    
    fechamento = float(atual['Close'])
    adx_atual = float(atual[adx_col])
    rsi_atual = float(atual[rsi_col])
    
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
        "Força (ADX)": forca,
        "IFR": round(rsi_atual, 1),
        "Divergência": sinal_divergencia
    }

# --- FLUXO PRINCIPAL ---
if modo == "Ação Individual":
    st.subheader("🔍 Análise de Ativo Específico")
    ticker_input = st.text_input("Digite o ticker do ativo (ex: PETR4):", value="PETR4").upper()
    
    if st.button("Executar Análise Individual"):
        ticker_busca = ticker_input if ticker_input.endswith(".SA") else f"{ticker_input}.SA"
        with st.spinner("Processando blocos MTF e estruturas..."):
            dados = yf.download(ticker_busca, period="60d", interval=intervalo_yf, progress=False)
            if not dados.empty:
                resumo = processar_indicadores(dados)
                mtf_sinal = carregar_mtf_unico(ticker_busca)
                
                st.divider()
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Preço", f"R$ {resumo['Preço']:.2f}")
                c2.metric("Tendência", resumo['Tendência'])
                c3.metric("MTF (30m | 60m | 1D | 1S)", mtf_sinal)
                c4.metric("Força (ADX)", resumo['Força (ADX)'])
                c5.metric("IFR", resumo['IFR'])
                
                st.info(f"Diagnóstico Estrutural: {resumo['Divergência']}")

else:
    st.subheader("📊 Top 10 B3: Alinhamento de Múltiplos Tempos Gráficos")
    if st.button("Atualizar Grade de Mercado"):
        # Mensagem de espera, pois ler 10 ações em 4 tempos leva cerca de 10-15 segundos
        with st.spinner("A rastrear 10 ativos em 4 tempos gráficos. Isso leva alguns segundos..."):
            linhas = []
            dados_lote = yf.download(TOP_10_TICKERS, period="60d", interval=intervalo_yf, group_by="ticker", progress=False)
            
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
                # Ordenação rígida forçada aqui:
                df_final = df_final[["Ativo", "Preço", "Tendência", "MTF (30m | 60m | 1D | 1S)", "Força (ADX)", "IFR", "Divergência"]]
                st.dataframe(df_final, use_container_width=True, hide_index=True)
