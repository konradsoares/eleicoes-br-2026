#!/usr/bin/env python3
"""Experimental scenario simulator using all 27 UFs, even during very early counting.

NOT a calibrated election-winning probability. Uses 2022 turnout as a proxy and
2018/2022 geographic patterns as priors; Flavio 2026 != Jair 2022.
"""
import csv, json, math, random
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'docs/data/latest.json'
OUTPUT=ROOT/'docs/data/projection.json'

def history(year):
    f=ROOT/f'data/history_{year}.csv'
    if not f.exists(): return {}
    with f.open(encoding='utf-8-sig',newline='') as h:
        d={}
        for row in csv.DictReader(h):
            v=float(row['bolsonaro_pct'].replace(',','.'))
            d[row['uf'].upper()]={'share':v/100 if v>1 else v,'total':int(row['total_valid'])}
    return d

def group(c):
    s=(str(c.get('name',''))+' '+str(c.get('number',''))).lower()
    if any(x in s for x in ('flávio','flavio','bolsonaro')) or str(c.get('number'))=='22':return 'b'
    if any(x in s for x in ('lula','luiz in')) or str(c.get('number'))=='13':return 'l'
    return None

def clamp(x,lo,hi):return max(lo,min(hi,x))

def main():
    result={'available':False,'mode':'exploratory','note':'Cenários ilustrativos, NÃO probabilidade de vitória calibrada.'}
    try: current=json.loads(DATA.read_text(encoding='utf-8'))
    except (OSError,ValueError):current={}
    h18,h22=history(2018),history(2022)
    if not current.get('national') or set(h18)!=set(h22) or len(h22)!=27:
        result['reason']='Aguardando dados atuais e históricos oficiais completos das 27 UFs.'
    else:
        observations={}
        for state in current.get('states',[]):
            uf=state.get('uf','').upper()
            if uf not in h22:continue
            votes={group(c):int(c.get('votes') or 0) for c in state.get('candidates',[]) if group(c)}
            total=votes.get('b',0)+votes.get('l',0)
            progress=state.get('progress')
            if total>0:
                observations[uf]={'b':votes.get('b',0),'l':votes.get('l',0),'total':total,
                                  'share':votes.get('b',0)/total,
                                  'progress':clamp(float(progress or 0),0,1)}
        if not observations:
            result['reason']='Nenhum voto estadual contabilizado; impossível condicionar cenários à apuração atual.'
        else:
            # Conservative common-swing estimate: do not transfer local early-count
            # deviations mechanically to the whole country.
            weighted=weight=0.
            for uf,o in observations.items():
                w=math.sqrt(o['total'])*min(.3,max(.02,o['progress']))
                weighted+=w*clamp(o['share']-h22[uf]['share'],-.25,.25)
                weight+=w
            raw_swing=weighted/weight if weight else 0.
            observed_sections=sum(o['progress'] for o in observations.values())/27
            # Tiny early snapshots -> very weak inference about national swing.
            shrink=clamp(observed_sections*2,0,.65)
            inferred_swing=raw_swing*shrink
            rng=random.Random(20261025)
            trials=[]
            for _ in range(4000):
                # Correlated uncertainty matters: states cannot be treated independent.
                swing=rng.gauss(inferred_swing,.095*(1-shrink)+.025)
                b=l=0.
                for uf,h in h22.items():
                    o=observations.get(uf)
                    hist=h['share'];old=h18[uf]['share']
                    # General election and candidate changes are not recoverable
                    # from Jair Bolsonaro's 2022 share alone.
                    regional_sd=clamp(.055+abs(hist-old)*.24,.06,.15)
                    p=clamp(hist+swing+rng.gauss(0,regional_sd),.01,.99)
                    observed_total=o['total'] if o else 0
                    if o:
                        # Condition weakly on observed within-state share, because
                        # the ordering of counted precincts is nonrandom.
                        reliability=clamp(o['progress']*.7,0,.85)
                        p=(1-reliability)*p+reliability*o['share']
                    # 2022 turnout is a *rough* scale proxy, not 2026 turnout.
                    estimated_final=max(observed_total,h['total']*rng.uniform(.94,1.06))
                    remaining=max(0,estimated_final-observed_total)
                    b+=(o['b'] if o else 0)+remaining*p
                    l+=(o['l'] if o else 0)+remaining*(1-p)
                trials.append(b/(b+l))
            trials.sort()
            avg=sum(trials)/len(trials)
            frequency=sum(v>.5 for v in trials)/len(trials)
            result.update({'available':True,'provisional':True,'coverage_states':len(observations),
                'baseline_states':27,'observed_votes':sum(x['total'] for x in observations.values()),
                'bolsonaro_projected_share':round(avg,5),
                'interval_90':[round(trials[199],5),round(trials[3799],5)],
                'simulation_frequency_bolsonaro':round(frequency,4),
                'simulation_frequency_lula':round(1-frequency,4),
                'method':'4.000 cenários exploratórios com incerteza correlacionada e 27 UFs.',
                'assumptions':'Usa votos 2026 observados, pesos de comparecimento de 2022, geografia 2018/2022 e forte incerteza. Não equipara Flávio 2026 a Jair 2022. Simulações não foram calibradas por backtesting.',
                'warning':'APURAÇÃO INICIAL: resultados podem mudar muito. Frequência de cenário NÃO é chance de vitória calibrada.'})
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(result.get('reason') or f"Cenários exploratórios: {result['coverage_states']}/27 UFs com votos; 27 UFs no modelo. NÃO calibrado.")

if __name__=='__main__':main()
