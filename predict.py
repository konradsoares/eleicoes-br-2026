#!/usr/bin/env python3
"""Projeção regional exploratória, Monte Carlo, com separação de dados observados."""
import csv,json,math,os,random,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'docs/data/latest.json'
OUTPUT=ROOT/'docs/data/projection.json'
UF_WEIGHTS={}  # populated only with actual historical 2022 total_valid

def read_history(year):
    p=ROOT/f'data/history_{year}.csv'
    if not p.exists():return {}
    with p.open(encoding='utf-8-sig',newline='') as f:
        items={}
        for r in csv.DictReader(f):
            uf=r['uf'].upper();share=float(r['bolsonaro_pct'].replace(',','.'))
            items[uf]={'bolsonaro':share/100 if share>1 else share, 'total':int(r['total_valid'])}
        return items

def candidate_group(candidate):
    s=(candidate['name']+' '+candidate.get('number','')).lower()
    if 'flávio' in s or 'flavio' in s or 'bolsonaro' in s or candidate.get('number')=='22':return 'bolsonaro'
    if 'lula' in s or 'luiz inácio' in s or 'luiz inacio' in s or candidate.get('number')=='13':return 'lula'
    return None

def main():
    out={'available':False,'note':'Estimativa condicionada a dados estaduais; não é pesquisa eleitoral nem resultado oficial.'}
    try:data=json.loads(DATA.read_text(encoding='utf-8'))
    except FileNotFoundError:data={}
    national=data.get('national')
    h18=read_history(2018);h22=read_history(2022)
    if not national or not h18 or not h22:
        out['reason']='Dados ao vivo e CSVs históricos 2018/2022 necessários. Nenhuma probabilidade foi inventada.'
    else:
        states=[]
        for s in data.get('states',[]):
            uf=s['uf'];p=s.get('progress'); rows=s.get('candidates',[])
            if uf not in h18 or uf not in h22 or p is None or p<=0 or p>1:continue
            votes={candidate_group(c):c['votes'] for c in rows if candidate_group(c)}
            if not ('bolsonaro' in votes and 'lula' in votes):continue
            total=sum(votes.values())
            if total<=0:continue
            # Scale remaining votes to historical 2022 valid votes (participation proxy).
            baseline=h22[uf]['bolsonaro']; old=h18[uf]['bolsonaro']
            observed=votes['bolsonaro']/total
            # Shrink current observed share toward the 2022 geographic proxy.
            # This is ONLY a scenario assumption, not identification of voter intent.
            mean=p*observed+(1-p)*baseline
            volatility=abs(baseline-old)
            # generous uncertainty: historical deviation + incomplete state coverage
            sigma=max(.025, .035+ .35*volatility)*(1-p)**.7
            remaining=max(0,int(h22[uf]['total']*(1-p)))
            states.append({'uf':uf,'progress':p,'mean':mean,'sigma':sigma,'votes_b':votes['bolsonaro'],
                           'votes_l':votes['lula'],'remaining':remaining,'historical_delta':volatility})
        if len(states)<15 or sum(s['votes_b']+s['votes_l'] for s in states)<1000000:
            out['reason']=f'Apenas {len(states)} estados elegíveis. Mínimo: 15 estados e 1 milhão de votos observados.'
        elif national.get('progress') is None:
            out['reason']='TSE não forneceu percentual nacional de apuração reconhecível; projeção suspensa.'
        else:
            rng=random.Random(20261025)
            trials=[]
            for _ in range(4000):
                b=l=0
                for s in states:
                    share=min(.99,max(.01,rng.gauss(s['mean'],s['sigma'])))
                    b+=s['votes_b']+s['remaining']*share
                    l+=s['votes_l']+s['remaining']*(1-share)
                trials.append(b/(b+l))
            trials.sort()
            win=sum(x>.5 for x in trials)/len(trials)
            out.update({'available':True,'coverage_states':len(states),
                        'bolsonaro_projected_share':round(sum(trials)/len(trials),5),
                        'interval_90':[round(trials[200],5),round(trials[3799],5)],
                        'simulation_frequency_bolsonaro':round(win,4),
                        'simulation_frequency_lula':round(1-win,4),
                        'assumptions':'Cenário condicionado: distribuição dos votos restantes proporcional aos totais estaduais de 2022; média encolhida para participação de Bolsonaro em 2022, desvio calibrado pela mudança regional 2018–22. Não é uma probabilidade calibrada de vitória.',
                        'method':'4.000 simulações de cenário; não interpretar frequência como chance estatística validada.',
                        'states':[{'uf':x['uf'],'progress':x['progress'],'projected_b_share':round(x['mean'],4)} for x in states]})
    OUTPUT.parent.mkdir(exist_ok=True,parents=True)
    OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(out.get('reason') or f"Cenários estimados para {out['coverage_states']} UFs")

if __name__=='__main__':main()
