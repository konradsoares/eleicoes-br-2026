#!/usr/bin/env python3
"""One-time TSE open-data bootstrap for presidential runoff UF totals (2018/2022).
Downloads official municipality/zone data, processes _BR.csv and caches a 27-UF CSV.
Run again safely: completed caches are never downloaded again.
"""
import csv
import io
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UFS = set('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split())
API = 'https://dadosabertos.tse.jus.br/api/3/action/package_show?id=resultados-{}'
# Official archive mirrors. Fall back to resource URL discovered from TSE CKAN API.
MIRRORS = {
    2018: 'https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2018.zip',
    2022: 'https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip',
}

def open_url(url, timeout=55):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; PublicElectoralStats/1.0)'})
    return urllib.request.urlopen(req, timeout=timeout)

def existing(year):
    file = ROOT / 'data' / f'history_{year}.csv'
    if not file.is_file():
        return False
    try:
        with file.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        return {r['uf'] for r in rows} == UFS and len(rows) == 27 and all(int(r['total_valid']) > 0 for r in rows)
    except (ValueError, KeyError, OSError):
        return False

def get_urls(year):
    urls = [MIRRORS[year]]
    try:
        with open_url(API.format(year), timeout=15) as resp:
            meta = json.load(resp)
        resources = meta['result']['resources']
        for resource in resources:
            name = ' '.join(str(resource.get(k, '')) for k in ('name', 'description', 'url')).lower()
            if 'votacao_candidato_munzona' in name or ('votação' in name and 'município' in name and 'zona' in name):
                url = resource.get('url')
                if url and url not in urls:
                    urls.append(url)
    except Exception as exc:
        print(f'History {year}: aviso — metadados CKAN indisponíveis: {exc}')
    return urls

def download(url, dest):
    with open_url(url) as resp, dest.open('wb') as out:
        shutil.copyfileobj(resp, out, length=1024 * 1024)

def parse_archive(path, year):
    votes = defaultdict(lambda: defaultdict(int))
    with zipfile.ZipFile(path) as archive:
        members = [m for m in archive.namelist() if m.lower().endswith('_br.csv') and 'votacao_candidato_munzona' in m.lower()]
        if not members:
            raise ValueError('Arquivo de Presidente *_BR.csv não encontrado no ZIP do TSE')
        for member in members:
            with archive.open(member) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding='latin-1', newline=''), delimiter=';')
                fields = set(reader.fieldnames or [])
                required = {'SG_UF', 'NR_TURNO', 'NR_CANDIDATO', 'QT_VOTOS_NOMINAIS'}
                if not required.issubset(fields):
                    raise ValueError(f'Campos ausentes em {member}: {required-fields}')
                for row in reader:
                    if row['NR_TURNO'].strip() != '2':
                        continue
                    uf = row['SG_UF'].strip().upper()
                    number = row['NR_CANDIDATO'].strip()
                    if uf not in UFS or number not in ('13', '17', '22'):
                        continue
                    if 'CD_CARGO' in fields and row['CD_CARGO'].strip() != '1':
                        continue
                    if 'DS_CARGO' in fields and 'PRESIDENTE' not in row['DS_CARGO'].upper():
                        continue
                    votes[uf][number] += int(row['QT_VOTOS_NOMINAIS'] or 0)
    opponent = '17' if year == 2018 else '22'
    rows = []
    for uf in sorted(UFS):
        lula_side = votes[uf]['13']  # Haddad (2018), Lula (2022)
        bolsonaro_side = votes[uf][opponent]
        total = lula_side + bolsonaro_side
        if lula_side == 0 or bolsonaro_side == 0:
            raise ValueError(f'{year}/{uf} contém votos insuficientes: 13={lula_side}, {opponent}={bolsonaro_side}')
        rows.append({'uf': uf, 'bolsonaro_pct': f'{bolsonaro_side * 100 / total:.8f}', 'total_valid': total})
    return rows

def main():
    (ROOT/'data').mkdir(exist_ok=True)
    for year in (2018, 2022):
        if existing(year):
            print(f'History {year}: cache completo (27 UFs), download dispensado')
            continue
        errors = []
        for url in get_urls(year):
            with tempfile.TemporaryDirectory() as directory:
                archive = Path(directory) / f'{year}.zip'
                try:
                    print(f'History {year}: baixando arquivo consolidado do TSE: {url}', flush=True)
                    download(url, archive)
                    rows = parse_archive(archive, year)
                    target = ROOT/'data'/f'history_{year}.csv'
                    tmp = target.with_suffix('.tmp')
                    with tmp.open('w', newline='', encoding='utf-8') as out:
                        writer = csv.DictWriter(out, fieldnames=['uf', 'bolsonaro_pct', 'total_valid'])
                        writer.writeheader(); writer.writerows(rows)
                    tmp.replace(target)
                    print(f'History {year}: OK, 27 UFs, {sum(r["total_valid"] for r in rows):,} votos válidos')
                    break
                except Exception as exc:
                    errors.append(f'{type(exc).__name__}: {exc}')
        else:
            print(f'History {year}: ERRO. Fontes tentadas: {len(errors)}; ' + ' | '.join(errors[:3]))
            print('Dados históricos não foram fabricados; painel de projeção permanecerá indisponível.')

if __name__ == '__main__':
    main()
