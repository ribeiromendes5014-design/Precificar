import streamlit as st
import pandas as pd



import streamlit as st
import pandas as pd

# Funções auxiliares (exemplo simplificado)
def exibir_precificacao():
    st.header("📊 Precificação")
    st.write("Conteúdo da aba Precificação aqui...")
    # Aqui você pode colocar o código que já tem da aba Precificador (pdf, manual, github)

def exibir_papelaria():
    st.header("🖋️ Papelaria")
    st.write("Conteúdo da aba Papelaria aqui...")
    # Coloque o que quiser mostrar na aba Papelaria






# ===============================
# Funções auxiliares
# ===============================


import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
from io import BytesIO

# Configurações Telegram
TELEGRAM_TOKEN = "8412132908:AAG8N_vFzkpVNX-WN3bwT0Vl3H41Q-9Rfw4"
TELEGRAM_CHAT_ID = "-1003030758192"
TOPICO_ID = 28  # ID do tópico (thread) no grupo Telegram


def gerar_pdf(df: pd.DataFrame) -> BytesIO:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Relatório de Precificação", 0, 1, "C")
    pdf.ln(5)

    # Configurações de fonte para tabela
    pdf.set_font("Arial", "B", 12)

    # Definindo largura das colunas (em mm)
    col_widths = {
        "Produto": 50,
        "Qtd": 15,
        "Custo Unitário": 35,
        "Margem (%)": 25,
        "Preço à Vista": 35,
        "Preço no Cartão": 35
    }

    # Cabeçalho da tabela
    for col_name, width in col_widths.items():
        pdf.cell(width, 10, col_name, border=1, align='C')
    pdf.ln()

    # Fonte para corpo da tabela
    pdf.set_font("Arial", "", 12)

    if df.empty:
        pdf.cell(sum(col_widths.values()), 10, "Nenhum produto cadastrado.", border=1, align="C")
        pdf.ln()
    else:
        # Itera pelas linhas e escreve na tabela
        for idx, row in df.iterrows():
            pdf.cell(col_widths["Produto"], 10, str(row["Produto"]), border=1)
            pdf.cell(col_widths["Qtd"], 10, str(row["Qtd"]), border=1, align="C")
            pdf.cell(col_widths["Custo Unitário"], 10, f"R$ {row['Custo Unitário']:.2f}", border=1, align="R")
            pdf.cell(col_widths["Margem (%)"], 10, f"{row['Margem (%)']:.2f}%", border=1, align="R")
            pdf.cell(col_widths["Preço à Vista"], 10, f"R$ {row['Preço à Vista']:.2f}", border=1, align="R")
            pdf.cell(col_widths["Preço no Cartão"], 10, f"R$ {row['Preço no Cartão']:.2f}", border=1, align="R")
            pdf.ln()

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_bytes)


def enviar_pdf_telegram(pdf_bytesio, thread_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    files = {'document': ('precificacao.pdf', pdf_bytesio, 'application/pdf')}
    data = {"chat_id": TELEGRAM_CHAT_ID}
    if thread_id is not None:
        data["message_thread_id"] = thread_id

    response = requests.post(url, data=data, files=files)
    resp_json = response.json()
    st.write("DEBUG TELEGRAM PDF:", resp_json)
    if not resp_json.get("ok"):
        st.error(f"Erro ao enviar PDF: {resp_json.get('description')}")
    else:
        st.success("✅ PDF enviado para o Telegram com sucesso!")

# --- Streamlit app ---

st.title("📊 Precificador de Produtos")

if "df_produtos_geral" not in st.session_state:
    st.session_state.df_produtos_geral = pd.DataFrame([
        {"Produto": "Produto A", "Qtd": 10, "Custo Unitário": 5.0, "Margem (%)": 20, "Preço à Vista": 6.0, "Preço no Cartão": 6.5},
        {"Produto": "Produto B", "Qtd": 5, "Custo Unitário": 3.0, "Margem (%)": 15, "Preço à Vista": 3.5, "Preço no Cartão": 3.8},
    ])

st.subheader("Produtos cadastrados")
st.dataframe(st.session_state.df_produtos_geral)

if st.button("📤 Gerar PDF e enviar para Telegram"):
    if st.session_state.df_produtos_geral.empty:
        st.warning("⚠️ Nenhum produto para gerar PDF.")
    else:
        pdf_io = gerar_pdf(st.session_state.df_produtos_geral)
        enviar_pdf_telegram(pdf_io, thread_id=TOPICO_ID)








# ===============================
# Funções auxiliares
# ===============================

def exibir_resultados(df: pd.DataFrame, imagens_dict: dict):
    """Exibe os resultados de precificação com tabela e imagens dos produtos."""
    if df is None or df.empty:
        st.info("⚠️ Nenhum produto disponível para exibir.")
        return

    st.subheader("📊 Resultados da Precificação")

    for idx, row in df.iterrows():
        with st.container():
            cols = st.columns([1, 3])
            with cols[0]:
                img_bytes = imagens_dict.get(row.get("Produto"))
                if img_bytes:
                    st.image(img_bytes, width=100)
                elif row.get("Imagem") is not None:
                    try:
                        st.image(row.get("Imagem"), width=100)
                    except Exception:
                        st.write("🖼️ N/A")
            with cols[1]:
                st.markdown(f"**{row.get('Produto', '—')}**")
                st.write(f"📦 Quantidade: {row.get('Qtd', '—')}")
                if "Custo Unitário" in df.columns:
                    st.write(f"💰 Custo Unitário: R$ {row.get('Custo Unitário', 0):.2f}")
                if "Custos Extras Produto" in df.columns:
                    st.write(f"🛠 Custos Extras: R$ {row.get('Custos Extras Produto', 0):.2f}")
                if "Margem (%)" in df.columns:
                    margem_val = row.get("Margem (%)", 0)
                    try:
                        margem_float = float(margem_val)
                    except Exception:
                        margem_float = 0
                    st.write(f"📈 Margem: {margem_float:.2f}%")
                if "Preço à Vista" in df.columns:
                    st.write(f"💸 Preço à Vista: R$ {row.get('Preço à Vista', 0):.2f}")
                if "Preço no Cartão" in df.columns:
                    st.write(f"💳 Preço no Cartão: R$ {row.get('Preço no Cartão', 0):.2f}")

    st.markdown("### 📋 Tabela Consolidada")
    st.dataframe(df, use_container_width=True)


import pandas as pd
import streamlit as st

def processar_dataframe(df: pd.DataFrame, frete_total: float, custos_extras: float,
                        modo_margem: str, margem_fixa: float) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    rateio_unitario = 0

    # Calcular rateio por unidade com base no frete + custos extras
    if frete_total > 0 or custos_extras > 0:
        qtd_total = df["Qtd"].sum()
        if qtd_total > 0:
            rateio_unitario = (frete_total + custos_extras) / qtd_total

    # Garantir que a coluna "Custos Extras Produto" exista e esteja limpa
    if "Custos Extras Produto" not in df.columns:
        df["Custos Extras Produto"] = 0.0
    else:
        df["Custos Extras Produto"] = df["Custos Extras Produto"].fillna(0.0)

    # Adicionar o rateio ao custo extra por produto
    df["Custos Extras Produto"] += rateio_unitario

    # Garantir que a coluna "Custo Unitário" exista e esteja limpa
    if "Custo Unitário" not in df.columns:
        df["Custo Unitário"] = 0.0
    else:
        df["Custo Unitário"] = df["Custo Unitário"].fillna(0.0)

    # Calcular o custo total por unidade
    df["Custo Total Unitário"] = df["Custo Unitário"] + df["Custos Extras Produto"]

    # Processar margens conforme o modo selecionado
    if "Margem (%)" not in df.columns:
        df["Margem (%)"] = margem_fixa
    else:
        df["Margem (%)"] = df["Margem (%)"].fillna(margem_fixa)

    if modo_margem == "Margem fixa":
        # Apenas sobrescreve onde ainda for NaN (já tratado acima)
        pass  # Nada mais a fazer, pois já aplicamos fillna acima
    elif modo_margem == "Margem por produto":
        # Já foi tratado acima com fillna, então respeita os valores existentes
        pass
    else:
        # Modo desconhecido: ainda assim, usamos a margem fixa como fallback (também já tratado)
        pass

    # Calcular os preços finais
    df["Preço à Vista"] = df["Custo Total Unitário"] * (1 + df["Margem (%)"] / 100)
    df["Preço no Cartão"] = df["Preço à Vista"] / 0.8872

    return df

def load_csv_github(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar CSV do GitHub: {e}")
        return pd.DataFrame()



def load_csv_github(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar CSV do GitHub: {e}")
        return pd.DataFrame()


def extrair_produtos_pdf(pdf_file) -> list:
    # Implementação fictícia, substitua pela sua função real de extração
    # Retornar lista de dicionários com chaves: Produto, Qtd, Custo Unitário, Margem (%)
    # Exemplo:
    # return [
    #     {"Produto": "Produto A", "Qtd": 10, "Custo Unitário": 5.0, "Margem (%)": 30},
    #     ...
    # ]
    st.warning("Função extrair_produtos_pdf ainda não implementada.")
    return []


# ===============================
# Estado da sessão e variáveis fixas
# ===============================
if "produtos_manuais" not in st.session_state:
    st.session_state.produtos_manuais = pd.DataFrame(columns=[
        "Produto", "Qtd", "Custo Unitário", "Custos Extras Produto", "Margem (%)", "Imagem"
    ])
if "rateio_manual" not in st.session_state:
    st.session_state["rateio_manual"] = 0.0

if "frete_manual" not in st.session_state:
    st.session_state["frete_manual"] = 0.0
if "extras_manual" not in st.session_state:
    st.session_state["extras_manual"] = 0.0
if "qtd_total_manual" not in st.session_state:
    st.session_state["qtd_total_manual"] = 1

# Valores padrão para margem
if "modo_margem" not in st.session_state:
    st.session_state["modo_margem"] = "Margem fixa"  # ou "Margem por produto"
if "margem_fixa" not in st.session_state:
    st.session_state["margem_fixa"] = 30.0

# Inicializar variáveis para uso no processamento
frete_total = st.session_state.get("frete_manual", 0.0)
custos_extras = st.session_state.get("extras_manual", 0.0)
modo_margem = st.session_state.get("modo_margem", "Margem fixa")
margem_fixa = st.session_state.get("margem_fixa", 30.0)

# URL do CSV do GitHub
ARQ_CAIXAS = "https://raw.githubusercontent.com/ribeiromendes5014-design/Precificar/main/precificacao.csv"

# Dicionário para armazenar imagens em memória para PDF ou manual
imagens_dict = {}  # produto → imagem bytes

# Criar as tabs
tab_pdf, tab_manual, tab_github = st.tabs([
    "📄 Precificador PDF",
    "✍️ Precificador Manual",
    "📥 Carregar CSV do GitHub"
])

# === Tab PDF ===
with tab_pdf:
    st.markdown("---")
    pdf_file = st.file_uploader("📤 Selecione o PDF da nota fiscal ou lista de compras", type=["pdf"])
    if pdf_file:
        try:
            produtos_pdf = extrair_produtos_pdf(pdf_file)
            if not produtos_pdf:
                st.warning("⚠️ Nenhum produto encontrado no PDF.")
            else:
                df_pdf = pd.DataFrame(produtos_pdf)
                df_pdf["Custos Extras Produto"] = 0.0
                df_pdf["Imagem"] = None  # sem imagem para PDF importado
                st.session_state.produtos_manuais = df_pdf.copy()
                st.session_state.df_produtos_geral = processar_dataframe(
                    df_pdf,
                    frete_total,
                    custos_extras,
                    modo_margem,
                    margem_fixa
                )
                if "df_produtos_geral" in st.session_state and not st.session_state.df_produtos_geral.empty:
                    exibir_resultados(st.session_state.df_produtos_geral, imagens_dict)
                else:
                    st.info("⚠️ Nenhum produto processado para exibir.")

        except Exception as e:
            st.error(f"❌ Erro ao processar o PDF: {e}")
    else:
        st.info("📄 Faça upload de um arquivo PDF para começar.")
        if st.button("📥 Carregar CSV de exemplo (PDF Tab)"):
            df_exemplo = load_csv_github(ARQ_CAIXAS)
            if not df_exemplo.empty:
                df_exemplo["Custos Extras Produto"] = 0.0
                df_exemplo["Imagem"] = None
                st.session_state.produtos_manuais = df_exemplo.copy()
                st.session_state.df_produtos_geral = processar_dataframe(
                    df_exemplo, frete_total, custos_extras, modo_margem, margem_fixa
                )
                exibir_resultados(st.session_state.df_produtos_geral, imagens_dict)

# === Tab Manual ===
with tab_manual:
    st.markdown("---")
    aba_prec_manual, aba_rateio = st.tabs(["✍️ Novo Produto Manual", "🔢 Rateio Manual"])

    with aba_rateio:
        st.subheader("🔢 Cálculo de Rateio Unitário (Frete + Custos Extras)")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            frete_manual = st.number_input("🚚 Frete Total (R$)", min_value=0.0, step=0.01, key="frete_manual")
        with col_r2:
            extras_manual = st.number_input("🛠 Custos Extras (R$)", min_value=0.0, step=0.01, key="extras_manual")
        with col_r3:
            qtd_total_manual = st.number_input("📦 Quantidade Total de Produtos", min_value=1, step=1, key="qtd_total_manual")

        if qtd_total_manual > 0:
            rateio_calculado = (frete_manual + extras_manual) / qtd_total_manual
        else:
            rateio_calculado = 0.0

        st.session_state["rateio_manual"] = round(rateio_calculado, 4)
        st.markdown(f"💰 **Rateio Unitário Calculado:** R$ {rateio_calculado:,.4f}")

    with aba_prec_manual:
        # Se flag de rerun estiver presente, dispara o rerun e limpa os campos
        if st.session_state.get("rerun_after_add"):
            del st.session_state["rerun_after_add"]
            st.rerun()

        st.subheader("Adicionar novo produto")

        col1, col2 = st.columns(2)
        with col1:
            produto = st.text_input("📝 Nome do Produto")
            quantidade = st.number_input("📦 Quantidade", min_value=1, step=1)
            valor_pago = st.number_input("💰 Valor Pago (R$)", min_value=0.0, step=0.01)
            imagem_file = st.file_uploader("🖼️ Foto do Produto (opcional)", type=["png", "jpg", "jpeg"], key="imagem_manual")
        with col2:
            valor_default_rateio = st.session_state.get("rateio_manual", 0.0)
            custo_extra_produto = st.number_input(
                "💰 Custos extras do Produto (R$)", min_value=0.0, step=0.01, value=valor_default_rateio
            )
            preco_final_sugerido = st.number_input(
                "💸 Valor Final Sugerido (Preço à Vista) (R$)", min_value=0.0, step=0.01
            )

        custo_total_unitario = valor_pago + custo_extra_produto

        if preco_final_sugerido > 0:
            margem_calculada = 0.0
            if custo_total_unitario > 0:
                margem_calculada = (preco_final_sugerido / custo_total_unitario - 1) * 100
            margem_manual = round(margem_calculada, 2)
            st.info(f"🧮 Margem calculada automaticamente (com base no preço sugerido): {margem_manual:.2f}%")
            preco_a_vista_calc = preco_final_sugerido
            preco_no_cartao_calc = preco_final_sugerido / 0.8872
        else:
            margem_manual = st.number_input("🧮 Margem de Lucro (%)", min_value=0.0, value=30.0)
            preco_a_vista_calc = custo_total_unitario * (1 + margem_manual / 100)
            preco_no_cartao_calc = preco_a_vista_calc / 0.8872

        st.markdown(f"**Preço à Vista Calculado:** R$ {preco_a_vista_calc:,.2f}")
        st.markdown(f"**Preço no Cartão Calculado:** R$ {preco_no_cartao_calc:,.2f}")

        with st.form("form_submit_manual"):
            adicionar_produto = st.form_submit_button("➕ Adicionar Produto (Manual)")
            if adicionar_produto:
                if produto and quantidade > 0 and valor_pago >= 0:
                    imagem_bytes = None
                    if imagem_file is not None:
                        imagem_bytes = imagem_file.read()
                        imagens_dict[produto] = imagem_bytes

                    novo_produto = pd.DataFrame([{
                        "Produto": produto,
                        "Qtd": quantidade,
                        "Custo Unitário": valor_pago,
                        "Custos Extras Produto": custo_extra_produto,
                        "Margem (%)": margem_manual,
                        "Imagem": imagem_bytes
                    }])
                    st.session_state.produtos_manuais = pd.concat(
                        [st.session_state.produtos_manuais, novo_produto],
                        ignore_index=True
                    )
                    st.session_state.df_produtos_geral = processar_dataframe(
                        st.session_state.produtos_manuais,
                        frete_total,
                        custos_extras,
                        modo_margem,
                        margem_fixa
                    )
                    st.success("✅ Produto adicionado!")
                    st.session_state["rerun_after_add"] = True  # ← Adiciona flag aqui
                else:
                    st.warning("⚠️ Preencha todos os campos obrigatórios.")

        st.markdown("---")
        st.subheader("Produtos cadastrados")

        # Exibir produtos com botão de exclusão
        produtos = st.session_state.produtos_manuais

        if produtos.empty:
            st.info("⚠️ Nenhum produto cadastrado.")
        else:
            if "produto_para_excluir" not in st.session_state:
                st.session_state["produto_para_excluir"] = None

            for i, row in produtos.iterrows():
                cols = st.columns([4, 1])
                with cols[0]:
                    st.write(f"**{row['Produto']}** — Quantidade: {row['Qtd']} — Custo Unitário: R$ {row['Custo Unitário']:.2f}")
                with cols[1]:
                    if st.button(f"❌ Excluir", key=f"excluir_{i}"):
                        st.session_state["produto_para_excluir"] = i

            if st.session_state["produto_para_excluir"] is not None:
                i = st.session_state["produto_para_excluir"]
                st.session_state.produtos_manuais = produtos.drop(i).reset_index(drop=True)

                # Atualizar df_produtos_geral também para refletir exclusão
                st.session_state.df_produtos_geral = processar_dataframe(
                    st.session_state.produtos_manuais,
                    frete_total,
                    custos_extras,
                    modo_margem,
                    margem_fixa
                )

                # Resetar variável para evitar loop infinito
                st.session_state["produto_para_excluir"] = None

                st.rerun()

        # Exibir resultados após possíveis alterações, fora do form
        if "df_produtos_geral" in st.session_state and not st.session_state.df_produtos_geral.empty:
            exibir_resultados(st.session_state.df_produtos_geral, imagens_dict)
        else:
            st.info("⚠️ Nenhum produto processado para exibir.")

# === Tab GitHub ===
with tab_github:
    st.markdown("---")
    st.header("📥 Carregar CSV de Precificação do GitHub")
    if st.button("🔄 Carregar CSV do GitHub (Tab GitHub)"):
        df_exemplo = load_csv_github(ARQ_CAIXAS)
        if not df_exemplo.empty:
            df_exemplo["Custos Extras Produto"] = 0.0
            df_exemplo["Imagem"] = None
            st.session_state.produtos_manuais = df_exemplo.copy()
            st.session_state.df_produtos_geral = processar_dataframe(
                df_exemplo, frete_total, custos_extras, modo_margem, margem_fixa
            )
            st.success("✅ CSV carregado e processado com sucesso!")
            exibir_resultados(st.session_state.df_produtos_geral, imagens_dict)
        else:
            st.warning("⚠️ Não foi possível carregar o CSV do GitHub.")





import streamlit as st
import pandas as pd
import requests
from io import StringIO



import streamlit as st
import pandas as pd
import base64
import requests
from io import StringIO
import hashlib

# =====================================
# Aba Papelaria (função completa, com campos dinâmicos e salvamento automático no GitHub)
# =====================================
def papelaria_aba():
    st.write("📚 Gerenciador Papelaria Personalizada")

    # ---------------------
    # Token e repositório GitHub
    # ---------------------
    GITHUB_TOKEN = st.secrets["github_token"]
    GITHUB_REPO = "ribeiromendes5014-design/Precificar"
    GITHUB_BRANCH = "main"

    # ---------------------
    # Configuração de arquivos remotos (ajuste para o seu repositório real)
    # ---------------------
    URL_BASE = "https://raw.githubusercontent.com/ribeiromendes5014-design/Precificar/main/"
    INSUMOS_CSV_URL = URL_BASE + "insumos_papelaria.csv"
    PRODUTOS_CSV_URL = URL_BASE + "produtos_papelaria.csv"
    CAMPOS_CSV_URL = URL_BASE + "categorias_papelaria.csv"

    # ---------------------
    # Colunas padrão dos dados
    # ---------------------
    INSUMOS_BASE_COLS = ["Nome", "Categoria", "Unidade", "Preço Unitário (R$)"]
    PRODUTOS_BASE_COLS = ["Produto", "Custo Total", "Preço à Vista", "Preço no Cartão", "Margem (%)"]
    COLUNAS_CAMPOS = ["Campo", "Aplicação", "Tipo", "Opções"]  # Aplicação: Insumos | Produtos | Ambos

    # ---------------------
    # Função para salvar no GitHub via API
    # ---------------------
    def salvar_csv_no_github(token, repo, path, dataframe, branch="main", mensagem="Atualização via app"):
        """Salva um DataFrame como CSV diretamente no GitHub."""
        from requests import get, put

        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        conteudo = dataframe.to_csv(index=False)
        conteudo_b64 = base64.b64encode(conteudo.encode()).decode()
        headers = {"Authorization": f"token {token}"}

        # Obtém SHA do arquivo (necessário para atualizar)
        r = get(url, headers=headers)
        if r.status_code == 200:
            sha = r.json().get("sha")
        else:
            sha = None

        payload = {
            "message": mensagem,
            "content": conteudo_b64,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        r2 = put(url, headers=headers, json=payload)
        if r2.status_code in (200, 201):
            st.success(f"✅ Arquivo `{path}` atualizado no GitHub!")
        else:
            st.error(f"❌ Erro ao salvar `{path}`: {r2.text}")

    # ---------------------
    # Função para gerar hash do DataFrame
    # ---------------------
    def hash_df(df):
        return hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()

    # ---------------------
    # Utilitários de manipulação
    # ---------------------
    def carregar_csv_github(url, colunas=None):
        """Tenta carregar um CSV remoto. Se 'colunas' for fornecido, garante essas colunas (criando se faltar)."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
            if colunas is not None:
                for c in colunas:
                    if c not in df.columns:
                        df[c] = None
                df = df[[c for c in colunas if c in df.columns]]
            return df
        except Exception as e:
            st.warning(f"Não foi possível carregar CSV do GitHub ({url}): {e}")
            return pd.DataFrame(columns=colunas) if colunas else pd.DataFrame()

    def baixar_csv(df, nome_arquivo):
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            f"⬇️ Baixar {nome_arquivo}",
            data=csv,
            file_name=nome_arquivo,
            mime="text/csv"
        )

    def _opcoes_para_lista(opcoes_str):
        if pd.isna(opcoes_str) or not str(opcoes_str).strip():
            return []
        return [o.strip() for o in str(opcoes_str).split(",") if o.strip()]

    def col_defs_para(aplicacao: str):
        """Retorna DataFrame de campos extras filtrando por aplicação."""
        df = st.session_state.campos
        if df.empty:
            return df
        return df[(df["Aplicação"] == aplicacao) | (df["Aplicação"] == "Ambos")].copy()

    def garantir_colunas_extras(df: pd.DataFrame, aplicacao: str) -> pd.DataFrame:
        """Garante que o DataFrame tenha as colunas extras definidas para a aplicação."""
        defs = col_defs_para(aplicacao)
        for campo in defs["Campo"].tolist():
            if campo not in df.columns:
                df[campo] = ""
        return df

    def render_input_por_tipo(label, tipo, opcoes, valor_padrao=None, key=None):
        """Renderiza o widget apropriado conforme o tipo de campo."""
        if tipo == "Número":
            valor = float(valor_padrao) if (valor_padrao is not None and str(valor_padrao).strip() != "") else 0.0
            return st.number_input(label, min_value=0.0, format="%.2f", value=valor, key=key)
        elif tipo == "Seleção":
            lista = _opcoes_para_lista(opcoes)
            if not lista:
                return st.text_input(label, value=str(valor_padrao) if valor_padrao is not None else "", key=key)
            if valor_padrao not in lista and valor_padrao not in (None, "", "nan"):
                lista = [str(valor_padrao)] + [o for o in lista if o != valor_padrao]
            return st.selectbox(label, options=lista, index=0 if valor_padrao in (None, "", "nan") else lista.index(str(valor_padrao)), key=key)
        else:
            return st.text_input(label, value=str(valor_padrao) if valor_padrao is not None else "", key=key)

    # ---------------------
    # Estado da sessão
    # ---------------------
    if "insumos" not in st.session_state:
        st.session_state.insumos = carregar_csv_github(INSUMOS_CSV_URL)

    if "produtos" not in st.session_state:
        st.session_state.produtos = carregar_csv_github(PRODUTOS_CSV_URL)

    if "campos" not in st.session_state:
        st.session_state.campos = carregar_csv_github(CAMPOS_CSV_URL, COLUNAS_CAMPOS)

    # Garante colunas base nos DataFrames
    for col in INSUMOS_BASE_COLS:
        if col not in st.session_state.insumos.columns:
            st.session_state.insumos[col] = "" if col != "Preço Unitário (R$)" else 0.0

    for col in PRODUTOS_BASE_COLS:
        if col not in st.session_state.produtos.columns:
            st.session_state.produtos[col] = "" if col not in ["Custo Total", "Preço à Vista", "Preço no Cartão", "Margem (%)"] else 0.0

    # Garante colunas extras
    st.session_state.insumos = garantir_colunas_extras(st.session_state.insumos, "Insumos")
    st.session_state.produtos = garantir_colunas_extras(st.session_state.produtos, "Produtos")

    # ---------------------
    # Verifica se houve alteração nos produtos para salvar automaticamente
    # ---------------------
    if "hash_produtos" not in st.session_state:
        st.session_state.hash_produtos = hash_df(st.session_state.produtos)

    novo_hash = hash_df(st.session_state.produtos)
    if novo_hash != st.session_state.hash_produtos:
        salvar_csv_no_github(
            GITHUB_TOKEN,
            GITHUB_REPO,
            "produtos_papelaria.csv",
            st.session_state.produtos,
            GITHUB_BRANCH,
            mensagem="♻️ Alteração automática nos produtos"
        )
        st.session_state.hash_produtos = novo_hash


    # Inicialização das variáveis no session_state
if "campos" not in st.session_state:
    st.session_state.campos = pd.DataFrame(columns=["Campo", "Aplicação", "Tipo", "Opções"])

if "insumos" not in st.session_state:
    st.session_state.insumos = pd.DataFrame(columns=["Nome", "Categoria", "Unidade", "Preço Unitário (R$)"])

if "produtos" not in st.session_state:
    st.session_state.produtos = pd.DataFrame(columns=["Nome", "Categoria", "Unidade", "Preço Unitário (R$)"])
    # ---------------------
# Criação das abas
# ---------------------
aba_campos, aba_insumos, aba_produtos = st.tabs(["Campos (Colunas)", "Insumos", "Produtos"])

# =====================================
# Aba Campos (gerencia colunas extras)
# =====================================
with aba_campos:
    st.header("Campos / Colunas Personalizadas")

    with st.form("form_add_campo"):
        st.subheader("Adicionar novo campo")
        nome_campo = st.text_input("Nome do Campo (será o nome da coluna)")
        aplicacao = st.selectbox("Aplicação", ["Insumos", "Produtos", "Ambos"])
        tipo = st.selectbox("Tipo", ["Texto", "Número", "Seleção"])
        opcoes = st.text_input("Opções (se 'Seleção', separe por vírgula)")
        adicionar = st.form_submit_button("Adicionar Campo")

        if adicionar:
            if not nome_campo.strip():
                st.warning("Informe um nome de campo válido.")
            else:
                ja_existe = (
                    (st.session_state.campos["Campo"].astype(str).str.lower() == nome_campo.strip().lower())
                    & (st.session_state.campos["Aplicação"] == aplicacao)
                ).any()
                if ja_existe:
                    st.warning("Já existe um campo com esse nome para essa aplicação.")
                else:
                    nova_linha = {
                        "Campo": nome_campo.strip(),
                        "Aplicação": aplicacao,
                        "Tipo": tipo,
                        "Opções": opcoes
                    }
                    st.session_state.campos = pd.concat(
                        [st.session_state.campos, pd.DataFrame([nova_linha])],
                        ignore_index=True
                    )
                    st.success(f"Campo '{nome_campo}' adicionado para {aplicacao}!")
                    if aplicacao in ("Insumos", "Ambos"):
                        if nome_campo not in st.session_state.insumos.columns:
                            st.session_state.insumos[nome_campo] = ""
                    if aplicacao in ("Produtos", "Ambos"):
                        if nome_campo not in st.session_state.produtos.columns:
                            st.session_state.produtos[nome_campo] = ""
                    st.rerun()

    st.markdown("### Campos cadastrados")
if st.session_state.campos.empty:
    st.info("Nenhum campo extra cadastrado ainda.")
else:
    st.dataframe(st.session_state.campos, use_container_width=True)

if not st.session_state.campos.empty:
    st.divider()
    st.subheader("Editar ou Excluir campo")
    rotulos = [
        f"{row.Campo}  ·  ({row.Aplicação})"
        for _, row in st.session_state.campos.iterrows()
    ]
    escolha = st.selectbox("Escolha um campo", [""] + rotulos)
    if escolha:
        idx = rotulos.index(escolha)
        campo_atual = st.session_state.campos.iloc[idx]
        acao_campo = st.radio(
            "Ação",
            ["Nenhuma", "Editar", "Excluir"],
            horizontal=True,
            key=f"acao_campo_{idx}"
        )
        if acao_campo == "Excluir":
            if st.button("Confirmar Exclusão", key=f"excluir_campo_{idx}"):
                nome = campo_atual["Campo"]
                aplic = campo_atual["Aplicação"]
                st.session_state.campos = st.session_state.campos.drop(st.session_state.campos.index[idx]).reset_index(drop=True)
                if aplic in ("Insumos", "Ambos"):
                    if nome in st.session_state.insumos.columns:
                        st.session_state.insumos = st.session_state.insumos.drop(columns=[nome])
                if aplic in ("Produtos", "Ambos"):
                    if nome in st.session_state.produtos.columns:
                        st.session_state.produtos = st.session_state.produtos.drop(columns=[nome])
                st.success(f"Campo '{nome}' removido de {aplic}!")
                st.rerun()
        if acao_campo == "Editar":
            with st.form(f"form_edit_campo_{idx}"):
                novo_nome = st.text_input("Nome do Campo", value=str(campo_atual["Campo"]))
                nova_aplic = st.selectbox("Aplicação", ["Insumos", "Produtos", "Ambos"], index=["Insumos","Produtos","Ambos"].index(campo_atual["Aplicação"]))
                novo_tipo = st.selectbox("Tipo", ["Texto", "Número", "Seleção"], index=["Texto","Número","Seleção"].index(campo_atual["Tipo"]))
                novas_opcoes = st.text_input("Opções (se 'Seleção')", value=str(campo_atual["Opções"]) if pd.notna(campo_atual["Opções"]) else "")
                salvar = st.form_submit_button("Salvar Alterações")
                if salvar:
                    nome_antigo = campo_atual["Campo"]
                    aplic_antiga = campo_atual["Aplicação"]
                    st.session_state.campos.loc[st.session_state.campos.index[idx], ["Campo","Aplicação","Tipo","Opções"]] = [
                        novo_nome, nova_aplic, novo_tipo, novas_opcoes
                    ]
                    renomeou = (str(novo_nome).strip() != str(nome_antigo).strip())
                    if renomeou:
                        if aplic_antiga in ("Insumos", "Ambos") and nome_antigo in st.session_state.insumos.columns:
                            st.session_state.insumos = st.session_state.insumos.rename(columns={nome_antigo: novo_nome})
                        if aplic_antiga in ("Produtos", "Ambos") and nome_antigo in st.session_state.produtos.columns:
                            st.session_state.produtos = st.session_state.produtos.rename(columns={nome_antigo: novo_nome})
                    if nova_aplic in ("Insumos", "Ambos"):
                        if novo_nome not in st.session_state.insumos.columns:
                            st.session_state.insumos[novo_nome] = ""
                    if nova_aplic in ("Produtos", "Ambos"):
                        if novo_nome not in st.session_state.produtos.columns:
                            st.session_state.produtos[novo_nome] = ""
                    st.success("Campo atualizado!")
                    st.rerun()

def baixar_csv(df, nome_arquivo):
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Baixar {nome_arquivo}",
        data=csv,
        file_name=nome_arquivo,
        mime='text/csv',
    )

# Função para garantir que as colunas extras estejam no dataframe
def garantir_colunas_extras(df, tipo_aplicacao):
    if "campos" not in st.session_state or st.session_state.campos.empty:
        return df
    campos_aplicaveis = st.session_state.campos[
        (st.session_state.campos["Aplicação"] == tipo_aplicacao) |
        (st.session_state.campos["Aplicação"] == "Ambos")
    ]
    for campo in campos_aplicaveis["Campo"]:
        if campo not in df.columns:
            df[campo] = ""
    return df

def col_defs_para(tipo_aplicacao):
    if "campos" not in st.session_state or st.session_state.campos.empty:
        return pd.DataFrame(columns=["Campo", "Aplicação", "Tipo", "Opções"])
    return st.session_state.campos[
        (st.session_state.campos["Aplicação"] == tipo_aplicacao) |
        (st.session_state.campos["Aplicação"] == "Ambos")
    ].reset_index(drop=True)

with aba_insumos:
    st.header("Insumos")
    st.session_state.insumos = garantir_colunas_extras(st.session_state.insumos, "Insumos")


  


# =====================================
# Definições globais de colunas base
# =====================================
INSUMOS_BASE_COLS = ["Nome", "Categoria", "Unidade", "Preço Unitário (R$)"]
PRODUTOS_BASE_COLS = ["Produto", "Custo Total", "Preço à Vista", "Preço no Cartão", "Margem (%)"]

# =====================================
# Aba Insumos
# =====================================
with aba_insumos:
    st.header("Insumos")

    st.session_state.insumos = garantir_colunas_extras(st.session_state.insumos, "Insumos")

    with st.form("form_add_insumo"):
        st.subheader("Adicionar novo insumo")
        nome_insumo = st.text_input("Nome do Insumo")
        categoria_insumo = st.text_input("Categoria")
        unidade_insumo = st.text_input("Unidade de Medida (ex: un, kg, m)")
        preco_insumo = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")

        extras_insumos = col_defs_para("Insumos")
        valores_extras = {}
        if not extras_insumos.empty:
            st.markdown("**Campos extras**")
            for i, row in extras_insumos.reset_index(drop=True).iterrows():
                key = f"novo_insumo_extra_{row['Campo']}"
                valores_extras[row["Campo"]] = render_input_por_tipo(
                    label=row["Campo"],
                    tipo=row["Tipo"],
                    opcoes=row["Opções"],
                    valor_padrao=None,
                    key=key
                )

        adicionou = st.form_submit_button("Adicionar Insumo")
        if adicionou:
            if not nome_insumo.strip():
                st.warning("Informe o Nome do Insumo.")
            else:
                novo = {
                    "Nome": nome_insumo.strip(),
                    "Categoria": categoria_insumo.strip(),
                    "Unidade": unidade_insumo.strip(),
                    "Preço Unitário (R$)": float(preco_insumo),
                }
                for k, v in valores_extras.items():
                    novo[k] = v
                todas_cols = list(dict.fromkeys(INSUMOS_BASE_COLS + extras_insumos["Campo"].tolist()))
                st.session_state.insumos = st.session_state.insumos.reindex(columns=list(set(st.session_state.insumos.columns) | set(todas_cols)))
                st.session_state.insumos = pd.concat([st.session_state.insumos, pd.DataFrame([novo])], ignore_index=True)
                st.success(f"Insumo '{nome_insumo}' adicionado!")
                st.rerun()

    st.markdown("### Insumos cadastrados")
    ordem_cols = INSUMOS_BASE_COLS + [c for c in st.session_state.insumos.columns if c not in INSUMOS_BASE_COLS]
    st.dataframe(st.session_state.insumos.reindex(columns=ordem_cols), use_container_width=True)

    if not st.session_state.insumos.empty:
        insumo_selecionado = st.selectbox(
            "Selecione um insumo",
            [""] + st.session_state.insumos["Nome"].astype(str).fillna("").tolist()
        )
    else:
        insumo_selecionado = None

    if insumo_selecionado:
        acao_insumo = st.radio(
            f"Ação para '{insumo_selecionado}'",
            ["Nenhuma", "Editar", "Excluir"],
            horizontal=True,
            key=f"acao_insumo_{insumo_selecionado}"
        )

        idxs = st.session_state.insumos.index[st.session_state.insumos["Nome"] == insumo_selecionado].tolist()
        idx = idxs[0] if idxs else None

        if acao_insumo == "Excluir" and idx is not None:
            if st.button("Confirmar Exclusão", key=f"excluir_insumo_{idx}"):
                st.session_state.insumos = st.session_state.insumos.drop(index=idx).reset_index(drop=True)
                st.success(f"Insumo '{insumo_selecionado}' removido!")
                st.rerun()

        if acao_insumo == "Editar" and idx is not None:
            atual = st.session_state.insumos.loc[idx]
            with st.form(f"form_edit_insumo_{idx}"):
                novo_nome = st.text_input("Nome do Insumo", value=str(atual.get("Nome","")))
                nova_categoria = st.text_input("Categoria", value=str(atual.get("Categoria","")))
                nova_unidade = st.text_input("Unidade de Medida (ex: un, kg, m)", value=str(atual.get("Unidade","")))
                novo_preco = st.number_input(
                    "Preço Unitário (R$)", min_value=0.0, format="%.2f",
                    value=float(atual.get("Preço Unitário (R$)", 0.0))
                )

                valores_extras_edit = {}
                extras_insumos = col_defs_para("Insumos")
                if not extras_insumos.empty:
                    st.markdown("**Campos extras**")
                    for i, row in extras_insumos.reset_index(drop=True).iterrows():
                        campo = row["Campo"]
                        key = f"edit_insumo_extra_{idx}_{campo}"
                        valores_extras_edit[campo] = render_input_por_tipo(
                            label=campo,
                            tipo=row["Tipo"],
                            opcoes=row["Opções"],
                            valor_padrao=atual.get(campo, ""),
                            key=key
                        )

                salvou = st.form_submit_button("Salvar Alterações", key=f"salvar_insumo_{idx}")
                if salvou:
                    st.session_state.insumos.loc[idx, "Nome"] = novo_nome
                    st.session_state.insumos.loc[idx, "Categoria"] = nova_categoria
                    st.session_state.insumos.loc[idx, "Unidade"] = nova_unidade
                    st.session_state.insumos.loc[idx, "Preço Unitário (R$)"] = float(novo_preco)
                    for k, v in valores_extras_edit.items():
                        st.session_state.insumos.loc[idx, k] = v
                    st.success("Insumo atualizado!")
                    st.rerun()

    baixar_csv(st.session_state.insumos, "insumos_papelaria.csv")
    if st.button("📤 Salvar INSUMOS no GitHub"):
        salvar_csv_no_github(GITHUB_TOKEN, GITHUB_REPO, "insumos_papelaria.csv", st.session_state.insumos, GITHUB_BRANCH)





# =====================================
# Aba Produtos
# =====================================
with aba_produtos:
    st.header("Produtos")

    with st.form("form_add_produto"):
        st.subheader("Adicionar novo produto")
        nome_produto = st.text_input("Nome do Produto")

        # Verificar se a coluna "Nome" está presente em insumos
        if 'Nome' in st.session_state.insumos.columns:
            insumos_disponiveis = st.session_state.insumos["Nome"].dropna().unique().tolist()
        else:
            insumos_disponiveis = []

        insumos_selecionados = st.multiselect("Selecione os insumos usados", insumos_disponiveis)

        insumos_usados = []
        custo_total = 0.0


        for insumo in insumos_selecionados:
            dados_insumo = st.session_state.insumos[st.session_state.insumos["Nome"] == insumo].iloc[0]
            preco_unit = float(dados_insumo.get("Preço Unitário (R$)", 0.0))
            unidade = str(dados_insumo.get("Unidade", ""))

            qtd_usada = st.number_input(
                f"Quantidade usada de {insumo} ({unidade}) - Preço unitário R$ {preco_unit:.2f}",
                min_value=0.0,
                step=0.01,
                key=f"novo_qtd_{insumo}"
            )

            custo_insumo = qtd_usada * preco_unit
            custo_total += custo_insumo

            insumos_usados.append({
                "Insumo": insumo,
                "Quantidade Usada": qtd_usada,
                "Unidade": unidade,
                "Preço Unitário (R$)": preco_unit,
                "Custo": custo_insumo
            })

        st.markdown(f"**Custo Total Calculado (Insumos): R$ {custo_total:,.2f}**")

        margem = st.number_input("Margem de Lucro (%)", min_value=0.0, format="%.2f", value=30.0)

        preco_vista = custo_total * (1 + margem / 100) if custo_total > 0 else 0.0
        preco_cartao = preco_vista / 0.8872 if preco_vista > 0 else 0.0

        st.markdown(f"💸 **Preço à Vista Calculado:** R$ {preco_vista:,.2f}")
        st.markdown(f"💳 **Preço no Cartão Calculado:** R$ {preco_cartao:,.2f}")

        extras_produtos = col_defs_para("Produtos")
        valores_extras_prod = {}
        if not extras_produtos.empty:
            st.markdown("**Campos extras**")
            for i, row in extras_produtos.reset_index(drop=True).iterrows():
                key = f"novo_produto_extra_{row['Campo']}"
                valores_extras_prod[row["Campo"]] = render_input_por_tipo(
                    label=row["Campo"],
                    tipo=row["Tipo"],
                    opcoes=row["Opções"],
                    valor_padrao=None,
                    key=key
                )

        adicionou_prod = st.form_submit_button("Adicionar Produto")
        if adicionou_prod:
            if not nome_produto.strip():
                st.warning("Informe o Nome do Produto.")
            elif not insumos_usados:
                st.warning("Selecione ao menos um insumo para o produto.")
            else:
                novo = {
                    "Produto": nome_produto.strip(),
                    "Custo Total": float(custo_total),
                    "Preço à Vista": float(preco_vista),
                    "Preço no Cartão": float(preco_cartao),
                    "Margem (%)": float(margem),
                    "Insumos Usados": str(insumos_usados)
                }
                for k, v in valores_extras_prod.items():
                    novo[k] = v

                # 🔔 Envio da mensagem para o Telegram
                try:
                    TELEGRAM_TOKEN = st.secrets["telegram_token"]
                    TELEGRAM_CHAT_ID = "-1003030758192"
                    THREAD_ID = 43

                    mensagem = f"<b>📦 Novo Produto Cadastrado:</b>\n"
                    mensagem += f"<b>Produto:</b> {nome_produto}\n"
                    mensagem += "<b>Insumos:</b>\n"

                    for insumo in insumos_usados:
                        nome = insumo['Insumo']
                        qtd = insumo['Quantidade Usada']
                        un = insumo['Unidade']
                        custo = insumo['Custo']
                        mensagem += f"• {nome} - {qtd} {un} (R$ {custo:.2f})\n"

                    mensagem += f"\n<b>Custo Total:</b> R$ {custo_total:.2f}"
                    mensagem += f"\n<b>Preço à Vista:</b> R$ {preco_vista:.2f}"
                    mensagem += f"\n<b>Preço no Cartão:</b> R$ {preco_cartao:.2f}"

                    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    payload = {
                        "chat_id": TELEGRAM_CHAT_ID,
                        "message_thread_id": THREAD_ID,
                        "text": mensagem,
                        "parse_mode": "HTML"
                    }

                    response = requests.post(telegram_url, json=payload)
                    if response.status_code == 200:
                        st.success("✅ Mensagem enviada para o Telegram!")
                    else:
                        st.warning(f"⚠️ Erro ao enviar para Telegram: {response.text}")
                except Exception as e:
                    st.warning(f"⚠️ Falha ao tentar enviar para o Telegram: {e}")

                # 🗃️ Salva no DataFrame local
                todas_cols = list(dict.fromkeys(PRODUTOS_BASE_COLS + ["Insumos Usados"] + extras_produtos["Campo"].tolist()))
                st.session_state.produtos = st.session_state.produtos.reindex(
                    columns=list(set(st.session_state.produtos.columns) | set(todas_cols))
                )
                st.session_state.produtos = pd.concat(
                    [st.session_state.produtos, pd.DataFrame([novo])],
                    ignore_index=True
                )
                st.success(f"Produto '{nome_produto}' adicionado!")
                st.rerun()

        st.markdown("### Produtos cadastrados")
        ordem_cols_p = PRODUTOS_BASE_COLS + ["Insumos Usados"] + [c for c in st.session_state.produtos.columns if c not in PRODUTOS_BASE_COLS + ["Insumos Usados"]]
        st.dataframe(st.session_state.produtos.reindex(columns=ordem_cols_p), use_container_width=True)

        if not st.session_state.produtos.empty:
            produto_selecionado = st.selectbox(
                "Selecione um produto",
                [""] + st.session_state.produtos["Produto"].astype(str).fillna("").tolist()
            )
        else:
            produto_selecionado = None

        if produto_selecionado:
            acao_produto = st.radio(
                f"Ação para '{produto_selecionado}'",
                ["Nenhuma", "Editar", "Excluir"],
                horizontal=True,
                key=f"acao_produto_{produto_selecionado}"
            )

            idxs_p = st.session_state.produtos.index[st.session_state.produtos["Produto"] == produto_selecionado].tolist()
            idx_p = idxs_p[0] if idxs_p else None

            if acao_produto == "Excluir" and idx_p is not None:
                if st.button("Confirmar Exclusão", key=f"excluir_produto_{idx_p}"):
                    st.session_state.produtos = st.session_state.produtos.drop(index=idx_p).reset_index(drop=True)
                    st.success(f"Produto '{produto_selecionado}' removido!")
                    st.rerun()

            if acao_produto == "Editar" and idx_p is not None:
                atual_p = st.session_state.produtos.loc[idx_p]
                with st.form(f"form_edit_produto_{idx_p}"):
                    novo_nome = st.text_input("Nome do Produto", value=str(atual_p.get("Produto","")))
                    nova_margem = st.number_input("Margem (%)", min_value=0.0, format="%.2f", value=float(atual_p.get("Margem (%)", 0.0)))

                    try:
                        import ast
                        insumos_atual = ast.literal_eval(atual_p.get("Insumos Usados", "[]"))
                        if not isinstance(insumos_atual, list):
                            insumos_atual = []
                    except Exception:
                        insumos_atual = []

                    insumos_disponiveis = st.session_state.insumos["Nome"].dropna().unique().tolist()
                    nomes_pre_selecionados = [i["Insumo"] for i in insumos_atual]
                    insumos_editados = st.multiselect("Selecione os insumos usados", insumos_disponiveis, default=nomes_pre_selecionados)

                    insumos_usados_edit = []
                    novo_custo = 0.0

                    for insumo in insumos_editados:
                        dados_insumo = st.session_state.insumos[st.session_state.insumos["Nome"] == insumo].iloc[0]
                        preco_unit = float(dados_insumo.get("Preço Unitário (R$)", 0.0))
                        unidade = str(dados_insumo.get("Unidade", ""))

                        qtd_default = 0.0
                        for item in insumos_atual:
                            if item.get("Insumo") == insumo:
                                qtd_default = float(item.get("Quantidade Usada", 0.0))

                        qtd_usada = st.number_input(
                            f"Quantidade usada de {insumo} ({unidade}) - Preço unitário R$ {preco_unit:.2f}",
                            min_value=0.0,
                            step=0.01,
                            value=qtd_default,
                            key=f"edit_qtd_{idx_p}_{insumo}"
                        )

                        custo_insumo = qtd_usada * preco_unit
                        novo_custo += custo_insumo

                        insumos_usados_edit.append({
                            "Insumo": insumo,
                            "Quantidade Usada": qtd_usada,
                            "Unidade": unidade,
                            "Preço Unitário (R$)": preco_unit,
                            "Custo": custo_insumo
                        })

                    novo_vista = novo_custo * (1 + nova_margem / 100)
                    novo_cartao = novo_vista / 0.8872

                    st.markdown(f"**Novo custo calculado: R$ {novo_custo:,.2f}**")
                    st.markdown(f"💸 **Preço à Vista Recalculado:** R$ {novo_vista:,.2f}")
                    st.markdown(f"💳 **Preço no Cartão Recalculado:** R$ {novo_cartao:,.2f}")

                    valores_extras_edit_p = {}
                    extras_produtos = col_defs_para("Produtos")
                    if not extras_produtos.empty:
                        st.markdown("**Campos extras**")
                        for i, row in extras_produtos.reset_index(drop=True).iterrows():
                            campo = row["Campo"]
                            key = f"edit_produto_extra_{idx_p}_{campo}"
                            valores_extras_edit_p[campo] = render_input_por_tipo(
                                label=campo,
                                tipo=row["Tipo"],
                                opcoes=row["Opções"],
                                valor_padrao=atual_p.get(campo, ""),
                                key=key
                            )

                    salvou_p = st.form_submit_button("Salvar Alterações", key=f"salvar_produto_{idx_p}")
                    if salvou_p:
                        st.session_state.produtos.loc[idx_p, "Produto"] = novo_nome
                        st.session_state.produtos.loc[idx_p, "Custo Total"] = float(novo_custo)
                        st.session_state.produtos.loc[idx_p, "Preço à Vista"] = float(novo_vista)
                        st.session_state.produtos.loc[idx_p, "Preço no Cartão"] = float(novo_cartao)
                        st.session_state.produtos.loc[idx_p, "Margem (%)"] = float(nova_margem)
                        st.session_state.produtos.loc[idx_p, "Insumos Usados"] = str(insumos_usados_edit)
                        for k, v in valores_extras_edit_p.items():
                            st.session_state.produtos.loc[idx_p, k] = v
                        st.success("Produto atualizado!")
                        st.rerun()

        baixar_csv(st.session_state.produtos, "produtos_papelaria.csv")
        if st.button("📤 Salvar PRODUTOS no GitHub"):
            salvar_csv_no_github(GITHUB_TOKEN, GITHUB_REPO, "produtos_papelaria.csv", st.session_state.produtos, GITHUB_BRANCH)








if pagina == "Precificação":
    # exibir_precificacao()  # substitua com sua função de precificação
    st.write("📊 Precificação aqui...")
elif pagina == "Papelaria":
    papelaria_aba()
























































