import streamlit as st

# ==========================
# 1. Puxar dados do secrets
# ==========================
videos = st.secrets["google_drive"]["videos"]
titulos = st.secrets["google_drive"]["titulos"]
descricoes = st.secrets["google_drive"]["descricoes"]

# ==========================
# 2. Índice do vídeo
# ==========================
if "video_index" not in st.session_state:
    st.session_state.video_index = 0

idx = st.session_state.video_index

# ==========================
# 3. Navegação estilo TikTok
# ==========================
col1, col2, col3 = st.columns([1, 6, 1])

with col1:
    if st.button("⬆️ Anterior") and idx > 0:
        st.session_state.video_index -= 1

with col3:
    if st.button("⬇️ Próximo") and idx < len(videos) - 1:
        st.session_state.video_index += 1

# ==========================
# 4. Exibir vídeo com iframe
# ==========================
video_url = videos[idx]

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

# ==========================
# 5. Mostrar título e descrição
# ==========================
st.markdown(f"### {titulos[idx]}")
st.write(descricoes[idx])
