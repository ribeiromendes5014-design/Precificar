import streamlit as st
import pandas as pd
from datetime import datetime
import requests
from io import StringIO
import base64

# ==================== CONFIGURAÇÕES DO APLICATIVO ====================
TOKEN = st.secrets["GITHUB_TOKEN"]
OWNER = st.secrets["REPO_OWNER"]
REPO = st.secrets["REPO_NAME"]
CSV_PATH = st.secrets["CSV_PATH"]
COMMIT_MESSAGE = "Atualiza livro caixa via Streamlit"
COMMIT_MESSAGE_DELETE = "Exclui movimentações do livro caixa"
BRANCH = st.secrets.get("BRANCH", "main")

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# ==================== FUNÇÕES ====================
@st.cache_data(show_spinner="Carregando dados do GitHub...")
def carregar_dados_do_github():
    url_raw = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{CSV_PATH}"
    try:
        response = requests.get(url_raw)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), parse_dates=["Data"])
        return df
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            st.info("Arquivo CSV não encontrado. Criando um novo DataFrame.")
            return pd.DataFrame(columns=["Data", "Cliente", "Valor", "Forma de Pagamento", "Tipo"])
        else:
            st.error(f"Erro HTTP ao carregar dados: {e}")
            return pd.DataFrame(columns=["Data", "Cliente", "Valor", "Forma de Pagamento", "Tipo"])
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
        return pd.DataFrame(columns=["Data", "Cliente", "Valor", "Forma de Pagamento", "Tipo"])

def salvar_dados_no_github(df, commit_message=COMMIT_MESSAGE):
    url_api = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{CSV_PATH}"
    
    try:
        response_sha = requests.get(url_api, headers=HEADERS)
        response_sha.raise_for_status()
        sha = response_sha.json()["sha"]
    except Exception:
        st.warning("SHA não encontrado. Criando novo arquivo.")
        sha = None

    csv_string = df.to_csv(index=False)
    csv_encoded = base64.b64encode(csv_string.encode()).decode()
    
    payload = {
        "message": commit_message,
        "content": csv_encoded,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    
    try:
        response = requests.put(url_api, headers=HEADERS, json=payload)
        response.raise_for_status()
        if response.status_code in [200, 201]:
            st.success("📁 Dados salvos no GitHub com sucesso!")
            return True
        else:
            st.error(f"Erro ao salvar no GitHub. Código: {response.status_code}")
            st.code(response.json())
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao salvar no GitHub: {e}")
        return False

# ==================== INTERFACE ====================
st.title("📘 Livro Caixa - Streamlit + GitHub")

# ----------- BOTÕES DE CONTROLE ------------
st.sidebar.markdown("### 📥 Controle de Dados")

if st.sidebar.button("🔄 Carregar CSV do GitHub"):
    st.session_state.df = carregar_dados_do_github()
    st.success("✅ Dados carregados com sucesso!")

# Garante que df exista mesmo se o botão não for clicado
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Data", "Cliente", "Valor", "Forma de Pagamento", "Tipo"])

# ----------- FORMULÁRIO ------------
st.sidebar.header("Nova Movimentação")
with st.sidebar.form("form_movimentacao"):
    data = st.date_input("Data", datetime.today())
    cliente = st.text_input("Nome do Cliente")
    valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
    forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão", "PIX", "Transferência"])
    tipo = st.radio("Tipo", ["Entrada", "Saída"])
    enviar = st.form_submit_button("Adicionar Movimentação")

if enviar:
    if not cliente or valor <= 0:
        st.sidebar.warning("Preencha corretamente o nome e valor.")
    else:
        nova_linha = {
            "Data": pd.to_datetime(data),
            "Cliente": cliente,
            "Valor": valor if tipo == "Entrada" else -valor,
            "Forma de Pagamento": forma_pagamento,
            "Tipo": tipo
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([nova_linha])], ignore_index=True)
        st.success("Movimentação adicionada.")

# ----------- BOTÃO SALVAR ------------
if st.button("💾 Salvar no GitHub"):
    if salvar_dados_no_github(st.session_state.df):
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("Falha ao salvar. Verifique os logs.")

# ----------- TABELA ------------
st.subheader("📊 Movimentações Registradas")
if st.session_state.df.empty:
    st.info("Nenhuma movimentação registrada.")
else:
    df_exibicao = st.session_state.df.copy()
    df_exibicao = df_exibicao.sort_values(by="Data", ascending=False)
    st.dataframe(df_exibicao, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🗑️ Excluir Movimentações")
    opcoes_exclusao = {
        f"ID: {row.name} - Data: {row['Data'].strftime('%d/%m/%Y')} - {row['Cliente']} - R$ {row['Valor']:,.2f}": row.name
        for _, row in st.session_state.df.iterrows()
    }
    selecionadas = st.multiselect("Selecione as movimentações para excluir:", options=list(opcoes_exclusao.keys()))
    indices_excluir = [opcoes_exclusao[s] for s in selecionadas]

    if st.button("Excluir Selecionadas"):
        if indices_excluir:
            st.session_state.df = st.session_state.df.drop(indices_excluir)
            st.warning("Movimentações excluídas. Clique em 'Salvar no GitHub' para confirmar.")
        else:
            st.warning("Nenhuma movimentação selecionada.")

    # ----------- RESUMO FINANCEIRO ------------
    st.markdown("---")
    st.markdown("### 💰 Resumo Financeiro")
    total_entradas = df_exibicao[df_exibicao["Tipo"] == "Entrada"]["Valor"].sum()
    total_saidas = df_exibicao[df_exibicao["Tipo"] == "Saída"]["Valor"].sum()
    saldo = df_exibicao["Valor"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas", f"R$ {total_entradas:,.2f}")
    col2.metric("Saídas", f"R$ {abs(total_saidas):,.2f}")
    col3.metric("Saldo", f"R$ {saldo:,.2f}")

    # ----------- FILTRO POR PERÍODO ------------
    st.markdown("---")
    st.markdown("### 📅 Filtrar por Período")
    col1, col2 = st.columns(2)
    with col1:
        data_inicial = st.date_input("Data Inicial", value=df_exibicao["Data"].min())
    with col2:
        data_final = st.date_input("Data Final", value=df_exibicao["Data"].max())

    if data_inicial and data_final:
        df_filtrado = df_exibicao[
            (df_exibicao["Data"] >= pd.to_datetime(data_inicial)) &
            (df_exibicao["Data"] <= pd.to_datetime(data_final))
        ]
        if df_filtrado.empty:
            st.warning("Nenhuma movimentação no período selecionado.")
        else:
            st.dataframe(df_filtrado, use_container_width=True)
            entradas = df_filtrado[df_filtrado["Tipo"] == "Entrada"]["Valor"].sum()
            saidas = df_filtrado[df_filtrado["Tipo"] == "Saída"]["Valor"].sum()
            saldo_filtro = df_filtrado["Valor"].sum()

            colf1, colf2, colf3 = st.columns(3)
            colf1.metric("Entradas", f"R$ {entradas:,.2f}")
            colf2.metric("Saídas", f"R$ {abs(saidas):,.2f}")
            colf3.metric("Saldo", f"R$ {saldo_filtro:,.2f}")
