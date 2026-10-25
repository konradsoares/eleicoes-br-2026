#!/usr/bin/env python3
"""OpenAI analysis of observed TSE metrics; optional, runs only when key present."""
import json,os,urllib.request
from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'docs/data'
a=json.loads((p/'latest.json').read_text(encoding='utf-8')) if (p/'latest.json').exists() else {}
b=json.loads((p/'projection.json').read_text(encoding='utf-8')) if (p/'projection.json').exists() else {}
key=os.getenv('OPENAI_API_KEY','')
if not key or not a.get('national'):
 print('Sem chave OpenAI ou resultado real; comentário ignorado.');raise SystemExit(0)
summary={'timestamp':a['updated_at'],'national':a['national'],'states':a['states'], 'projection':b}
request={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),'messages':[
 {'role':'system','content':'Você é analista quantitativo neutro. Responda em português brasileiro em até 130 palavras. Diferencie votos reais, projeção condicional e incerteza. Nunca afirme que uma frequência de simulação equivale a probabilidade de vitória calibrada. Não faça persuasão política, nem invente fatos.'},
 {'role':'user','content':'Interprete este snapshot estruturado, salientando viés de ordem de apuração e limitações: '+json.dumps(summary,ensure_ascii=False)[:25000]}
 ],'temperature':0.1,'max_tokens':280}
req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(request).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
try:
 with urllib.request.urlopen(req,timeout=35) as r:ans=json.load(r)['choices'][0]['message']['content']
 (p/'commentary.json').write_text(json.dumps({'updated_at':a['updated_at'],'text':ans},ensure_ascii=False,indent=2),encoding='utf-8')
 print('Análise textual atualizada')
except Exception as e:print('OpenAI indisponível:',type(e).__name__,str(e)[:160])
