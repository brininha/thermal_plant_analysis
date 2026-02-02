import streamlit as st
import pandas as pd
import plotly.express as px
import cv2
import numpy as np
from PIL import Image, ExifTags
from streamlit_cropper import st_cropper
from fpdf import FPDF
import tempfile
import os

# Configuração da página
st.set_page_config(page_title="Análise térmica de plantas", layout="wide", page_icon="🌱")

# Calibração
ESCALAS_CAMERA = {
    '21': (16.8, 23.0), '27': (25.7, 31.8),
    '35': (28.9, 35.0), '45': (37.0, 49.1),
}
ESCALA_PADRAO = (20.0, 40.0)

# Funções

def pixel_para_temp(valor_pixel, temp_min, temp_max):
    return temp_min + (valor_pixel / 255.0) * (temp_max - temp_min)

def carregar_imagem(uploaded_file):
    try:
        image = Image.open(uploaded_file)
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
        return Image.open(uploaded_file)

def organizar_pares(uploaded_files):
    pares = {}
    for arq in uploaded_files:
        nome = arq.name.lower()
        tipo = 'thermal' if 'thermal' in nome else 'visual' if 'visual' in nome else None
        if not tipo: continue
        
        id_comum = nome.replace('_thermal', '').replace('thermal', '')\
                       .replace('_visual', '').replace('visual', '')\
                       .replace('.jpg', '').replace('.jpeg', '')
        
        if id_comum not in pares:
            pares[id_comum] = {'id': id_comum, 'visual': None, 'thermal': None, 'meta': None}
        
        pares[id_comum][tipo] = arq
        
        if pares[id_comum]['meta'] is None:
            partes = id_comum.split('_')
            if len(partes) >= 5:
                pares[id_comum]['meta'] = {
                    'Planta': partes[0], 'Ambiente': partes[1], 'Tratamento': partes[2],
                    'Periodo': partes[3], 'Replica': partes[4] if len(partes)>4 else '1'
                }
            else:
                pares[id_comum]['meta'] = {'Planta': id_comum, 'Ambiente': '27', 'Tratamento': 'N/A', 'Periodo': 'N/A', 'Replica': '1'}
    
    return [p for p in pares.values() if p['thermal'] is not None]

def processar_termica(img_pil_recortada, temp_ambiente):
    """
    Função ajustada:
    1. Usa grayscale APENAS para criar a máscara (recortar o fundo).
    2. Usa a COR (HSV) para calcular a temperatura se a imagem for colorida.
    """
    img = np.array(img_pil_recortada)
    
    # 1. Segmentação (Mantém a lógica original de usar cinza para achar o recorte)
    if len(img.shape) == 3: 
        img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else: 
        img_gray = img
    
    blur = cv2.GaussianBlur(img_gray, (5,5), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    img_cont = clahe.apply(blur)
    _, mask = cv2.threshold(img_cont, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 2. Extração de Temperatura (Nova lógica para Rainbow Palette)
    
    # Define limites de temperatura
    t_min, t_max = ESCALA_PADRAO
    if temp_ambiente in ESCALAS_CAMERA:
        t_min, t_max = ESCALAS_CAMERA[temp_ambiente]

    if len(img.shape) == 3:
        # Lógica NOVA: Usa Matiz (Hue) do sistema HSV
        # Vermelho (Quente) = Hue 0 ou 180
        # Azul (Frio) = Hue 120 (no OpenCV o range é 0-180)
        
        img_hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        hue = img_hsv[:, :, 0].astype(float) # Pega só o canal de cor
        
        # Pega os pixels dentro da máscara
        pixels_hue = hue[mask > 0]
        if len(pixels_hue) < 10: pixels_hue = hue.flatten()
        
        # Limita o range para evitar ruídos de violeta (>120)
        pixels_hue = np.clip(pixels_hue, 0, 120)
        
        # Cálculo: (120 - Hue) / 120  --> Vai dar 1.0 se for vermelho(0) e 0.0 se for azul(120)
        fator = (120.0 - pixels_hue) / 120.0
        
        temps = t_min + fator * (t_max - t_min)
        
    else:
        # Lógica ORIGINAL (Fallback para imagens P&B reais)
        pixels = img_gray[mask > 0]
        if len(pixels) < 10: pixels = img_gray.flatten()
        temps = [pixel_para_temp(p, t_min, t_max) for p in pixels]
    
    return {
        'Temp_Media': np.mean(temps), 'Temp_Max': np.max(temps),
        'Temp_Min': np.min(temps), 'Desvio': np.std(temps)
    }, Image.fromarray(img)

# Pdf

class PDFRelatorio(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Relatório técnico', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf_final(lista_dados):
    pdf = PDFRelatorio()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        for item in lista_dados:
            pdf.add_page()
            meta = item['meta']
            stats = item['stats']
            
            pdf.set_font('Arial', 'B', 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 10, f"ID da planta: {meta['Planta']}  |  Tratamento: {meta['Tratamento']}", 1, 1, 'L', fill=True)
            
            y_img = pdf.get_y() + 10 
            
            if item['img_visual']:
                path_v = os.path.join(tmpdir, f"v_{meta['Planta']}.jpg")
                item['img_visual'].save(path_v)
                pdf.image(path_v, x=10, y=y_img, w=90, h=70)
                pdf.text(10, y_img - 3, "Imagem visual")
            
            path_t = os.path.join(tmpdir, f"t_{meta['Planta']}.jpg")
            item['img_termica_crop'].save(path_t)
            pdf.image(path_t, x=110, y=y_img, w=90, h=70)
            pdf.text(110, y_img - 3, "Amostra da imagem térmica")
            
            pdf.set_y(y_img + 80)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 8, "Estatísticas térmicas", 0, 1, 'L')
            
            pdf.set_font('Arial', '', 10)
            col_w = 45
            h_row = 8
            
            pdf.cell(col_w, h_row, "Temperatura média", 1)
            pdf.cell(col_w, h_row, f"{stats['Temp_Media']:.2f} C", 1, 1)
            pdf.cell(col_w, h_row, "Temperatura máxima", 1)
            pdf.cell(col_w, h_row, f"{stats['Temp_Max']:.2f} C", 1, 1)
            pdf.cell(col_w, h_row, "Temperatura mínima", 1)
            pdf.cell(col_w, h_row, f"{stats['Temp_Min']:.2f} C", 1, 1)
            pdf.cell(col_w, h_row, "Desvio padrão", 1)
            pdf.cell(col_w, h_row, f"{stats['Desvio']:.2f}", 1, 1)
            
            pdf.ln(5)
            pdf.set_font('Arial', 'I', 9)
            pdf.multi_cell(0, 5, f"Obs.: Período {meta['Periodo']}, réplica {meta['Replica']}. Calibrado para amb: {meta['Ambiente']} C.")

    return pdf.output(dest='S').encode('latin-1')

# Estado
if 'idx' not in st.session_state: st.session_state['idx'] = 0
if 'dados' not in st.session_state: st.session_state['dados'] = []

st.title("🌱 Análise térmica de plantas")

with st.sidebar:
    st.header("Upload")
    files = st.file_uploader("Pares de imagens (visual + térmica)", accept_multiple_files=True)
    st.divider()
    if st.button("Reiniciar", type="primary"):
        st.session_state['idx'] = 0
        st.session_state['dados'] = []
        st.rerun()

pares = organizar_pares(files) if files else []
tab_edit, tab_dash = st.tabs(["Editor de recorte", "Dashboard completo"])

# Aba 1: Editor
with tab_edit:
    if pares:
        if st.session_state['idx'] < len(pares):
            par = pares[st.session_state['idx']]
            meta = par['meta']
            st.subheader(f"Processando: {meta['Planta']} - {meta['Tratamento']}")
            c1, c2 = st.columns(2)
            with c1:
                img_vis = carregar_imagem(par['visual']) if par['visual'] else None
                if img_vis: st.image(img_vis, width='stretch', caption="Visual")
            with c2:
                img_therm = carregar_imagem(par['thermal'])
                img_crop = st_cropper(img_therm, realtime_update=True, box_color='#FF0000', aspect_ratio=None, key=f"c_{par['id']}")
                if st.button("Confirmar", type="primary", width='content'):
                    stats, img_proc = processar_termica(img_crop, meta['Ambiente'])
                    st.session_state['dados'].append({'meta': meta, 'stats': stats, 'img_visual': img_vis, 'img_termica_crop': img_proc})
                    st.toast(f"Salvo! {stats['Temp_Media']:.1f}°C")
                    st.session_state['idx'] += 1
                    st.rerun()
        else:
            st.success("Imagens processadas! Vá para o dashboard.")
    else:
        st.info("Aguardando imagens...")

# Aba 2: Dashboard (barras, heatmap, boxplot)
with tab_dash:
    if st.session_state['dados']:
        flat_data = []
        for d in st.session_state['dados']:
            row = d['meta'].copy()
            row.update(d['stats'])
            flat_data.append(row)
        df = pd.DataFrame(flat_data)
        
        # Header e download
        st.subheader("Relatório e exportação")
        cd1, cd2 = st.columns(2)
        with cd1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar tabela (CSV)", csv, "dados.csv", "text/csv", width='stretch')
        with cd2:
            if st.button("Gerar PDF (imagens + dados)", width='stretch'):
                with st.spinner("Gerando PDF..."):
                    pdf_b = gerar_pdf_final(st.session_state['dados'])
                    st.download_button("Baixar relatório PDF", pdf_b, "Relatorio.pdf", "application/pdf", width='stretch')
        st.divider()

        # Filtros para gráficos
        cf1, cf2 = st.columns(2)
        sel_trat = cf1.multiselect("Filtrar tratamento", df['Tratamento'].unique(), default=df['Tratamento'].unique())
        sel_per = cf2.multiselect("Filtrar período", df['Periodo'].unique(), default=df['Periodo'].unique())
        
        df_chart = df[df['Tratamento'].isin(sel_trat) & df['Periodo'].isin(sel_per)]

        if not df_chart.empty:
            
            # Gráfico de barras
            st.markdown("### Média de temperatura")
            st.caption("Comparação direta das médias por tratamento e período.")
            
            df_bar = df_chart.groupby(['Tratamento', 'Periodo'])['Temp_Media'].mean().reset_index()
            fig_bar = px.bar(
                df_bar, 
                x="Tratamento", 
                y="Temp_Media", 
                color="Periodo", 
                barmode='group', 
                text_auto='.1f',
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_bar.update_layout(yaxis_title="Temp (°C)")
            st.plotly_chart(fig_bar, width='stretch')

            st.divider()
            
            # Heatmap e boxplot lado a lado
            col_heat, col_box = st.columns(2)

            with col_heat:
                st.markdown("### Mapa de calor")
                st.caption("Visão matricial da intensidade térmica.")
                try:
                    heatmap_data = df_chart.pivot_table(index='Tratamento', columns='Periodo', values='Temp_Media', aggfunc='mean')
                    fig_heat = px.imshow(
                        heatmap_data, 
                        text_auto='.1f', 
                        aspect="auto",
                        color_continuous_scale='RdBu_r', 
                        origin='lower'
                    )
                    st.plotly_chart(fig_heat, width='stretch')
                except:
                    st.warning("Dados insuficientes para heatmap.")

            with col_box:
                st.markdown("### Distribuição")
                st.caption("Dispersão dos dados e outliers.")
                fig_box = px.box(
                    df_chart, 
                    x="Tratamento", 
                    y="Temp_Media", 
                    color="Periodo", 
                    points="all",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_box.update_layout(yaxis_title="Temp (°C)")
                st.plotly_chart(fig_box, width='stretch')

        else:
            st.warning("Sem dados para os filtros selecionados.")
    else:
        st.info("Processe as imagens primeiro na aba 'Editor de recorte'.")