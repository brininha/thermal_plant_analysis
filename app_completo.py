import streamlit as st
import pandas as pd
import plotly.express as px
import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ExifTags
from streamlit_cropper import st_cropper
from fpdf import FPDF
import tempfile
import os

# --- IMPORTAÇÃO DA BIBLIOTECA RADIOMÉTRICA ---
try:
    from flirimageextractor import FlirImageExtractor
except ImportError:
    st.error("Biblioteca 'flirimageextractor' não encontrada. Instale com: pip install flirimageextractor")

# Configuração da página
st.set_page_config(page_title="Análise térmica de plantas", layout="wide", page_icon="🌱")

# --- FUNÇÕES UTILITÁRIAS ---

def carregar_imagem(uploaded_file):
    """Carrega a imagem visualmente, respeitando a rotação EXIF."""
    uploaded_file.seek(0)
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
        uploaded_file.seek(0)
        return Image.open(uploaded_file)

def organizar_pares(uploaded_files):
    """Agrupa as imagens em pares visual + térmica."""
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
            # Ex: P01_27_Controle_Dia_R1_thermal.jpg
            if len(partes) >= 5:
                pares[id_comum]['meta'] = {
                    'Planta': partes[0], 'Ambiente': partes[1], 'Tratamento': partes[2],
                    'Periodo': partes[3], 'Replica': partes[4] if len(partes)>4 else '1'
                }
            else:
                pares[id_comum]['meta'] = {'Planta': id_comum, 'Ambiente': 'N/A', 'Tratamento': 'N/A', 'Periodo': 'N/A', 'Replica': '1'}
    
    return [p for p in pares.values() if p['thermal'] is not None]

# --- LÓGICA RADIOMÉTRICA ---

def processar_termica_radiometrica(img_crop_pil, img_full_pil, arquivo_original):
    """
    Retorna: Estatísticas, Imagem Visual do Crop, e a MATRIZ TÉRMICA CRUA (numpy).
    """
    # 1. Extração dos dados brutos
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        arquivo_original.seek(0)
        tmp.write(arquivo_original.read())
        tmp_path = tmp.name

    try:
        flir = FlirImageExtractor(is_debug=False)
        flir.process_image(tmp_path)
        matriz_termica = flir.get_thermal_np()
    except Exception as e:
        st.error(f"Erro ao ler dados radiométricos: {e}")
        return None, img_crop_pil, None
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

    # 2. Sincronização de tamanho (Raw vs Visual)
    img_full_arr = np.array(img_full_pil)
    img_crop_arr = np.array(img_crop_pil)
    h_vis, w_vis = img_full_arr.shape[:2]
    
    # Redimensiona a matriz térmica para bater com a resolução visual
    matriz_termica = cv2.resize(matriz_termica, (w_vis, h_vis), interpolation=cv2.INTER_CUBIC)

    # 3. Localizar o Crop na imagem original
    full_gray = cv2.cvtColor(img_full_arr, cv2.COLOR_RGB2GRAY) if len(img_full_arr.shape)==3 else img_full_arr
    crop_gray = cv2.cvtColor(img_crop_arr, cv2.COLOR_RGB2GRAY) if len(img_crop_arr.shape)==3 else img_crop_arr

    res = cv2.matchTemplate(full_gray, crop_gray, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(res)
    x, y = max_loc
    h_crop, w_crop = crop_gray.shape[:2]

    # 4. Recorte da matriz térmica
    termica_recortada = matriz_termica[y:y+h_crop, x:x+w_crop]

    # Como removemos a segmentação automática, todos os pixels do retângulo contam
    pixels_validos = termica_recortada.flatten()

    stats = {
        'Temp_Media': np.mean(pixels_validos),
        'Temp_Max': np.max(pixels_validos),
        'Temp_Min': np.min(pixels_validos),
        'Desvio': np.std(pixels_validos)
    }
    
    return stats, Image.fromarray(img_crop_arr), termica_recortada

# --- GERAÇÃO DE PDF ---

class PDFRelatorio(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Relatório técnico', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_grafico_matplotlib(matriz_termica, path_saida):
    """Gera um heatmap com barra de cores para o PDF usando Matplotlib."""
    plt.figure(figsize=(5, 4))
    plt.imshow(matriz_termica, cmap='inferno')
    plt.colorbar(label='Temperatura (°C)')
    plt.axis('off')
    plt.title("Mapa térmico")
    plt.tight_layout()
    plt.savefig(path_saida, dpi=150, bbox_inches='tight')
    plt.close()

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
            pdf.cell(0, 10, f"ID: {meta['Planta']} | Trat: {meta['Tratamento']} | Amb: {meta['Ambiente']}", 1, 1, 'L', fill=True)
            
            y_img = pdf.get_y() + 10 
            
            # 1. Imagem Visual
            if item['img_visual']:
                path_v = os.path.join(tmpdir, f"v_{meta['Planta']}.jpg")
                item['img_visual'].save(path_v)
                pdf.image(path_v, x=10, y=y_img, w=60, h=50)
                pdf.text(10, y_img - 3, "Imagem visual")
            
            # 2. Imagem Térmica (Crop Visual)
            path_t = os.path.join(tmpdir, f"t_{meta['Planta']}.jpg")
            item['img_termica_crop'].save(path_t)
            pdf.image(path_t, x=75, y=y_img, w=60, h=50)
            pdf.text(75, y_img - 3, "Recorte analisado")

            # 3. Mapa de Calor Radiométrico
            if item['raw_matrix'] is not None:
                path_h = os.path.join(tmpdir, f"h_{meta['Planta']}.png")
                gerar_grafico_matplotlib(item['raw_matrix'], path_h)
                pdf.image(path_h, x=140, y=y_img, w=60, h=50)
                pdf.text(140, y_img - 3, "Dados reais")
            
            pdf.set_y(y_img + 60)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 8, "Estatísticas da área selecionada", 0, 1, 'L')
            
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

    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE ---

if 'idx' not in st.session_state: st.session_state['idx'] = 0
if 'dados' not in st.session_state: st.session_state['dados'] = []

st.title("🌱 Análise térmica de plantas")

with st.sidebar:
    st.header("Upload")
    files = st.file_uploader("Pares de imagens", accept_multiple_files=True)
    st.divider()
    if st.button("Reiniciar", type="primary"):
        st.session_state['idx'] = 0
        st.session_state['dados'] = []
        st.rerun()

pares = organizar_pares(files) if files else []
tab_edit, tab_dash = st.tabs(["Editor de recorte", "Dashboard"])

# Aba 1: Editor
with tab_edit:
    if pares:
        if st.session_state['idx'] < len(pares):
            par = pares[st.session_state['idx']]
            meta = par['meta']
            st.subheader(f"Processando: {meta['Planta']} - {meta['Tratamento']}")
            c1, c2 = st.columns(2)
            
            img_vis_full = carregar_imagem(par['visual']) if par['visual'] else None
            img_therm_full = carregar_imagem(par['thermal'])
            
            with c1:
                if img_vis_full: st.image(img_vis_full, use_column_width=True, caption="Visual")
            with c2:
                st.caption("⚠️ Recorte apenas a área da planta. Todos os pixels do retângulo serão calculados.")
                img_crop = st_cropper(img_therm_full, realtime_update=True, box_color='#FF0000', aspect_ratio=None, key=f"c_{par['id']}")
                
                if st.button("Confirmar", type="primary", width='content'):
                    with st.spinner("Extraindo temperaturas reais..."):
                        stats, img_proc, raw_matrix = processar_termica_radiometrica(img_crop, img_therm_full, par['thermal'])
                    
                    if stats:
                        st.session_state['dados'].append({
                            'meta': meta, 
                            'stats': stats, 
                            'img_visual': img_vis_full, 
                            'img_termica_crop': img_proc,
                            'raw_matrix': raw_matrix 
                        })
                        st.toast(f"Salvo! Média: {stats['Temp_Media']:.1f}°C")
                        st.session_state['idx'] += 1
                        st.rerun()
        else:
            st.success("Todas as imagens foram processadas!")
    else:
        st.info("Faça o upload das imagens na barra lateral.")

# Aba 2: Dashboard
with tab_dash:
    if st.session_state['dados']:
        flat_data = []
        for d in st.session_state['dados']:
            row = d['meta'].copy()
            row.update(d['stats'])
            flat_data.append(row)
        df = pd.DataFrame(flat_data)
        
        # --- SEÇÃO 1: INSPECTOR INTERATIVO (NOVIDADE) ---
        st.markdown("### Inspeção de pixels")
        st.info("Selecione uma amostra para visualizar o mapa térmico radiométrico completo da área recortada. Passe o mouse sobre os pixels para ver a temperatura exata.")
        
        opcoes = {f"{d['meta']['Planta']} ({d['meta']['Tratamento']})": i for i, d in enumerate(st.session_state['dados'])}
        escolha = st.selectbox("Escolha a amostra para inspecionar:", list(opcoes.keys()))
        
        if escolha:
            idx_escolhido = opcoes[escolha]
            matriz = st.session_state['dados'][idx_escolhido]['raw_matrix']
            
            # Gráfico interativo que permite passar o mouse para ver temperatura
            fig_pixel = px.imshow(
                matriz,
                color_continuous_scale='Inferno',
                labels=dict(x="Eixo X", y="Eixo Y", color="Temp (°C)"),
                title=f"Termografia: {escolha}"
            )
            fig_pixel.update_xaxes(showticklabels=False)
            fig_pixel.update_yaxes(showticklabels=False)
            fig_pixel.update_traces(hovertemplate="Temp: %{z:.2f} °C<extra></extra>")
            
            st.plotly_chart(fig_pixel, width='stretch')

        st.divider()

        # --- SEÇÃO 2: GRÁFICOS ESTATÍSTICOS (RESTAURADOS) ---
        st.subheader("Análise estatística")
        
        cf1, cf2 = st.columns(2)
        sel_trat = cf1.multiselect("Filtrar tratamento", df['Tratamento'].unique(), default=df['Tratamento'].unique())
        sel_per = cf2.multiselect("Filtrar período", df['Periodo'].unique(), default=df['Periodo'].unique())
        
        df_chart = df[df['Tratamento'].isin(sel_trat) & df['Periodo'].isin(sel_per)]

        if not df_chart.empty:
            
            # Gráfico 1: Barras
            st.markdown("### Comparação de médias")
            df_bar = df_chart.groupby(['Tratamento', 'Periodo'])['Temp_Media'].mean().reset_index()
            fig_bar = px.bar(
                df_bar, 
                x="Tratamento", 
                y="Temp_Media", 
                color="Periodo", 
                barmode='group', 
                text_auto='.1f',
                color_discrete_sequence=px.colors.qualitative.Pastel # Cor restaurada
            )
            fig_bar.update_layout(yaxis_title="Temp média (°C)")
            st.plotly_chart(fig_bar, width='stretch')

            st.divider()
            
            # Gráfico 2 e 3: Heatmap e Boxplot
            col_heat, col_box = st.columns(2)

            with col_heat:
                st.markdown("### Mapa de calor (tratamento x período)")
                try:
                    heatmap_data = df_chart.pivot_table(index='Tratamento', columns='Periodo', values='Temp_Media', aggfunc='mean')
                    fig_heat = px.imshow(
                        heatmap_data, 
                        text_auto='.1f', 
                        aspect="auto",
                        color_continuous_scale='RdBu_r', # Escala restaurada
                        origin='lower'
                    )
                    st.plotly_chart(fig_heat, width='stretch')
                except:
                    st.warning("Dados insuficientes para gerar o heatmap.")

            with col_box:
                st.markdown("### Distribuição e outliers")
                fig_box = px.box(
                    df_chart, 
                    x="Tratamento", 
                    y="Temp_Media", 
                    color="Periodo", 
                    points="all",
                    color_discrete_sequence=px.colors.qualitative.Pastel # Cor restaurada
                )
                fig_box.update_layout(yaxis_title="Temp (°C)")
                st.plotly_chart(fig_box, width='stretch')

        else:
            st.warning("Sem dados para os filtros selecionados.")
            
        st.divider()

        # --- SEÇÃO 3: DOWNLOAD ---
        st.subheader("Relatório e exportação")
        cd1, cd2 = st.columns(2)
        with cd1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar tabela (CSV)", csv, "dados_radiometricos.csv", "text/csv", width='stretch')
        with cd2:
            if st.button("Gerar relatório PDF completo", width='stretch'):
                with st.spinner("Gerando PDF..."):
                    pdf_b = gerar_pdf_final(st.session_state['dados'])
                    st.download_button("Baixar PDF", pdf_b, "relatorio_tecnico.pdf", "application/pdf", width='stretch')
    else:
        st.info("Processe as imagens primeiro na aba 'Editor de recorte'.")