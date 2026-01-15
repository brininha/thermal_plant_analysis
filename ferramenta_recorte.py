import streamlit as st
import os
import cv2
import numpy as np
import pandas as pd
from PIL import Image, ExifTags
from streamlit_cropper import st_cropper

# --- CONFIGURAÇÕES ---
PASTA_IMAGENS = 'imagens'
PASTA_SAIDA = 'dados_processados'
ARQUIVO_CSV = 'dados_termografia_final.csv'

# Calibração de Temperatura (Escalas Dinâmicas)
ESCALAS_CAMERA = {
    '21': (15.0, 25.0),
    '27': (20.0, 35.0),
    '35': (25.0, 45.0),
    '45': (35.0, 55.0),
}
ESCALA_PADRAO = (20.0, 40.0)

if not os.path.exists(PASTA_SAIDA):
    os.makedirs(PASTA_SAIDA)

# --- FUNÇÕES ---
def pixel_para_temp(valor_pixel, temp_min, temp_max):
    return temp_min + (valor_pixel / 255.0) * (temp_max - temp_min)

def carregar_imagem_pil(caminho):
    """ Carrega imagem e corrige a rotação EXIF """
    try:
        image = Image.open(caminho)
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation': break
        exif = image._getexif()
        if exif:
            exif = dict(exif.items())
            val = exif.get(orientation)
            if val == 3: image = image.rotate(180, expand=True)
            elif val == 6: image = image.rotate(270, expand=True)
            elif val == 8: image = image.rotate(90, expand=True)
        return image
    except:
        return Image.open(caminho)

def extrair_metadados(nome_arquivo):
    partes = os.path.splitext(nome_arquivo)[0].split('_')
    if len(partes) >= 6:
        return {
            'ID_Planta': partes[0], 'Temp_Ambiente': partes[1], 'Tratamento': partes[2],
            'Periodo': partes[3], 'Tipo': partes[4], 'Replica': partes[5], 'Arquivo_Original': nome_arquivo
        }
    return None

def processar_e_salvar(nome_arquivo, img_recortada_pil):
    # Converte o recorte (que vem em PIL) para Numpy/OpenCV
    img_recortada = np.array(img_recortada_pil)
    
    # Se for RGB, converte pra BGR (padrão OpenCV) para salvar a imagem correntamente
    # E para Grayscale para calcular a temperatura
    if len(img_recortada.shape) == 3:
        img_bgr_salvar = cv2.cvtColor(img_recortada, cv2.COLOR_RGB2BGR)
        recorte_gray = cv2.cvtColor(img_recortada, cv2.COLOR_RGB2GRAY)
    else:
        img_bgr_salvar = img_recortada
        recorte_gray = img_recortada

    # Identifica Escala de Temperatura
    meta = extrair_metadados(nome_arquivo)
    temp_min, temp_max = ESCALA_PADRAO
    if meta and meta['Temp_Ambiente'] in ESCALAS_CAMERA:
        temp_min, temp_max = ESCALAS_CAMERA[meta['Temp_Ambiente']]
    
    # Estatísticas (Filtro Otsu para limpar seleção)
    blur = cv2.GaussianBlur(recorte_gray, (5,5), 0)
    _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pixels = recorte_gray[mask > 0]
    
    # Se a seleção for muito pequena ou Otsu falhar, usa tudo
    if len(pixels) < 10: pixels = recorte_gray.flatten()
    
    temps = [pixel_para_temp(p, temp_min, temp_max) for p in pixels]
    
    stats = {
        'Temp_Media': np.mean(temps), 'Temp_Max': np.max(temps),
        'Temp_Min': np.min(temps), 'Desvio_Padrao': np.std(temps),
        'Area_Pixels': len(pixels)
    }
    
    # Salvar Imagem Recortada
    nome_proc = f"proc_{nome_arquivo}"
    cv2.imwrite(os.path.join(PASTA_SAIDA, nome_proc), img_bgr_salvar)
    
    # Salvar CSV
    nova_linha = {**meta, **stats, 'Caminho_Imagem_Proc': nome_proc}
    
    if os.path.exists(ARQUIVO_CSV):
        df = pd.read_csv(ARQUIVO_CSV)
        df = df[df['Arquivo_Original'] != nome_arquivo]
        df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
    else:
        df = pd.DataFrame([nova_linha])
    
    df.to_csv(ARQUIVO_CSV, index=False)
    return stats

# --- INTERFACE ---
st.set_page_config(page_title="Ferramenta Cropper", layout="wide")
st.title("✂️ Recorte Inteligente de Plantas")

if 'arquivos' not in st.session_state:
    st.session_state['arquivos'] = sorted([f for f in os.listdir(PASTA_IMAGENS) if 'thermal' in f.lower() and f.endswith('.jpg')])

if not st.session_state['arquivos']:
    st.error("Sem imagens térmicas.")
    st.stop()

if 'idx' not in st.session_state: st.session_state['idx'] = 0

# Navegação
c1, c2, c3 = st.columns([1, 2, 1])
if c1.button("⬅️ Anterior") and st.session_state['idx'] > 0:
    st.session_state['idx'] -= 1
    st.rerun()
if c3.button("Próxima ➡️") and st.session_state['idx'] < len(st.session_state['arquivos']) - 1:
    st.session_state['idx'] += 1
    st.rerun()

arquivo = st.session_state['arquivos'][st.session_state['idx']]

# Carrega Imagem
img_pil = carregar_imagem_pil(os.path.join(PASTA_IMAGENS, arquivo))

col_crop, col_dados = st.columns([2, 1])

with col_crop:
    st.markdown(f"**Imagem:** {arquivo}")
    st.caption("Arraste os cantos da caixa para selecionar a planta.")
    
    # O COMPONENTE MÁGICO
    # Ele retorna a imagem já recortada em tempo real
    img_recortada = st_cropper(
        img_pil,
        realtime_update=True,
        box_color='#FF0000', # Caixa vermelha
        aspect_ratio=None    # Livre (retângulo ou quadrado)
    )

with col_dados:
    st.subheader("Resultado")
    st.image(img_recortada, caption="Preview do Recorte", width=200)
    
    if st.button("💾 CONFIRMAR E PRÓXIMA", type="primary", use_container_width=True):
        stats = processar_e_salvar(arquivo, img_recortada)
        
        st.toast(f"✅ Salvo! Temp Média: {stats['Temp_Media']:.1f}°C")
        
        # Avança automático
        if st.session_state['idx'] < len(st.session_state['arquivos']) - 1:
            st.session_state['idx'] += 1
            st.rerun()
        else:
            st.success("Você finalizou todas as imagens!")