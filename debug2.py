import streamlit as st
import pandas as pd
import numpy as np
from flirimageextractor import FlirImageExtractor
import tempfile
import os

st.set_page_config(page_title="Debug radiométrico", page_icon="🌡️")

st.title("🛠️ Debug: extrator de dados brutos")
st.markdown("""
Esta ferramenta extrai a matriz numérica de temperatura de uma imagem FLIR 
e calcula estatísticas exatas baseadas nos sensores (sem estimativa visual).
""")

uploaded_file = st.file_uploader("Arraste a imagem térmica (JPG)", type=["jpg", "jpeg"])

if uploaded_file is not None:
    # 1. Salvar arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        uploaded_file.seek(0)
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        # 2. Extração Radiométrica
        flir = FlirImageExtractor(is_debug=False)
        flir.process_image(tmp_path)
        matriz_termica = flir.get_thermal_np() # Matriz numpy pura (float)

        # ---------------------------------------------------------
        # NOVO: Cálculo e Exibição das Estatísticas
        # ---------------------------------------------------------
        temp_min = np.min(matriz_termica)
        temp_max = np.max(matriz_termica)
        temp_media = np.mean(matriz_termica)
        
        st.divider()
        st.subheader("📊 Estatísticas da imagem inteira")
        
        col1, col2, col3 = st.columns(3)
        
        # O delta_color="inverse" deixa o vermelho para o quente e azul para o frio
        col1.metric("Mínima", f"{temp_min:.2f} °C", delta_color="normal")
        col2.metric("Máxima", f"{temp_max:.2f} °C", delta="-Max", delta_color="inverse")
        col3.metric("Média global", f"{temp_media:.2f} °C")
        
        st.info(f"Dimensões do sensor: {matriz_termica.shape[1]}px (largura) x {matriz_termica.shape[0]}px (altura)")
        st.divider()
        # ---------------------------------------------------------

        # 3. Conversão para Tabela (Pandas DataFrame)
        df = pd.DataFrame(matriz_termica)

        # 4. Visualização Rápida (Mapa de Calor)
        st.subheader("Matriz bruta")
        st.dataframe(df.style.format("{:.2f}").background_gradient(cmap="RdYlBu_r"), height=400)

        # 5. Botão de Download
        csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        
        st.download_button(
            label="📥 Baixar planilha completa (.csv)",
            data=csv,
            file_name=f"dados_termicos_{uploaded_file.name}.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
    
    finally:
        # Limpeza
        if os.path.exists(tmp_path):
            os.remove(tmp_path)