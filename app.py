import streamlit as st

# Dados do secrets
videos = st.secrets["google_drive"]["videos"]
titulos = st.secrets["google_drive"]["titulos"]
descricoes = st.secrets["google_drive"]["descricoes"]

# Estado do vídeo atual
if "video_index" not in st.session_state:
    st.session_state.video_index = 0

idx = st.session_state.video_index

# Navegação com botões
col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    if st.button("⬆️ Anterior") and idx > 0:
        st.session_state.video_index -= 1
with col3:
    if st.button("⬇️ Próximo") and idx < len(videos) - 1:
        st.session_state.video_index += 1

# Criar link para embed do Google Drive no formato certo, com autoplay
def gerar_link_embed(drive_url):
    # extrai o id do vídeo do link do google drive
    import re
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_url)
    if match:
        video_id = match.group(1)
        # link embed + autoplay
        return f"https://drive.google.com/file/d/{video_id}/preview?autoplay=1"
    else:
        return drive_url  # fallback

video_embed_link = gerar_link_embed(videos[idx])

# Exibir vídeo via iframe com autoplay
st.markdown(
    f"""
    <div style="position: relative; padding-bottom: 177.78%; height: 0; overflow: hidden;">
        <iframe 
            src="{video_embed_link}" 
            frameborder="0" 
            allow="autoplay; encrypted-media" 
            allowfullscreen 
            style="position: absolute; top:0; left: 0; width: 100%; height: 100%;">
        </iframe>
    </div>
    """,
    unsafe_allow_html=True
)

# Título e descrição
st.markdown(f"### {titulos[idx]}")
st.write(descricoes[idx])
