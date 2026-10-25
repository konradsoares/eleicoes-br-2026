#!/usr/bin/env python3
"""Automatic historical TSE bootstrap. Best effort; fails closed on missing data."""
import csv,json,re,urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parent
UFS='AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split()

def request(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 EleicoesPublicas/1.0','Accept':'application/json,text/javascript,*/*'})
    with urllib.request.urlopen(req,timeout=14) as r: raw=r.read().decode('utf-8-sig')
    try:return json.loads(raw)
    except json.JSONDecodeError:
        begin=raw.find('{'); end=raw.rfind('}')
        if begin<0 or end<begin:raise
        return json.loads(raw[begin:end+1])

def integer(value):
    try:return int(str(value).replace('.','').replace(',',''))
    except (ValueError,TypeError):return 0

def find_candidates(obj):
    """Match commonly published TSE formats, avoid double-counting nested totals."""
    if isinstance(obj,dict):
        for key in ('cand','candidatos'):
            arr=obj.get(key)
            if isinstance(arr,list) and arr and all(isinstance(x,dict) for x in arr):
                if any('vap' in c for c in arr):return arr
        for key in ('carg','carper','agr','par','resultado','dados'):
            child=obj.get(key)
            if child is not None:
                found=find_candidates(child)
                if found:return found
    if isinstance(obj,list):
        for x in obj:
            found=find_candidates(x)
            if found:return found
    return []

def extract(data,uf,year):
    cand=find_candidates(data)
    def is_b(c):
        name=' '.join(str(c.get(k,'')) for k in ('nm','nmu','nome','n')).lower()
        return 'bolsonaro' in name or str(c.get('n',''))=='22'
    def is_l(c):
        name=' '.join(str(c.get(k,'')) for k in ('nm','nmu','nome','n')).lower()
        return 'lula' in name or 'haddad' in name or str(c.get('n',''))=='13'
    b=sum(integer(c.get('vap',c.get('votos',0))) for c in cand if is_b(c))
    other=sum(integer(c.get('vap',c.get('votos',0))) for c in cand if is_l(c))
    total=b+other
    if total<=0 or b<=0 or other<=0:raise ValueError(f'{year}/{uf}: cannot identify both candidates ({len(cand)} entries)')
    return {'uf':uf,'bolsonaro_pct':round(b/total*100,8),'total_valid':total}

def get_one(year,uf):
    lower=uf.lower()
    if year==2022:
        urls=[f'https://resultados.tse.jus.br/oficial/ele2022/545/dados-simplificados/{lower}/{lower}-c0001-e000545-r.json',
              f'https://resultados.tse.jus.br/oficial/ele2022/545/dados/{lower}/{lower}-c0001-e000545-u.json']
    else:
        urls=[f'https://interessados.divulgacao.tse.jus.br/2018/divulgacao/oficial/296/dadosdivweb/{lower}/{lower}-c0001-e000296-w.js',
              f'https://interessados2.divulgacao.tse.jus.br/2018/divulgacao/oficial/296/dadosdivweb/{lower}/{lower}-c0001-e000296-w.js']
    errors=[]
    for url in urls:
        try:return extract(request(url),uf,year)
        except Exception as e:errors.append(type(e).__name__+': '+str(e)[:90])
    raise RuntimeError('; '.join(errors))

def valid_file(p):
    if not p.exists():return False
    try:
        rows=list(csv.DictReader(p.open(encoding='utf-8-sig')))
        return len(rows)==27 and set(x['uf'] for x in rows)==set(UFS) and all(int(x['total_valid'])>0 for x in rows)
    except Exception:return False

def main():
    (ROOT/'data').mkdir(exist_ok=True)
    for year in (2018,2022):
        dest=ROOT/f'data/history_{year}.csv'
        if valid_file(dest):print(f'History {year}: cached 27 UFs');continue
        results=[];errors=[]
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures={pool.submit(get_one,year,uf):uf for uf in UFS}
            for f in as_completed(futures):
                try:results.append(f.result())
                except Exception as exc:errors.append(f'{futures[f]}: {exc}')
        if len(results)!=27:
            print(f'History {year}: {len(results)}/27 UFs; no incomplete CSV will be published.')
            for error in errors[:5]:print('  ',error)
            continue
        with dest.open('w',newline='',encoding='utf-8') as file:
            writer=csv.DictWriter(file,fieldnames=['uf','bolsonaro_pct','total_valid']);writer.writeheader();writer.writerows(sorted(results,key=lambda r:r['uf']))
        print(f'History {year}: downloaded 27 UFs')
if __name__=='__main__':main()
