import streamlit as st
import pandas as pd

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


def processar_dataframe(df: pd.DataFrame, frete_total: float, custos_extras: float,
                        modo_margem: str, margem_fixa: float) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    rateio_unitario = 0
    if frete_total > 0 or custos_extras > 0:
        qtd_total = df["Qtd"].sum()
        if qtd_total > 0:
            rateio_unitario = (frete_total + custos_extras) / qtd_total

    if "Custos Extras Produto" not in df.columns:
        df["Custos Extras Produto"] = 0.0
    else:
        df["Custos Extras Produto"] = df["Custos Extras Produto"].fillna(0)

    df["Custos Extras Produto"] += rateio_unitario

    if "Custo Unitário" not in df.columns:
        df["Custo Unitário"] = 0.0
    else:
        df["Custo Unitário"] = df["Custo Unitário"].fillna(0)

    df["Custo Total Unitário"] = df["Custo Unitário"] + df["Custos Extras Produto"]

    if modo_margem == "Margem fixa":
        df["Margem (%)"] = margem_fixa
    elif modo_margem == "Margem por produto":
        # Usar a margem do produto, preenchendo NaNs com o valor fixo (exemplo: 30%)
        if "Margem (%)" not in df.columns:
            df["Margem (%)"] = margem_fixa
        else:
            df["Margem (%)"] = df["Margem (%)"].fillna(margem_fixa)
    else:
        # Segurança para outros casos, também preencher com fixo
        if "Margem (%)" not in df.columns:
            df["Margem (%)"] = margem_fixa
        else:
            df["Margem (%)"] = df["Margem (%)"].fillna(margem_fixa)

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
            st.experimental_rerun()

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

                st.experimental_rerun()

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
