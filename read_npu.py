"""Last ned og les NPU-data fra Decipher API.

Laster ned surveydata i SPSS-format (.sav) fra Decipher og leser inn med pyreadstat.

Variabler:
    - q2r98, q3, b9, b10, b8, b8_region

Krever miljovariabel:
    - BEACON_KEY (64-tegns API-nokkel fra Decipher)
"""

import os
import sys
import zipfile
import io
from pathlib import Path
import pyreadstat
from decipher.beacon import api

os.environ.setdefault('BEACON_HOST', 'https://opiniongroup.decipherinc.com')

# -----------------------------
# Konfig
# -----------------------------

SURVEY = 'surveys/selfserve/4923/260109'

OUTPUT_FILE = Path.home() / 'Downloads' / 'NPU_decipherAPI.sav'


def download_npu_spss():
    """Last ned SPSS-data fra Decipher og lagre til Downloads."""
    if not SURVEY:
        raise ValueError('SURVEY er ikke satt. Oppdater SURVEY-variabelen med riktig sti.')

    print(f'Laster ned SPSS-data fra {SURVEY}...')

    data = api.get(SURVEY + '/data', format='spss16', cond='qualified')

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            sav_files = [f for f in zf.namelist() if f.endswith('.sav')]
            if not sav_files:
                raise ValueError(f'Fant ingen .sav-fil i zip-arkivet. Innhold: {zf.namelist()}')
            sav_content = zf.read(sav_files[0])
    except zipfile.BadZipFile:
        sav_content = data

    with open(OUTPUT_FILE, 'wb') as f:
        f.write(sav_content)
    print(f'OK: Lagret til {OUTPUT_FILE}')

    return OUTPUT_FILE


def read_npu():
    """Last ned og les NPU-data. Returnerer DataFrame med utvalgte variabler."""
    sav_file = download_npu_spss()

    df, meta = pyreadstat.read_sav(str(sav_file))

    vlabels = meta.variable_value_labels
    clabels = meta.column_names_to_labels

    print(f'OK: Lest {len(df)} rader, {len(df.columns)} kolonner')
    print(f'Kolonner: {list(df.columns)}')

    return df, vlabels, clabels


if __name__ == '__main__':
    try:
        df, vlabels, clabels = read_npu()
        print(df.head())
    except Exception as e:
        print(f'FEIL: {e}')
        sys.exit(1)
