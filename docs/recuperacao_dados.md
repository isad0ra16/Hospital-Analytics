# Estratégia de recuperação dos dados

O projeto original foi perdido junto com o computador. Esta estratégia garante que os dados
possam ser recuperados e **comprovados idênticos** mesmo que o ambiente de execução seja perdido.

## Três camadas de proteção

| Camada | O que guarda | Onde | Protege contra |
|---|---|---|---|
| 1. Código + manifesto | Pipeline, testes, `data/MANIFEST.json` (URLs, datas, tamanhos, SHA-256, impressões digitais) | Git (GitHub) | Perda do ambiente / computador |
| 2. Cópia arquivada do original | `RDRJ2401.dbc` exatamente como baixado | Release `data-rdrj2401` do GitHub (fora do histórico do Git) | Republicação ou indisponibilidade do DATASUS |
| 3. Fonte oficial | Arquivo publicado | FTP do DATASUS | Perda da Release |

Os arquivos derivados (Parquet) **não precisam de backup**: são regenerados pelo pipeline e
comprovados idênticos pela impressão digital do conteúdo registrada no manifesto.

## Procedimento de recuperação (do zero)

```bash
git clone https://github.com/isad0ra16/Hospital-Analytics.git
cd Hospital-Analytics
make install      # ambiente idêntico (uv.lock)
make fetch-data   # baixa o .dbc da Release e confere o SHA-256 com o manifesto
make convert      # regenera o Parquet
make validate     # confirma 73.046 registros, 113 colunas, R$ 125.440.636,13 e a impressão digital
```

Se a Release estiver indisponível, baixar do FTP oficial (`official_url` no manifesto) para
`data/raw/` e executar `make verify`. Se o SHA-256 **não** coincidir, o DATASUS publicou outra
versão do arquivo: ela deve ser registrada como **nova fonte**, nunca substituir a atual, e todos
os indicadores precisam ser reconciliados novamente.

## Identificação da versão dos dados

O DATASUS não versiona os arquivos. A versão é identificada por:

1. **SHA-256** do `.dbc`: `a3f0ea9a6ce75099fa8210d81b13736fc4da4ac1acf30e8245c7aa3a0d7dfc9c`;
2. **data de última atualização** gravada no cabeçalho DBF: **2025-02-08**;
3. **data do download**: 2026-11-09.

## Recomendações

- Manter também uma cópia offline pessoal do `.dbc` (por exemplo, em armazenamento em nuvem
  pessoal), com o SHA-256 anotado.
- Não editar nem substituir o asset da Release `data-rdrj2401`. Se precisar de outra versão,
  criar outra Release com outra tag.
- Considerar proteger a tag nas configurações do repositório (*Rules → Tag rulesets*).
