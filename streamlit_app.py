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
                    st.write(f"📈 Margem: {row.get('Margem (%)', 0)}%")
                if "Preço à Vista" in df.columns:
                    st.write(f"💸 Preço à Vista: R$ {row.get('Preço à Vista', 0):.2f}")
                if "Preço no Cartão" in df.columns:
                    st.write(f"💳 Preço no Cartão: R$ {row.get('Preço no Cartão', 0):.2f}")

    st.markdown("### 📋 Tabela Consolidada")
    st.dataframe(df, use_container_width=True)


def processar_dataframe(df: pd.DataFrame, frete_total: float, custos_extras: float,
                        modo_margem: str, margem_fixa: float) -> pd.DataFrame:
    """Processa dataframe para adicionar custos rateados e preços finais."""
    if df.empty:
        return df

    df = df.copy()
    # Acrescentar custos extras rateados ao custo unitário
    rateio_unitario = 0
    if frete_total > 0 or custos_extras > 0:
        qtd_total = df["Qtd"].sum()
        if qtd_total > 0:
            rateio_unitario = (frete_total + custos_extras) / qtd_total

    df["Custos Extras Produto"] = df["Custos Extras Produto"].fillna(0) + rateio_unitario
    df["Custo Total Unitário"] = df["Custo Unitário"] + df["Custos Extras Produto"]

    if modo_margem == "Margem fixa":
        df["Margem (%)"] = margem_fixa

    df["Preço à Vista"] = df["Custo Total Unitário"] * (1 + df["Margem (%)"] / 100)
    # Considerando taxa do cartão como 11.28%, dividimos por 0.8872 para obter o preço no cartão
    df["Preço no Cartão"] = df["Preço à Vista"] / 0.8872

    return df


def extrair_produtos_pdf(pdf_file) -> list:
    """Simulação de extração de produtos de PDF (substitua pelo OCR real)."""
    # Aqui você poderia usar PyPDF2, pdfplumber ou OCR.
    # Por enquanto retorna um exemplo fixo.
    return [
        {"Produto": "Shampoo", "Qtd": 10, "Custo Unitário": 15.0},
        {"Produto": "Condicionador", "Qtd": 8, "Custo Unitário": 18.0},
    ]


def load_csv_github(url: str) -> pd.DataFrame:
    """Carrega CSV público do GitHub."""
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Erro ao carregar CSV do GitHub: {e}")
        return pd.DataFrame()


# ===============================
# Estado da sessão e variáveis fixas
# ===============================
if "produtos_manuais" not in st.session_state:
    st.session_state.produtos_manuais = pd.DataFrame(columns=[
        "Produto", "Qtd", "Custo Unitário", "Custos Extras Produto", "Margem (%)", "Imagem"
    ])
if "rateio_manual" not in st.session_state:
    st.session_state["rateio_manual"] = 0.0

frete_total = 0.0
custos_extras = 0.0
modo_margem_global = "Margem fixa"
margem_fixa_sidebar = 30.0

# URL do CSV do GitHub
ARQ_CAIXAS = "https://raw.githubusercontent.com/ribeiromendes5014-design/Precificar/main/precificacao.csv"

# dicionário para armazenar imagens em memória para PDF
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
                    modo_margem_global,
                    margem_fixa_sidebar
                )
                st.success("✅ Produtos precificados com sucesso!")
                exibir_resultados(st.session_state.df_produtos_geral, imagens_dict)
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
                    df_exemplo, frete_total, custos_extras, modo_margem_global, margem_fixa_sidebar
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

        rateio_calculado = (frete_manual + extras_manual) / qtd_total_manual
        st.session_state["rateio_manual"] = round(rateio_calculado, 4)
        st.markdown(f"💰 **Rateio Unitário Calculado:** R$ {rateio_calculado:,.4f}")

    with aba_prec_manual:
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
            with aba_prec_manual:
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
                    modo_margem_global,
                    margem_fixa_sidebar
                )
                st.success("✅ Produto adicionado!")
            else:
                st.warning("⚠️ Preencha todos os campos obrigatórios.")

    if not st.session_state.produtos_manuais.empty:
        exibir_resultados(st.session_state.df_produtos_geral, imagens_dict)

        st.markdown(f"**Preço à Vista Calculado:** R$ {preco_a_vista_calc:,.2f}")
        st.markdown(f"**Preço no Cartão Calculado:** R$ {preco_no_cartao_calc:,.2f}")

        with st.form("form_submit_manual"):
            adicionar_produto = st.form_submit_button("➕ Adicionar Produto (Manual)")
            if adicionar_produto:
                if produto and quantidade > 0 and valor_pago >= 0:
                    imagem_bytes = None
                    if imagem_file is not None:
                        imagem_bytes = imagem_file.read()
                        # registrar no dicionário para o PDF
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
                    # recalcular df geral
                    st.session_state.df_produtos_geral = processar_dataframe(
                        st.session_state.produtos_manuais,
                        frete_total,
                        custos_extras,
                        modo_margem_global,
                        margem_fixa_sidebar
                    )
                    st.success("✅ Produto adicionado!")
                else:
                    st.warning("⚠️ Preencha todos os campos obrigatórios.")

        # se já houverem produtos manuais cadastrados, exibir resultados
        if not st.session_state.produtos_manuais.empty:
            exibir_resultados(st.session_state.df_produtos_geral, imagens_dict)

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
                df_exemplo, frete_total, custos_extras, modo_margem_global, margem_fixa_sidebar
            )
            st.success("✅ CSV carregado e processado com sucesso!")
            exibir_resultados(st.session_state.df_produtos_geral, imagens_dict)
        else:
            st.warning("⚠️ Não foi possível carregar o CSV do GitHub.")


