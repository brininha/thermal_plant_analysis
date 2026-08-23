# todos os imports de bibliotecas necessárias
import streamlit as st
import pandas as pd
import plotly.express as px
import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ExifTags
from fpdf import FPDF
import tempfile
import os
from streamlit_drawable_canvas import st_canvas

# biblioteca radiométrica para extrair a temperatura dos metadados
try:
    from flirimageextractor import FlirImageExtractor
except ImportError:
    st.error("Biblioteca 'flirimageextractor' não encontrada. Instale com: pip install flirimageextractor")

# configuração da página
st.set_page_config(page_title="Análise térmica de plantas", layout="wide", page_icon="🌱")

# funções utilitárias
def carregar_imagem(uploaded_file):
    """carrega a imagem visualmente, respeitando a rotação EXIF."""
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
    """agrupa as imagens em pares visual + térmica."""
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
            
            if len(partes) == 5:
                pares[id_comum]['meta'] = {
                    'Planta': partes[0], 'Ambiente': partes[1], 'Tratamento': partes[2],
                    'Periodo': partes[3], 'Replica': partes[4], 'Variedade': 'N/A'
                }

            elif len(partes) >= 6:
                pares[id_comum]['meta'] = {
                    'Planta': partes[0], 'Ambiente': partes[1], 'Tratamento': partes[2],
                    'Periodo': partes[3], 'Replica': partes[4], 'Variedade': partes[5]
                }
            else:
                pares[id_comum]['meta'] = {
                    'Planta': id_comum, 'Ambiente': 'N/A', 'Tratamento': 'N/A', 
                    'Periodo': 'N/A', 'Replica': '1', 'Variedade': 'N/A'
                }
    
    return [p for p in pares.values() if p['thermal'] is not None]

# segmentação automática
def gerar_mascara_automatica(img_visual_arr, periodo, w_termica, h_termica, dx=-5, dy=20):
    """
    aplica o pipeline de segmentação condicional (dia/noite) e corrige paralaxe.
    """
    if periodo.lower() == 'noite':
        # pipeline noturno: HSV + maior contorno
        hsv = cv2.cvtColor(img_visual_arr, cv2.COLOR_RGB2HSV)
        lower_green = np.array([30, 80, 40]) # saturação mínima 80 para ignorar sombras
        upper_green = np.array([90, 255, 255])
        mask_hsv = cv2.inRange(hsv, lower_green, upper_green)

        kernel_conexao = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_conectada = cv2.morphologyEx(mask_hsv, cv2.MORPH_CLOSE, kernel_conexao)
        contornos, _ = cv2.findContours(mask_conectada, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask_planta = np.zeros_like(mask_hsv)

        if contornos:
            maior_planta = max(contornos, key=cv2.contourArea)
            cv2.drawContours(mask_planta, [maior_planta], -1, 255, thickness=cv2.FILLED)
            mask_planta = cv2.bitwise_and(mask_hsv, mask_planta)
        else:
            mask_planta = mask_hsv.copy()
    else:
        # pipeline diurno: guilhotina morfológica
        img_gray = cv2.cvtColor(img_visual_arr, cv2.COLOR_RGB2GRAY)
        img_blur = cv2.GaussianBlur(img_gray, (5, 5), 0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(32, 32))
        img_equalized = clahe.apply(img_blur)
        
        _, mask_escuros = cv2.threshold(img_equalized, 75, 255, cv2.THRESH_BINARY_INV)
        
        kernel_grosso = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 30))
        mask_vaso_ref = cv2.morphologyEx(mask_escuros, cv2.MORPH_OPEN, kernel_grosso)
        
        contornos_vaso, _ = cv2.findContours(mask_vaso_ref, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask_planta = mask_escuros.copy()

        if contornos_vaso:
            contornos_solidos = [c for c in contornos_vaso if cv2.contourArea(c) > 500]
            if contornos_solidos:
                contornos_ordenados = sorted(contornos_solidos, key=lambda c: cv2.boundingRect(c)[1])
                x, y, w, h = cv2.boundingRect(contornos_ordenados[0])
                linha_de_corte = max(y - 5, 0)
                mask_planta[linha_de_corte:, :] = 0

        kernel_limpeza = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_planta = cv2.morphologyEx(mask_planta, cv2.MORPH_OPEN, kernel_limpeza)
        mask_planta = cv2.morphologyEx(mask_planta, cv2.MORPH_DILATE, kernel_limpeza)

    # sincronização e paralaxe
    mask_res = cv2.resize(mask_planta, (w_termica, h_termica), interpolation=cv2.INTER_NEAREST)
    _, mask_res = cv2.threshold(mask_res, 127, 255, cv2.THRESH_BINARY)
    
    matriz_translacao = np.float32([[1, 0, dx], [0, 1, dy]])
    mask_alinhada = cv2.warpAffine(mask_res, matriz_translacao, (w_termica, h_termica))

    return mask_alinhada

# lógica radiométrica
def processar_termica_radiometrica(img_vis_pil, img_therm_pil, arquivo_original_therm, periodo):
    """
    Retorna: estatísticas, imagem mascarada e matriz crua.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        arquivo_original_therm.seek(0)
        tmp.write(arquivo_original_therm.read())
        tmp_path = tmp.name

    try:
        flir = FlirImageExtractor(is_debug=False)
        flir.process_image(tmp_path)
        matriz_termica = flir.get_thermal_np()
    except Exception as e:
        st.error(f"Erro ao ler dados radiométricos: {e}")
        return None, None, None, None, None, None, None
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

    img_vis_arr = np.array(img_vis_pil)
    img_therm_arr = np.array(img_therm_pil)
    
    # capturamos as dimensões da imagem visual (base de alta resolução)
    h_vis, w_vis = img_vis_arr.shape[:2]
    
    # sincroniza a imagem de cores térmica com o tamanho da visual
    if img_therm_arr.shape[:2] != (h_vis, w_vis):
        img_therm_arr = cv2.resize(img_therm_arr, (w_vis, h_vis), interpolation=cv2.INTER_CUBIC)
    
    # redimensiona matriz bruta para bater com visual
    matriz_termica = cv2.resize(matriz_termica, (w_vis, h_vis), interpolation=cv2.INTER_CUBIC)

    # automação da máscara
    mask_planta = gerar_mascara_automatica(img_vis_arr, periodo, w_vis, h_vis)

    # garante que a máscara é estritamente 8-bits para o opencv
    mask_planta = mask_planta.astype(np.uint8)

    pixels_validos = matriz_termica[mask_planta == 255]

    if len(pixels_validos) == 0:
        return None, None, None, None, None, None, None

    stats = {
        'Temp_Media': np.mean(pixels_validos),
        'Temp_Max': np.max(pixels_validos),
        'Temp_Min': np.min(pixels_validos),
        'Desvio': np.std(pixels_validos)
    }
    
    img_recortada_arr = cv2.bitwise_and(img_therm_arr, img_therm_arr, mask=mask_planta)
    img_recortada_pil = Image.fromarray(img_recortada_arr)
    
    matriz_termica_dash = matriz_termica.copy()
    matriz_termica_dash[mask_planta == 0] = np.nan 
    
    return stats, img_recortada_pil, matriz_termica_dash, mask_planta, matriz_termica, img_therm_arr, img_vis_arr

# geração de pdf

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
        for i, item in enumerate(lista_dados):
            pdf.add_page()
            meta = item['meta']
            stats = item['stats']
            
            pdf.set_font('Arial', 'B', 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 10, f"ID: {meta['Planta']} | Variedade: {meta['Variedade']} | Tratamento: {meta['Tratamento']} | Ambiente: {meta['Ambiente']} | Período: {meta['Periodo']} | R{meta['Replica']}", 1, 1, 'L', fill=True)
            
            y_img = pdf.get_y() + 10 
            
            # imagem visual
            if item['img_visual']:
                path_v = os.path.join(tmpdir, f"v_{i}.jpg")
                item['img_visual'].save(path_v)
                pdf.image(path_v, x=10, y=y_img, w=60, h=50)
                pdf.text(10, y_img - 3, "Imagem visual")
            
            # imagem térmica
            path_t = os.path.join(tmpdir, f"t_{i}.jpg")
            item['img_termica_crop'].save(path_t)
            pdf.image(path_t, x=75, y=y_img, w=60, h=50)
            pdf.text(75, y_img - 3, "Recorte analisado")

            # mapa de calor radiométrico
            if item['raw_matrix'] is not None:
                path_h = os.path.join(tmpdir, f"h_{i}.png")
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

# interface
# if 'idx' not in st.session_state: st.session_state['idx'] = 0
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
tab_edit, tab_dash = st.tabs(["Processamento de amostras", "Dashboard"])

# aba de processamento
with tab_edit:
    if pares:
        if len(st.session_state['dados']) == len(pares):
             st.success(f"Todas as {len(pares)} amostras foram processadas! Verifique os resultados no Dashboard.")
             
             # secao de revisao manual
             st.divider()
             st.subheader("Revisão de segmentação")
             st.info("Caso a segmentação automática tenha falhado para alguma imagem, selecione-a abaixo para corrigir o recorte.")
             
             opcoes_edicao = {f"{d['meta']['Planta']} - {d['meta']['Tratamento']} - {d['meta']['Periodo']} - R{d['meta']['Replica']}": i for i, d in enumerate(st.session_state['dados'])}
             escolha_edicao = st.selectbox("Escolha a amostra para revisar/editar:", ["Selecione..."] + list(opcoes_edicao.keys()))
             
             if escolha_edicao != "Selecione...":
                 idx = opcoes_edicao[escolha_edicao]
                 dado_atual = st.session_state['dados'][idx]
                 
                 img_vis_arr = dado_atual['img_vis_arr']
                 mask_atual = dado_atual['mask_planta']
                 
                 img_mascarada_auto = cv2.bitwise_and(img_vis_arr, img_vis_arr, mask=mask_atual)
                 st.image(img_mascarada_auto, caption="Resultado automático atual", use_column_width=True)
                 
                 editar = st.toggle("Ajustar segmentação manualmente")
                 mascara_final = mask_atual.copy()
                 
                 if editar:
                     col1, col2 = st.columns([1, 3])
                     with col1:
                         modo_desenho = st.radio("Ferramenta:", ("Desenhar", "Apagar"))
                         tamanho_pincel = st.slider("Tamanho do pincel", 1, 50, 20)
                         stroke_color = "#00FF00" if modo_desenho == "Desenhar" else "#FF0000"
                     
                     with col2:
                         # cria uma copia da imagem visual para o overlay
                         overlay = img_vis_arr.copy()
                         
                         overlay[mask_atual == 255] = [0, 255, 0]
                         
                         img_fundo_destaque = cv2.addWeighted(img_vis_arr, 0.7, overlay, 0.3, 0)
                         bg_image = Image.fromarray(img_fundo_destaque)
                         
                         canvas_result = st_canvas(
                             fill_color="rgba(255, 165, 0, 0.3)",
                             stroke_width=tamanho_pincel,
                             stroke_color=stroke_color,
                             background_image=bg_image,
                             update_streamlit=True,
                             height=bg_image.height,
                             width=bg_image.width,
                             drawing_mode="freedraw",
                             key=f"canvas_{idx}"
                         )
                         
                     if canvas_result.image_data is not None:
                         desenho_rgba = canvas_result.image_data
                         canal_r, canal_g, canal_alpha = desenho_rgba[:, :, 0], desenho_rgba[:, :, 1], desenho_rgba[:, :, 3]
                         
                         mascara_adicionar = (canal_g > 150) & (canal_r < 100) & (canal_alpha > 0)
                         mascara_remover = (canal_r > 150) & (canal_g < 100) & (canal_alpha > 0)
                         
                         mascara_final[mascara_adicionar] = 255
                         mascara_final[mascara_remover] = 0
                         
                     if st.button("Salvar nova máscara e recalcular dados", type="primary"):
                         # recalcula as estatisticas e as matrizes com a nova mascara
                         mask_nova = mascara_final.astype(np.uint8)
                         mat_raw = dado_atual['matriz_termica_raw']
                         therm_arr = dado_atual['img_therm_arr']
                         
                         pixels_validos = mat_raw[mask_nova == 255]
                         if len(pixels_validos) > 0:
                             novo_stats = {
                                 'Temp_Media': np.mean(pixels_validos),
                                 'Temp_Max': np.max(pixels_validos),
                                 'Temp_Min': np.min(pixels_validos),
                                 'Desvio': np.std(pixels_validos)
                             }
                             
                             img_recortada_arr = cv2.bitwise_and(therm_arr, therm_arr, mask=mask_nova)
                             mat_dash = mat_raw.copy()
                             mat_dash[mask_nova == 0] = np.nan
                             
                             # atualiza o session_state
                             st.session_state['dados'][idx]['stats'] = novo_stats
                             st.session_state['dados'][idx]['img_termica_crop'] = Image.fromarray(img_recortada_arr)
                             st.session_state['dados'][idx]['raw_matrix'] = mat_dash
                             st.session_state['dados'][idx]['mask_planta'] = mask_nova
                             
                             st.success("Dados radiométricos atualizados!")
                             st.rerun()
             # fim da secao de revisao
             
             st.divider()
             if st.button("Reprocessar todas as imagens"):
                 st.session_state['dados'] = []
                 st.rerun()
        else:
            st.subheader(f"Amostras detectadas: {len(pares)}")
            st.info("Confira os pares abaixo. O sistema usará a segmentação automática baseada nos metadados para extrair as temperaturas.")

            # criamos uma área de scroll ou lista para os pares
            st.divider()
            st.subheader("Pré-visualização das Imagens")

            # define quantos pares mostrar por vez
            itens_por_pagina = 5
            total_paginas = max(1, (len(pares) - 1) // itens_por_pagina + 1)

            # cria o controle de paginacao visual
            if total_paginas > 1:
                pagina_atual = st.slider("Página", min_value=1, max_value=total_paginas, value=1)
            else:
                pagina_atual = 1

            # fatia a lista matematica para a pagina atual
            inicio = (pagina_atual - 1) * itens_por_pagina
            fim = inicio + itens_por_pagina
            pares_exibicao = pares[inicio:fim]

            # exibe apenas a fatia selecionada
            for i, par in enumerate(pares_exibicao):
                meta = par['meta']
                
                with st.container(border=True):
                    st.markdown(f"**ID: {meta['Planta']}** | Tratamento: {meta['Tratamento']} | Período: {meta['Periodo']}")
                    
                    col_v, col_t = st.columns(2)
                    
                    img_vis_preview = carregar_imagem(par['visual']) if par['visual'] else None
                    img_therm_preview = carregar_imagem(par['thermal'])
                    
                    with col_v:
                        if img_vis_preview:
                            st.image(img_vis_preview, caption="Referência visual", use_column_width=True)
                        else:
                            st.warning("Imagem visual não encontrada para este par.")
                            
                    with col_t:
                        st.image(img_therm_preview, caption="Imagem térmica", use_column_width=True)

            st.divider()
            
            # botão de processamento em lote
            if st.button("Processar tudo", type="primary"):
                barra_progresso = st.progress(0)
                status_texto = st.empty()
                
                st.session_state['dados'] = [] 
                
                for i, par in enumerate(pares):
                    meta = par['meta']
                    status_texto.text(f"Processando radiometria: {meta['Planta']} ({i+1}/{len(pares)})...")
                    
                    img_vis_full = carregar_imagem(par['visual']) if par['visual'] else None
                    img_therm_full = carregar_imagem(par['thermal'])
                    
                    # chama a sua lógica de extração de dados brutos (matriz de sensores)
                    # conforme definido no seu pipeline radiométrico
                    stats, img_proc, raw_matrix, mask_planta, matriz_termica_raw, img_therm_arr, img_vis_arr = processar_termica_radiometrica(
                        img_vis_full, img_therm_full, par['thermal'], meta['Periodo']
                    )
                    
                    if stats:
                        st.session_state['dados'].append({
                            'meta': meta, 
                            'stats': stats, 
                            'img_visual': img_vis_full, 
                            'img_termica_crop': img_proc,
                            'raw_matrix': raw_matrix,
                            'mask_planta': mask_planta,
                            'matriz_termica_raw': matriz_termica_raw,
                            'img_therm_arr': img_therm_arr,
                            'img_vis_arr': img_vis_arr
                        })
                    
                    barra_progresso.progress((i + 1) / len(pares))
                
                status_texto.text("Processamento concluído!")
                st.balloons()
                st.rerun()
    else:
        st.info("Aguardando upload de imagens na barra lateral.")

# aba do dashboard
with tab_dash:
    if st.session_state['dados']:
        flat_data = []
        for d in st.session_state['dados']:
            row = d['meta'].copy()
            row.update(d['stats'])
            flat_data.append(row)
        df = pd.DataFrame(flat_data)
        
        # seção 1: inspetor interativo de pixels
        st.markdown("### Inspeção de pixels")
        st.info("Selecione uma amostra para visualizar o mapa térmico radiométrico completo da área recortada. Passe o mouse sobre os pixels para ver a temperatura exata.")
        
        opcoes = {f"{d['meta']['Planta']} - {d['meta']['Tratamento']} - {d['meta']['Periodo']} - R{d['meta']['Replica']}": i for i, d in enumerate(st.session_state['dados'])}
        escolha = st.selectbox("Escolha a amostra para inspecionar:", list(opcoes.keys()))
        
        if escolha:
            idx_escolhido = opcoes[escolha]
            matriz = st.session_state['dados'][idx_escolhido]['raw_matrix']
            
            # se for NaN, avisa que é fundo
            # se for número, formata a temperatura.
            def formatar_pixel(val):
                if np.isnan(val):
                    return "Fundo (sem leitura)"
                return f"Temp: {val:.2f} °C"
            
            # aplicamos essa regra matematicamente em todos os pixels da matriz de uma vez
            matriz_hover = np.vectorize(formatar_pixel)(matriz)
            
            # geramos o gráfico
            fig_pixel = px.imshow(
                matriz,
                color_continuous_scale='icefire',
                labels=dict(x="Eixo X", y="Eixo Y", color="Temp (°C)"),
                title=f"Termografia: {escolha}"
            )
            
            fig_pixel.update_xaxes(showticklabels=False)
            fig_pixel.update_yaxes(showticklabels=False)
            
            # injetamos a nossa matriz de textos (customdata) no lugar da formatação padrão
            fig_pixel.update_traces(
                customdata=matriz_hover,
                hovertemplate="%{customdata}<extra></extra>"
            )
            
            st.plotly_chart(fig_pixel, use_container_width=True)

        st.divider()

        # seção 2: gráficos
        st.subheader("Análise estatística")
        
        cf1, cf2 = st.columns(2)
        sel_trat = cf1.multiselect("Filtrar tratamento", df['Tratamento'].unique(), default=df['Tratamento'].unique())
        sel_per = cf2.multiselect("Filtrar período", df['Periodo'].unique(), default=df['Periodo'].unique())
        
        df_chart = df[df['Tratamento'].isin(sel_trat) & df['Periodo'].isin(sel_per)]

        if not df_chart.empty:
            
            # gráfico 1: barras
            st.markdown("### Comparação de médias")
            df_bar = df_chart.groupby(['Tratamento', 'Periodo'])['Temp_Media'].mean().reset_index()
            fig_bar = px.bar(
                df_bar, 
                x="Tratamento", 
                y="Temp_Media", 
                color="Periodo", 
                barmode='group', 
                text_auto='.1f',
                color_discrete_sequence=px.colors.qualitative.Pastel # cor restaurada
            )
            fig_bar.update_layout(yaxis_title="Temp média (°C)")
            st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()
            
            # gráfico 2 e 3: heatmap e boxplot
            col_heat, col_box = st.columns(2)

            with col_heat:
                st.markdown("### Mapa de calor (tratamento x período)")
                try:
                    heatmap_data = df_chart.pivot_table(index='Tratamento', columns='Periodo', values='Temp_Media', aggfunc='mean')
                    fig_heat = px.imshow(
                        heatmap_data, 
                        text_auto='.1f', 
                        aspect="auto",
                        color_continuous_scale='RdBu_r', # escala restaurada
                        origin='lower'
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)
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
                    color_discrete_sequence=px.colors.qualitative.Pastel # cor restaurada
                )
                fig_box.update_layout(yaxis_title="Temp (°C)")
                st.plotly_chart(fig_box, use_container_width=True)

        else:
            st.warning("Sem dados para os filtros selecionados.")
            
        st.divider()

        # seção 3: download
        st.subheader("Relatório e exportação")
        cd1, cd2 = st.columns(2)
        # baixar csv dos dados obtidos
        with cd1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar tabela (CSV)", csv, "dados_radiometricos.csv", "text/csv", use_container_width=True)
        # baixar pdf dos dados obtidos
        with cd2:
            if st.button("Gerar relatório PDF completo", use_container_width=True):
                with st.spinner("Gerando PDF..."):
                    pdf_b = gerar_pdf_final(st.session_state['dados'])
                    st.download_button("Baixar PDF", pdf_b, "relatorio_tecnico.pdf", "application/pdf", use_container_width=True)
    else:
        st.info("Processe as imagens primeiro na aba 'Processamento de amostras'.")