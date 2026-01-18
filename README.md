[![Keep alive Streamlit](https://github.com/brininha/thermal_plant_analysis/actions/workflows/keep_alive.yml/badge.svg)](https://github.com/brininha/thermal_plant_analysis/actions/workflows/keep_alive.yml)

# 🌱 Análise térmica de plantas

Aplicação web desenvolvida em Python para processamento e análise estatística de imagens térmicas de plantas. O sistema automatiza o pareamento de imagens RGB/térmicas, permite segmentação semi-automática e gera relatórios detalhados para pesquisa acadêmica.

> 📘 **Não é desenvolvedor?**
> [Clique aqui para ler o guia de uso](./USER_GUIDE.md) com o passo a passo de como operar a ferramenta.

---

## 🚀 Funcionalidades

* **Pareamento inteligente:** Algoritmo que identifica e agrupa automaticamente pares de imagens (visual e térmica) baseados em nomenclatura padronizada.
* **Segmentação de imagem:** Interface interativa para recorte e remoção de fundo utilizando **OpenCV** (processamento de imagem) e **Streamlit Cropper**.
* **Extração de dados:** Cálculo automático de temperatura mínima, média, máxima e desvio padrão por amostra.
* **Dashboard analítico:** Visualização de dados interativa com **Plotly**:
    * Gráficos de barras agrupados.
    * Heatmaps de temperatura por tratamento.
    * Boxplots para detecção de outliers.
* **Relatórios automatizados:** Geração de PDFs com as imagens processadas e tabelas estatísticas usando **FPDF**.

## 🛠️ Tecnologias utilizadas

* **Linguagem:** Python 3.9+
* **Frontend/framework:** Streamlit
* **Processamento de imagem:** OpenCV, Pillow, NumPy
* **Análise de dados:** Pandas
* **Visualização:** Plotly Express
* **Infraestrutura:** GitHub Actions

## 📦 Como rodar localmente

Siga os passos abaixo para executar a aplicação na sua máquina:

### 1. Clonar o repositório
```bash
git clone [https://github.com/brininha/thermal_plant_analysis.git](https://github.com/brininha/thermal_plant_analysis.git)
cd thermal_plant_analysis
```

### 2. Criar um ambiente virtual (recomendado)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Executar a aplicação

O arquivo principal da aplicação é o app_completo.py.

```bash
streamlit run app_completo.py
```

## 📂 Estrutura do projeto

- `app_completo.py`: Código fonte principal contendo a lógica da interface, processamento de imagem e geração de gráficos.

- `requirements.txt`: Lista de bibliotecas necessárias.

- `keep_alive.py`: Script de automação para manter o servidor ativo.

- `.github/workflows`: Configuração do GitHub Actions para monitoramento.

- `USER_GUIDE.md`: Guia para operação do software.