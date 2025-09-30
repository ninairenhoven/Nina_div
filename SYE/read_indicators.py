import pandas as pd
from pathlib import Path
import re
from write_dfs_to_excel import write_dfs_to_excel

user_path = Path.home()
sye_path = user_path.joinpath(r"Opinion AS\Opinion SharePoint - 07_Oppdrag 5_Mål- og resultatstyring_Utvikling av beregningsmodeller")
path = sye_path.joinpath(r"04 Data og beregninger\indikatorer")





# ===========================================================
# INPUT FILER
# ===========================================================

#files = list(path.glob(""))
#filenames = [f.name for f in files]

filer_internkontroll_LM = list(path.glob("Legemiddelinternkontroll*.xlsx"))
filer_internkontroll_LM = [f.name for f in filer_internkontroll_LM]

filenames = {
    'antall_plasser':'Antall plasser på institusjon.xlsx',
    "ernaring": "Ernæringsmessig risiko og ernæringsplan 2024 2025.csv",
    "vaksinerte": "Andel vaksinerte medarbeidere.xlsx",
    "infeksjoner": "Infeksjoner.xlsx",
    "LMG": "Andel gjennomførte legemiddelgjennomganger 2024 2025.csv",
    "legemidler_8": "Andel pasienter med 8 eller flere legemidler over tid.xlsx",
    "antibiotika": "Gunstig antibiotika.xlsx",
    "ADL": "IPLOS-1.kvartal-2025.xlsx",
    "responstid": "responstid.xlsx",
    "oppstartsamtale": "Tilbud oppstartsamtale.xlsx",
    "UH": "Antall Uønskede hendelser.xlsx",
    "forbedring": "antall forbedringsforslag.xlsx",
    "raabra": "Råbra.csv"
}

files = {k:path.joinpath(v) for k, v in filenames.items()}









# RENAME
rename1 = {x : 'Institusjon' for x in [
    'Administrasjonsenhet', 
    'Institusjonsnavn i dag', 
    'Administrasjonsenhet i dag']
    }

def date_string_to_period(s: pd.Series, format='%Y%m', freq='M'):
    date_dt = pd.to_datetime(s, format=format)
    return date_dt.dt.to_period(freq)


def pct_str_to_float(s):
    s_clean = s.str.replace('%','').str.strip().str.replace(',','.')
    return s_clean.astype(float)/100


def keep_text_in_brackets(cols):
    pattern = r"\[([^\]]+)\]"
    cleaned_cols = cols.str.extract(pattern, expand=True)[0]
    if cleaned_cols.duplicated().any():
        print('Tekst i brackets gir dupliserte navn. Beholder original')
        return cols
    else:
        return cleaned_cols


def indicator_report(df):
    if isinstance(df.columns, pd.PeriodIndex):
        deltas = df.columns.to_timestamp().diff()
        deltas = deltas[1:]
        delta_months = (deltas.days/30.4).round().astype('Int64')
        x = pd.Series(delta_months).describe()
        frekvens = f'{x["mean"]:.1f} mnd'
        frekvens_min = f'{x["min"]} mnd'
        frekvens_maks = f'{x["max"]} mnd'
    else:
        frekvens = ''
        frekvens_min = ''
        frekvens_maks = ''
    stats = df.astype('float').stack().describe(percentiles=[0.05,0.95]).round(3)
    return {
        'Frekvens': frekvens,
        'Frekvens min': frekvens_min,
        'Frekvens maks': frekvens_maks,
        'Første':str(df.columns.min()),
        'Siste':str(df.columns.max()),
        'Antall perioder':df.columns.size,
        'Antall Institusjoner':df.index.size,
        'Rapporteringsgrad':round((df.notna().mean().mean()),2),
        'Gjennomsnitt': stats['mean'],
        'Min': stats['min'],
        'p05': stats['5%'],
        'Median': stats['50%'],
        'p95': stats['95%'],
        'Max': stats['max']
    }


mnd_nr = {'Januar': 1, 'Februar': 2, 'Mars': 3, 'April': 4, 
    'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
    'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12}

raw_data = {}
data = {}
qdata = {}

for key, p in files.items():
    print(p.name)
    if p.suffix == '.xlsx':
        df = pd.read_excel(p)
    else:
        df = pd.read_csv(p, sep=";")
    raw_data[key] = df

excel_collected = path.joinpath('Indikatorer samlet.xlsx')
write_dfs_to_excel(raw_data, excel_collected)
    

# ===========================================================
# Antall plasser på institusjon
# ===========================================================
df = pd.read_excel(files['antall_plasser'])
df = df.rename(columns=rename1)
df = df.set_index('Institusjon')
df = df.loc[~df.index.isna()]
df = df.drop('Total')

data['antall_plasser'] = df.copy()
antall_plasser = df['Antall døgnplasser'].copy()
institusjoner = antall_plasser.index

# ===========================================================
# ERNÆRING
# Rapporteres per måned
# ===========================================================
df = pd.read_csv(files['ernaring'], sep=";")
df = df.rename(columns = rename1)

df['month'] = date_string_to_period(df['Periode'])
df['quarter']= date_string_to_period(df['Periode'], freq='Q')

df['ERNRIS'] = pct_str_to_float(df['F_Vurdert_for_ernæringsmessig risiko'])
df['ERNPLAN'] = pct_str_to_float(df['F_Andel_ernæringsmessig risiko med plan'])

#df = df.set_index(['Institusjon','month'])

ernris = df.set_index(['Institusjon','month'])['ERNRIS'].unstack()
ernplan = df.set_index(['Institusjon','month'])['ERNPLAN'].unstack()

ernris_q = df.groupby(['Institusjon','quarter'])['ERNRIS'].mean().unstack()
ernplan_q = df.groupby(['Institusjon','quarter'])['ERNPLAN'].mean().unstack()


data['ERNRIS'] = ernris
data['ERNPLAN'] = ernplan

qdata['ERNRIS'] = ernris_q
qdata['ERNPLAN'] = ernplan_q


 
#df.groupby(['Institusjon','quarter'])[['ERNRIS','ERPLAN']].mean()

# ===========================================================
# VAKSINERTE
# Rapporteres per vintersesong, angitt som 2022/2023
# Rapporterte tall skal gjelde fra Q4 t.o.m Q3
# ===========================================================

df = pd.read_excel(files['vaksinerte'], index_col=0)
df = df.drop('Institusjon').dropna(how='all')
df.index.name = 'Institusjon'

#y = df.columns.str.split("/").str[0]
#y = date_string_to_period(pd.Series(y), format="%Y", freq='Y')
#df.columns = y

season2quarters = {
    '2022/2023': ['2022Q4','2023Q1','2023Q2','2023Q3'],
    '2023/2024': ['2023Q4','2024Q1','2024Q2','2024Q3'],
    '2024/2025': ['2024Q4','2025Q1','2025Q2','2025Q3']
}

dfq = pd.DataFrame(index=df.index)
for s, qs in season2quarters.items():
    for q in qs:
        dfq[q] = df[s]

dfq.columns =  pd.PeriodIndex(dfq.columns, freq='Q')
dfq = dfq.loc[:,dfq.columns>='2024']

data['vaksinerte'] = df.copy()
qdata['vaksinerte'] = dfq.copy()


# ===========================================================
# Andel helsetjenesteassosierte infeksjoner
# ===========================================================
df = pd.read_excel(files['infeksjoner'], index_col=[0,1])
df = df.dropna(how='all')
df = df.reset_index()

df  = df.rename(columns=rename1)

# Fjern total per institusjon (viser gjennomsnitt over tid)
df = df.loc[df['År - halvår']!='Total']
df = df.loc[df['Institusjon']!='Total']

y = df['År - halvår'].str.extract(r'^(\d{4})-')[0].astype(float)
half = df['År - halvår'].str.extract(r'-(\d)\. halvår')[0].astype(float)
# Sluttmåned: 1 -> jun, 2 -> des
mnth = half * 6

df['period'] = pd.to_datetime({'year': y, 'month': mnth, 'day': 1}).dt.to_period('M')
df = df.set_index(['Institusjon','period']).sort_index()

df = df['Prevalens av infeksjoner'].unstack(level='period')
data['infeksjoner'] = df.copy()


# Prevalens av infeksjoner er riktig kolonne.
# Hvordan mappe til kvartal? Rapporteres på slutten av halvår?
# Manuelt rapportert - manglende rapportering må telle negativt

# ===========================================================
# Legemiddelgjennomgang
# ===========================================================
df = pd.read_csv(files['LMG'], sep=";")
df = df.rename(columns = rename1)
df['month'] = date_string_to_period(df['Periode'])
df['quarter'] = date_string_to_period(df['Periode'], freq='Q')
df['LMG'] = pct_str_to_float(df['F_Legemiddelgjennomgang'])

dfq = df.groupby(['Institusjon','quarter'])['LMG'].mean().unstack()
dfm = df.set_index(['Institusjon','month'])['LMG'].unstack()

data['LMG'] = dfm.copy()
qdata['LMG'] = dfq.copy()

# ===========================================================
# Andel pasienter med minst 8 faste medikamenter
# ===========================================================

df = pd.read_excel(files['legemidler_8'])
df.columns = keep_text_in_brackets(df.columns)
df = df.rename(columns=rename1)
df = df.rename(columns={'F_AndelPasienterMedMerEnn8Faste':'Andel'})

df['month'] = date_string_to_period(df['DateID'], format='%Y%m%d')
df['quarter'] = date_string_to_period(df['DateID'], format='%Y%m%d', freq='Q')

mask = df['month']>='2024'
df = df.loc[mask]

dfq = df.groupby(['Institusjon','quarter'])['Andel'].mean().unstack()
dfm = df.set_index(['Institusjon','month'])['Andel'].unstack()

data['legemidler_8'] = dfm.copy()
qdata['legemidler_8'] = dfq.copy()


# ===========================================================
# Internkontroll legemidler
# ===========================================================

filer_IKLM = list(path.glob("Legemiddelinternkontroll*.xlsx"))
filer_IKLM = [path.joinpath(f) for f in filer_IKLM]

s = pd.Series([str(p) for p in filer_IKLM])

# Regex som fanger to datoer dd.mm.yyyy med " til " imellom
pattern = r'\d{2}\.(\d{2}\.\d{4})\s+til\s+\d{2}\.(\d{2}\.\d{4})'

# Ekstraher til to kolonner: 'fra' og 'til'
datoer = s.str.extract(pattern)
datoer.columns = ['fra', 'til']
#perioder = datoer.apply(lambda r: '-'.join(r),axis=1)
perioder = date_string_to_period(datoer['til'], format='%m.%Y')

df= pd.DataFrame()

for fil, periode in zip(filer_IKLM, perioder):
    temp = pd.read_excel(fil, index_col=[0], header=1)
    temp = temp.dropna(how='all', axis=1)
    temp.columns = [periode]
    df = pd.concat([df,temp], axis=1)#, axis=1)

df = df.sort_index(axis=1)

slaa_sammen = [
    'Bjølsenhjemmet',
    'Ellingsrudhjemmet',
    'Langerudhjemmet',
    'Lillohjemmet',
    'Madserudhjemmet',
    'Majorstuhjemmet',
    'Midtåsenhjemmet',
    'Nordseterhjemmet',
    'Oppsalhjemmet',
    'Stovnerskoghjemmet',
    'Ullernhjemmet',
    'Uranienborghjemmet',
    'Vinderenhjemmet',
    'Økernhjemmet',
    'Furuset Hageby',
    'Ilahjemmet',
    'Kantarellenhjemmet',
    'Lambertseterhjemmet'
    ]

df['Institusjon'] = ""
for inst in slaa_sammen:
    mask =  df.index.str.contains(inst)
    df.loc[mask,'Institusjon'] = inst
    

df2 = df.groupby('Institusjon').sum(numeric_only=True)

data['IKLM'] = df2.copy()

# ===========================================================
# Gunstig antibiotika
# ===========================================================
df = pd.read_excel(files['antibiotika'], index_col=0)
df = df.dropna(how='all').drop('Total')
df = df.reset_index()
df = df.rename(columns=rename1)

df['month'] = date_string_to_period(df['Periode'])
df['quarter'] = date_string_to_period(df['Periode'],freq='Q')

mask = df['month']>='2024'
df = df.loc[mask]

dfq = df.groupby(['Institusjon','quarter'])['F_AndelAvBrukereMedGunstig'].mean().unstack()
dfm = df.set_index(['Institusjon','month'])['F_AndelAvBrukereMedGunstig'].unstack()

data['antibiotika'] = dfm.copy()
qdata['antibiotika'] = dfq.copy()

# ===========================================================
# Responstid
# ===========================================================
df = pd.read_excel(files['responstid'], index_col=[0,1])
df = df.dropna(how='all')
df = df.reset_index()

df = df.rename(columns=rename1)
df.columns = df.columns.str.replace('Andel alarmer akseptert ','')

df = df.loc[df['Periode']!='Total']
df = df.loc[df['Institusjon']!='Total']

sumcols =['mellom 2 sek og 5 minutter','mellom 5 og 10 min']
df['Andel_10min'] = df[sumcols].sum(axis=1)

df['month'] = date_string_to_period(df['Periode'])
df['quarter'] = date_string_to_period(df['Periode'],freq='Q')

dfq = df.groupby(['Institusjon','quarter'])['Andel_10min'].mean().unstack()
dfm = df.set_index(['Institusjon','month'])['Andel_10min'].unstack()

data['responstid'] = dfm.copy()
qdata['responstid'] = dfq.copy()


# ===========================================================
# EQS
# 'Antall Uønskede hendelser.xlsx'
# 'antall forbedringsforslag.xlsx'
# 'Råbra.csv'

# ===========================================================

# UØNSKEDE HENDELSER
df = pd.read_excel(files['UH'])
df = df.dropna(subset=['Institusjon','Year_Month'])

df['antall_plasser'] = df['Institusjon'].map(antall_plasser)
df['UHPP'] = df['Antall uønskede hendelser']/df['antall_plasser']

y = df['Year_Month'].str.split('-').str[0]
mnth = df['Year_Month'].str.split('-').str[1].map(mnd_nr)
yyyymm = y + mnth.astype(str).str.zfill(2)
df['month'] = date_string_to_period(yyyymm)
df['quarter'] = date_string_to_period(yyyymm, freq='Q')

dfq = df.groupby(['Institusjon','quarter'])['UHPP'].mean().unstack()
dfm = df.set_index(['Institusjon','month'])['UHPP'].unstack()

data['UHPP'] = dfm.copy()
qdata['UHPP'] = dfq.copy()



# FORBEDRINGSFORSLAG + RÅBRA
forb = pd.read_excel(files['forbedring'])
raabra = pd.read_csv(files['raabra'], sep=";")

forb = forb.dropna(subset=['Institusjon','Periode'])
raabra = raabra.dropna(subset=['Institusjon','Periode'])

forb['month'] = date_string_to_period(forb['Periode'].astype(int).astype(str))
raabra['month'] = date_string_to_period(raabra['Periode'].astype(str))

forb = forb.rename(columns={'Antall ID_Melding':'Forbedring'})
raabra = raabra.rename(columns={'Antall ID_Melding':'Råbra'})

forb = forb.set_index(['Institusjon','month'])['Forbedring']
raabra = raabra.set_index(['Institusjon','month'])['Råbra']

df = pd.concat([forb,raabra], axis=1).sort_index().reset_index()

mask = df['month']>='2024'
df = df.loc[mask]
df = df.loc[df['Institusjon']!='Sykehjemsetaten administrasjon']

df['total'] = df[['Forbedring','Råbra']].sum(axis=1)
df['antall_plasser'] = df['Institusjon'].map(antall_plasser)
df['EQS_PP'] = df['total']/df['antall_plasser']

df['quarter'] = df['month'].astype('period[Q]')

dfq = df.groupby(['Institusjon','quarter'])['EQS_PP'].mean().unstack()
dfm = df.set_index(['Institusjon','month'])['EQS_PP'].unstack()

data['EQS'] = dfq.copy()
qdata['EQS'] = dfm.copy()



# ===========================================================
# Oppstartssamtale
# Tilbud oppstartsamtale.xlsx'
# ===========================================================



df0 = pd.read_excel(files['oppstartsamtale'])
df = df0.copy()

# Behold tekst inne i []
df.columns = keep_text_in_brackets(df.columns)

df = df.dropna(subset='Institusjon')
df = df.loc[df['Institusjon']!= 'Etatsnivå']

yq = df['Year_Quarter'].str.extract(r"(\d{4})-(\d)\. kvartal")
yq = yq.astype(int)
df['quarter'] = pd.PeriodIndex.from_fields(year=yq[0], quarter=yq[1], freq="Q")

dfq = df.set_index(['Institusjon','quarter'])['F_TilbudOppstartsamtale_Gjennomsnitt']
dfq = dfq.unstack()

data['oppstartsamtale'] = dfq.copy()
qdata['oppstartsamtale'] = dfq.copy()



# ===========================================================
# ADL
# IPLOS-1.kvartal-2025.xlsx
# ===========================================================
df = pd.read_excel(files['ADL'], header=3, index_col=0, usecols='A:Q')
h0 = pd.read_excel(files['ADL'], header=1, index_col=0, usecols='A:Q', nrows=2)

temp = pd.DataFrame(np.reshape(h0.iloc[0],(4,4)))[[1,2]]

months = pd.PeriodIndex.from_fields(
    year = temp[2],
    month = temp[1].map(mnd_nr),
    freq = "M"
)

cols0 = months.repeat(4)
df.columns = pd.MultiIndex.from_arrays([cols0, h0.iloc[1]])

df1 = df.xs('3 mnd 1',level=1, axis=1)

df1 = df1.loc[~df1.index.isna()]
df1 = df1.loc[~df1.index.str.startswith('TOTALT')]
df1 = df1.loc[~df1.index.str.startswith('Område')]
df1 = df1.drop('Utenbys')
df1 = df1.dropna(how='all')

data['ADL'] = df1.copy()

# ========================================================
"""
data24 = {}

for key, df in data.items():
    if key not in ["antall_plasser",'summaries']:
        keepcols = df.columns>='2024'
        df_keep = df.loc[:,keepcols].copy()
        df_keep = df_keep.dropna(how='all')
        data24[key] = df_keep
"""



# ========================================================
#counts = pd.DataFrame()
#f#irst = pd.DataFrame()
inst_summaries = pd.DataFrame(index=antall_plasser.index)

for key, df in qdata.items():
    if key not in ["antall_plasser",'summaries', 'indicator_summary']:
        m = df.notna()
        counts = m.sum(axis=1)
        rapporteringsgrad = (counts/df.columns.size).round(2)
        first = m.idxmax(axis=1)
        last = m.iloc[:, ::-1].idxmax(axis=1)
        temp = pd.concat([counts,rapporteringsgrad,first,last], axis=1)
        temp.columns = pd.MultiIndex.from_product([[key],['Antall perioder','Andel perioder','Første','Siste']])
        inst_summaries = pd.concat([inst_summaries,temp], axis=1)

inst_summaries.columns = pd.MultiIndex.from_tuples(inst_summaries.columns)

indicator_summaries = pd.DataFrame(columns=indicator_report(pd.DataFrame()))
for key, df in qdata.items():
    if key not in ["antall_plasser",'summaries', 'indicator_summary']:
        indicator_summaries.loc[key] = indicator_report(df)

summaries = {
    'Antall plasser':antall_plasser.to_frame(),
    'Indicator summary':indicator_summaries,
    'Institusjon summary':inst_summaries
}

# ========================================================
output_excel = path.joinpath('INDIKATORER TIDSSERIER Kvartaler fra 2024.xlsx')
write_dfs_to_excel(summaries|qdata, output_excel, auto_width=True)

import numpy as np
