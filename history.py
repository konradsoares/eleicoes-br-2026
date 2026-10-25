#!/usr/bin/env python3
"""Bootstrap TSE historic presidential runoff votes by UF.

Uses published presidential nationwide BR archives for voting by section;
never relies on obsolete election-results JSON IDs. Built-in URL fallback and
validation; publishes CSV atomically only after both candidates and 27 UFs pass.
"""
import csv
import io
import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UFS = set('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split())
BASE = 'https://cdn.tse.jus.br/estatistica/sead/odsele'
SOURCES = lambda year: [
    f'{BASE}/votacao_candidato_munzona/votacao_candidato_munzona_{year}.zip',
]
EXPECTED_MIN = 80_000_000


def fetch(url, destination):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/zip,*/*'})
    with urllib.request.urlopen(req, timeout=45) as src, destination.open('wb') as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)


def rows_for_archive(archive_path, year):
    totals = defaultdict(lambda: defaultdict(int))
    with zipfile.ZipFile(archive_path) as archive:
        members = [x for x in archive.namelist() if x.lower().endswith('.csv')]
        if not members:
            raise ValueError('ZIP sem CSV')
        for member in members:
            # BR voting-by-section contains all states; consolidated munzona may
            # include one CSV per state; ignore non-presidential files.
            with archive.open(member) as stream:
                text = io.TextIOWrapper(stream, encoding='latin-1', newline='')
                reader = csv.DictReader(text, delimiter=';')
                fields = set(reader.fieldnames or [])
                uf_key = 'SG_UF'
                number_key = 'NR_VOTAVEL' if 'NR_VOTAVEL' in fields else 'NR_CANDIDATO'
                votes_key = 'QT_VOTOS' if 'QT_VOTOS' in fields else 'QT_VOTOS_NOMINAIS'
                required = {uf_key, 'NR_TURNO', number_key, votes_key}
                if not required <= fields:
                    continue
                for row in reader:
                    if row['NR_TURNO'].strip() != '2':
                        continue
                    if 'CD_CARGO' in fields and row['CD_CARGO'].strip().lstrip('0') != '1':
                        continue
                    if 'DS_CARGO' in fields and 'PRESIDENTE' not in row['DS_CARGO'].upper():
                        continue
                    uf = row[uf_key].strip().upper()
                    candidate = row[number_key].strip().lstrip('0')
                    if uf not in UFS or candidate not in ('13', '17', '22'):
                        continue
                    totals[uf][candidate] += int(row[votes_key].strip() or '0')
    opponent = '17' if year == 2018 else '22'
    results = []
    for uf in sorted(UFS):
        a, b = totals[uf]['13'], totals[uf][opponent]
        if not a or not b:
            raise ValueError(f'{year}: dados incompletos {uf}, 13={a}, {opponent}={b}')
        results.append({'uf': uf, 'bolsonaro_pct': f'{100*b/(a+b):.8f}', 'total_valid': a+b})
    national = sum(int(x['total_valid']) for x in results)
    if national < EXPECTED_MIN:
        raise ValueError(f'{year}: total {national:,} abaixo do esperado; verificar extração')
    return results


def cache_valid(path):
    if not path.exists():
        return False
    try:
        with path.open(encoding='utf-8-sig', newline='') as fh:
            rows = list(csv.DictReader(fh))
        return len(rows) == 27 and {r['uf'] for r in rows} == UFS and sum(int(r['total_valid']) for r in rows) >= EXPECTED_MIN
    except (OSError, KeyError, ValueError):
        return False


def main():
    directory = ROOT / 'data'
    directory.mkdir(exist_ok=True)
    errors = []
    for year in (2018, 2022):
        target = directory / f'history_{year}.csv'
        if cache_valid(target):
            print(f'History {year}: cache válido, sem download', flush=True)
            continue
        success = False
        for url in SOURCES(year):
            try:
                print(f'History {year}: tentando {url}', flush=True)
                with tempfile.TemporaryDirectory() as tmpdir:
                    archive = Path(tmpdir) / 'source.zip'
                    fetch(url, archive)
                    print(f'History {year}: download {archive.stat().st_size:,} bytes', flush=True)
                    rows = rows_for_archive(archive, year)
                tmpfile = target.with_suffix('.tmp')
                with tmpfile.open('w', encoding='utf-8', newline='') as fh:
                    writer = csv.DictWriter(fh, ['uf', 'bolsonaro_pct', 'total_valid'])
                    writer.writeheader()
                    writer.writerows(rows)
                tmpfile.replace(target)
                print(f'History {year}: OK — 27 UFs; {sum(x["total_valid"] for x in rows):,} votos válidos', flush=True)
                success = True
                break
            except Exception as exc:
                msg = f'{url}: {type(exc).__name__}: {exc}'
                errors.append(msg)
                print('AVISO ' + msg, flush=True)
        if not success:
            print(f'ERRO: History {year} indisponível. Nenhum CSV parcial gerado.', flush=True)
    if errors and not all(cache_valid(directory/f'history_{y}.csv') for y in (2018, 2022)):
        raise SystemExit('Históricos incompletos: ver logs de download acima')


if __name__ == '__main__':
    main()
