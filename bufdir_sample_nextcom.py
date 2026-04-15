import pandas as pd
import numpy as np
from pathlib import Path
import pyreadstat

# === FILER ==================================================================================================


USER_PATH = Path.home()
path_local = USER_PATH.joinpath('Documents/RVU_LOKAL/')
path_sample = path_local.joinpath('Bufdir sample')
sample_file = path_sample.joinpath('Bufdir_unike lenker_m telefon og status.xlsx')

data_file = path_sample.joinpath('Bufdir – Holdninger til lhbt januar 2026_11. mars 2026.sav')

nextcom_template_file = path_local.joinpath('RVU_sample_2026/Mal_Nextcom_liste_privat_v6.csv')

# === SAMPLE ==================================================================================================

dtypes = {'mobilnummer':str, 'postnummer':str}
df = pd.read_excel(sample_file, dtype=dtypes)

removals = [
    'burzx5',
    'qxta24',
    'bep5uz',
    'nsesyr'
    ]

df = df.set_index('altid')
df = df.drop(removals)
df = df.reset_index()

# === STATUS WALR ==================================================================================================
besvart, _ = pyreadstat.read_sav(data_file, usecols=['altid'])
besvart = besvart.squeeze()
mask = df['altid'].isin(besvart)

df.loc[mask, 'status_web'] = 'Besvart'

# === NEXTCOM TEMPLAT ==================================================================================================
template = pd.read_csv(nextcom_template_file, sep=";", encoding='Windows-1252')
template.columns = ["" if str(c).startswith("Unnamed") else c for c in template.columns]


# === NEXTCOM KLARGJØRING ==================================================================================================

# dictonary {nextcom_column: sample_column}
nextcom_col_mapping = {
    'Postadresse': 'adresse', 
    'Postnr': 'postnummer', 
    'Sted': 'poststed', 
    'Mobiltelefon': 'mobilnummer', #'Mobiltelefon': 'phone', 
    'Fornavn': 'navn', 
    'Epost': 'email', 
     #'Kommune': 'kommunenavn', 
     #'Kommunenr': 'kommunenummer', 
     #'Kjønn': 'kjonn', 
    'Extra1': 'altid', 
     #'Extra2': 'aldersgruppe', 
    'Extra3': 'uniklenke', #'Extra3': 'uniksurveylink', 
     #'Extra4': 'segment', 
     #'Extra5': 'utvalgskode', 
     #'Extra18': 'varslingsstatus', 
    'Extra19': 'status_web'
     #'Extra20': 'batch', 
     #'ExtraNumeric': 'batch',
     #'ExtraDate1': 'utsendelsesdato',
    }

# Sjekker at alle keys er i template
print(template[nextcom_col_mapping.keys()])

# Bygger nextcom-data
df_nextcom = pd.DataFrame(index=df.index, columns=template.columns)
for k,v in nextcom_col_mapping.items():
    print(f'{k} = {v}')
    df_nextcom[k] = df[v]

df_nextcom


# === LAGRE TIL CSV ==================================================================================================

output_file_nextcom = path_sample.joinpath(f'NEXTCOM_{sample_file.stem}.csv')

df_nextcom.to_csv(
    output_file_nextcom, 
    index=False, 
    sep = ";", 
    encoding='Windows-1252'
)
