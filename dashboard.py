import streamlit as st
import pandas as pd
import plotly.express as px
import os
from PIL import Image, ImageOps # Adicionei ImageOps

# Configuração da Página
st.set_page_config(page_title="Dashboard | Análise térmica", layout="wide", page_icon="🌾")

# Constantes
PASTA_PROCESSADOS = 'dados_processados'
PASTA_IMAGENS = 'imagens' 
ARQUIVO_CSV = 'dados_termografia_final.csv'

# --- FUNÇÕES ---
@st.cache_data
def carregar_dados():
    if not os.path.exists(ARQUIVO_CSV):
        return None
    df = pd.read_csv(ARQUIVO_CSV)
    cols_num = ['Temp_Media', 'Temp_Max', 'Temp_Min', 'Desvio_Padrao']
    for col in cols_num:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def carregar_imagem(caminho):
    """
    Carrega imagem e aplica a rotação EXIF automaticamente
    para que fotos verticais não apareçam deitadas.
    """
    if not os.path.exists(caminho):
        return None
    
    try:
        img = Image.open(caminho)
        # O pulo do gato: esta função lê o metadado e roda os pixels
        img = ImageOps.exif_transpose(img) 
        return img
    except Exception:
        return None

# --- INTERFACE ---
st.title("Análise térmica de cultivos de arroz")
st.markdown("**Monitoramento de estresse térmico e recuperação**")

df = carregar_dados()

if df is None:
    st.error("Arquivo de dados não encontrado! Rode o script 'ferramenta_recorte.py' primeiro.")
    st.stop()

# --- SIDEBAR (FILTROS) ---
st.sidebar.header("Filtros de análise")

tratamentos = df['Tratamento'].unique()
sel_tratamento = st.sidebar.multiselect("Tratamento", tratamentos, default=tratamentos)

periodos = df['Periodo'].unique()
sel_periodo = st.sidebar.multiselect("Período", periodos, default=periodos)

temps = df['Temp_Ambiente'].unique()
sel_temp = st.sidebar.multiselect("Temperatura ambiente", temps, default=temps)

# Aplica filtros
df_filtrado = df[
    (df['Tratamento'].isin(sel_tratamento)) &
    (df['Periodo'].isin(sel_periodo)) &
    (df['Temp_Ambiente'].isin(sel_temp))
]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# --- KPI CARDS ---
col1, col2, col3, col4 = st.columns(4)
total_plantas = df_filtrado['ID_Planta'].nunique()
col1.metric("Total de plantas", total_plantas)
col2.metric("Temp. média geral", f"{df_filtrado['Temp_Media'].mean():.2f} °C")
col3.metric("Temp. máxima absoluta", f"{df_filtrado['Temp_Max'].max():.2f} °C")
col4.metric("Desvio padrão médio", f"{df_filtrado['Desvio_Padrao'].mean():.2f}")

st.divider()

# --- ABAS ---
tab1, tab2 = st.tabs(["📊 Análise estatística", "🖼️ Galeria de imagens"])

with tab1:
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Distribuição de temperatura por tratamento")
        fig_box = px.box(
            df_filtrado, 
            x="Tratamento", 
            y="Temp_Media", 
            color="Periodo",
            points="all",
            title="Variação térmica",
            color_discrete_map={'dia': '#FFD700', 'noite': '#191970'}
        )
        st.plotly_chart(fig_box, width='content')

    with c2:
        st.subheader("Temperatura da planta vs ambiente")
        df_agrupado = df_filtrado.groupby(['Temp_Ambiente', 'Tratamento'])['Temp_Media'].mean().reset_index()
        
        fig_bar = px.bar(
            df_agrupado,
            x="Temp_Ambiente",
            y="Temp_Media",
            color="Tratamento",
            barmode="group",
            title="Resposta Térmica Média",
            text_auto='.1f'
        )
        st.plotly_chart(fig_bar, width='content')

    st.subheader("Histograma de temperaturas")
    fig_hist = px.histogram(df_filtrado, x="Temp_Media", color="Tratamento", nbins=20, opacity=0.7)
    st.plotly_chart(fig_hist, width='content')

# --- GALERIA DE IMAGENS ---
with tab2:
    st.subheader("Inspeção visual das amostras")

    lista_plantas = df_filtrado['ID_Planta'].unique()
    planta_sel = st.selectbox("Selecione o ID da planta para visualizar:", lista_plantas)
    
    dados_planta = df_filtrado[df_filtrado['ID_Planta'] == planta_sel]
    
    if not dados_planta.empty:
        for i, row in dados_planta.iterrows():
            st.markdown(f"**Tratamento:** {row['Tratamento']} | **Ambiente:** {row['Temp_Ambiente']} | **Réplica:** {row['Replica']}")
            
            c_vis, c_therm, c_seg, c_info = st.columns([1, 1, 1, 1.2])
            
            # 1. Caminhos
            caminho_img_proc = os.path.join(PASTA_PROCESSADOS, row['Caminho_Imagem_Proc'])
            caminho_thermal = os.path.join(PASTA_IMAGENS, row['Arquivo_Original'])
            
            # Lógica para achar a visual
            nome_visual = row['Arquivo_Original'].replace('thermal', 'visual').replace('Thermal', 'Visual')
            caminho_visual = os.path.join(PASTA_IMAGENS, nome_visual)
            
            if not os.path.exists(caminho_visual):
                 nome_visual_alt = row['Arquivo_Original'].lower().replace('thermal', 'visual')
                 caminho_visual_alt = os.path.join(PASTA_IMAGENS, nome_visual_alt)
                 if os.path.exists(caminho_visual_alt):
                     caminho_visual = caminho_visual_alt

            # 2. Exibição usando a nova função segura
            with c_vis:
                st.markdown("**Visual**")
                img = carregar_imagem(caminho_visual)
                if img:
                    st.image(img, width='stretch')
                else:
                    st.warning(f"Não encontrada")

            with c_therm:
                st.markdown("**Térmica**")
                img = carregar_imagem(caminho_thermal)
                if img:
                    st.image(img, width='stretch')
                else:
                    st.warning("Não encontrada")

            with c_seg:
                st.markdown("**Recorte**")
                img = carregar_imagem(caminho_img_proc)
                if img:
                    st.image(img, width='stretch')
                else:
                    st.warning("Não processada")
            
            with c_info:
                st.info(f"""
                **Estatísticas da planta:**
                - 🌡️ **Média:** {row['Temp_Media']:.2f} °C
                - 📈 **Máxima:** {row['Temp_Max']:.2f} °C
                - 📉 **Mínima:** {row['Temp_Min']:.2f} °C
                - 📏 **Área:** {row['Area_Pixels']} px
                """)
            
            st.divider()