import pandas as pd
import numpy as np
from pathlib import Path
import re
from write_dfs_to_excel import write_dfs_to_excel

user_path = Path.home()
sye_path = user_path.joinpath(r"Opinion AS\Opinion SharePoint - 07_Oppdrag 5_Mål- og resultatstyring_Utvikling av beregningsmodeller")

path = sye_path.joinpath(r"04 Data og beregninger")
path_input = path.joinpath(r"Data fra SYE")

path_input = path_input.parent.joinpath("Sykehjemsetaten kvalitetsindeks MOTTATT 2026-03-12")


# ===========================================================
# INPUT FILER
# ===========================================================

#files = list(path.glob(""))
#filenames = [f.name for f in files]

filenames = {
    'ANTPL':'Antall plasser på institusjon.xlsx',
    'ANTBB':'Antall beboere siste dag i måneden 2024 2025.csv',
    "ernaring": "Ernæringsmessig risiko og ernæringsplan 2024 2025.csv",
    "VAKS": "Andel vaksinerte medarbeidere.xlsx",
    "INFK": "Infeksjoner.xlsx",
    "LMG": "Andel gjennomførte legemiddelgjennomganger 2024 2025.csv",
    #"legemidler_8": "Andel pasienter med 8 eller flere legemidler over tid.xlsx",
    "LM10": "Andel pasienter med 10 eller flere legemidler over tid.xlsx",
    "GABI": "Gunstig antibiotika.xlsx",
    "ADL": "IPLOS-1.kvartal-2025.xlsx",
    "RESP": "responstid.xlsx",
    "OPPSAMT": "Tilbud oppstartsamtale.xlsx",
    "UH": "Antall Uønskede hendelser.xlsx",
    "forbedring": "antall forbedringsforslag.xlsx",
    "raabra": "Råbra.csv",
    "raabra2025": "Råbra 2025 edit.xlsx"
}

filenames['VAKS'] = 'Andel vaksinerte medarbeidere 2022-2026.xlsx'
filenames['LMG'] = 'Andel gjennomførte legemiddelgjennomganger 2024 2026.csv'
filenames['ADL'] = 'IPLOS-4.kvartal-2025 EDIT.xlsx'

files = {k:path_input.joinpath(v) for k, v in filenames.items()}

files_IKLM = list(path_input.glob("Legemiddelinternkontroll*.xlsx"))
filenames_IKLM = [f.name for f in files_IKLM]


# RENAME
rename1 = {x : 'Institusjon' for x in [
    'Administrasjonsenhet', 'Institusjonsnavn i dag', 'Administrasjonsenhet i dag']
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


def month2quarters(input_months, n_quarters, extend=False):
    intervals = pd.Index(input_months).to_timestamp().diff()
    q_intervals = (intervals.dropna().days*(4/365)).round().astype(int)
    print(f'Intervaller: {q_intervals.min()}-{q_intervals.max()} kvartaler')
    if extend:
        # Generate enough quarters to fill all gaps
        n_use = q_intervals.max()
    else:
        n_use = n_quarters
    # Generate quarters for each reported month
    x = pd.Series(input_months.sort_values()).to_frame('months')
    x[0] = input_months.astype('period[Q]')    
    for i in range(1, n_use):
        x[i] = x[0] + i
    x = x.set_index('months')
    # Remove duplicate quarters and convert to list
    x = x.stack().drop_duplicates(keep='last').unstack()
    x = x.apply(lambda r: r.dropna().to_list(), axis=1)
    # Remove extended quarters for last row
    x.iloc[-1] = x.iloc[-1][0:n_quarters]
    return (x)


def indicator_frequency(df):
    d = {'Antall perioder': df.columns.size}
    if isinstance(df.columns, pd.PeriodIndex):
        period_type = df.columns.freqstr
        deltas = df.columns.to_timestamp().diff()
        deltas = deltas[1:]
        delta_months = (deltas.days/30.4).round().astype('Int64')
        freq = pd.Series(delta_months).describe()
        d['Periode'] = period_type 
        d['Frekvens'] = f'{freq["mean"]:.1f} mnd'
        d['Frekvens min'] = f'{freq["min"]:.0f} mnd'
        d['Frekvens maks'] =f'{freq["max"]:.0f} mnd'
    return d


month_name_to_nr = {'Januar': 1, 'Februar': 2, 'Mars': 3, 'April': 4, 
    'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
    'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12}

raw_data = {}
all_data = {}
time_data = {}
qdata = {}

"""
for key, p in files.items():
    print(p.name)
    if p.suffix == '.xlsx':
        df = pd.read_excel(p)
    else:
        df = pd.read_csv(p, sep=";")
    raw_data[key] = df
    """

excel_collected = path.joinpath('Indikatorer samlet.xlsx')
#write_dfs_to_excel(raw_data, excel_collected)
    

# ===========================================================
# Antall plasser på institusjon
# ===========================================================
df = pd.read_excel(files['ANTPL'])
df = df.rename(columns=rename1)
df = df.set_index('Institusjon')
df = df.loc[~df.index.isna()]
df = df.drop('Total')

antall_plasser = df['Antall døgnplasser'].copy()
institusjoner = antall_plasser.sort_index().index

# Driftsform og områder
 
institusjon_til_omrade = {
    "Ellingsrudhjemmet": 1,
    "Langerudhjemmet": 1,
    "Lillohjemmet": 1,
    "Lindeberghjemmet": 1,
    "Madserudhjemmet": 1,
    "Midtåsenhjemmet": 1,
    "Nordseterhjemmet": 1,
    "Stovnerskoghjemmet": 1,
    "Ullernhjemmet": 1,
    "Vinderenhjemmet": 1,
    "Økernhjemmet": 1,
    "Dronning Ingrids hage": 2,
    "Furuset hageby": 2,
    "Lambertseterhjemmet": 2,
    "Majorstuhjemmet": 2,
    "Tåsenhjemmet": 2,
}

df['Område'] = df.index.map(institusjon_til_omrade)
df['gruppert'] = df['Driftsform']
df.loc[df['Driftsform']=='Kommunal','gruppert'] = df['Område'].apply(lambda x: f'Kommunal {x:0.0f}') 


driftsform = df['Driftsform'].copy()
kommunale = driftsform[driftsform=='Kommunal'].index
ikke_kommunale = driftsform[driftsform!='Kommunal'].index

driftsform_inst = df.reset_index().groupby('Driftsform')['Institusjon'].apply(list)



# ===========================================================
# Antall beboere på institusjon per måned
# ===========================================================

antall_beboere = pd.read_csv(files['ANTBB'], sep=';')
antall_beboere = antall_beboere.rename(columns=rename1)
antall_beboere['month'] = date_string_to_period(antall_beboere['Periode'])
antall_beboere = antall_beboere.set_index(['Institusjon','month'])['Sum på Nevner_Belegg_UnikeBrukere'].unstack()


# ===========================================================
# ERNÆRING
# Rapporteres per måned
# ===========================================================
df = pd.read_csv(files['ernaring'], sep=";")
df = df.rename(columns = rename1)

df['Institusjon'].isin(institusjoner)


df['month'] = date_string_to_period(df['Periode'])
df['quarter']= date_string_to_period(df['Periode'], freq='Q')

df['ERNRIS'] = pct_str_to_float(df['F_Vurdert_for_ernæringsmessig risiko'])
df['ERNPLAN'] = pct_str_to_float(df['F_Andel_ernæringsmessig risiko med plan'])

#df = df.set_index(['Institusjon','month'])

ernris = df.set_index(['Institusjon','month'])['ERNRIS'].unstack()
ernplan = df.set_index(['Institusjon','month'])['ERNPLAN'].unstack()

ernris_q = df.groupby(['Institusjon','quarter'])['ERNRIS'].mean().unstack()
ernplan_q = df.groupby(['Institusjon','quarter'])['ERNPLAN'].mean().unstack()

all_data['ernering'] = df.copy()

ernris = ernris.reindex(index=institusjoner)
ernplan = ernplan.reindex(index=institusjoner)
ernris_q = ernris_q.reindex(index=institusjoner)
ernplan_q = ernplan_q.reindex(index=institusjoner)

time_data['ERNRIS'] = ernris
time_data['ERNPLAN'] = ernplan

qdata['ERNRIS'] = ernris_q
qdata['ERNPLAN'] = ernplan_q


 
#df.groupby(['Institusjon','quarter'])[['ERNRIS','ERPLAN']].mean()

# ===========================================================
# VAKSINERTE
# Rapporteres per vintersesong, angitt som 2022/2023
# Rapporterte tall skal gjelde fra Q4 t.o.m Q3
# ===========================================================

df = pd.read_excel(files['VAKS'], index_col=0)
df = df.drop('Institusjon').dropna(how='all')
df.index.name = 'Institusjon'
df = df.reindex(index=institusjoner)

y = df.columns.str.split("/").str[1]
y = date_string_to_period(pd.Series(y), format="%Y", freq='Y')
df.columns = y
df = df.astype(float)

y2quarters = {
    '2023': ['2023Q1','2023Q2','2023Q3','2023Q4'],
    '2024': ['2024Q1','2024Q2','2024Q3','2024Q4'],
    '2025': ['2025Q1','2025Q2','2025Q3','2025Q4']
}

dfq = pd.DataFrame(index=df.index)
for s, qs in y2quarters.items():
    for q in qs:
        dfq[q] = df[s]

dfq.columns =  pd.PeriodIndex(dfq.columns, freq='Q')
dfq = dfq.loc[:,dfq.columns>='2024']


all_data['VAKS'] = df.copy()
time_data['VAKS'] = df.copy()
qdata['VAKS'] = dfq.copy()


# ===========================================================
# INFEKSJONER
#
# Andel helsetjenesteassosierte infeksjoner
# Har/har ikke rapportert
# ===========================================================
df = pd.read_excel(files['INFK'], index_col=[0,1])
df = df.dropna(how='all')
df = df.reset_index()

df  = df.rename(columns=rename1)

# Fjern total per institusjon (viser gjennomsnitt over tid)
df = df.loc[df['År - halvår']!='Total']
df = df.loc[df['Institusjon']!='Total']

yh = df['År - halvår'].str.extract(r'^(\d{4})-(\d)\. halvår').astype(float)
# Sluttmåned: 1 -> jun, 2 -> des
mnth = yh[1] * 6

df['period'] = pd.to_datetime({'year': yh[0], 'month': mnth, 'day': 1}).dt.to_period('M')
df = df.set_index(['period','Institusjon'])

# Har/har ikke rapportert
df1 = df['Prevalens av infeksjoner'].unstack(level='period').notna().astype(int)

# Utvider fra halvårlig rapportering til kvartaler
quarters = month2quarters(df1.columns, 2, extend=True)

dfq = pd.DataFrame(index=df1.index)
for col, qs in quarters.items():
    for q in qs:
        dfq[q] = (df1[col])

dfq = dfq.loc[:,dfq.columns>='2024']

df1 = df1.reindex(index=institusjoner)
dfq = dfq.reindex(index=institusjoner)


all_data['INFK'] = df.copy
time_data['INFK'] = df1.copy()
qdata['INFK'] = dfq.copy()

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

dfm = dfm.reindex(index=institusjoner)
dfq = dfq.reindex(index=institusjoner)

all_data['LMG'] = df.copy()
time_data['LMG'] = dfm.copy()
qdata['LMG'] = dfq.copy()


# ===========================================================
# Andel pasienter med minst 10 faste medikamenter
# ===========================================================


df = pd.read_excel(files['LM10'])
#df.columns = keep_text_in_brackets(df.columns)
#df = df.rename(columns=rename1)
#df = df.rename(columns={'F_AndelPasienterMedMerEnn8Faste':'Andel'})
df = df.rename(columns={'F_AndelPasienterMed10EllerMerFaste':'Andel'})
df = df.dropna(subset=['Dato','Institusjon'])
#df = df.loc[df['Dato']!='Total']

df['month'] = date_string_to_period(df['Dato'], format='%Y%m%d')
df['quarter'] = date_string_to_period(df['Dato'], format='%Y%m%d', freq='Q')

mask = df['month']>='2024'
df = df.loc[mask]

dfq = df.groupby(['Institusjon','quarter'])['Andel'].mean().unstack()
dfm = df.set_index(['Institusjon','month'])['Andel'].unstack()


dfm = dfm.reindex(index=institusjoner)
dfq = dfq.reindex(index=institusjoner)


all_data['LM10'] = df.copy()
time_data['LM10'] = dfm.copy()
qdata['LM10'] = dfq.copy()


# ===========================================================
# Internkontroll legemidler
# ===========================================================

filer_IKLM = list(path_input.glob("Legemiddelinternkontroll*.xlsx"))
#filer_IKLM = [path.joinpath(f) for f in filer_IKLM]

filer_s = pd.Series([str(p) for p in filer_IKLM])

filer_df = pd.DataFrame({
    'filename': [p.name for p in filer_IKLM],
    'path':filer_IKLM
    })

# Regex som fanger to datoer dd.mm.yyyy med " til " imellom
pattern = r'\d{2}\.(\d{2}\.\d{4})\s+til\s+\d{2}\.(\d{2}\.\d{4})'

dato_filer = filer_df['filename'].str.extract(pattern)
filer_df = pd.concat([filer_df,dato_filer], axis=1)
filer_df['tildato'] = date_string_to_period(filer_df[1], format='%m.%Y')
filer_df = filer_df.sort_values(by='tildato')

readfiles = filer_df.set_index('tildato')['path'].squeeze().to_dict()

df= pd.DataFrame()
for date, p in readfiles.items():
    temp = pd.read_excel(p, index_col=[0], header=1)
    temp = temp.dropna(how='all', axis=1)
    temp.columns = [date]
    df = pd.concat([df,temp], axis=1)#, axis=1)

df = df.sort_index(axis=1)


df['Institusjon'] = ""
for inst in institusjoner:
    mask =  df.index.str.lower().str.contains(inst.lower())
    df.loc[mask,'Institusjon'] = inst


df1 = df.groupby('Institusjon').sum(numeric_only=True)
df1.columns =  pd.PeriodIndex(df1.columns, freq='M')

# IK rapportert i mai 2024 gjelder for indeksberegning i Q2+Q3 2024
quarters = month2quarters(filer_df['tildato'],2)

# Har/har ikke gjennomført IK ved forrige rapportering
dfq = pd.DataFrame(index=df1.index)
for col, qs in quarters.items():
    for q in qs:
        dfq[q] = (df1[col]>0).astype(int)

dfq = dfq.loc[:,dfq.columns>='2024']
dfq = dfq.reindex(index=institusjoner)

# Kun gyldig for kommunale sykehjem, de øvrige skal forbli NaN
dfq.loc[kommunale] = dfq.loc[kommunale].fillna(0)
dfq.loc[ikke_kommunale] = np.nan

all_data['IKLM'] = df.copy()
time_data['IKLM'] = df1.copy()
qdata['IKLM'] = dfq.copy()




# ===========================================================
# Gunstig antibiotika
# ===========================================================
df = pd.read_excel(files['GABI'], index_col=0)
df = df.dropna(how='all')
#df = df.drop('Total')
df = df.reset_index()
df = df.rename(columns=rename1)

df['month'] = date_string_to_period(df['Periode'])
df['quarter'] = date_string_to_period(df['Periode'],freq='Q')

mask = df['month']>='2024'
df = df.loc[mask]

dfq = df.groupby(['Institusjon','quarter'])['F_AndelAvBrukereMedGunstig'].mean().unstack()
dfm = df.set_index(['Institusjon','month'])['F_AndelAvBrukereMedGunstig'].unstack()


dfm = dfm.reindex(index=institusjoner)
dfq = dfq.reindex(index=institusjoner)

all_data['GABI']= df.copy()
time_data['GABI'] = dfm.copy()
qdata['GABI'] = dfq.copy()

# ===========================================================
# Responstid
# ===========================================================
df = pd.read_excel(files['RESP'], index_col=[0,1])
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



dfm = dfm.reindex(index=institusjoner)
dfq = dfq.reindex(index=institusjoner)

all_data['RESP'] = df.copy()
time_data['RESP'] = dfm.copy()
qdata['RESP'] = dfq.copy()


# ===========================================================
# EQS: UØNSKEDE HENDELSER
# 'Antall Uønskede hendelser.xlsx'
# ===========================================================


df = pd.read_excel(files['UH'])
df = df.dropna(subset=['Institusjon','Year_Month'])
df = df.loc[df['Institusjon']!='Sykehjemsetaten administrasjon']
df = df.loc[~df['Institusjon'].str.lower().str.contains('helsehus')]

df['antall_plasser'] = df['Institusjon'].map(antall_plasser)
df['UHPP'] = df['Antall uønskede hendelser']/df['antall_plasser']

ym = df['Year_Month'].str.split('-',expand=True)
yyyymm = ym[0] + ym[1].map(month_name_to_nr).astype(str).str.zfill(2)
df['month'] = date_string_to_period(yyyymm)
df['quarter'] = date_string_to_period(yyyymm, freq='Q')

# Antall UH per hhv kvartal og måned
antall_q = df.groupby(['Institusjon','quarter'])['Antall uønskede hendelser'].sum().unstack().fillna(0)
antall_m = df.set_index(['Institusjon','month'])['Antall uønskede hendelser'].unstack().fillna(0)

temp_plasser = antall_plasser[antall_plasser.index.isin(df['Institusjon'])]

# Antall UH per plass per måned, beregnet for hhv kvartal og måned
dfq = (1/3)*antall_q.div(temp_plasser, axis=0)
dfm = antall_m.div(temp_plasser, axis=0)

dfq = (100*dfq).round(2)
dfm = (100*dfm).round(2)

dfm = dfm.reindex(index=institusjoner)
dfq = dfq.reindex(index=institusjoner)

# Kommersielle skal ikke vurderes på dette # f.o.m Q2 2025
#kommersielle = driftsform_inst['Kommersiell']
#dfm.loc[kommersielle, dfm.columns>='2025Q2'] = np.nan
#dfq.loc[kommersielle, dfq.columns>='2025Q2'] = np.nan
dfm.loc[ikke_kommunale] = np.nan
dfq.loc[ikke_kommunale] = np.nan

all_data['UHPP'] = df.copy()
time_data['UHPP'] = dfm.copy()
qdata['UHPP'] = dfq.copy()


# ===========================================================
# EQS: FORBEDRINGSFORSLAG + RÅBRA
# 'antall forbedringsforslag.xlsx'
# 'Råbra.csv'
# ===========================================================
#files2 = {k: path0.joinpath(f) for k,f in filenames.items()}

forb = pd.read_excel(files['forbedring'])
raabra = pd.read_csv(files['raabra'], sep=";")
raabra2025 = pd.read_excel(files['raabra2025'])

forb = forb.dropna(subset=['Institusjon','Periode'])
raabra = raabra.dropna(subset=['Institusjon','Periode'])

# Måned og kvartal
forb['month'] = date_string_to_period(forb['Periode'].astype(int).astype(str))
raabra['month'] = date_string_to_period(raabra['Periode'].astype(str))

forb['quarter'] = forb['month'].astype('period[Q]')
raabra['quarter'] = raabra['month'].astype('period[Q]')

# Antall per kvartal
forb_q = forb.groupby(['Institusjon','quarter'])['Antall ID_Melding'].sum()
raabra_q = raabra.groupby(['Institusjon','quarter'])['Antall ID_Melding'].sum()

# Råbra 2025
raabra2025 = raabra2025.set_index('Institusjon')
raabra2025.columns.name = 'quarter'
raabra2025.columns = pd.PeriodIndex(raabra2025.columns, freq='Q')
raabra2025 = raabra2025.stack()
raabra_q = pd.concat([raabra_q,raabra2025]).sort_index()

# Merge
raabra_q.name = 'Råbra'
forb_q.name = 'Forbedring'

df = pd.concat([forb_q,raabra_q], axis=1).sort_index().reset_index()

#mask = df['quarter']>='2024'
#df = df.loc[mask]
df = df.loc[df['Institusjon']!='Sykehjemsetaten administrasjon']
df = df.loc[~df['Institusjon'].str.lower().str.contains('helsehus')]

df['total'] = df[['Forbedring','Råbra']].sum(axis=1)
df['antall_plasser'] = df['Institusjon'].map(antall_plasser)

#df['quarter'] = df['month'].astype('period[Q]')

# Antall per hhv kvartal og mnd
#antall_q = df.groupby(['Institusjon','quarter'])['total'].sum().unstack().fillna(0)
#antall_m = df.set_index(['Institusjon','month'])['total'].unstack().fillna(0)

#temp_plasser = antall_plasser[antall_plasser.index.isin(df['Institusjon'])]

# Antall per 100 plasser per måned, beregnet for hhv kvartal og måned
#dfq = (1/3)*antall_q.div(temp_plasser, axis=0)
#dfm = antall_m.div(temp_plasser, axis=0)

# Antall per 100 plasser per måned
df['indeks'] = 100*(1/3)*df['total']/df['antall_plasser']
dfq = df.set_index(['Institusjon','quarter'])['indeks'].round(2).unstack().fillna(0)
dfq = dfq.loc[:,(dfq.columns>='2024') & (dfq.columns<'2026')]

#dfq = (100*dfq).round(2)
#dfm = (100*dfm).round(2)


#dfm = dfm.reindex(index=institusjoner)
dfq = dfq.reindex(index=institusjoner)


# Kommersielle skal ikke vurderes på dette f.o.m Q2 2025
#kommersielle = driftsform_inst['Kommersiell']
#dfm.loc[kommersielle, dfm.columns>='2025Q2'] = np.nan
#dfq.loc[kommersielle, dfq.columns>='2025Q2'] = np.nan
#dfm.loc[kommersielle] = np.nan
dfq.loc[ikke_kommunale] = np.nan

all_data['EQS'] = df.sort_values(['Institusjon','quarter'])
#time_data['EQS'] = dfm.copy()
qdata['EQS'] = dfq.copy()



# ===========================================================
# Oppstartssamtale
# Tilbud oppstartsamtale.xlsx'
# ===========================================================

df = pd.read_excel(files['OPPSAMT'])

# Behold tekst inne i []
df.columns = keep_text_in_brackets(df.columns)

df = df.dropna(subset='Institusjon')
df = df.loc[df['Institusjon']!= 'Etatsnivå']
df['Institusjon'] = df['Institusjon'].replace('Majorstuhjemmet, avd Økern','Majorstuhjemmet')

yq = df['Year_Quarter'].str.extract(r"(\d{4})-(\d)\. kvartal")
yq = yq.astype(int)
df['quarter'] = pd.PeriodIndex.from_fields(year=yq[0], quarter=yq[1], freq="Q")

df = df.loc[df['quarter']>='2024']

dfq = df.set_index(['Institusjon','quarter'])['F_TilbudOppstartsamtale_Gjennomsnitt']
dfq = dfq.unstack()

dfq = dfq.reindex(index=institusjoner)

all_data['OPPSAMT'] = df.copy()
time_data['OPPSAMT'] = dfq.copy()
qdata['OPPSAMT'] = dfq.copy()



# ===========================================================
# ADL
# IPLOS-1.kvartal-2025.xlsx
# ===========================================================


df = pd.read_excel(files['ADL'], header=3, index_col=0, usecols='A:Y')
h0 = pd.read_excel(files['ADL'], header=1, index_col=0, usecols='A:Y', nrows=2)

temp = pd.DataFrame(np.reshape(h0.iloc[0],(6,4)))[[1,2]]

months = pd.PeriodIndex.from_fields(
    year = temp[2],
    month = temp[1].map(month_name_to_nr),
    freq = "M"
)

cols0 = months.repeat(4)
df.columns = pd.MultiIndex.from_arrays([cols0, h0.iloc[1]])
df.index.name = 'Institusjon'

df1 = df.xs('3 mnd 1',level=1, axis=1)

df1 = df1.loc[~df1.index.isna()]
df1 = df1.loc[~df1.index.str.startswith('TOTALT')]
df1 = df1.loc[~df1.index.str.startswith('Område')]
df1 = df1.drop('Utenbys')
df1 = df1.dropna(how='all')
df1.index = df1.index.str.strip()

d = {'Furusethageby': 'Furuset hageby',
    'Jødisk bo- og sen.senter': 'Jødisk bo- og seniorsenter',
    'St.Hanshaugen Omsorgssenter': 'St. Hanshaugen omsorgssenter',
    'Vålerengahjemmet': 'Vålerengahjemmet bo- og kultursenter',
    'Fagertun sykehjem 5': 'Fagertun sykehjem',
    'Sofienbergsenteret': 'Sofienberghjemmet',
    'Cathinka Guldbergsenteret': 'Cathinka Guldberg-senteret Lovisenberg',
    'DIH':'Dronning Ingrids hage',
    'Villa Skaar Jevnaker 5':'Villa Skaar Jevnaker', 
    'Villa Skaar Sylling 5':'Villa Skaar Sylling',
    'Villa Skaar Valstad 5':'Villa Skaar Valstad',
     }

df1 = df1.rename(d)
df1 = df1.reindex(index=institusjoner)

df1 = df1.stack().to_frame(name='ADL3')
temp_beboere = antall_beboere.stack().reindex_like(df1)
df1['beboere'] = temp_beboere
df1['Andel ikke ADL 3mnd'] = df1['ADL3']/df1['beboere']

df2= df1['Andel ikke ADL 3mnd'].unstack()
df2 = df2.astype(float)

quarters = month2quarters(df2.columns, 2, extend=True)

dfq = pd.DataFrame(index=df2.index)
for report_date, qs in quarters.items():
    for q in qs:
        dfq[q] = (df2[report_date])


all_data['ADL'] = df1.copy()
time_data['ADL'] = df2.copy()
qdata['ADL'] = dfq.copy()



# ========================================================

indicator_order = [
    'ERNRIS',
    'ERNPLAN',
    'LMG',
    'GABI',
    'RESP',
    'OPPSAMT',
    'VAKS',
    'LM10',
    'ADL',
    'INFK',
    'IKLM',
    'UHPP',
    'EQS'
    ]

for key in indicator_order:
    temp = qdata.pop(key)
    qdata[key] = temp

for key in indicator_order:
    temp = time_data.pop(key)
    time_data[key] = temp

quarter_cols = pd.period_range(start='2024Q1', end='2025Q4', freq='Q')

for key, df in qdata.items():
    qdata[key] = df.reindex(index=institusjoner, columns=quarter_cols).round(4)

# Sammendrag av alle indikatorer for alle institusjoner
inst_summaries = pd.DataFrame(index=institusjoner)
for key, df in qdata.items():
    stats = df.apply(['count','min','mean','max'],axis=1).round(4)
    stats.columns = pd.MultiIndex.from_product([[key],stats.columns])
    inst_summaries = pd.concat([inst_summaries,stats], axis=1)

inst_summaries.columns = pd.MultiIndex.from_tuples(inst_summaries.columns)

inst_indicators = (inst_summaries.xs('count', level=1, axis=1)>0).astype(int)
n_indicators =inst_indicators.sum(axis=1)
inst_summaries.insert(0, 'Antall indikatorer', n_indicators)

inst_summaries
inst_indicators

indicator_freqs = pd.DataFrame()
for key, df in time_data.items():
    indicator_freqs[key] = indicator_frequency(df)

indicator_freqs = indicator_freqs.T
indicator_freqs.index.name = 'Indicator'


indicator_stats = pd.DataFrame()
for key, df in qdata.items():
    stats = df.astype('float').stack().describe(percentiles=[0.1,0.2,0.8,0.9]).round(4)
    valid = df.dropna(how='all',axis=1).dropna(how='all',axis=0)
    temp = pd.Series({
        'Antall perioder':valid.columns.size,
        'Antall institusjoner':valid.index.size,
        'Antall missing': df.isna().sum().sum()
        })
    vc = df.stack().value_counts()
    if vc.index.size==2:
        vc = vc.rename(lambda s: f'Antall {s:1.0f}')
        stats = pd.concat([temp,vc,stats])
    else:
        stats = pd.concat([temp,stats])
    #indicator_stats[key] = stats
    stats.name = key
    indicator_stats = pd.concat([indicator_stats,stats], axis=1)


indicator_stats.index.str.endswith('%')

# "50%"' -> "median", "5%" -> "p05" etc.
indicator_stats = indicator_stats.rename({'50%':'median'}).rename(
    lambda s: f'p{int(s.replace("%","")):02d}' if s.endswith('%') else s)

indicator_stats = indicator_stats.T
indicator_stats.index.name = 'Indikator'

#summaries = {
#    'Antall plasser':antall_plasser.to_frame(),
#    'Antall beboere':antall_beboere,
#    'Indicator frequency':indicator_freqs,
#    'Indicator stats':indicator_stats,
#    'Institusjon summary':inst_summaries,
#    'Institusjon x Indikator':inst_indicators
#}


# ====== SLÅ SAMMEN ALLE DATA PÅ KVARTALSNIVÅ =======
qdata_all = pd.DataFrame()
for key, df in qdata.items():
    temp = df.stack()
    temp.name = key
    qdata_all = pd.concat([qdata_all,temp], axis=1)
    #print(qdata_all)
    #input()

qdata_all = qdata_all.stack().unstack(level=1)
stacked_index = pd.MultiIndex.from_product([institusjoner,indicator_order])
qdata_all = qdata_all.reindex(stacked_index)
qdata_all.index = qdata_all.index.set_names(['Institusjon','Indikator'])

# ========================================================
output_path = path.joinpath('data_processed_20260315')
output_excel = output_path.joinpath('INDIKATORER TIDSSERIER Kvartaler 2024-2025.xlsx')
write_dfs_to_excel(summaries|qdata, output_excel, auto_width=True)

for key, df in (summaries|qdata).items():
    csv_path = output_path.joinpath(f'{key}.csv')
    print(csv_path.name)
    df.to_csv(csv_path, encoding='ISO8859-10', float_format='%.4f')


# ====== LAGRE ALLE_INDIKATORER.csv ======
csv_file = output_path.joinpath(f'ALLE_INDIKATORER.csv')
print(csv_file)
qdata_all.to_csv(csv_file, encoding='ISO8859-10', float_format='%.4f')

stats_csv_file = output_path.joinpath('indicator_stats.csv')
indicator_stats.to_csv(stats_csv_file, encoding='ISO8859-10', float_format='%.4f')
# ========================================================

#for key, df in summaries.items():
    f = output_path.joinpath(f'{key}.csv')
    print(f.name)
    df.to_csv(f, encoding='ISO8859-10', float_format='%.4f')



for key, df in (summaries|qdata).items():
    print(key)
    df.dtypes

# LAGRE EN ELLER NOEN datasett:
for key in ['IKLM']:
    df = qdata[key]
    csv_path = path.joinpath(f'data_processed/{key}.csv')
    df.to_csv(csv_path, encoding='ISO8859-10', float_format='%.4f')

    
# ======================================================== 
# Lese inn data fra fil
# ======================================================== 

all_data = pd.read_csv(path.joinpath(f'data_processed/ALLE_INDIKATORER.csv'), encoding='ISO8859-10')
all_data = all_data.set_index(['Institusjon','Indikator'])
all_data.columns = pd.PeriodIndex(all_data.columns, freq='Q')
all_data.columns.name = 'quarter'

#qdata = {k: table.drop(columns='Indikator').set_index('Institusjon') 
#        for k, table in all_data.groupby(level=1)}

qdata = {k: table for k, table in all_data.groupby(level=1, sort=False)}

for key, df in qdata.items():
    df.index = df.index.droplevel(1)
    qdata[key] = df



csv_path = path.joinpath(f'data_processed/Indicator stats.csv')
indicator_stats.to_csv(csv_path, encoding='ISO8859-10', float_format='%.4f')