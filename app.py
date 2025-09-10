import streamlit as st

videos = st.secrets["google_drive"]["videos"]
titulos = st.secrets["google_drive"]["titulos"]
descricoes = st.secrets["google_drive"]["descricoes"]

# Função para gerar link embed do Google Drive com autoplay
video_embed_link = gerar_link_embed(videos[idx])
def gerar_link_embed(video_id):
    return f"https://drive.google.com/uc?export=preview&id={video_id}&autoplay=1"

# Estado para índice do vídeo atual
if "video_index" not in st.session_state:
    st.session_state.video_index = 0

idx = st.session_state.video_index

# Layout: botões para navegar entre vídeos
col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    if st.button("⬆️ Anterior") and idx > 0:
        st.session_state.video_index -= 1
with col3:
    if st.button("⬇️ Próximo") and idx < len(video_ids) - 1:
        st.session_state.video_index += 1

# Gera o link do vídeo atual
video_embed_link = gerar_link_embed(video_ids[idx])

# Exibe o vídeo em iframe responsivo
st.markdown(
    f"""
    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
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

# Mostra título e descrição do vídeo
st.markdown(f"### {titulos[idx]}")
st.write(descricoes[idx])


