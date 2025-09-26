import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
from io import BytesIO, StringIO
import base64
import hashlib
import ast
from datetime import datetime

# ===============================
# FUNÇÕES AUXILIARES GLOBAIS
# ===============================

# Configurações Telegram
# O token hardcoded agora é um fallback. O token real deve estar em st.secrets["telegram_token"].
HARDCODED_TELEGRAM_TOKEN = "8412132908:AAG8N_vFzkpVNX-WN3bwT0Vl3H41Q-9Rfw4"
TELEGRAM_CHAT_ID = "-1003030758192"
TOPICO_ID = 28 # ID do tópico (thread) no grupo Telegram


# --- NOVA FUNÇÃO: FORMATACAO BRL ---
def formatar_brl(valor, decimais=2, prefixo=True):
    """Formata um valor float para a string de moeda BRL (R$ X.XXX,XX/XXXX) de forma simplificada."""
    try:
        valor = float(valor)
    except (ValueError, TypeError):
        return "R$ 0,00" if prefixo else "0,00"

    # 1. Formata para o número correto de decimais (usando ponto como separador decimal temporário)
    s = f"{valor:.{decimais}f}"
    
    # 2. Divide em parte inteira e decimal
    if '.' in s:
        inteira, decimal = s.split('.')
    else:
        inteira = s
        decimal = '0' * decimais

    # 3. Formata a parte inteira para separador de milhar (ponto)
    inteira_formatada = ''
    for i, digito in enumerate(reversed(inteira)):
        # Adiciona ponto a cada 3 dígitos (exceto no primeiro)
        if i > 0 and i % 3 == 0 and digito.isdigit():
            inteira_formatada += '.'
        inteira_formatada += digito
    
    # Inverte a string e remove o prefixo de ponto extra (se houver)
    inteira_formatada = inteira_formatada[::-1].lstrip('.')

    # 4. Junta tudo com a vírgula como separador decimal
    resultado = f"{inteira_formatada},{decimal}"
    if prefixo:
        return f"R$ {resultado}"
    return resultado
# --- FIM NOVA FUNÇÃO ---


def gerar_pdf(df: pd.DataFrame) -> BytesIO:
    """Gera um PDF formatado a partir do DataFrame de precificação, incluindo a URL da imagem."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Relatório de Precificação", 0, 1, "C")
    pdf.ln(5)

    # Configurações de fonte para tabela
    pdf.set_font("Arial", "B", 10) # Fonte menor para caber mais dados

    # Definindo largura das colunas (em mm)
    col_widths = {
        "Produto": 40,
        "Qtd": 15,
        "Custo Unitário": 25,
        "Margem (%)": 20,
        "Preço à Vista": 25,
        "Preço no Cartão": 25,
        "URL da Imagem": 40 # Nova coluna para a URL
    }
    
    # Define as colunas a serem exibidas no PDF
    pdf_cols = [col for col in col_widths.keys() if col in df.columns or col == "Custo Unitário"]
    current_widths = [col_widths[col] for col in pdf_cols]

    # Cabeçalho da tabela
    for col_name, width in zip(pdf_cols, current_widths):
        pdf.cell(width, 10, col_name, border=1, align='C')
    pdf.ln()

    # Fonte para corpo da tabela
    pdf.set_font("Arial", "", 8) # Fonte ainda menor para caber a URL

    if df.empty:
        pdf.cell(sum(current_widths), 10, "Nenhum produto cadastrado.", border=1, align="C")
        pdf.ln()
    else:
        # Itera pelas linhas e escreve na tabela
        for idx, row in df.iterrows():
            if "Produto" in pdf_cols:
                pdf.cell(col_widths["Produto"], 10, str(row.get("Produto", "")), border=1)
            if "Qtd" in pdf_cols:
                pdf.cell(col_widths["Qtd"], 10, str(row.get("Qtd", 0)), border=1, align="C")
            if "Custo Unitário" in pdf_cols:
                # Usa o Custo Total Unitário para o relatório, se disponível
                custo_unit_val = row.get("Custo Total Unitário", row.get("Custo Unitário", 0.0))
                pdf.cell(col_widths["Custo Unitário"], 10, formatar_brl(custo_unit_val), border=1, align="R")
            if "Margem (%)" in pdf_cols:
                pdf.cell(col_widths["Margem (%)"], 10, f"{row.get('Margem (%)', 0.0):.2f}%", border=1, align="R")
            if "Preço à Vista" in pdf_cols:
                pdf.cell(col_widths["Preço à Vista"], 10, formatar_brl(row.get('Preço à Vista', 0.0)), border=1, align="R")
            if "Preço no Cartão" in pdf_cols:
                pdf.cell(col_widths["Preço no Cartão"], 10, formatar_brl(row.get('Preço no Cartão', 0.0)), border=1, align="R")
            
            # --- NOVO: URL da Imagem no PDF ---
            if "URL da Imagem" in pdf_cols:
                url_display = str(row.get("Imagem_URL", ""))
                # Limita o tamanho da URL para não quebrar o layout
                if len(url_display) > 35:
                    url_display = url_display[:32] + "..."
                pdf.cell(col_widths["URL da Imagem"], 10, url_display, border=1, align="L", link=str(row.get("Imagem_URL", "")))
            # --- FIM NOVO ---
                
            pdf.ln()

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_bytes)


def enviar_pdf_telegram(pdf_bytesio, df_produtos: pd.DataFrame, thread_id=None):
    """Envia o arquivo PDF e a primeira imagem (se existir) em mensagens separadas para o Telegram."""
    
    token = st.secrets.get("telegram_token", HARDCODED_TELEGRAM_TOKEN)
    
    image_url = None
    image_caption = "Relatório de Precificação"
    
    if not df_produtos.empty and "Imagem_URL" in df_produtos.columns:
        # Tenta encontrar a primeira linha com um produto para usar a imagem e dados
        first_valid_row = df_produtos.iloc[0]
        url = first_valid_row.get("Imagem_URL")
        produto = first_valid_row.get("Produto", "Produto")
        
        if isinstance(url, str) and url.startswith("http"):
            image_url = url
            # Adiciona informações de filtro ao caption, se aplicável
            date_info = ""
            if "Data_Cadastro" in df_produtos.columns and not df_produtos['Data_Cadastro'].empty:
                try:
                    # Converte para datetime e remove NaN/NaT
                    valid_dates = pd.to_datetime(df_produtos['Data_Cadastro'], errors='coerce').dropna()
                    if not valid_dates.empty:
                        min_date = valid_dates.min().strftime('%d/%m/%Y')
                        max_date = valid_dates.max().strftime('%d/%m/%Y')
                        if min_date == max_date:
                            date_info = f"\n🗓️ Cadastro em: {min_date}"
                        else:
                            date_info = f"\n🗓️ Período: {min_date} a {max_date}"
                except Exception:
                    pass # Ignora erros de formatação
            
            # Use df_produtos.shape[0] para obter a contagem de produtos no relatório
            count_info = f"\n📦 Total de Produtos: {df_produtos.shape[0]}"

            image_caption = f"📦 Produto Principal: {produto}{count_info}{date_info}\n\n[Relatório de Precificação em anexo]"

    # Se não houver URL de imagem, usa um caption simples
    caption_doc = image_caption if not image_url else "[Relatório de Precificação em anexo]"

    # 1. Envia o PDF (mensagem principal)
    
    url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
    files_doc = {'document': ('precificacao.pdf', pdf_bytesio, 'application/pdf')}
    data_doc = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption_doc}
    if thread_id is not None:
        data_doc["message_thread_id"] = thread_id
    
    resp_doc = requests.post(url_doc, data=data_doc, files=files_doc)
    resp_doc_json = resp_doc.json()
    
    if not resp_doc_json.get("ok"):
         st.error(f"❌ Erro ao enviar PDF: {resp_doc_json.get('description')}")
         return

    st.success("✅ PDF enviado para o Telegram.")
    
    # 2. Envia a foto (se existir) em uma mensagem separada
    if image_url:
        try:
            url_photo = f"https://api.telegram.org/bot{token}/sendPhoto"
            
            # Faz o Telegram buscar a foto diretamente da URL
            data_photo = {
                "chat_id": TELEGRAM_CHAT_ID, 
                "photo": image_url,
                "caption": f"🖼️ Foto do Produto Principal: {produto}"
            }
            if thread_id is not None:
                data_photo["message_thread_id"] = thread_id

            resp_photo = requests.post(url_photo, data=data_photo)
            resp_photo_json = resp_photo.json()

            if resp_photo_json.get("ok"):
                st.success("✅ Foto do produto principal enviada com sucesso!")
            else:
                 st.warning(f"❌ Erro ao enviar a foto do produto: {resp_photo_json.get('description')}")
                 
        except Exception as e:
            st.warning(f"⚠️ Erro ao tentar enviar a imagem. Erro: {e}")
            

def exibir_resultados(df: pd.DataFrame, imagens_dict: dict):
    """Exibe os resultados de precificação com tabela e imagens dos produtos."""
    if df is None or df.empty:
        st.info("⚠️ Nenhum produto disponível para exibir.")
        return

    st.subheader("📊 Resultados Detalhados da Precificação")

    for idx, row in df.iterrows():
        with st.container():
            cols = st.columns([1, 3])
            with cols[0]:
                img_to_display = None
                
                # 1. Tenta carregar imagem do dicionário (upload manual)
                img_to_display = imagens_dict.get(row.get("Produto"))

                # 2. Tenta carregar imagem dos bytes (se persistido)
                if img_to_display is None and row.get("Imagem") is not None and isinstance(row.get("Imagem"), bytes):
                    try:
                        img_to_display = row.get("Imagem")
                    except Exception:
                        pass # Continua tentando a URL

                # 3. Tenta carregar imagem da URL (se persistido)
                img_url = row.get("Imagem_URL")
                if img_to_display is None and img_url and isinstance(img_url, str) and img_url.startswith("http"):
                    st.image(img_url, width=100, caption="URL")
                elif img_to_display:
                    st.image(img_to_display, width=100, caption="Arquivo")
                else:
                    st.write("🖼️ N/A")
                    
            with cols[1]:
                st.markdown(f"**{row.get('Produto', '—')}**")
                st.write(f"📦 Quantidade: {row.get('Qtd', '—')}")
                
                # Exibição dos novos campos, se existirem
                cor = row.get('Cor', 'N/A')
                marca = row.get('Marca', 'N/A')
                data_cadastro = row.get('Data_Cadastro', 'N/A')
                if data_cadastro != 'N/A':
                    try:
                        # Formata a data para dd/mm/yyyy para exibição
                        date_dt = pd.to_datetime(data_cadastro, errors='coerce')
                        if pd.notna(date_dt):
                            data_cadastro = date_dt.strftime('%d/%m/%Y')
                        else:
                            data_cadastro = 'Data Inválida'
                    except Exception:
                        pass # Mantém o valor original se a formatação falhar

                st.write(f"🎨 Cor: {cor} | 🏭 Marca: {marca} | 📅 Cadastro: {data_cadastro}")

                custo_base = row.get('Custo Unitário', 0.0)
                custo_total_unitario = row.get('Custo Total Unitário', custo_base)

                st.write(f"💰 Custo Base: {formatar_brl(custo_base)}")

                custos_extras_prod = row.get('Custos Extras Produto', 0.0)
                # Puxa o rateio global unitário calculado na função processar_dataframe
                rateio_global_unitario = row.get('Rateio Global Unitário', 0.0) 
                
                # Exibe a soma dos custos extras específicos (se houver) e o rateio global por unidade
                # NOTA: O Custos Extras Produto é o valor ESPECÍFICO do produto (digitado pelo usuário ou 0.0)
                rateio_e_extras_display = custos_extras_prod + rateio_global_unitario
                st.write(f"🛠 Rateio/Extras (Total/Un.): {formatar_brl(rateio_e_extras_display, decimais=4)}") # Exibição com mais decimais para rateio
                
                if 'Custo Total Unitário' in df.columns:
                    st.write(f"💸 Custo Total/Un: **{formatar_brl(custo_total_unitario)}**")

                if "Margem (%)" in df.columns:
                    margem_val = row.get("Margem (%)", 0)
                    try:
                        margem_float = float(margem_val)
                    except Exception:
                        margem_float = 0
                    st.write(f"📈 Margem: **{margem_float:.2f}%**")
                
                if "Preço à Vista" in df.columns:
                    st.write(f"💰 Preço à Vista: **{formatar_brl(row.get('Preço à Vista', 0))}**")
                if "Preço no Cartão" in df.columns:
                    st.write(f"💳 Preço no Cartão: **{formatar_brl(row.get('Preço no Cartão', 0))}**")


def processar_dataframe(df: pd.DataFrame, frete_total: float, custos_extras: float,
                        modo_margem: str, margem_fixa: float) -> pd.DataFrame:
    """Processa o DataFrame, aplica rateio, margem e calcula os preços finais."""
    if df.empty:
        # Garante que o DataFrame tem as colunas mínimas esperadas para evitar erros de índice/coluna
        return pd.DataFrame(columns=[
            "Produto", "Qtd", "Custo Unitário", "Custos Extras Produto", 
            "Custo Total Unitário", "Margem (%)", "Preço à Vista", "Preço no Cartão", 
            "Rateio Global Unitário", "Cor", "Marca", "Data_Cadastro" # ADDED NEW COLUMNS
        ])

    df = df.copy()

    # Garante que as colunas de custo e quantidade são numéricas
    for col in ["Qtd", "Custo Unitário", "Margem (%)", "Custos Extras Produto"]:
        if col in df.columns:
            # Tenta converter, falhando para 0.0 se não for possível
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        elif col not in df.columns:
            # Adiciona colunas ausentes com valor 0.0 se for necessário para o cálculo
            df[col] = 0.0
    
    # Garante as novas colunas de texto/data
    for col in ["Cor", "Marca", "Data_Cadastro"]:
         if col not in df.columns:
            df[col] = "" # Inicializa como string vazia

    # --- Cálculo do Rateio Global ---
    # NOTA: O cálculo do rateio é sempre baseado nos totais para consistência.
    qtd_total = df["Qtd"].sum()
    rateio_unitario = 0.0
    if qtd_total > 0:
        rateio_unitario = (frete_total + custos_extras) / qtd_total

    # Salva o rateio global unitário na coluna que será persistida e usada no cálculo total
    df["Rateio Global Unitário"] = rateio_unitario 
    
    # O Custo Total Unitário é a soma do Custo Unitário Base + Custos Específicos + Rateio Global.
    df["Custo Total Unitário"] = df["Custo Unitário"] + df["Custos Extras Produto"] + df["Rateio Global Unitário"]

    # Processar margens conforme o modo selecionado
    if "Margem (%)" not in df.columns:
        df["Margem (%)"] = margem_fixa
    
    df["Margem (%)"] = df["Margem (%)"].apply(lambda x: x if pd.notna(x) else margem_fixa)


    # Calcular os preços finais
    df["Preço à Vista"] = df["Custo Total Unitário"] * (1 + df["Margem (%)"] / 100)
    # Taxa de cartão de 11.28% (para chegar a 0.8872 do preço de venda)
    df["Preço no Cartão"] = df["Preço à Vista"] / 0.8872

    # Seleciona as colunas relevantes para o DataFrame final de exibição
    cols_to_keep = [
        "Produto", "Qtd", "Custo Unitário", "Custos Extras Produto", 
        "Custo Total Unitário", "Margem (%)", "Preço à Vista", "Preço no Cartão", 
        "Imagem", "Imagem_URL", "Rateio Global Unitário", 
        "Cor", "Marca", "Data_Cadastro" # ADDED NEW COLUMNS
    ]
    
    # Mantém apenas as colunas que existem no DF
    df_final = df[[col for col in cols_to_keep if col in df.columns]]

    return df_final


def load_csv_github(url: str) -> pd.DataFrame:
    """Carrega um arquivo CSV diretamente do GitHub."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        return df
    except Exception as e:
        # st.error(f"Erro ao carregar CSV do GitHub: {e}") # Silencioso na inicialização
        return pd.DataFrame()


def extrair_produtos_pdf(pdf_file) -> list:
    """Função mock para extração de produtos de PDF."""
    st.warning("Função extrair_produtos_pdf ainda não implementada. Use o carregamento manual ou de CSV.")
    return []


# Funções auxiliares gerais
def baixar_csv_aba(df, nome_arquivo, key_suffix=""):
    """Cria um botão de download para o DataFrame."""
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        f"⬇️ Baixar {nome_arquivo}",
        data=csv,
        file_name=nome_arquivo,
        mime="text/csv",
        key=f"download_button_{nome_arquivo.replace('.', '_')}_{key_suffix}"
    )

def _opcoes_para_lista(opcoes_str):
    """Converte string de opções separadas por vírgula em lista."""
    if pd.isna(opcoes_str) or not str(opcoes_str).strip():
        return []
    return [o.strip() for o in str(opcoes_str).split(",") if o.strip()]

def hash_df(df):
    """
    Gera um hash para o DataFrame para detecção de mudanças.
    Usa um método mais robusto que evita problemas com dtypes específicos do pandas.
    """
    # Cria uma cópia para evitar SettingWithCopyWarning e garante que não há colunas de bytes,
    # que devem ser removidas ANTES de chamar esta função (o que já está sendo feito no precificacao_completa).
    df_temp = df.copy() 
    
    # Converte colunas 'object' para string explícita para garantir hash consistente, se necessário,
    # mas o pd.util.hash_pandas_object deve lidar bem com 'object' por padrão.
    # O foco aqui é garantir que todos os dados estejam em formatos que o hash consiga processar.
    
    try:
        return hashlib.md5(pd.util.hash_pandas_object(df_temp, index=False).values).hexdigest()
    except Exception as e:
        # Se houver erro, tenta converter colunas object para string
        for col in df_temp.select_dtypes(include=['object']).columns:
             df_temp[col] = df_temp[col].astype(str)
        try:
             return hashlib.md5(pd.util.hash_pandas_object(df_temp, index=False).values).hexdigest()
        except Exception as inner_e:
             st.error(f"Erro interno no hash do DataFrame: {inner_e}")
             return "error" # Retorna um valor fixo em caso de falha grave
             

def salvar_csv_no_github(token, repo, path, dataframe, branch="main", mensagem="Atualização via app"):
    """Salva o DataFrame como CSV no GitHub via API."""
    from requests import get, put
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    # O DF de entrada já deve estar sem colunas de bytes (ex: 'Imagem')
    conteudo = dataframe.to_csv(index=False)
    conteudo_b64 = base64.b64encode(conteudo.encode()).decode()
    headers = {"Authorization": f"token {token}"}
    r = get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None
    payload = {"message": mensagem, "content": conteudo_b64, "branch": branch}
    if sha: payload["sha"] = sha
    r2 = put(url, headers=headers, json=payload)
    if r2.status_code in (200, 201):
        # st.success(f"✅ Arquivo `{path}` atualizado no GitHub!")
        pass # Mensagem de sucesso silenciosa para evitar ruído
    else:
        st.error(f"❌ Erro ao salvar `{path}`: {r2.text}")


# Definições de colunas base
INSUMOS_BASE_COLS_GLOBAL = ["Nome", "Categoria", "Unidade", "Preço Unitário (R$)"]
PRODUTOS_BASE_COLS_GLOBAL = ["Produto", "Custo Total", "Preço à Vista", "Preço no Cartão", "Margem (%)"]
COLUNAS_CAMPOS = ["Campo", "Aplicação", "Tipo", "Opções"]

def col_defs_para(aplicacao: str):
    """Filtra as definições de colunas extras por aplicação."""
    if "campos" not in st.session_state or st.session_state.campos.empty:
        return pd.DataFrame(columns=COLUNAS_CAMPOS)
    df = st.session_state.campos
    return df[(df["Aplicação"] == aplicacao) | (df["Aplicação"] == "Ambos")].copy()

def garantir_colunas_extras(df: pd.DataFrame, aplicacao: str) -> pd.DataFrame:
    """Adiciona colunas extras ao DataFrame se ainda não existirem."""
    defs = col_defs_para(aplicacao)
    for campo in defs["Campo"].tolist():
        if campo not in df.columns:
            df[campo] = ""
    return df

def render_input_por_tipo(label, tipo, opcoes, valor_padrao=None, key=None):
    """Renderiza um widget Streamlit baseado no tipo de campo definido."""
    if tipo == "Número":
        valor = float(valor_padrao) if (valor_padrao is not None and str(valor_padrao).strip() != "") else 0.0
        return st.number_input(label, min_value=0.0, format="%.2f", value=valor, key=key)
    elif tipo == "Seleção":
        lista = _opcoes_para_lista(opcoes)
        valor_display = str(valor_padrao) if valor_padrao is not None and pd.notna(valor_padrao) else ""
        
        # Garante que o valor padrão atual está na lista, senão adiciona ele na primeira posição
        if valor_display not in lista and valor_display != "":
            lista = [valor_display] + [o for o in lista if o != valor_display]
        elif valor_display == "" and lista:
            # Se não tem valor padrão e tem opções, usa a primeira como default
            valor_display = lista[0]
            
        try:
            index_padrao = lista.index(valor_display) if valor_display in lista else 0
        except ValueError:
            index_padrao = 0
            
        return st.selectbox(label, options=lista, index=index_padrao, key=key)
    else:
        return st.text_input(label, value=str(valor_padrao) if valor_padrao is not None else "", key=key)


# ==============================================================================
# FUNÇÃO DA PÁGINA: PRECIFICAÇÃO COMPLETA
# ==============================================================================

def precificacao_completa():
    st.title("📊 Gestão de Precificação e Produtos")
    
    # --- Configurações do GitHub para SALVAR ---
    GITHUB_TOKEN = st.secrets.get("github_token", "TOKEN_FICTICIO")
    GITHUB_REPO = "ribeiromendes5014-design/Precificar"
    GITHUB_BRANCH = "main"
    PATH_PRECFICACAO = "precificacao.csv"
    ARQ_CAIXAS = "https://raw.githubusercontent.com/ribeiromendes5014-design/Precificar/main/" + PATH_PRECFICACAO
    imagens_dict = {}
    
    # ----------------------------------------------------
    # Inicialização e Configurações de Estado
    # ----------------------------------------------------
    
    # Inicialização de variáveis de estado da Precificação
    if "produtos_manuais" not in st.session_state:
        st.session_state.produtos_manuais = pd.DataFrame(columns=[
            "Produto", "Qtd", "Custo Unitário", "Custos Extras Produto", "Margem (%)", "Imagem", "Imagem_URL",
            "Cor", "Marca", "Data_Cadastro" # NOVAS COLUNAS
        ])
    
    # Inicializa o rateio global unitário que será usado na exibição e cálculo
    if "rateio_global_unitario_atual" not in st.session_state:
        st.session_state["rateio_global_unitario_atual"] = 0.0

    # === Lógica de Carregamento AUTOMÁTICO do CSV do GitHub (Correção de Persistência) ===
    if "produtos_manuais_loaded" not in st.session_state:
        df_loaded = load_csv_github(ARQ_CAIXAS)
        
        # Define as colunas de ENTRADA (apenas dados brutos)
        cols_entrada = ["Produto", "Qtd", "Custo Unitário", "Margem (%)", "Custos Extras Produto", "Imagem", "Imagem_URL", "Cor", "Marca", "Data_Cadastro"]
        df_base_loaded = df_loaded[[col for col in cols_entrada if col in df_loaded.columns]].copy()
        
        # Garante que as colunas de ENTRADA existam, mesmo que vazias
        if "Custos Extras Produto" not in df_base_loaded.columns: df_base_loaded["Custos Extras Produto"] = 0.0
        if "Imagem" not in df_base_loaded.columns: df_base_loaded["Imagem"] = None
        if "Imagem_URL" not in df_base_loaded.columns: df_base_loaded["Imagem_URL"] = ""
        # NOVAS COLUNAS
        if "Cor" not in df_base_loaded.columns: df_base_loaded["Cor"] = ""
        if "Marca" not in df_base_loaded.columns: df_base_loaded["Marca"] = ""
        # Garante que Data_Cadastro é string para evitar problemas de tipo no Streamlit
        if "Data_Cadastro" not in df_base_loaded.columns: df_base_loaded["Data_Cadastro"] = pd.to_datetime('today').normalize().strftime('%Y-%m-%d')
        

        if not df_base_loaded.empty:
            st.session_state.produtos_manuais = df_base_loaded.copy()
            st.success(f"✅ {len(df_base_loaded)} produtos carregados do GitHub.")
        else:
            # Caso não consiga carregar do GitHub, usa dados de exemplo
            st.info("⚠️ Não foi possível carregar dados persistidos. Usando dados de exemplo.")
            exemplo_data = [
                {"Produto": "Produto A", "Qtd": 10, "Custo Unitário": 5.0, "Margem (%)": 20, "Preço à Vista": 6.0, "Preço no Cartão": 6.5, "Cor": "Azul", "Marca": "Genérica", "Data_Cadastro": pd.to_datetime('2024-01-01').strftime('%Y-%m-%d')},
                {"Produto": "Produto B", "Qtd": 5, "Custo Unitário": 3.0, "Margem (%)": 15, "Preço à Vista": 3.5, "Preço no Cartão": 3.8, "Cor": "Vermelho", "Marca": "XYZ", "Data_Cadastro": pd.to_datetime('2024-02-15').strftime('%Y-%m-%d')},
            ]
            df_base = pd.DataFrame(exemplo_data)
            df_base["Custos Extras Produto"] = 0.0
            df_base["Imagem"] = None
            df_base["Imagem_URL"] = ""
            st.session_state.produtos_manuais = df_base.copy()
            
        st.session_state.df_produtos_geral = processar_dataframe(
            st.session_state.produtos_manuais, 
            st.session_state.get("frete_manual", 0.0), 
            st.session_state.get("extras_manual", 0.0), 
            st.session_state.get("modo_margem", "Margem fixa"), 
            st.session_state.get("margem_fixa", 30.0)
        )
        st.session_state.produtos_manuais_loaded = True
    # === FIM da Lógica de Carregamento Automático ===


    if "frete_manual" not in st.session_state:
        st.session_state["frete_manual"] = 0.0
    if "extras_manual" not in st.session_state:
        st.session_state["extras_manual"] = 0.0
    if "modo_margem" not in st.session_state:
        st.session_state["modo_margem"] = "Margem fixa"
    if "margem_fixa" not in st.session_state:
        st.session_state["margem_fixa"] = 30.0

    frete_total = st.session_state.get("frete_manual", 0.0)
    custos_extras = st.session_state.get("extras_manual", 0.0)
    modo_margem = st.session_state.get("modo_margem", "Margem fixa")
    margem_fixa = st.session_state.get("margem_fixa", 30.0)
    
    # Recalcula o DF geral para garantir que ele reflita o rateio mais recente (caso frete/extras tenham mudado)
    st.session_state.df_produtos_geral = processar_dataframe(
        st.session_state.produtos_manuais, frete_total, custos_extras, modo_margem, margem_fixa
    )


    # ----------------------------------------------------
    # Lógica de Salvamento Automático
    # ----------------------------------------------------
    
    # 1. Cria uma cópia do DF geral e remove colunas não-CSV-serializáveis (Imagem)
    df_to_save = st.session_state.df_produtos_geral.drop(columns=["Imagem"], errors='ignore')
    
    # 2. Inicializa o hash para o estado da precificação
    if "hash_precificacao" not in st.session_state:
        st.session_state.hash_precificacao = hash_df(df_to_save)

    # 3. Verifica se houve alteração nos produtos (agora baseado no DF completo)
    novo_hash = hash_df(df_to_save)
    if novo_hash != st.session_state.hash_precificacao:
        if novo_hash != "error": # Evita salvar se a função hash falhou
            salvar_csv_no_github(
                GITHUB_TOKEN,
                GITHUB_REPO,
                PATH_PRECFICACAO,
                df_to_save, # Salva o df completo com custos e preços
                GITHUB_BRANCH,
                mensagem="♻️ Alteração automática na precificação"
            )
            st.session_state.hash_precificacao = novo_hash


    # ----------------------------------------------------
    # Definição das Abas Principais de Gestão
    # ----------------------------------------------------

    tab_cadastro, tab_relatorio, tab_tabela_principal = st.tabs([
        "✍️ Cadastro de Produtos",
        "🔍 Relatórios & Filtro",
        "📊 Tabela Principal"
    ])


    # =====================================
    # ABA 1: Cadastro de Produtos
    # =====================================
    with tab_cadastro:
        st.header("✍️ Cadastro Manual e Rateio Global")
        
        # --- Sub-abas para Cadastro e Rateio ---
        aba_prec_manual, aba_rateio = st.tabs(["➕ Novo Produto", "🔢 Rateio Manual"])

        with aba_rateio:
            st.subheader("🔢 Cálculo de Rateio Unitário (Frete + Custos Extras)")
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                frete_manual = st.number_input("🚚 Frete Total (R$)", min_value=0.0, step=0.01, key="frete_manual")
            with col_r2:
                extras_manual = st.number_input("🛠 Custos Extras (R$)", min_value=0.0, step=0.01, key="extras_manual")
            with col_r3:
                qtd_total_produtos = st.session_state.df_produtos_geral["Qtd"].sum() if "Qtd" in st.session_state.df_produtos_geral.columns else 0
                st.markdown(f"📦 **Qtd. Total de Produtos no DF:** {qtd_total_produtos}")
                
            qtd_total_manual = st.number_input("📦 Qtd. Total para Rateio (ajuste)", min_value=1, step=1, value=qtd_total_produtos or 1, key="qtd_total_manual_override")


            if qtd_total_manual > 0:
                rateio_calculado = (frete_total + custos_extras) / qtd_total_manual
            else:
                rateio_calculado = 0.0
            
            # --- ATUALIZA O RATEIO GLOBAL UNITÁRIO NO ESTADO DA SESSÃO ---
            st.session_state["rateio_global_unitario_atual"] = round(rateio_calculado, 4)
            # --- FIM ATUALIZAÇÃO ---

            st.session_state["rateio_manual"] = round(rateio_calculado, 4)
            st.markdown(f"💰 **Rateio Unitário Calculado:** {formatar_brl(rateio_calculado, decimais=4)}")
            
            if st.button("🔄 Aplicar Novo Rateio aos Produtos Existentes", key="aplicar_rateio_btn"):
                # O processar_dataframe usará o frete_total e custos_extras atualizados.
                st.session_state.df_produtos_geral = processar_dataframe(
                    st.session_state.produtos_manuais,
                    frete_total,
                    custos_extras,
                    modo_margem,
                    margem_fixa
                )
                st.success("✅ Rateio aplicado! Verifique a tabela principal.")
                st.rerun() 

        with aba_prec_manual:
            # Rerunning para limpar o formulário após a adição
            if st.session_state.get("rerun_after_add"):
                del st.session_state["rerun_after_add"]
                st.rerun()

            st.subheader("➕ Adicionar Novo Produto")

            col1, col2 = st.columns(2)
            with col1:
                produto = st.text_input("📝 Nome do Produto", key="input_produto_manual")
                quantidade = st.number_input("📦 Quantidade", min_value=1, step=1, key="input_quantidade_manual")
                valor_pago = st.number_input("💰 Valor Pago (Custo Unitário Base R$)", min_value=0.0, step=0.01, key="input_valor_pago_manual")
                
                # --- Campo de URL da Imagem ---
                imagem_url = st.text_input("🔗 URL da Imagem (opcional)", key="input_imagem_url_manual")
                # --- FIM NOVO ---
                
                # --- NOVOS CAMPOS DE CADASTRO ---
                cor_produto = st.text_input("🎨 Cor do Produto", key="input_cor_manual")
                marca_produto = st.text_input("🏭 Marca", key="input_marca_manual")
                # --- FIM NOVOS CAMPOS DE CADASTRO ---

                
            with col2:
                # Informa o rateio atual (fixo)
                rateio_global_unitario = st.session_state.get("rateio_global_unitario_atual", 0.0)
                st.info(f"O Rateio Global/Un. (R$ {formatar_brl(rateio_global_unitario, decimais=4, prefixo=False)}) será adicionado automaticamente ao custo total.")
                
                # O valor inicial do custo extra deve ser 0.0, 
                # pois o rateio GLOBAL é adicionado automaticamente na função processar_dataframe.
                # O usuário deve inserir aqui APENAS custos específicos que não fazem parte do rateio global.
                custo_extra_produto = st.number_input(
                    "💰 Custos Extras ESPECÍFICOS do Produto (R$)", 
                    min_value=0.0, 
                    step=0.01, 
                    value=0.0, # Valor padrão 0.0, como o esperado.
                    key="input_custo_extra_manual"
                )
                
                preco_final_sugerido = st.number_input(
                    "💸 Valor Final Sugerido (Preço à Vista) (R$)", min_value=0.0, step=0.01, key="input_preco_sugerido_manual"
                )
                
                # Uploader de arquivo (mantido como alternativa)
                imagem_file = st.file_uploader("🖼️ Foto do Produto (Upload - opcional)", type=["png", "jpg", "jpeg"], key="imagem_manual")


            # Custo total unitário AQUI PARA FINS DE PRÉ-CÁLCULO E PREVIEW
            custo_total_unitario_com_rateio = valor_pago + custo_extra_produto + rateio_global_unitario


            margem_manual = 30.0 # Valor padrão

            if preco_final_sugerido > 0:
                preco_a_vista_calc = preco_final_sugerido
                
                if custo_total_unitario_com_rateio > 0:
                    # Calcula a margem REQUERIDA para atingir o preço sugerido
                    margem_calculada = (preco_a_vista_calc / custo_total_unitario_com_rateio - 1) * 100
                else:
                    margem_calculada = 0.0
                    
                margem_manual = round(margem_calculada, 2)
                st.info(f"🧮 Margem necessária calculada: **{margem_manual:,.2f}%**")
            else:
                # Se não há preço sugerido, usa a margem padrão (ou a digitada) para calcular o preço.
                margem_manual = st.number_input("🧮 Margem de Lucro (%)", min_value=0.0, value=30.0, key="input_margem_manual")
                preco_a_vista_calc = custo_total_unitario_com_rateio * (1 + margem_manual / 100)
                
            preco_no_cartao_calc = preco_a_vista_calc / 0.8872

            st.markdown(f"**Preço à Vista Calculado:** {formatar_brl(preco_a_vista_calc)}")
            st.markdown(f"**Preço no Cartão Calculado:** {formatar_brl(preco_no_cartao_calc)}")
            
            # O `Custos Extras Produto` salvo no DF manual é o valor digitado (Custos Extras ESPECÍFICOS), 
            # pois o rateio global será adicionado no `processar_dataframe` com base no estado global.
            custo_extra_produto_salvar = custo_extra_produto # É o valor específico (R$ 0,00 por padrão)

            with st.form("form_submit_manual"):
                adicionar_produto = st.form_submit_button("➕ Adicionar Produto (Manual)")
                if adicionar_produto:
                    if produto and quantidade > 0 and valor_pago >= 0:
                        imagem_bytes = None
                        url_salvar = ""

                        # Prioriza o arquivo uploaded, se existir
                        if imagem_file is not None:
                            imagem_bytes = imagem_file.read()
                            imagens_dict[produto] = imagem_bytes # Guarda para exibição na sessão
                        
                        # Se não houver upload, usa a URL
                        elif imagem_url.strip():
                            url_salvar = imagem_url.strip()

                        # --- CAPTURA DA DATA DE CADASTRO ---
                        data_cadastro = pd.to_datetime('today').normalize().strftime('%Y-%m-%d')
                        # --- FIM CAPTURA DA DATA DE CADASTRO ---


                        # Salva na lista manual apenas os dados de ENTRADA do usuário (Custo Extra ESPECÍFICO)
                        novo_produto_data = {
                            "Produto": [produto],
                            "Qtd": [quantidade],
                            "Custo Unitário": [valor_pago],
                            "Custos Extras Produto": [custo_extra_produto_salvar], # Salva apenas o custo específico (sem o rateio)
                            "Margem (%)": [margem_manual],
                            "Imagem": [imagem_bytes],
                            "Imagem_URL": [url_salvar], # Salva a URL para persistência
                            "Cor": [cor_produto.strip()],
                            "Marca": [marca_produto.strip()],
                            "Data_Cadastro": [data_cadastro]
                        }
                        novo_produto = pd.DataFrame(novo_produto_data)

                        # Adiciona ao produtos_manuais
                        st.session_state.produtos_manuais = pd.concat(
                            [st.session_state.produtos_manuais, novo_produto],
                            ignore_index=True
                        ).reset_index(drop=True)
                        
                        # Processa e atualiza o DataFrame geral
                        # O rateio global será recalculado em processar_dataframe usando frete_total e custos_extras
                        st.session_state.df_produtos_geral = processar_dataframe(
                            st.session_state.produtos_manuais,
                            frete_total,
                            custos_extras,
                            modo_margem,
                            margem_fixa
                        )
                        st.success("✅ Produto adicionado!")
                        st.session_state["rerun_after_add"] = True 
                    else:
                        st.warning("⚠️ Preencha todos os campos obrigatórios (Produto, Qtd, Custo Unitário).")

            st.markdown("---")
            st.subheader("Produtos adicionados manualmente (com botão de Excluir individual)")

            # Exibir produtos com botão de exclusão
            produtos = st.session_state.produtos_manuais

            if produtos.empty:
                st.info("⚠️ Nenhum produto cadastrado manualmente.")
            else:
                if "produto_para_excluir" not in st.session_state:
                    st.session_state["produto_para_excluir"] = None
                
                # Exibir produtos individualmente com a opção de exclusão
                for i, row in produtos.iterrows():
                    cols = st.columns([4, 1])
                    with cols[0]:
                        custo_unit_val = row.get('Custo Unitário', 0.0)
                        st.write(f"**{row['Produto']}** — Quantidade: {row['Qtd']} — Custo Unitário Base: {formatar_brl(custo_unit_val)}")
                    with cols[1]:
                        if st.button(f"❌ Excluir", key=f"excluir_{i}"):
                            st.session_state["produto_para_excluir"] = i
                            break 

                # Processamento da Exclusão
                if st.session_state["produto_para_excluir"] is not None:
                    i = st.session_state["produto_para_excluir"]
                    produto_nome_excluido = produtos.loc[i, "Produto"]
                    
                    # 1. Remove do DataFrame manual
                    st.session_state.produtos_manuais = produtos.drop(i).reset_index(drop=True)
                    
                    # 2. Recalcula e atualiza o DataFrame geral
                    st.session_state.df_produtos_geral = processar_dataframe(
                        st.session_state.produtos_manuais,
                        frete_total,
                        custos_extras,
                        modo_margem,
                        margem_fixa
                    )
                    
                    # 3. Limpa o estado e força o rerun
                    st.session_state["produto_para_excluir"] = None
                    st.success(f"✅ Produto '{produto_nome_excluido}' removido da lista manual.")
                    st.rerun()


    # =====================================
    # ABA 2: Relatórios & Filtro
    # =====================================
    with tab_relatorio:
        st.header("🔍 Relatórios por Período")

        # --- Lógica de Filtro ---
        df_temp_filter = st.session_state.df_produtos_geral.copy()
        df_produtos_filtrado = df_temp_filter.copy() # Default: sem filtro

        if "Data_Cadastro" in df_temp_filter.columns and not df_temp_filter.empty:
            st.subheader("Filtro de Produtos por Data de Cadastro")
            
            # Garante que a coluna 'Data_Cadastro' esteja no formato datetime
            df_temp_filter['Data_Cadastro_DT'] = pd.to_datetime(df_temp_filter['Data_Cadastro'], errors='coerce').dt.normalize()
            
            valid_dates = df_temp_filter['Data_Cadastro_DT'].dropna()
            
            min_date = valid_dates.min().date() if not valid_dates.empty else datetime.today().date()
            max_date = valid_dates.max().date() if not valid_dates.empty else datetime.today().date()
            
            if min_date > max_date: min_date = max_date 

            # Define as datas de início e fim. Usa o máximo/mínimo do DF como padrão.
            # Inicializa o estado se for a primeira vez
            if 'data_inicio_filtro' not in st.session_state:
                st.session_state.data_inicio_filtro = min_date
            if 'data_fim_filtro' not in st.session_state:
                st.session_state.data_fim_filtro = max_date


            # Input de data
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                data_inicio = st.date_input(
                    "📅 Data de Início", 
                    value=st.session_state.data_inicio_filtro,
                    min_value=min_date,
                    max_value=max_date,
                    key="input_data_inicio_report" # Chave diferente para evitar conflito
                )
            with col_date2:
                data_fim = st.date_input(
                    "📅 Data de Fim", 
                    value=st.session_state.data_fim_filtro,
                    min_value=min_date,
                    max_value=max_date,
                    key="input_data_fim_report" # Chave diferente para evitar conflito
                )
            
            # Aplica o filtro
            dt_inicio = pd.to_datetime(data_inicio).normalize()
            dt_fim = pd.to_datetime(data_fim).normalize()
            
            df_produtos_filtrado = df_temp_filter[
                (df_temp_filter['Data_Cadastro_DT'] >= dt_inicio) &
                (df_temp_filter['Data_Cadastro_DT'] <= dt_fim)
            ].copy()
            
            st.info(f"Mostrando {len(df_produtos_filtrado)} de {len(st.session_state.df_produtos_geral)} produtos de acordo com o filtro de data.")

        else:
            st.warning("Adicione produtos primeiro para habilitar a filtragem por data.")
            # Se não há produtos, o DF filtrado é vazio
            df_produtos_filtrado = pd.DataFrame()


        # --- Geração de Relatório ---
        st.markdown("---")
        if st.button("📤 Gerar PDF e enviar para Telegram (Aplicando Filtro de Data)", key='precificacao_pdf_button'):
            df_relatorio = df_produtos_filtrado
            if df_relatorio.empty:
                st.warning("⚠️ Nenhum produto encontrado com o filtro de data selecionado para gerar PDF.")
            else:
                pdf_io = gerar_pdf(df_relatorio) # Usa o DataFrame filtrado
                # Passa o DataFrame filtrado para a função de envio (para usar data no caption)
                enviar_pdf_telegram(pdf_io, df_relatorio, thread_id=TOPICO_ID)

        # --- Exibição de Resultados Detalhados ---
        st.markdown("---")
        exibir_resultados(df_produtos_filtrado, imagens_dict)


    # =====================================
    # ABA 3: Tabela Principal
    # =====================================
    with tab_tabela_principal:
        st.header("📊 Tabela Principal de Produtos (Edição)")
        st.info("Aqui você pode editar todos os produtos. As mudanças aqui são salvas no GitHub.")
        
        # Colunas completas para exibição na tabela de edição principal (sem filtro)
        cols_display = [
            "Produto", "Qtd", "Custo Unitário", "Custos Extras Produto", 
            "Custo Total Unitário", "Margem (%)", "Preço à Vista", "Preço no Cartão",
            "Cor", "Marca", "Data_Cadastro" 
        ]
        cols_to_show = [col for col in cols_display if col in st.session_state.df_produtos_geral.columns]

        editado_df = st.data_editor(
            st.session_state.df_produtos_geral[cols_to_show],
            num_rows="dynamic", # Permite que o usuário adicione ou remova linhas
            use_container_width=True,
            key="editor_produtos_geral"
        )

        original_len = len(st.session_state.df_produtos_geral)
        edited_len = len(editado_df)
        
        # 1. Lógica de Exclusão
        if edited_len < original_len:
            
            # Filtra os produtos_manuais para manter apenas aqueles que sobreviveram na edição
            produtos_manuais_filtrado = st.session_state.produtos_manuais[
                st.session_state.produtos_manuais['Produto'].isin(editado_df['Produto'])
            ].copy()
            
            st.session_state.produtos_manuais = produtos_manuais_filtrado.reset_index(drop=True)

            # Atualiza o DataFrame geral
            st.session_state.df_produtos_geral = processar_dataframe(
                st.session_state.produtos_manuais, frete_total, custos_extras, modo_margem, margem_fixa
            )
            
            st.success("✅ Produto excluído da lista e sincronizado.")
            st.rerun()
            
        # 2. Lógica de Edição de Dados
        elif not editado_df.equals(st.session_state.df_produtos_geral[cols_to_show]):
            
            # 2a. Sincroniza as mudanças essenciais de volta ao produtos_manuais
            for idx, row in editado_df.iterrows():
                produto_nome = str(row.get('Produto'))
                
                # Encontra o índice correspondente no produtos_manuais
                manual_idx_list = st.session_state.produtos_manuais[st.session_state.produtos_manuais['Produto'] == produto_nome].index.tolist()
                
                if manual_idx_list:
                    manual_idx = manual_idx_list[0]
                    
                    # Sincronização dos campos de ENTRADA editáveis na tabela
                    st.session_state.produtos_manuais.loc[manual_idx, "Produto"] = produto_nome
                    st.session_state.produtos_manuais.loc[manual_idx, "Qtd"] = row.get("Qtd", 1)
                    st.session_state.produtos_manuais.loc[manual_idx, "Custo Unitário"] = row.get("Custo Unitário", 0.0)
                    st.session_state.produtos_manuais.loc[manual_idx, "Margem (%)"] = row.get("Margem (%)", margem_fixa)
                    st.session_state.produtos_manuais.loc[manual_idx, "Custos Extras Produto"] = row.get("Custos Extras Produto", 0.0)
                    # NOVOS CAMPOS DE TEXTO/DATA
                    st.session_state.produtos_manuais.loc[manual_idx, "Cor"] = row.get("Cor", "")
                    st.session_state.produtos_manuais.loc[manual_idx, "Marca"] = row.get("Marca", "")
                    # Data_Cadastro pode ser editada na tabela, então salvamos o valor.
                    st.session_state.produtos_manuais.loc[manual_idx, "Data_Cadastro"] = row.get("Data_Cadastro", pd.to_datetime('today').normalize().strftime('%Y-%m-%d'))


            # 2b. Recalcula o DataFrame geral com base no manual atualizado
            st.session_state.df_produtos_geral = processar_dataframe(
                st.session_state.produtos_manuais, frete_total, custos_extras, modo_margem, margem_fixa
            )
            
            st.success("✅ Dados editados e precificação recalculada!")
            st.rerun()

        # 3. Lógica de Adição (apenas alerta)
        elif edited_len > original_len:
            st.warning("⚠️ Use o formulário 'Novo Produto Manual' ou o carregamento de CSV para adicionar produtos.")
            # Reverte a adição no df_produtos_geral
            st.session_state.df_produtos_geral = st.session_state.df_produtos_geral
            st.rerun() 


    # ----------------------------------------------------
    # Abas de Utilidade (Carregamento/PDF)
    # ----------------------------------------------------
    
    tab_util_pdf, tab_util_github = st.tabs([
        "📄 Carregar PDF",
        "📥 Carregar CSV do GitHub"
    ])

    # === Tab PDF ===
    with tab_util_pdf:
        st.markdown("---")
        pdf_file = st.file_uploader("📤 Selecione o PDF da nota fiscal ou lista de compras", type=["pdf"])
        if pdf_file:
            try:
                produtos_pdf = extrair_produtos_pdf(pdf_file)
                if not produtos_pdf:
                    st.warning("⚠️ Nenhum produto encontrado no PDF. Use o CSV de exemplo abaixo.")
                else:
                    df_pdf = pd.DataFrame(produtos_pdf)
                    df_pdf["Custos Extras Produto"] = 0.0
                    df_pdf["Imagem"] = None
                    df_pdf["Imagem_URL"] = "" # Inicializa nova coluna
                    df_pdf["Cor"] = ""
                    df_pdf["Marca"] = ""
                    df_pdf["Data_Cadastro"] = pd.to_datetime('today').normalize().strftime('%Y-%m-%d')
                    # Concatena os novos produtos ao manual
                    st.session_state.produtos_manuais = pd.concat([st.session_state.produtos_manuais, df_pdf], ignore_index=True)
                    st.session_state.df_produtos_geral = processar_dataframe(
                        st.session_state.produtos_manuais, frete_total, custos_extras, modo_margem, margem_fixa
                    )
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao processar o PDF: {e}")
        else:
            st.info("📄 Faça upload de um arquivo PDF para começar.")
            if st.button("📥 Carregar CSV de exemplo (PDF Tab)"):
                df_exemplo = load_csv_github(ARQ_CAIXAS)
                if not df_exemplo.empty:
                    # Filtra colunas de ENTRADA
                    cols_entrada = ["Produto", "Qtd", "Custo Unitário", "Margem (%)", "Custos Extras Produto", "Imagem", "Imagem_URL", "Cor", "Marca", "Data_Cadastro"]
                    df_base_loaded = df_exemplo[[col for col in cols_entrada if col in df_exemplo.columns]].copy()
                    
                    # Garante colunas ausentes
                    if "Custos Extras Produto" not in df_base_loaded.columns: df_base_loaded["Custos Extras Produto"] = 0.0
                    if "Imagem" not in df_base_loaded.columns: df_base_loaded["Imagem"] = None
                    if "Imagem_URL" not in df_base_loaded.columns: df_base_loaded["Imagem_URL"] = ""
                    if "Cor" not in df_base_loaded.columns: df_base_loaded["Cor"] = ""
                    if "Marca" not in df_base_loaded.columns: df_base_loaded["Marca"] = ""
                    if "Data_Cadastro" not in df_base_loaded.columns: df_base_loaded["Data_Cadastro"] = pd.to_datetime('today').normalize().strftime('%Y-%m-%d')


                    st.session_state.produtos_manuais = df_base_loaded.copy()
                    st.session_state.df_produtos_geral = processar_dataframe(
                        st.session_state.produtos_manuais, frete_total, custos_extras, modo_margem, margem_fixa
                    )
                    st.rerun()

    # === Tab GitHub ===
    with tab_util_github:
        st.markdown("---")
        st.header("📥 Carregar CSV de Precificação do GitHub")
        if st.button("🔄 Carregar CSV do GitHub"):
            df_exemplo = load_csv_github(ARQ_CAIXAS)
            if not df_exemplo.empty:
                # Filtra colunas de ENTRADA
                cols_entrada = ["Produto", "Qtd", "Custo Unitário", "Margem (%)", "Custos Extras Produto", "Imagem", "Imagem_URL", "Cor", "Marca", "Data_Cadastro"]
                
                # Garante que só carrega colunas que existem no CSV e que são de ENTRADA
                df_base_loaded = df_exemplo[[col for col in cols_entrada if col in df_exemplo.columns]].copy()
                
                # Garante colunas ausentes
                if "Custos Extras Produto" not in df_base_loaded.columns: df_base_loaded["Custos Extras Produto"] = 0.0
                if "Imagem" not in df_base_loaded.columns: df_base_loaded["Imagem"] = None
                if "Imagem_URL" not in df_base_loaded.columns: df_base_loaded["Imagem_URL"] = ""
                if "Cor" not in df_base_loaded.columns: df_base_loaded["Cor"] = ""
                if "Marca" not in df_base_loaded.columns: df_base_loaded["Marca"] = ""
                if "Data_Cadastro" not in df_base_loaded.columns: df_base_loaded["Data_Cadastro"] = pd.to_datetime('today').normalize().strftime('%Y-%m-%d')


                st.session_state.produtos_manuais = df_base_loaded.copy()
                
                # Recalcula o DF geral a partir dos dados de entrada carregados
                st.session_state.df_produtos_geral = processar_dataframe(
                    st.session_state.produtos_manuais, frete_total, custos_extras, modo_margem, margem_fixa
                )
                st.success("✅ CSV carregado e processado com sucesso!")
                # Força o rerun para re-aplicar os filtros de data no display
                st.rerun()


# ==============================================================================
# FUNÇÃO DA PÁGINA: PAPELARIA
# ==============================================================================

def papelaria_aba():
    st.title("📚 Gerenciador Papelaria Personalizada")
    
    # Variáveis de Configuração
    GITHUB_TOKEN = st.secrets.get("github_token", "TOKEN_FICTICIO")
    GITHUB_REPO = "ribeiromendes5014-design/Precificar"
    GITHUB_BRANCH = "main"
    URL_BASE = "https://raw.githubusercontent.com/ribeiromendes5014-design/Precificar/main/"
    INSUMOS_CSV_URL = URL_BASE + "insumos_papelaria.csv"
    PRODUTOS_CSV_URL = URL_BASE + "produtos_papelaria.csv"
    CAMPOS_CSV_URL = URL_BASE + "categorias_papelaria.csv"

    # Estado da sessão
    if "insumos" not in st.session_state:
        st.session_state.insumos = load_csv_github(INSUMOS_CSV_URL)

    if "produtos" not in st.session_state:
        st.session_state.produtos = load_csv_github(PRODUTOS_CSV_URL)

    if "campos" not in st.session_state:
        st.session_state.campos = load_csv_github(CAMPOS_CSV_URL)
        
    # Inicializações de estado para garantir DFs não nulos
    if "campos" not in st.session_state or st.session_state.campos.empty:
        st.session_state.campos = pd.DataFrame(columns=["Campo", "Aplicação", "Tipo", "Opções"])

    if "insumos" not in st.session_state or st.session_state.insumos.empty:
        st.session_state.insumos = pd.DataFrame(columns=INSUMOS_BASE_COLS_GLOBAL)

    if "produtos" not in st.session_state or st.session_state.produtos.empty:
        st.session_state.produtos = pd.DataFrame(columns=["Produto", "Custo Total", "Preço à Vista", "Preço no Cartão", "Margem (%)", "Insumos Usados"])
    
    # Garante colunas base
    for col in INSUMOS_BASE_COLS_GLOBAL:
        if col not in st.session_state.insumos.columns:
            st.session_state.insumos[col] = "" if col != "Preço Unitário (R$)" else 0.0

    cols_base_prod = ["Produto"] + [c for c in PRODUTOS_BASE_COLS_GLOBAL if c != "Produto"]
    for col in cols_base_prod:
        if col not in st.session_state.produtos.columns:
            st.session_state.produtos[col] = "" if col not in ["Custo Total", "Preço à Vista", "Preço no Cartão", "Margem (%)"] else 0.0
            
    if "Insumos Usados" not in st.session_state.produtos.columns:
        st.session_state.produtos["Insumos Usados"] = "[]"


    # Garante colunas extras e tipos
    st.session_state.insumos = garantir_colunas_extras(st.session_state.insumos, "Insumos")
    st.session_state.produtos = garantir_colunas_extras(st.session_state.produtos, "Produtos")

    # Verifica se houve alteração nos produtos para salvar automaticamente
    if "hash_produtos" not in st.session_state:
        st.session_state.hash_produtos = hash_df(st.session_state.produtos)

    novo_hash = hash_df(st.session_state.produtos)
    if novo_hash != st.session_state.hash_produtos:
        if novo_hash != "error": # Evita salvar se a função hash falhou
            salvar_csv_no_github(
                GITHUB_TOKEN,
                GITHUB_REPO,
                "produtos_papelaria.csv",
                st.session_state.produtos,
                GITHUB_BRANCH,
                mensagem="♻️ Alteração automática nos produtos"
            )
            st.session_state.hash_produtos = novo_hash

    # Criação das abas
    aba_campos, aba_insumos, aba_produtos = st.tabs(["Campos (Colunas)", "Insumos", "Produtos"])

    # =====================================
    # Aba Campos (gerencia colunas extras)
    # =====================================
    with aba_campos:
        st.header("Campos / Colunas Personalizadas")

        with st.form("form_add_campo"):
            st.subheader("Adicionar novo campo")
            nome_campo = st.text_input("Nome do Campo (será o nome da coluna)", key="novo_campo_nome")
            aplicacao = st.selectbox("Aplicação", ["Insumos", "Produtos", "Ambos"], key="novo_campo_aplicacao")
            tipo = st.selectbox("Tipo", ["Texto", "Número", "Seleção"], key="novo_campo_tipo")
            opcoes = st.text_input("Opções (se 'Seleção', separe por vírgula)", key="novo_campo_opcoes")
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
                        ).reset_index(drop=True)
                        st.success(f"Campo '{nome_campo}' adicionado para {aplicacao}!")
                        
                        st.session_state.insumos = garantir_colunas_extras(st.session_state.insumos, "Insumos")
                        st.session_state.produtos = garantir_colunas_extras(st.session_state.produtos, "Produtos")
                        
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
                f"{row.Campo} · ({row.Aplicação})"
                for _, row in st.session_state.campos.iterrows()
            ]
            escolha = st.selectbox("Escolha um campo", [""] + rotulos, key="campo_escolhido_edit_del")
            
            if escolha:
                idx_list = st.session_state.campos.index[st.session_state.campos.apply(lambda row: f"{row.Campo} · ({row.Aplicação})" == escolha, axis=1)].tolist()
                idx = idx_list[0] if idx_list else None
                
                if idx is not None:
                    campo_atual = st.session_state.campos.loc[idx]
                    
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
                            
                            st.session_state.campos = st.session_state.campos.drop(index=idx).reset_index(drop=True)
                            
                            if aplic in ("Insumos", "Ambos") and nome in st.session_state.insumos.columns:
                                st.session_state.insumos = st.session_state.insumos.drop(columns=[nome], errors='ignore')
                            if aplic in ("Produtos", "Ambos") and nome in st.session_state.produtos.columns:
                                st.session_state.produtos = st.session_state.produtos.drop(columns=[nome], errors='ignore')
                                
                            st.success(f"Campo '{nome}' removido de {aplic}!")
                            st.rerun()
                            
                    if acao_campo == "Editar":
                        with st.form(f"form_edit_campo_{idx}"):
                            novo_nome = st.text_input("Nome do Campo", value=str(campo_atual["Campo"]), key=f"edit_nome_{idx}")
                            
                            aplic_opts = ["Insumos", "Produtos", "Ambos"]
                            aplic_idx = aplic_opts.index(campo_atual["Aplicação"])
                            nova_aplic = st.selectbox("Aplicação", aplic_opts, index=aplic_idx, key=f"edit_aplic_{idx}")
                            
                            tipo_opts = ["Texto", "Número", "Seleção"]
                            tipo_idx = tipo_opts.index(campo_atual["Tipo"])
                            novo_tipo = st.selectbox("Tipo", tipo_opts, index=tipo_idx, key=f"edit_tipo_{idx}")
                            
                            novas_opcoes = st.text_input("Opções (se 'Seleção')", value=str(campo_atual["Opções"]) if pd.notna(campo_atual["Opções"]) else "", key=f"edit_opcoes_{idx}")
                            
                            salvar = st.form_submit_button("Salvar Alterações")
                            
                            if salvar:
                                nome_antigo = campo_atual["Campo"]
                                aplic_antiga = campo_atual["Aplicação"]
                                
                                st.session_state.campos.loc[idx, ["Campo","Aplicação","Tipo","Opções"]] = [
                                    novo_nome, nova_aplic, novo_tipo, novas_opcoes
                                ]
                                
                                renomeou = (str(novo_nome).strip() != str(nome_antigo).strip())
                                
                                if renomeou:
                                    if aplic_antiga in ("Insumos", "Ambos") and nome_antigo in st.session_state.insumos.columns:
                                        st.session_state.insumos = st.session_state.insumos.rename(columns={nome_antigo: novo_nome})
                                    if aplic_antiga in ("Produtos", "Ambos") and nome_antigo in st.session_state.produtos.columns:
                                        st.session_state.produtos = st.session_state.produtos.rename(columns={nome_antigo: novo_nome})
                                        
                                st.session_state.insumos = garantir_colunas_extras(st.session_state.insumos, "Insumos")
                                st.session_state.produtos = garantir_colunas_extras(st.session_state.produtos, "Produtos")

                                st.success("Campo atualizado!")
                                st.rerun()
                            
        if not st.session_state.produtos.empty:
            st.markdown("### 📥 Exportação (aba Campos)")
            baixar_csv_aba(st.session_state.produtos, "produtos_papelaria.csv", key_suffix="campos")


    # =====================================
    # Aba Insumos
    # =====================================
    with aba_insumos:
        st.header("Insumos")

        st.session_state.insumos = garantir_colunas_extras(st.session_state.insumos, "Insumos")

        with st.form("form_add_insumo"):
            st.subheader("Adicionar novo insumo")
            nome_insumo = st.text_input("Nome do Insumo", key="novo_insumo_nome")
            categoria_insumo = st.text_input("Categoria", key="novo_insumo_categoria")
            unidade_insumo = st.text_input("Unidade de Medida (ex: un, kg, m)", key="novo_insumo_unidade")
            preco_insumo = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f", key="novo_insumo_preco")

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
                        
                    st.session_state.insumos = garantir_colunas_extras(st.session_state.insumos, "Insumos")
                    
                    st.session_state.insumos = pd.concat([st.session_state.insumos, pd.DataFrame([novo])], ignore_index=True).reset_index(drop=True)
                    st.success(f"Insumo '{nome_insumo}' adicionado!")
                    st.rerun()

        st.markdown("### Insumos cadastrados")
        ordem_cols = INSUMOS_BASE_COLS_GLOBAL + [c for c in st.session_state.insumos.columns if c not in INSUMOS_BASE_COLS_GLOBAL]
        st.dataframe(st.session_state.insumos.reindex(columns=ordem_cols), use_container_width=True)

        if not st.session_state.insumos.empty:
            insumo_selecionado = st.selectbox(
                "Selecione um insumo",
                [""] + st.session_state.insumos["Nome"].astype(str).fillna("").tolist(),
                key="insumo_escolhido_edit_del"
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
                atual = st.session_state.insumos.loc[idx].fillna("")
                with st.form(f"form_edit_insumo_{idx}"):
                    novo_nome = st.text_input("Nome do Insumo", value=str(atual.get("Nome","")), key=f"edit_insumo_nome_{idx}")
                    nova_categoria = st.text_input("Categoria", value=str(atual.get("Categoria","")), key=f"edit_insumo_categoria_{idx}")
                    nova_unidade = st.text_input("Unidade de Medida (ex: un, kg, m)", value=str(atual.get("Unidade","")), key=f"edit_insumo_unidade_{idx}")
                    novo_preco = st.number_input(
                        "Preço Unitário (R$)", min_value=0.0, format="%.2f",
                        value=float(atual.get("Preço Unitário (R$)", 0.0)),
                        key=f"edit_insumo_preco_{idx}"
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


    # =====================================
    # Aba Produtos
    # =====================================
    with aba_produtos:
        st.header("Produtos")

        with st.form("form_add_produto"):
            st.subheader("Adicionar novo produto")
            nome_produto = st.text_input("Nome do Produto", key="novo_produto_nome")

            if 'Nome' in st.session_state.insumos.columns:
                insumos_disponiveis = st.session_state.insumos["Nome"].dropna().unique().tolist()
            else:
                insumos_disponiveis = []

            insumos_selecionados = st.multiselect("Selecione os insumos usados", insumos_disponiveis, key="novo_produto_insumos_selecionados")

            insumos_usados = []
            custo_total = 0.0

            for insumo in insumos_selecionados:
                dados_insumo = st.session_state.insumos.loc[st.session_state.insumos["Nome"] == insumo].iloc[0]
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

            st.markdown(f"**Custo Total Calculado (Insumos): {formatar_brl(custo_total)}**")

            margem = st.number_input("Margem de Lucro (%)", min_value=0.0, format="%.2f", value=30.0, key="novo_produto_margem")

            preco_vista = custo_total * (1 + margem / 100) if custo_total > 0 else 0.0
            preco_cartao = preco_vista / 0.8872 if preco_vista > 0 else 0.0

            st.markdown(f"💸 **Preço à Vista Calculado:** {formatar_brl(preco_vista)}")
            st.markdown(f"💳 **Preço no Cartão Calculado:** {formatar_brl(preco_cartao)}")

            extras_produtos = col_defs_para("Produtos")
            valores_extras_prod = {}
            if not extras_produtos.empty:
                st.markdown("**Campos extras**")
                for i, row in extras_produtos.reset_index(drop=True).iterrows():
                    campo = row["Campo"]
                    key = f"novo_produto_extra_{row['Campo']}"
                    valores_extras_prod[campo] = render_input_por_tipo(
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

                    # Envio da mensagem para o Telegram (mantido)
                    try:
                        TELEGRAM_TOKEN_SECRET = st.secrets.get("telegram_token", HARDCODED_TELEGRAM_TOKEN)
                        TELEGRAM_CHAT_ID_PROD = TELEGRAM_CHAT_ID
                        THREAD_ID_PROD = 43

                        mensagem = f"<b>📦 Novo Produto Cadastrado:</b>\n"
                        mensagem += f"<b>Produto:</b> {nome_produto}\n"
                        mensagem += "<b>Insumos:</b>\n"

                        for insumo in insumos_usados:
                            nome = insumo['Insumo']
                            qtd = insumo['Quantidade Usada']
                            un = insumo['Unidade']
                            custo = insumo['Custo']
                            mensagem += f"• {nome} - {qtd} {un} ({formatar_brl(custo)})\n" # Formatado em BRL

                        mensagem += f"\n<b>Custo Total:</b> {formatar_brl(custo_total)}\n" # Formatado em BRL
                        mensagem += f"\n<b>Preço à Vista:</b> {formatar_brl(preco_vista)}\n" # Formatado em BRL
                        mensagem += f"\n<b>Preço no Cartão:</b> {formatar_brl(preco_cartao)}\n" # Formatado em BRL

                        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN_SECRET}/sendMessage"
                        payload = {
                            "chat_id": TELEGRAM_CHAT_ID_PROD,
                            "message_thread_id": THREAD_ID_PROD,
                            "text": mensagem,
                            "parse_mode": "HTML"
                        }

                        response = requests.post(telegram_url, json=payload)
                        if response.status_code != 200:
                            st.warning(f"⚠️ Erro ao enviar para Telegram: {response.text}")
                        else:
                             st.success("✅ Mensagem enviada para o Telegram!")

                    except Exception as e:
                        st.warning(f"⚠️ Falha ao tentar enviar para o Telegram: {e}")

                    # Salva no DataFrame local
                    st.session_state.produtos = garantir_colunas_extras(st.session_state.produtos, "Produtos")
                    
                    st.session_state.produtos = pd.concat(
                        [st.session_state.produtos, pd.DataFrame([novo])],
                        ignore_index=True
                    ).reset_index(drop=True)
                    st.success(f"Produto '{nome_produto}' adicionado!")
                    st.rerun()

        st.markdown("### Produtos cadastrados")
        ordem_cols_p = PRODUTOS_BASE_COLS_GLOBAL + ["Insumos Usados"] + [c for c in st.session_state.produtos.columns if c not in PRODUTOS_BASE_COLS_GLOBAL + ["Insumos Usados"]]
        st.dataframe(st.session_state.produtos.reindex(columns=ordem_cols_p), use_container_width=True)

        if not st.session_state.produtos.empty:
            produto_selecionado = st.selectbox(
                "Selecione um produto",
                [""] + st.session_state.produtos["Nome"].astype(str).fillna("").tolist(),
                key="produto_escolhido_edit_del"
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
                atual_p = st.session_state.produtos.loc[idx_p].fillna("")
                with st.form(f"form_edit_produto_{idx_p}"):
                    novo_nome = st.text_input("Nome do Produto", value=str(atual_p.get("Produto","")), key=f"edit_produto_nome_{idx_p}")
                    nova_margem = st.number_input("Margem (%)", min_value=0.0, format="%.2f", value=float(atual_p.get("Margem (%)", 0.0)), key=f"edit_produto_margem_{idx_p}")

                    try:
                        insumos_atual = ast.literal_eval(atual_p.get("Insumos Usados", "[]"))
                        if not isinstance(insumos_atual, list):
                            insumos_atual = []
                    except Exception:
                        insumos_atual = []

                    insumos_disponiveis = st.session_state.insumos["Nome"].dropna().unique().tolist()
                    nomes_pre_selecionados = [i["Insumo"] for i in insumos_atual]
                    insumos_editados = st.multiselect("Selecione os insumos usados", insumos_disponiveis, default=nomes_pre_selecionados, key=f"edit_produto_insumos_selecionados_{idx_p}")

                    insumos_usados_edit = []
                    novo_custo = 0.0

                    for insumo in insumos_editados:
                        dados_insumo = st.session_state.insumos.loc[st.session_state.insumos["Nome"] == insumo].iloc[0]
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

                    st.markdown(f"**Novo custo calculado: {formatar_brl(novo_custo)}**")
                    st.markdown(f"💸 **Preço à Vista Recalculado:** {formatar_brl(novo_vista)}")
                    st.markdown(f"💳 **Preço no Cartão Recalculado:** {formatar_brl(novo_cartao)}")

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
                        # LINHA CORRIGIDA ABAIXO
                        st.session_state.produtos.loc[idx_p, "Margem (%)"] = float(nova_margem)
                        st.session_state.produtos.loc[idx_p, "Insumos Usados"] = str(insumos_usados_edit)
                        for k, v in valores_extras_edit_p.items():
                            st.session_state.produtos.loc[idx_p, k] = v
                        st.success("Produto atualizado!")
                        st.rerun()

        # botão de exportação CSV fora dos forms
        if not st.session_state.produtos.empty:
            baixar_csv_aba(st.session_state.produtos, "produtos_papelaria.csv", key_suffix="produtos")
            
# FIM DA FUNÇÃO papelaria_aba()


# =====================================
# ROTEAMENTO FINAL
# =====================================

if 'main_page_select' not in st.session_state:
    st.session_state.main_page_select = "Precificação"

pagina = st.sidebar.radio(
    "Escolha a página:",
    ["Precificação", "Papelaria"],
    key='main_page_select_widget'
)

if pagina == "Precificação":
    precificacao_completa()
elif pagina == "Papelaria":
    papelaria_aba()
