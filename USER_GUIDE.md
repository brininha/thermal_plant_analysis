# 🌱 Ferramenta de análise térmica de plantas — guia do usuário

Ferramenta para extrair temperatura foliar de imagens FLIR, utilizando processamento radiométrico e geração de relatórios estatísticos.



## 1. Instalação e inicialização

O software foi preparado para rodar localmente no seu computador, garantindo performance e privacidade dos dados.

### Para usuários Windows (recomendado)

1.  **Download**:
    * Baixe o arquivo `software_analise_termica.zip`.
    * *Nota:* O arquivo tem cerca de **700 MB** pois contém todo o motor de processamento embutido.

2.  **Extração**:
    * **Não abra** o programa direto de dentro do arquivo ZIP.
    * Clique com o botão direito no arquivo baixado e selecione **"Extrair tudo..."** (Extract all). Escolha uma pasta de sua preferência.

3.  **Iniciar**:
    * Entre na pasta extraída `software_analise_termica`.
    * Dê um clique duplo no arquivo **`Iniciar.bat`**.
    * *Dica:* Se quiser um atalho na Área de Trabalho, clique com o botão direito no `Iniciar.bat` > Enviar para > Área de Trabalho (criar atalho). **Não arraste o arquivo original para fora da pasta.**

4.  **Uso**:
    * Uma janela preta (terminal) abrirá. **Não a feche**, ela é o motor do sistema.
    * O navegador abrirá automaticamente com a ferramenta pronta para uso.
    * **Se o navegador não abrir sozinho:**
        * Olhe para a janela preta e procure a linha que diz: `http://localhost:8501`
        * Segure a tecla **Ctrl** e clique neste link;
        * Ou copie o endereço `http://localhost:8501` e cole no seu navegador (Chrome, Edge, Firefox...).
  

### Para usuários Mac e Linux (avançado)
O pacote automático (`.bat`) é exclusivo para Windows. Em outros sistemas, siga estes passos manuais:

1.  **Pré-requisitos**:
    * Tenha o **Python 3.10+** instalado.
    * Instale a ferramenta **ExifTool**:
        * Mac: `brew install exiftool`
        * Linux: `sudo apt-get install libimage-exiftool-perl`

2.  **Execução**:
    * Abra o terminal na pasta do projeto.
    * Instale as dependências: `pip install -r requirements.txt`
    * Rode o comando: `streamlit run app_completo.py`



## 2. Preparação dos arquivos (importante)

Para o sistema agrupar automaticamente a foto visual com a foto térmica e ler metadados (tratamento, período, etc.), os arquivos devem seguir estritamente o padrão de nomenclatura abaixo, separados por underline (_).

**Padrão de nomenclatura**
```
ID_TempAmbiente_Tratamento_Periodo_Replica_Tipo.jpg
```

- ID: identificador único da planta (ex.: `P01`, `Planta10`).  
- TempAmbiente: temperatura da estufa/câmara no momento da foto (ex.: `21`, `27`, `35`, `45`). essencial para calibração automática.  
- Tratamento: grupo experimental (ex.: `controle`, `heatstress`, `recovery`).  
- Periodo: momento da coleta (ex.: `Dia`, `Noite`, `Manha`).  
- Replica: número da réplica (ex.: `R1`, `R2`).  
- Tipo: deve terminar com `thermal` ou `visual`.

Exemplos válidos:
- `P05_27_Controle_Dia_R1_visual.jpg`  
- `P05_27_Controle_Dia_R1_thermal.jpg`



## 3. Passo a passo de uso

### Passo 1 — Upload
1. Abra a aplicação no navegador.  
2. Na barra lateral, faça upload dos arquivos (aceita múltiplos).  
Dica: arraste dezenas de arquivos; o sistema agrupa pares automaticamente.

### Passo 2 — Editor de recorte
- Esquerda: imagem visual (referência).  
- Direita: imagem térmica com retângulo de seleção.  
Ajuste o retângulo para cobrir a planta e clique em **Confirmar**. O sistema salva os dados e passa para a próxima amostra.

### Passo 3 — Dashboard e análise
Abra a aba **Dashboard completo** para visualizar:
- Inspeção de pixels: Passe o mouse sobre o mapa de calor para ver a temperatura exata de cada ponto.

- Gráfico de barras: Comparativo de médias por tratamento.

- Heatmap geral: Matriz de calor (tratamento × período).

- Boxplot: Distribuição estatística para detecção de outliers.



## 4. Exportando resultados

Na seção **Relatório e exportação** do dashboard:

- **Baixar tabela (CSV)**: exporta dados brutos (média, máxima, mínima, desvio padrão).  
- **Gerar relatório PDF**: gera PDF com, para cada amostra:
  - foto visual original;  
  - recorte da imagem térmica; 
  - um mapa de calor gerado matematicamente a partir dos sensores. 
  - tabela de estatísticas.



## 5. Observações e dicas
- Use nomes consistentes para evitar falhas no pareamento automático.  
- Recomenda‑se imagens com boa resolução para melhores resultados (essa dica será útil para a próxima versão de segmentação automática).
- Se você subir uma imagem thermal sem a correspondente visual (ou vice-versa), o sistema avisará e ela não será processada.
