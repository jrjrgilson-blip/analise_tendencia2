import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# Configuração da página em modo "wide" para melhor aproveitamento do espaço
st.set_page_config(page_title="Rastreador de Tendências", layout="wide")

st.title("📈 Painel Avançado de Tendências e Divergências")

# 1. DEFINIÇÃO DAS 10 AÇÕES DE MAIOR LIQUIDEZ/VOLUME DA B3
TOP_10_TICKERS = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 
    'MGLU3.SA', 'WEGE3.SA', 'B3SA3.SA', 'GGBR4.SA', 'HAPV3.SA'
]

# --- PAINEL LATERAL DE CONFIGURAÇÕES (SIDEBAR) ---
st.sidebar.header("⚙️ Painel de Controle")
modo = st.sidebar.radio("Selecione o Modo de Análise:", options=["Ação Individual", "Top 10 Maiores Volumes"])
periodo = st.sidebar.selectbox("Tempo Gráfico:", options=['15m', '60m', '1d'], index=2)

intervalos_validos = {'15m': '15m', '60m': '1h', '1d': '1d'}
intervalo_yf = intervalos_validos[periodo]

# --- FUNÇÃO DE PROCESSAMENTO TÉCNICO ---
def processar_indicadores(ticker_df):
    """Calcula os indicadores técnicos e retorna um resumo estruturado."""
    if ticker_df.empty or len(ticker_df) < 25:
        return None
        
    # Forçar cópia para evitar avisos de atribuição
    df_dados = ticker_df.copy()
    
    # Cálculo dos Indicadores
    df_dados.ta.adx(length=14, append=True)
    df_dados.ta.rsi(length=14, append=True)
    df_dados.ta.ema(length=9, append=True)
    df_dados.ta.ema(length=20, append=True)
    
    atual = df_dados.iloc[-1]
    anterior = df_dados.iloc[-2]
    
    # Identificar colunas dinamicamente
    adx_col = [col for col in df_dados.columns if col.startswith('ADX')][0]
    rsi_col = [col for col in df_dados.columns if col.startswith('RSI')][0]
    
    fechamento = float(atual['Close'])
    adx_atual = float(atual[adx_col])
    rsi_atual = float(atual[rsi_col])
    
    # Direção e Força
    direcao = "Alta 🟢" if atual['EMA_9'] > atual['EMA_20'] else "Baixa 🔴"
    
    if adx_atual > 25:
        forca = f"{adx_atual:.1f} (Acelerando)" if adx_atual > anterior[adx_col] else f"{adx_atual:.1f} (Perdendo Força)"
    else:
        forca = f"{adx_atual:.1f} (Fraca / Lateral)"
        
    # Análise de Divergências (últimos 10 períodos vs anteriores)
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
        sinal_divergencia = "⚠️ Divergência de Baixa"
    elif direcao.startswith("Baixa") and min_preco_recente < min_preco_anterior and min_rsi_recente > min_rsi_anterior:
        sinal_divergencia = "🚀 Divergência de Alta"
        
    return {
        "Preço (R$)": round(fechamento, 2),
        "Tendência": direcao,
        "Força (ADX)": forca,
        "IFR (RSI)": round(rsi_atual, 1),
        "Divergência": sinal_divergencia
    }

# --- FLUXO DE EXECUÇÃO DO APLICATIVO ---

if modo == "Ação Individual":
    st.subheader("🔍 Análise de Ativo Específico")
    # Agora o usuário não precisa digitar o .SA
    ticker_input = st.text_input("Digite o ticker do ativo (ex: PETR4, VALE3):", value="PETR4").upper()
    
    if st.button("Executar Análise Individual"):
        
        # Tratamento inteligente: adiciona o .SA automaticamente se o usuário esquecer
        ticker_busca = ticker_input if ticker_input.endswith(".SA") else f"{ticker_input}.SA"
        
        with st.spinner(f"Processando {ticker_busca}..."):
            try:
                # O download agora usa a variável corrigida
                dados = yf.download(ticker_busca, period="60d", interval=intervalo_yf, progress=False)
                if dados.empty:
                    st.error("Ativo não encontrado. Verifique a grafia.")
                else:
                    resumo = processar_indicadores(dados)
                    if resumo:
                        st.divider()
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Preço Atual", f"R$ {resumo['Preço (R$)']:.2f}")
                        col2.metric("Tendência", resumo['Tendência'])
                        col3.metric("Força (ADX)", resumo['Força (ADX)'])
                        col4.metric("IFR (RSI)", resumo['IFR (RSI)'])
                        
                        st.subheader("Diagnóstico de Estrutura")
                        if "Divergência" in resumo['Divergência']:
                            st.warning(resumo['Divergência'])
                        else:
                            st.info("✅ Estrutura de preço saudável. Sem divergências detectadas no curto prazo.")
            except Exception as e:
                st.error(f"Erro ao processar o ativo: {e}")

else:
    st.subheader("📊 Screening Otimizado: Top 10 Maiores Volumes da B3")
    st.write("Abaixo está o mapa de força consolidado para os ativos mais negociados do mercado.")
    
    if st.button("Atualizar Grade de Mercado"):
        with st.spinner("Baixando dados em lote do mercado..."):
            try:
                # Baixa todos os tickers de uma vez só (muito mais rápido)
                dados_lote = yf.download(TOP_10_TICKERS, period="60d", interval=intervalo_yf, group_by="ticker", progress=False)
                
                linhas_tabela = []
                for t in TOP_10_TICKERS:
                    if t in dados_lote.columns.levels[0]:
                        df_ticker = dados_lote[t].dropna()
                        resumo_ticker = processar_indicadores(df_ticker)
                        if resumo_ticker:
                            resumo_ticker["Ativo"] = t.replace(".SA", "")
                            linhas_tabela.append(resumo_ticker)
                
                # Monta a tabela final formatada
                if linhas_tabela:
                    df_final = pd.DataFrame(linhas_tabela)
                    # Reorganiza as colunas para melhor leitura técnica
                    df_final = df_final[["Ativo", "Preço (R$)", "Tendência", "Força (ADX)", "IFR (RSI)", "Divergência"]]
                    
                    st.divider()
                    # Exibe como uma tabela de dados rica e interativa
                    st.dataframe(df_final, use_container_width=True, hide_index=True)
                else:
                    st.warning("Não foi possível extrair dados dos ativos selecionados.")
                    
            except Exception as e:
                st.error(f"Erro ao baixar lote de dados: {e}")
