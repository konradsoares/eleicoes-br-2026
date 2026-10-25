# v10 — simulações preliminares durante apuração lenta

* Substitui bloqueio fixo de 15 UFs / 1 milhão de votos por cenários condicionais com 27 UFs.
* Estados com 0 votos recebem base geográfica de 2022 e incerteza correlacionada; 2018 informa dispersão regional.
* Se houver pelo menos um estado com votos e os dois CSVs históricos completos, executa 4.000 simulações.
* A frequência das simulações **não** é uma probabilidade de vitória calibrada, e os cenários são altamente sensíveis às hipóteses sobre os votos ainda não apurados.
* Não gera cenários se os históricos não estiverem presentes.
* Não altera dados oficiais do TSE; nenhuma atualização nova do TSE é necessária para rodar o modelo.

## Atualização

Substitua `predict.py` e `docs/index.html`. Confirme que existem `data/history_2018.csv` e `data/history_2022.csv` no repositório, com 27 linhas válidas. Execute o workflow manualmente. Se os dois CSVs foram publicados pelo workflow anterior, não é necessário baixá-los de novo.
