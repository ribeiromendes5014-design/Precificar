import streamlit as st

# Dados (pode puxar do secrets)
videos = st.secrets["google_drive"]["videos"]
titulos = st.secrets["google_drive"]["titulos"]
descricoes = st.secrets["google_drive"]["descricoes"]

if "video_index" not in st.session_state:
    st.session_state.video_index = 0

idx = st.session_state.video_index

st.markdown(
    """
    <style>
    body {
        margin: 0;
        overflow-y: scroll;
        height: 100vh;
        scroll-snap-type: y mandatory;
    }
    .video-container {
        scroll-snap-align: start;
        height: 100vh;
        width: 100vw;
        position: relative;
        display: flex;
        justify-content: center;
        align-items: center;
        background-color: black;
        color: white;
        flex-direction: column;
    }
    video {
        max-height: 90vh;
        max-width: 100vw;
        object-fit: contain;
    }
    .info {
        position: absolute;
        bottom: 20px;
        left: 20px;
        background: rgba(0,0,0,0.5);
        padding: 10px;
        border-radius: 10px;
        max-width: 90vw;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Container para os vídeos (vamos criar um div com todos os vídeos para efeito scroll)
container_html = ""
for i, video_url in enumerate(videos):
    # Para autoplay só do vídeo atual
    autoplay = "autoplay muted loop playsinline" if i == idx else ""
    container_html += f"""
    <div class="video-container" id="video{i}">
        <video {autoplay} controls preload="metadata" >
            <source src="{video_url}" type="video/mp4">
            Seu navegador não suporta vídeo.
        </video>
        <div class="info">
            <h2>{titulos[i]}</h2>
            <p>{descricoes[i]}</p>
        </div>
    </div>
    """

st.markdown(container_html, unsafe_allow_html=True)

# JS para detectar scroll e enviar para Streamlit
scroll_js = """
<script>
const totalVideos = %d;
let lastIndex = %d;
window.onscroll = function() {
    let vh = window.innerHeight;
    for(let i=0; i<totalVideos; i++) {
        let el = document.getElementById("video"+i);
        let rect = el.getBoundingClientRect();
        if(rect.top >= 0 && rect.top < vh/2) {
            if(i !== lastIndex){
                lastIndex = i;
                // Enviar mensagem para Streamlit para atualizar estado
                window.parent.postMessage({isStreamlitMessage: true, type: 'streamlit:setComponentValue', value: i}, '*');
            }
            break;
        }
    }
}
</script>
""" % (len(videos), idx)

st.components.v1.html(scroll_js, height=0, width=0)

# Atualizar índice no Streamlit baseado no valor recebido do JS
idx_novo = st.experimental_get_query_params().get("video_index", [idx])[0]
try:
    idx_novo = int(idx_novo)
except:
    idx_novo = idx

if idx_novo != idx:
    st.session_state.video_index = idx_novo
    st.experimental_rerun()
