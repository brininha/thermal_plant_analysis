import cv2
import os
import numpy as np
import matplotlib.pyplot as plt

# caminho para a pasta das imagens
caminho_da_pasta = './imagens/P1_T27_controle_dia/a1'

# listando os arquivos na pasta
try:
    nomes_arquivos = os.listdir(caminho_da_pasta)
except FileNotFoundError:
    print(f"Erro: A pasta '{caminho_da_pasta}' não foi encontrada. Verifique o caminho.")
    exit()

# verificando se as imagens tem extensoes validas
extensoes_validas = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp') 
nomes_imagens = [f for f in nomes_arquivos if f.lower().endswith(extensoes_validas)]

if not nomes_imagens:
    print(f"Nenhuma imagem encontrada na pasta com as extensões {extensoes_validas}.")
    exit()

print(f"Encontradas {len(nomes_imagens)} imagens.")

# carregando imagens encontradas numa lista
lista_imagens_carregadas = list()
for nome_imagem in nomes_imagens:
    # constroi o caminho completo para cada imagem
    caminho_completo = os.path.join(caminho_da_pasta, nome_imagem)

    # carregando imagem
    img = cv2.imread(caminho_completo, cv2.IMREAD_GRAYSCALE)

    if img is not None:
        # adicionando imagem carregada a lista
        lista_imagens_carregadas.append(img)
    else:
        print(f"Aviso: Não foi possível carregar a imagem: {nome_imagem}")

print(f"Total de imagens carregadas com sucesso: {len(lista_imagens_carregadas)}")

# exibindo uma imagem da lista
# if lista_imagens_carregadas:
#     plt.imshow(lista_imagens_carregadas[2], cmap='gray')
#     plt.title(f"Nome da imagem: {nomes_imagens[2]}")
#     plt.show()


# recortando imagens
y1, y2, x1, x2 = 40, 270, 10, 200
imagens_recortadas = list()
for img in lista_imagens_carregadas:
    corte = img[y1:y2, x1:x2]
    imagens_recortadas.append(corte)

# exibindo uma imagem recortada
if imagens_recortadas:
    plt.imshow(imagens_recortadas[2], cmap='gray')
    plt.title("Imagem recortada")
    plt.colorbar(label='Temperatura')
    plt.show()