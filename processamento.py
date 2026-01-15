import os
import cv2
import numpy as np
import pandas as pd
from PIL import Image, ExifTags

# --- CONFIGURAÇÕES ---
PASTA_IMAGENS = 'imagens'
PASTA_SAIDA = 'dados_processados'
ARQUIVO_CSV = 'dados_termografia_final.csv'
TEMP_MIN_CAMERA = 20.0
TEMP_MAX_CAMERA = 40.0

if not os.path.exists(PASTA_SAIDA): os.makedirs(PASTA_SAIDA)

def pixel_para_temp(valor_pixel):
    return TEMP_MIN_CAMERA + (valor_pixel / 255.0) * (TEMP_MAX_CAMERA - TEMP_MIN_CAMERA)

def carregar_imagem_corrigida(caminho):
    """ Carrega corrigindo a rotação, pois o cv2.selectROI não lê EXIF """
    try:
        pil_img = Image.open(caminho)
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation': break
        exif = pil_img._getexif()
        if exif:
            exif = dict(exif.items())
            val = exif.get(orientation)
            if val == 3: pil_img = pil_img.rotate(180, expand=True)
            elif val == 6: pil_img = pil_img.rotate(270, expand=True)
            elif val == 8: pil_img = pil_img.rotate(90, expand=True)
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except:
        return cv2.imread(caminho)

def extrair_metadados(nome_arquivo):
    partes = os.path.splitext(nome_arquivo)[0].split('_')
    if len(partes) >= 6:
        return {
            'ID_Planta': partes[0], 'Temp_Ambiente': partes[1], 'Tratamento': partes[2],
            'Periodo': partes[3], 'Tipo': partes[4], 'Replica': partes[5], 'Arquivo_Original': nome_arquivo
        }
    return None

def main():
    print("--- MODO MANUAL: SELECIONE A PLANTA COM O MOUSE ---")
    print("1. Desenhe o retângulo na planta.")
    print("2. Aperte ENTER ou ESPAÇO para confirmar.")
    print("3. Aperte 'c' para cancelar/pular uma imagem ruim.")
    
    lista_dados = []
    arquivos = [f for f in os.listdir(PASTA_IMAGENS) if 'thermal' in f.lower() and f.endswith('.jpg')]
    
    cv2.namedWindow("Selecione a Planta (ENTER p/ Confirmar)", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Selecione a Planta (ENTER p/ Confirmar)", 800, 600)

    for i, arquivo in enumerate(arquivos):
        print(f"[{i+1}/{len(arquivos)}] Processando: {arquivo}")
        
        caminho = os.path.join(PASTA_IMAGENS, arquivo)
        img = carregar_imagem_corrigida(caminho)
        
        if img is None: continue

        # Abre seletor manual
        # showCrosshair=True mostra a cruz para ajudar a mirar
        roi = cv2.selectROI("Selecione a Planta (ENTER p/ Confirmar)", img, showCrosshair=True, fromCenter=False)
        
        # roi retorna (x, y, w, h). Se w ou h forem 0, usuário cancelou.
        if roi[2] == 0 or roi[3] == 0:
            print("   ⏩ Pulada (Seleção vazia)")
            continue

        x, y, w, h = roi
        
        # Recorta a planta baseada na sua seleção
        recorte = img[y:y+h, x:x+w]
        
        # Converte para tons de cinza para pegar temperatura
        recorte_gray = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
        
        # Opcional: Ainda aplica um Otsu simples DENTRO da sua seleção 
        # para tirar pequenos pedaços de fundo que vieram junto no retângulo
        blur = cv2.GaussianBlur(recorte_gray, (5,5), 0)
        _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        pixels_planta = recorte_gray[mask > 0]
        
        # Se o Otsu falhar (ficar vazio), usa o retângulo inteiro mesmo
        if len(pixels_planta) == 0:
            pixels_planta = recorte_gray.flatten()

        temps = [pixel_para_temp(p) for p in pixels_planta]
        
        # Salva a imagem recortada para o dashboard
        nome_proc = f"proc_{arquivo}"
        cv2.imwrite(os.path.join(PASTA_SAIDA, nome_proc), recorte)
        
        meta = extrair_metadados(arquivo)
        if meta:
            stats = {
                'Temp_Media': np.mean(temps), 'Temp_Max': np.max(temps),
                'Temp_Min': np.min(temps), 'Desvio_Padrao': np.std(temps),
                'Area_Pixels': len(pixels_planta)
            }
            lista_dados.append({**meta, **stats, 'Caminho_Imagem_Proc': nome_proc})
            print(f"   ✔ Salvo! Média: {stats['Temp_Media']:.1f}°C")

    cv2.destroyAllWindows()
    
    if lista_dados:
        pd.DataFrame(lista_dados).to_csv(ARQUIVO_CSV, index=False)
        print("\n✅ CSV gerado com sucesso!")

if __name__ == "__main__":
    main()