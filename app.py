import streamlit as st

# ==========================
# 1. Dados dos vídeos no secrets
# ==========================
videos = st.secrets["google_drive"]["videos"]
titulos = st.secrets["google_drive"]["titulos"]
descricoes = st.secrets["google_drive"]["descricoes"]

# ==========================
# 2. Inicializar índice do vídeo no session_state
# ==========================
if "video_index" not in st.session_state:
    st.session_state.video_index = 0

idx = st.session_state.video_index

# ==========================
# 3. Navegação com botões (estilo TikTok: anterior e próximo)
# ==========================
col1, col2, col3 = st.columns([1, 6, 1])

with col1:
    if st.button("⬆️ Anterior") and idx > 0:
        st.session_state.video_index -= 1

with col3:
    if st.button("⬇️ Próximo") and idx < len(videos) - 1:
        st.session_state.video_index += 1

# ==========================
# 4. Exibir vídeo com autoplay usando st.video()
# ==========================
st.video(videos[idx], start_time=0)

# ==========================
# 5. Mostrar título e descrição do vídeo
# ==========================
st.markdown(f"### {titulos[idx]}")
st.write(descricoes[idx])
