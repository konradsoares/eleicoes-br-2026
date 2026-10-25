#!/usr/bin/env python3
"""Snapshot automatizado, rastreável, das últimas pesquisas publicadas até 24/10/2026.
Fontes: resumo UOL (24/10) e matérias dos institutos. Não requer entrada do usuário.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parent/'docs/data/polls.json'
# Resultados publicados em 24/10, com votos válidos, exceto Palver (normalização assinalada).
# Snapshot de origem noticiosa verificável; nunca rotulado como coleta em tempo real.
SOURCE='https://noticias.uol.com.br/eleicoes/2026/10/24/lula-x-flavio-nas-novas-pesquisas-de-segundo-turno-veja-numeros-atualizados.ghtm'
P=[
 ('AtlasIntel/Bloomberg',50.8,49.2,'validos','https://noticias.uol.com.br/eleicoes/2026/10/24/atlasintel-presidencial-24-de-outubro.ghtm'),
 ('Datafolha',51.0,49.0,'validos',SOURCE),
 ('Quaest',51.0,49.0,'validos',SOURCE),
 ('BTG/Nexus',50.5,49.5,'validos',SOURCE),
 ('CNT/MDA',50.7,49.3,'validos','https://noticias.uol.com.br/eleicoes/2026/10/24/cntmda-pesquisa-presidencial-24-de-outubro.ghtm'),
 ('Palver',50/99*100,49/99*100,'estimativa_normalizada_de_votos_totais',SOURCE)
]

def main():
    result={'snapshot_date':'2026-10-24','generated_at':datetime.now(timezone.utc).isoformat(),
            'collection_method':'snapshot verificado de publicações jornalísticas; não coleta ao vivo',
            'disclaimer':'Registro no TSE não significa que os resultados numéricos estejam disponíveis no dataset público.',
            'polls':[{'id':name.lower().replace('/','-').replace(' ','-'),'institute':name,
              'published_at':'2026-10-24','flavio_valid_pct':flavio,'lula_valid_pct':lula,
              'basis':basis,'source_url':url,'source_date':'2026-10-24'} for name,flavio,lula,basis,url in P]}
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('Pesquisas carregadas:',len(result['polls']))
if __name__=='__main__':main()
