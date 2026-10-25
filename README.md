# Observatório eleitoral 2026 — protótipo

Dashboard HTML com resultados oficiais agregados do TSE, cenários regionais experimentais em Python e comentários opcionais da OpenAI API.

## Rodar localmente

```bash
python collector.py
python predict.py
# opcional: export OPENAI_API_KEY='...'; python commentary.py
python -m http.server 8000 --directory docs
```

Abra `http://localhost:8000`. Apenas Python 3.10+; sem dependências pip. O HTML usa Chart.js CDN.

## Preparar dados históricos

Crie `data/history_2018.csv` e `data/history_2022.csv` no formato dos templates:

`uf,bolsonaro_pct,total_valid`

Inclua as 27 UFs. `bolsonaro_pct` corresponde à % de votos válidos **do segundo turno** obtidos por Jair Bolsonaro no respectivo ano; `total_valid` representa o total de votos válidos no estado no segundo turno. Consulte dados oficiais TSE: https://www.tse.jus.br/eleicoes/resultados-eleicoes e https://dadosabertos.tse.jus.br/ . NÃO invente valores. Os templates estão intencionalmente vazios, pois a importação/validação dos CSVs históricos ainda não foi automatizada. Sem os dois arquivos, o sistema exibirá votos reais sem projeção.

**Hipótese limitada**: a distribuição do voto de Jair Bolsonaro em 2018/2022 serve apenas como proxy geográfico para Flávio Bolsonaro em 2026. Transferência de votos entre candidatos e mudanças demográficas podem invalidar a projeção. A frequência Monte Carlo NÃO equivale a uma chance calibrada de vitória. Necessário validar com backtesting e substituir proxy de comparecimento pelo eleitorado real 2026.

## Publicação no GitHub Pages

1. Crie repositório e envie todo o diretório.
2. Configure Settings → Pages → Build and deployment → Deploy from a branch → main, `/docs`.
3. Habilite GitHub Actions; rode **Coleta e projeção eleitoral** pelo `workflow_dispatch` uma vez.
4. Opcional: Settings → Secrets and variables → Actions → New repository secret `OPENAI_API_KEY`.
5. `schedule` está a cada 5 minutos; GitHub não garante intervalos exatos. A cada execução, o workflow grava `docs/data/*.json` e faz commit no branch. GitHub Pages pode demorar para republicar.

## Importante — validação do JSON 2026

O padrão `https://resultados.tse.jus.br/oficial/ele2026/6257/dados/{uf}/{uf}-c0001-e006257-u.json` deriva de documentação de coletor independente consultada em 25/out/2026, **não foi possível consultar esse endpoint deste ambiente**. Verifique se a identificação de `6257` corresponde ao 2º turno no momento da execução; pode ser necessário configurar `TSE_BASE` e os nomes de arquivos a partir do manifesto eleitoral oficial. `collector.py` falha explicitamente em vez de inventar números.

O parser usa a estrutura TSE `carper[].cand[]` de anos anteriores. A versão 2026 pode precisar de ajuste. Analise `docs/data/latest.json` e mensagens de erro antes de confiar nos valores. Crie um snapshot real e valide votos e percentuais contra o painel oficial.

## Limites e integridade

- Não mostra probabilidade se faltam dados. Não exibe números artificiais.
- Projeção só calcula com ao menos 15 estados elegíveis, 1 milhão de votos e histórico 2018/2022 preenchido.
- Estados não elegíveis ficam fora da estimativa; isso pode introduzir erro grave. **Não use como previsão eleitoral confiável sem ampliar a cobertura e backtesting.**
- Falha de coleta mantém último snapshot e mostra aviso de obsolescência.
- A API da OpenAI só interpreta dados, nunca gera votos ou percentuais.
- `OPENAI_API_KEY` jamais é enviada ao navegador.
- Este projeto é independente e não possui vínculo com o TSE.


## Pesquisas de 24/10 (automático)
`python polls.py` gera `docs/data/polls.json` com seis pesquisas divulgadas em 24/10/2026, suas fontes e bases de cálculo, sem preenchimento de arquivos pelo usuário. O workflow executa o módulo automaticamente. O dashboard mostra o erro absoluto em pontos percentuais comparado aos votos válidos oficiais recebidos do TSE e, se disponível, à projeção. O ranking é **provisório** até 100% da apuração. Os números das pesquisas são um snapshot fixo de publicações de 24/10 (e não um feed de atualização ao vivo), justamente porque esta data está encerrada; coleta e atualização em tempo real são exclusivamente para o TSE. A Palver divulgou votos totais e a normalização é identificada. A base não garante cobertura exaustiva de todos os registros no TSE, porque registro da pesquisa não equivale a resultado publicado.


### Histórico automático (v5)
O workflow agora executa `python history.py` antes de `predict.py`. Consulta resultados públicos de 2018 e 2022 por UF, grava `data/history_2018.csv` e `data/history_2022.csv` somente quando obter as 27 UFs. Os formatos e a disponibilidade dos endpoints antigos precisam ser validados em GitHub Actions; falhas ficam no log e nenhuma projeção é fabricada. Os CSVs históricos completos são commitados no repositório; assim o bootstrap não precisa repetir os downloads.

### OpenAI
Em Settings > Secrets and variables > Actions adicione `OPENAI_API_KEY` como Repository secret. A assinatura ChatGPT Plus não fornece uma API key nem créditos de API. A análise da IA só aparece se o segredo estiver configurado e o serviço responder sem erro.


### Correções v7 (25/10/2026)
- Corrigida a escala percentual do TSE: `s.pst=0,25` corresponde a 0,25%, armazenado como 0.0025.
- Cores unificadas: `--lula` vermelho e `--flavio` azul, em todos os gráficos e painéis.
- O GitHub Pages pode levar algum tempo até publicar o commit; para cache do navegador use Ctrl+F5.
