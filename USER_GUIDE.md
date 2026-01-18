# 🌱 Ferramenta de análise térmica de plantas — guia do usuário

Ferramenta para extrair temperatura foliar de imagens FLIR, com seleção semi‑automática e geração de relatórios estatísticos.

---

## 1. Preparação dos arquivos (importante)

Para o sistema agrupar automaticamente a foto visual (RGB) com a foto térmica (IR) e ler metadados (tratamento, período, etc.), os arquivos devem seguir estritamente o padrão de nomenclatura abaixo, separados por underline (_).

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

---

## 2. Passo a passo de uso

### Passo 1 — Upload
1. Abra a aplicação no navegador.  
2. Na barra lateral, faça upload dos arquivos (aceita múltiplos).  
Dica: arraste dezenas de arquivos; o sistema agrupa pares automaticamente.

### Passo 2 — Editor de recorte
- Esquerda: imagem visual (referência).  
- Direita: imagem térmica com retângulo de seleção.  
Ajuste o retângulo para cobrir a planta e clique em **Confirmar**. O algoritmo remove fundo automaticamente dentro da seleção. O sistema salva os dados e passa para a próxima amostra.

### Passo 3 — Dashboard e análise
Abra a aba **Dashboard completo** para visualizar:
- Gráfico de barras: média de temperatura por tratamento e período.  
- Heatmap: matriz (Tratamento × Período) das médias.  
- Boxplot: distribuição e pontos individuais (plantas).

---

## 3. Exportando resultados

Na seção **Relatório e exportação** do dashboard:

- **Baixar tabela (CSV)**: exporta dados brutos (média, máxima, mínima, desvio padrão).  
- **Gerar relatório PDF**: gera PDF com, para cada amostra:
  - foto visual original;  
  - recorte térmico processado;  
  - tabela de estatísticas.

---

## Observações e dicas
- Use nomes consistentes para evitar falhas no pareamento automático.  
- TempAmbiente fora dos valores previstos usa escala padrão.  
- Recomenda‑se imagens com boa resolução para melhores resultados.