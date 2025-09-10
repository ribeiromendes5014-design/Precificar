import streamlit as st
import re

videos = st.secrets["google_drive"]["videos"]
titulos = st.secrets["google_drive"]["titulos"]
descricoes = st.secrets["google_drive"]["descricoes"]

if "video_index" not in st.session_state:
    st.session_state.video_index = 0
idx = st.session_state.video_index

col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    if st.button("⬆️ Anterior") and idx > 0:
        st.session_state.video_index -= 1
with col3:
    if st.button("⬇️ Próximo") and idx < len(videos) - 1:
        st.session_state.video_index += 1

def gerar_link_embed(drive_url):
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_url)
    if match:
        video_id = match.group(1)
        # Link direto para preview + autoplay
        return f"https://drive.google.com/uc?export=preview&id={video_id}&autoplay=1"
    else:
        return drive_url

video_embed_link = gerar_link_embed(videos[idx])

# Tentar exibir iframe
try:
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
except:
    # Fallback para st.video() com link download direto
    video_id = re.search(r'/d/([a-zA-Z0-9_-]+)', videos[idx]).group(1)
    video_url_direct = f"https://drive.google.com/uc?export=download&id={video_id}"
    st.video(video_url_direct, start_time=0)

st.markdown(f"### {titulos[idx]}")
st.write(descricoes[idx])
