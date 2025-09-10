import streamlit as st

# ==============================
# 1️⃣ Puxar vídeos dos Secrets
# ==============================
ids = st.secrets["google_drive"]["videos"]
titulos = st.secrets["google_drive"]["titulos"]
descricoes = st.secrets["google_drive"]["descricoes"]

# ==============================
# 2️⃣ Inicializar índice do vídeo
# ==============================
if "video_index" not in st.session_state:
    st.session_state.video_index = 0

# ==============================
# 3️⃣ Função para gerar link do Google Drive
# ==============================
def id_para_link(id_video):
    return f"https://drive.google.com/uc?export=preview&id={id_video}"

# ==============================
# 4️⃣ Navegação
# ==============================
col1, col2, col3 = st.columns([1, 6, 1])

with col1:
    if st.button("⬆️ Anterior") and st.session_state.video_index > 0:
        st.session_state.video_index -= 1

with col3:
    if st.button("⬇️ Próximo") and st.session_state.video_index < len(ids) - 1:
        st.session_state.video_index += 1

# ==============================
# 5️⃣ Exibir vídeo atual
# ==============================
i = st.session_state.video_index
video_url = id_para_link(ids[i])

# Exibir vídeo em estilo vertical (estilo TikTok)
st.markdown(
    f"""
    <div style="position: relative; padding-bottom: 177.78%; height: 0; overflow: hidden;">
        <iframe src="{video_url}"
                frameborder="0"
                allowfullscreen
                style="position: absolute; top:0; left: 0; width: 100%; height: 100%;">
        </iframe>
    </div>
    """,
    unsafe_allow_html=True
)

# Nome e descrição do vídeo
st.markdown(f"### {titulos[i]}")
st.markdown(f"{descricoes[i]}")
