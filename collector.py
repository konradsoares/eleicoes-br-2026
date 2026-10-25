#!/usr/bin/env python3
"""Coletor público TSE: não inventa dados quando a origem falha."""
import json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'docs/data/latest.json'
BASE=os.getenv('TSE_BASE','https://resultados.tse.jus.br/oficial/ele2026/6258/dados')
UFS='AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split()

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ElectionAnalysisResearch/1.0 (public aggregate JSON)','Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=16) as r:
        return json.loads(r.read().decode('utf-8-sig'))

def num(x):
    try:return int(str(x).replace('.','').replace(',',''))
    except (ValueError,TypeError): return 0

def pct(x):
    try:
        f=float(str(x).replace(',','.'))
        return f / 100  # O TSE informa porcentagem (ex.: '0,25' significa 0,25%, não 25%)
    except (ValueError,TypeError):return 0

def extract(raw, uf):
    """EA20 (2026): carg -> agr -> par -> cand; 0% is still a valid snapshot."""
    blocks=raw.get('carg') or raw.get('carper') or []
    if isinstance(blocks,dict): blocks=[blocks]
    candidates=[]
    for block in blocks:
        if not isinstance(block,dict) or str(block.get('cd','1')).lstrip('0') not in ('1',''): continue
        entries=block.get('cand') or block.get('candidatos') or []
        for agr in block.get('agr',[]):
            entries.extend(agr.get('cand') or [])
            for party in agr.get('par',[]):
                entries.extend(party.get('cand') or [])
        for c in entries:
            if not isinstance(c,dict): continue
            name=c.get('nmu') or c.get('nm') or c.get('nome') or ''
            if not name: continue
            candidates.append({'name':str(name),'number':str(c.get('n','')),
                'votes':num(c.get('vap',c.get('votos',0))),
                'percent_reported':pct(c.get('pvap',0))})
    if not candidates: raise ValueError(f'Candidatos ausentes no layout EA20 para {uf}: {list(raw)[:20]}')
    summary=raw.get('s') or {}
    progress=pct(summary['pst']) if 'pst' in summary else None
    return {'uf':uf,'progress':progress,'candidates':sorted(candidates,key=lambda x:-x['votes']),
            'source_timestamp': ' '.join(x for x in [raw.get('dg',''),raw.get('hg','')] if x) or None}

def main():
    now=datetime.now(timezone.utc).isoformat()
    result={'updated_at':now,'source':BASE,'election':'Presidente do Brasil — 2º turno 2026','national':None,'states':[], 'errors':[]}
    locations=[('BR',f'{BASE}/br/br-c0001-e006258-u.json')]+[(uf,f'{BASE}/{uf.lower()}/{uf.lower()}-c0001-e006258-u.json') for uf in UFS]
    def collect(entry):
        uf,url=entry
        try:return uf,extract(fetch(url),uf),None
        except Exception as ex:return uf,None,f'{uf}: {type(ex).__name__}: {str(ex)[:180]}'
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(collect,entry) for entry in locations]
        for future in as_completed(futures):
            uf,parsed,err=future.result()
            if err: result['errors'].append(err)
            elif uf=='BR':result['national']=parsed
            else:result['states'].append(parsed)
    result['states'].sort(key=lambda s:s['uf'])
    OUT.parent.mkdir(parents=True,exist_ok=True)
    # Never replace valid data with empty snapshot; stale data must have its original timestamp.
    if not result['national'] and OUT.exists():
        old=json.loads(OUT.read_text(encoding='utf-8'))
        if old.get('national'):
            old['last_collection_error_at']=now
            old['last_collection_errors']=result['errors']
            OUT.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
            print('Falha na coleta; preservado snapshot anterior, explicitamente marcado.')
            return
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Estados:',len(result['states']),'Erros:',len(result['errors']))
    for err in result['errors'][:10]: print('  ',err)

if __name__=='__main__': main()
