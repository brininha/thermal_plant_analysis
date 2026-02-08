import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
import cv2
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from flirimageextractor import FlirImageExtractor
import tempfile
import os
import io

st.set_page_config(layout="wide", page_title="Debug V4: Validação de Pipeline")

st.title("🔬 Debug: validação técnica")
st.markdown("""
Esta ferramenta disseca o processo de extração de dados para provar a integridade da Versão 4.
Etapas analisadas:
1.  **Ingestão:** Leitura dos metadados brutos (Raw Thermal).
2.  **Sincronização:** Upscaling da matriz térmica (80x60 -> 320x240).
3.  **Geometria:** Template Matching para localizar o recorte visual na matriz térmica.
4.  **Amostragem:** Extração estatística dos dados físicos e visualização matricial.
""")

# --- UPLOAD ---
arquivo = st.file_uploader("Carregar imagem térmica (JPG)", type=['jpg', 'jpeg'])

if arquivo:
    # Salvar temp para a biblioteca ler
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        arquivo.seek(0)
        tmp.write(arquivo.read())
        tmp_path = tmp.name
    
    # Abrir visual
    arquivo.seek(0)
    img_pil = Image.open(arquivo)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("1. Definição da ROI (Visual)")
        st.caption("Faça um recorte na planta. O sistema tentará achar esses mesmos pixels na matriz térmica cega.")
        img_crop = st_cropper(img_pil, realtime_update=True, box_color='#FF0000', aspect_ratio=None, key="crop_debug")
        st.image(img_crop, caption="Recorte Visual (RGB)", width=150)
        
        validar = st.button("🔍 Executar validação de pipeline", type="primary")

    if validar:
        with st.spinner("Desconstruindo o arquivo..."):
            try:
                # --- ETAPA 1: EXTRAÇÃO RADIOMÉTRICA (PROVA DE DADOS FÍSICOS) ---
                flir = FlirImageExtractor(is_debug=False)
                flir.process_image(tmp_path)
                raw_thermal = flir.get_thermal_np() # Matriz original (ex: 80x60)
                
                # Prova 1: Histograma de Temperaturas (Float) vs Cores (0-255)
                fig1, (ax1a, ax1b) = plt.subplots(1, 2, figsize=(10, 4))
                
                # Plot da Matriz Bruta
                sns.heatmap(raw_thermal, ax=ax1a, cmap="inferno", cbar=False)
                ax1a.set_title(f"A. Matriz bruta do sensor\nDimensões: {raw_thermal.shape}", fontsize=10)
                
                # Histograma de valores
                vals = raw_thermal.flatten()
                ax1b.hist(vals, bins=30, color='orange', edgecolor='black')
                ax1b.set_title(f"B. Histograma radiométrico\nIntervalo: {vals.min():.1f}°C a {vals.max():.1f}°C", fontsize=10)
                ax1b.set_xlabel("Temperatura (°C) - Note: não é 0-255")
                
                st.divider()
                st.header("Etapa 1: ingestão de dados brutos")
                st.write("Prova que estamos lendo física (Graus Celsius com casas decimais), não cores (Inteiros 0-255).")
                st.pyplot(fig1)

                # --- ETAPA 2: SINCRONIZAÇÃO (PROVA DE UPSCALING) ---
                img_vis_np = np.array(img_pil)
                h_vis, w_vis = img_vis_np.shape[:2]
                
                # Resize
                thermal_upscaled = cv2.resize(raw_thermal, (w_vis, h_vis), interpolation=cv2.INTER_CUBIC)
                
                fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(10, 4))
                ax2a.imshow(img_vis_np)
                ax2a.set_title(f"Visual ({w_vis}x{h_vis})", fontsize=10)
                
                im_b = ax2b.imshow(thermal_upscaled, cmap='inferno')
                ax2b.set_title(f"Térmica redimensionada ({w_vis}x{h_vis})\nsincronizada", fontsize=10)
                
                st.divider()
                st.header("Etapa 2: sincronização espacial")
                st.write(f"Prova da adaptação da resolução nativa ({raw_thermal.shape}) para a resolução visual ({img_vis_np.shape[:2]}).")
                st.pyplot(fig2)

                # --- ETAPA 3: TEMPLATE MATCHING (PROVA DE GEOMETRIA) ---
                # Converter visual para gray
                full_gray = cv2.cvtColor(img_vis_np, cv2.COLOR_RGB2GRAY)
                crop_np = np.array(img_crop)
                crop_gray = cv2.cvtColor(crop_np, cv2.COLOR_RGB2GRAY)
                
                # Executar Matching
                res = cv2.matchTemplate(full_gray, crop_gray, cv2.TM_CCOEFF_NORMED)
                _, _, _, max_loc = cv2.minMaxLoc(res)
                x, y = max_loc
                h_c, w_c = crop_gray.shape[:2]
                
                # Criar visualização do "Alvo"
                fig3, ax3 = plt.subplots(figsize=(8, 5))
                ax3.imshow(thermal_upscaled, cmap='gray') # Fundo térmico
                # Desenhar retângulo onde achou
                rect = plt.Rectangle((x, y), w_c, h_c, linewidth=3, edgecolor='r', facecolor='none')
                ax3.add_patch(rect)
                ax3.set_title("C. Localização do recorte na matriz térmica", fontsize=12)
                
                st.divider()
                st.header("Etapa 3: localização da ROI")
                st.write("O algoritmo varre a imagem para encontrar onde o recorte visual se encaixa na matriz de temperatura.")
                st.pyplot(fig3)

                # --- ETAPA 4: AMOSTRAGEM FINAL (COM MATRIZ COLORIDA) ---
                roi_thermal = thermal_upscaled[y:y+h_c, x:x+w_c]
                
                # Prepara amostra pequena (10x10) para o gráfico ser legível
                amostra_h = min(10, h_c)
                amostra_w = min(10, w_c)
                roi_sample = roi_thermal[:amostra_h, :amostra_w]
                
                media = np.mean(roi_thermal)
                desvio = np.std(roi_thermal)
                
                st.divider()
                st.header("Etapa 4: resultado final e prova visual")

                c_res1, c_res2 = st.columns([1, 2])
                
                with c_res1:
                    st.markdown("### Estatística global")
                    st.caption("Calculada sobre a área TOTAL recortada")
                    st.metric("Temp. média real", f"{media:.2f} °C")
                    st.metric("Desvio padrão", f"{desvio:.2f}")
                    st.info("A matriz ao lado funciona como uma 'lupa', exibindo os valores exatos dos primeiros 100 pixels (10x10) do recorte para comprovar a precisão decimal.")

                with c_res2:
                    st.markdown("### 🔬 Lupa de dados (matriz 10x10)")
                    
                    fig4, ax4 = plt.subplots(figsize=(10, 8))
                    
                    # Gera o heatmap com números escritos (annot=True)
                    sns.heatmap(roi_sample, annot=True, fmt=".1f", cmap="viridis", 
                                ax=ax4, cbar=True, linewidths=.5, linecolor='black',
                                cbar_kws={'label': 'Temperatura (°C)'})
                    
                    ax4.set_title("Matriz física de temperatura (pixels individuais)", fontsize=12)
                    st.pyplot(fig4)

            except Exception as e:
                st.error(f"Erro na validação: {e}")
            finally:
                if os.path.exists(tmp_path): os.remove(tmp_path)