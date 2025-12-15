import pandas as pd
import numpy as np
import pyreadstat
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename
from pathlib import Path

path_user = Path.home()
path = path_user.joinpath(r'Opinion AS/Opinion SharePoint - Skolevei\Rapportering\Data NIH')
root = tkinter.Tk()
root.withdraw()




# KOMMUNE
oppslagsdata_path = path_user.joinpath('Opinion AS/Opinion SharePoint - Team kvant/Oppslagsdata')
kommuner_labels_fil = oppslagsdata_path.joinpath('oversikt-over-alle-landets-kommunenummer NY FRA 01.01.2024.xlsx')
kommuner = pd.read_excel(kommuner_labels_fil)
kommuner = kommuner.rename(columns={'Kommunenummer 1.1.24':'Kommunenr'})
kommunenr = kommuner.set_index('Kommune')['Kommunenr'].dropna()


#========================================================================
# Funksjon som repeterer svar for x antall barn
#========================================================================

def repeat_to_columns(value_col, n_reps_col, new_col_names = None, col_prefix=''):
    """
    Repeterer verdier fra en kolonne til flere kolonner basert på antall repetisjoner.
    #
    Parameters:
    -----------
    value_col : pd.Series
        kolonnen med verdier som skal repeteres
    n_reps_col : pd.Series
        kolonnen som angir hvor mange ganger verdien skal repeteres
    new_col_names : list
        Liste med nye kolonnenavn (f.eks. ['B1_barn1', 'B1_barn2', ...])
    new_col_prefix: string
        Hvis new_col_names er tom, genereres kolonne 1-7 med dette prefixet
    #
    Returns:
    --------
    DataFrame
        DataFrame med kun de nye kolonnene
    """
    # Sjekk at indeksene stemmer overens
    if not value_col.index.equals(n_reps_col.index):
        raise ValueError("Indeksene i value_col og n_reps_col stemmer ikke overens")
    #
    if new_col_names is None or len(new_col_names) == 0:
        new_col_names = [f'{col_prefix}{i}' for i in range(1, 8)]
    #
    # Opprett ny dataframe med samme index
    result = pd.DataFrame(index=value_col.index)
    #
    # Opprett nye kolonner basert på value_col sin dtype
    for col_name in new_col_names:
        result[col_name] = pd.Series(dtype=value_col.dtype, index=value_col.index)
    #
    # Fyll inn verdier
    for i, col_name in enumerate(new_col_names, start=1):
        # Fyll inn verdien hvis n_reps_col >= i
        mask = n_reps_col.notna() & (n_reps_col >= i)
        result.loc[mask, col_name] = value_col[mask]
    #
    return result


#========================================================================
# LES DATA
#========================================================================

spss_file = path.joinpath('RVU Skolevei 2025 13112025.sav')
spss_file = path.joinpath('RVU Skolevei 2025 13112025 RENAMED.sav')

#spss_file = askopenfilename(initialdir=path)
#path = Path(spss_file).parent
print('\Path:')
print(path)

print('\nLeser fil: ')
print(spss_file)


(df0, meta) = pyreadstat.read_sav(spss_file)
df = df0.copy()

print('\nDataFrame df:\n')
df

vlabels = meta.variable_value_labels
clabels = meta.column_names_to_labels 

print('\nvalue_labels: \n')
print(pd.Series(vlabels))

print('\ncol_labels: \n')
print(pd.Series(clabels))

# Genererer enkel og reproduserbar id
df = df.sort_values('respid')
df['id'] = [f'id{x:05d}' for x in range(1,len(df)+1)]
df = df.set_index('id')

# Missing på Antall barn -> 1
df['B1'].value_counts(dropna=False)

mask = ~df['B1'].isna()
df = df.loc[mask]


#========================================================================
# Slette variabler
#========================================================================
drop1 = df.filter(regex='Maps_1_\d{1,2}$').columns
drop2 = df.filter(regex='Maps_1_\d_other$').columns

drop3 = df.filter(regex='Maps_1_Barn[1-7]_\d{1,2}$').columns
drop4 = df.filter(regex='Maps_1_Barn[1-7]_\d_other$').columns

drop5 = ['data_time_2_1','data_time_2_2','altid','altidNumeric','PublishedVersion']

df = df.drop(columns=drop1)
df = df.drop(columns=drop2)
df = df.drop(columns=drop3)
df = df.drop(columns=drop4)
df = df.drop(columns=drop5)

# ===================================================
# Slå sammen kommunevariabler
# ===================================================

# B7A Kommuner i Akershus
# B7B Kommuner i Buskerud

clean_kommune_label = lambda s: s.replace('kommune','').replace('Kommune','').strip()
mapping_akershus = pd.Series(vlabels['B7A']).apply(clean_kommune_label).map(kommunenr)
mapping_buskerud = pd.Series(vlabels['B7B']).apply(clean_kommune_label).map(kommunenr)

mapped_B7A = df['B7A'].map(mapping_akershus)
mapped_B7B = df['B7B'].map(mapping_buskerud)

df['Kommune'] = mapped_B7A.fillna(mapped_B7B)

templabels = kommuner.set_index('Kommunenr')['Kommune']
templabels = templabels.loc[list(mapping_akershus.values)+list(mapping_buskerud.values)]
vlabels['Kommune'] = templabels.to_dict()

# ===================================================
# VALGTE SKOLER (Multi)
# ===================================================

# B8 - hvilken skole går barna på (multi), Akershus
# B9 - hvilken skole går barna på (multi), Buskerud
skole_cols_pattern = 'B[8,9][A-Z]_.{1,2}$'
skole_other_cols_pattern = 'B[8,9][A-Z]_.{1,2}_other'

# LABELS for skoler
skoler_labels = pd.Series(clabels).filter(regex=skole_cols_pattern)
skoler_labels = skoler_labels.str.split('går på', expand=True)[1].str.strip()
print(skoler_labels)

# Slå sammen "Annen skole, noter" til én kategori
mask = skoler_labels=='Annen skole, noter:'
values_annen = skoler_labels[mask].index
skoler_labels = skoler_labels.drop(values_annen)
skoler_labels['99'] = 'Annen skole, noter:'
print(skoler_labels)

recode_annen = {code: '99' for code in values_annen}


# Alle skoler som respondent har krysset av for
skoler = df.filter(regex=skole_cols_pattern)

# Liste med valgte skoler per respondent
valgte_skoler = skoler.apply(lambda row: list(skoler.columns[row.values == 1]), axis=1)
valgte_skoler.apply(len).value_counts()

valgte_skoler_df = valgte_skoler.apply(pd.Series)
valgte_skoler_df.columns = [f'valgt_skole_{i}' for i in range(1,len(valgte_skoler_df.columns)+1)]
valgte_skoler_df = valgte_skoler_df.replace(recode_annen)

df['valgte_skoler'] = valgte_skoler
df = pd.concat([df, valgte_skoler_df], axis=1)
vlabels = vlabels | {col: skoler_labels.to_dict() for col in valgte_skoler_df.columns}

# Skole fritekst -> samle fritekst oppgitt for hver kommune, til 1 kolonne
skoler_annen = df.filter(regex=skole_other_cols_pattern)
skoler_annen = skoler_annen.stack().replace('',np.nan).dropna()
skoler_annen.index = skoler_annen.index.droplevel(1)

df['skole_annen_oe'] = skoler_annen

# To clipboard for koding
#df[['Kommune','skole_annen_oe']].dropna(subset='skole_annen_oe').replace(vlabels['B7_kommune']).to_clipboard()




# 1: Hvis kun ett barn, eller alle barna går på samme skole: Legg inn første angitte skole for hvert barn
repeat_skole = repeat_to_columns(df['valgt_skole_1'], df['B1'], col_prefix='Skole_barn')
repeat_skole_annen = repeat_to_columns(df['skole_annen_oe'] , df['B1'], col_prefix='Skole_annen_barn')

mask = (df['B5']==1)|(df['B1']==1)
repeat_skole.loc[~mask] = np.nan
repeat_skole_annen.loc[~mask] = np.nan

df = pd.concat([df,repeat_skole], axis=1)
df = pd.concat([df,repeat_skole_annen], axis=1)

#df[repeat_skole_annen.columns] = df[repeat_skole_annen.columns].fillna(repeat_skole_annen)
#df[repeat_skole.columns] = repeat

temp_labels = {col:skoler_labels.to_dict() for col in repeat_skole.columns}
vlabels = vlabels|temp_labels



"""
# Skoler i kommune
skoler_kommune = df.groupby('B7_kommune')[df.filter(regex=skole_cols_pattern).columns].any()
skoler_kommune.columns.name = 'Skole_kode'
skoler_kommune.index.name = 'Knr'
skoler_kommune = skoler_kommune.stack()
skoler_kommune = skoler_kommune[skoler_kommune].reset_index().drop(columns=[0])
skoler_kommune['Skole'] = skoler_kommune['Skole_kode'].map(skoler_labels) 
skoler_kommune['Kommune'] = skoler_kommune['Knr'].map(vlabels['B7_kommune']) 

skoler_kommune = skoler_kommune[['Knr','Kommune','Skole_kode','Skole']]
skoler_kommune.to_clipboard()

data = df.groupby('B7_kommune')[df.filter(regex=skole_cols_pattern).columns].any()
data.columns = data.columns.str.split('_', expand=True)
data = data.stack(future_stack=True)
data = data.groupby(level=0).any()
result = data.idxmax(axis=1)
"""

#========================================================================
# KODE SVAR SOM GJELDER FLERE BARN
#========================================================================
"""
# Q1a Hvor langt er det til skolen?
result = repeat_to_columns(df['Q1a'], df['B1'], col_prefix='Q1b_barn')
print(result)
print(df[result.columns])
df[result.columns] = df[result.columns].fillna(result)

# Q2a Hvor stor del av skoleveien har fortau, gang- eller sykkelvei?
result = repeat_to_columns(df['Q2a'],df['B1'], col_prefix='Q2b_barn')
print(result)
print(df[result.columns])
df[result.columns] = df[result.columns].fillna(result)

# Q3a Opplever du at det er trygt for barnet/barna å krysse veier og gater i området rundt skolen?
result = repeat_to_columns(df['Q3a'], df['B1'], col_prefix='Q3b_barn')

"""

repeat_Q12345_variables = {
    'Q1a': 'Q1b_barn',
    'Q2a': 'Q2b_barn',
    'Q3a': 'Q3b_barn',
    'Q4a': 'Q4b_barn',
    'Q5a': 'Q5b_barn'
    }

repeat_Q6_variables = {
    'Q6a_1': [f'Q6b_barn{i}_1' for i in range(1,8)],
    'Q6a_2': [f'Q6b_barn{i}_2' for i in range(1,8)],
    'Q6a_3': [f'Q6b_barn{i}_3' for i in range(1,8)],
    'Q6a_4': [f'Q6b_barn{i}_4' for i in range(1,8)],
    'Q6a_5': [f'Q6b_barn{i}_5' for i in range(1,8)],
    'Q6a_6': [f'Q6b_barn{i}_6' for i in range(1,8)],
    'Q6a_7': [f'Q6b_barn{i}_7' for i in range(1,8)],
    'Q6a_9': [f'Q6b_barn{i}_9' for i in range(1,8)],
    'Q6a_10': [f'Q6b_barn{i}_10' for i in range(1,8)],
    'Q6a_11': [f'Q6b_barn{i}_11' for i in range(1,8)],
}

repeat_coord_variables = {
    'Maps_1_10_other': [f'Maps_1_Barn{i}_10_other' for i in range(1,8)],
    'Maps_1_11_other': [f'Maps_1_Barn{i}_11_other' for i in range(1,8)],
}


for col, prefix in repeat_Q12345_variables.items():
    result = repeat_to_columns(df[col], df['B1'], col_prefix=prefix)
    df[result.columns] = df[result.columns].fillna(result)


for col, col_list in repeat_Q6_variables.items():
    result = repeat_to_columns(df[col], df['B1'], new_col_names=col_list)
    df[result.columns] = df[result.columns].fillna(result)


for col, col_list in repeat_coord_variables.items():
    result = repeat_to_columns(df[col], df['B1'], new_col_names=col_list)
    df[result.columns] = result.where(result != "", df[result.columns])


rename_cols = [f'Maps_1_Barn{i}_{j}_other' for j in [10,11] for i in range(1,8)]
d = {col: col.replace('Barn','barn') for col in rename_cols}

df = df.rename(columns=d)

df = df.copy()

#========================================================================
# BARN NR
#========================================================================


cols = df.filter(regex='Barn_[1-7]$').columns

for i, col in enumerate(cols, start=1):
    mask = i<=df['B1']
    print(i)
    df.loc[mask, f'Barn_nr_barn{i}'] = df.loc[mask, col] * i




#========================================================================
# TRANSPONERING
#========================================================================

# Definere kolonnenavn til transponering
colname_pattern = r'(?P<SPM>.*)_(?P<Barn>barn[1-7])_?(?P<subscript>.*)'

data = df.filter(regex=colname_pattern).copy()

# Lage multiindex columns
split_cols = data.columns.str.extract(colname_pattern)
data.columns = pd.MultiIndex.from_frame(split_cols)

# TRANSPONERING
df_barn = data.stack(level=1, future_stack=True)
df_barn = df_barn.loc[df_barn['Barn_nr'].notna()]


# Flatten columns
df_barn.columns = df_barn.columns.map(lambda col: f"{col[0]}_{col[1]}" if col[1] else col[0])

# Lag barn ID
df_barn = df_barn.reset_index()
df_barn['respid'] = df_barn['id'].map(df['respid'])
df_barn['barn_ID'] = df_barn['id'] + "_" + df_barn['Barn_nr'].astype(int).astype(str)
df_barn['barn_respid'] = df_barn['respid'] + "_" + df_barn['Barn_nr'].astype(int).astype(str)
#df_barn = df_barn.set_index('barn_ID').reset_index()


# Noen justeringer
df_barn['Skole'] = df_barn['Skole'].fillna('')
df_barn['Skole_annen'] = df_barn['Skole_annen'].fillna('')
df_barn['B3_1'] = df_barn['B3_1'].fillna(3)

# Mappe inn kommune
df_barn['Kommune'] = df_barn['id'].map(df['Kommune'])

first_cols = ['barn_ID', 'id', 'barn_respid', 'respid', 'Barn', 'Barn_nr','Kommune','Skole','Skole_annen','Skole_oe']
remaining_cols = [c for c in df_barn.columns if c not in first_cols]

df_barn = df_barn[first_cols+remaining_cols]

# LABELS
vlabels_barn = pd.Series(vlabels).filter(regex='.*_barn1.*')
clabels_barn = pd.Series(clabels).filter(regex='.*_barn1.*')

vlabels_barn.index = vlabels_barn.index.str.replace('_barn1','')
clabels_barn.index = clabels_barn.index.str.replace('_barn1','')

# Clean column label text
clabels_barn = clabels_barn.str.replace('Barn 1: ,','')
clabels_barn = clabels_barn.str.replace('følgende barn', 'barnet')
clabels_barn = clabels_barn.str.replace('barn 1: ,', 'barnet')

vlabels_barn['Kommune'] = vlabels['Kommune']

vlabels_barn = vlabels_barn.to_dict()
clabels_barn = clabels_barn.to_dict()


# Data på respondentnivå

df_resp = df.reset_index()

dropcols = df.filter(regex=colname_pattern).columns
df_resp = df_resp.drop(columns=dropcols)

# Fjern kolonner som er repetert per barn
dropcols = (repeat_Q12345_variables|repeat_Q6_variables|repeat_coord_variables).keys()
df_resp = df_resp.drop(columns = dropcols)

# Fjern binær variabel per skole
dropcols = df.filter(regex=skole_cols_pattern+'|'+skole_other_cols_pattern).columns
df_resp = df_resp.drop(columns = dropcols)

dropcols = [f'Barn_{i}' for i in range (1,8)]
df_resp = df_resp.drop(columns = dropcols)


#========================================================================
# HENTE INN MANUELL KODING AV SKOLER
#========================================================================

fil_kodet_skole_respondent = path.parent.joinpath('B8_B9_Skoler_other_coded.xlsx')
fil_kodet_skole_per_barn = path.parent.joinpath('Skole_1-7_coded.xlsx')

# RESPONDENTNIVÅ: "Annen skole" valgt i B8 og B9

kodet_B8B9 = pd.read_excel(fil_kodet_skole_respondent, sheet_name='åpne svar')
kodet_B8B9 = kodet_B8B9.set_index('id')

# SLETTES
slettes_mask = kodet_B8B9['Slette respondent']=='JA'
delete_cases = slettes_mask[slettes_mask].index

# KODES
# Bruk kodet data på respondentnivå dersom antall barn = 1 eller alle barn på samme skole
kodet_mask = ~slettes_mask & kodet_B8B9['Kode'].notna() & ((kodet_B8B9['Antall barn']==1)|(kodet_B8B9['Alle samme skole']==1))
kodet =  kodet_B8B9.loc[kodet_mask]

skole_annen_kodet = df_barn['id'].map(kodet['Kode'])
kommune_korrigert_1 = df_barn['id'].map(kodet['Kommune_korr']).map(kommunenr)
fylke_korrigert_1  = df_barn['id'].map(kodet['Fylke_korr'])


# PER BARN: SKOLE BARN 1,2,3,4,5,6,7
# OE spørsmål per barn, hvis barna går på forskjellige skoler

kodet_barn1_7 = pd.read_excel(fil_kodet_skole_per_barn)
kodet_barn1_7 = kodet_barn1_7.set_index('barn_ID')

skole_per_barn_kodet = df_barn['barn_ID'].map(kodet_barn1_7['Kode'])
kommune_korrigert_2 = df_barn['barn_ID'].map(kodet_barn1_7['Kommune_korr']).map(kommunenr)
fylke_korrigert_2 = df_barn['barn_ID'].map(kodet_barn1_7['Fylke_korr'])


# KODE INN I df_barn

col_loc = df_barn.columns.get_loc('Skole')+1

df_barn.insert(col_loc, 'Skole_annen_kodet', np.nan)
df_barn.insert(col_loc+1, 'Skole_barn_kodet', np.nan)
df_barn.insert(col_loc+2, 'Kommune_korr', np.nan)
df_barn.insert(col_loc+3, 'Fylke_korr', np.nan)

df_barn['Skole_annen_kodet'] = skole_annen_kodet
df_barn['Skole_barn_kodet'] = skole_per_barn_kodet
df_barn['Kommune_korr'] = kommune_korrigert_1.fillna(kommune_korrigert_2)
df_barn['Fylke_korr'] = fylke_korrigert_1.fillna(fylke_korrigert_2)

vlabels_barn['Skole_annen_kodet'] = skoler_labels.to_dict()
vlabels_barn['Skole_barn_kodet'] = skoler_labels.to_dict()
vlabels_barn['Kommune_korr'] = vlabels['Kommune']

# Slette respondenter/barn
slettes_barn_1 = df_barn['id'].isin(delete_cases)
df_barn = df_barn[~slettes_barn_1]

slettes_resp = df_resp['id'].isin(delete_cases)
df_resp = df_resp[~slettes_resp]

slettes_barn_2 = df_barn['Skole_barn_kodet']==-1
df_barn = df_barn[~slettes_barn_2]


df_barn[['Skole','Skole_annen','Skole_annen_kodet','Kommune_korr','Fylke_korr']].dropna(subset='Skole_annen_kodet')


# KODE INN i df_resp
df

#========================================================================
# LAGRE
#========================================================================
formats1 = {col:'F4.0' for col in vlabels.keys()}
formats2 = {col:'F4.0' for col in vlabels_barn.keys()}
formats3 = {
    'Barn_nr':'F4.0',
    'Skole': 'A8'
}
formats4 = {col:'A8' for col in [f'valgt_skole_{i}' for i in range(1,4)]}

formats = formats1|formats2|formats3|formats4

stem = spss_file.stem
stem = stem.replace('RENAMED','').strip()
parent_dir = spss_file.parent

output_file_barn = stem +'_TRANSPONERT.sav'
output_file_barn = asksaveasfilename(initialdir=parent_dir, initialfile=output_file_barn)

output_file_resp = Path(output_file_barn).parent.joinpath(stem +'_RESPONDENT.sav')
output_file_total = Path(output_file_barn).parent.joinpath(stem +'_TOTAL.sav')


pyreadstat.write_sav(
    df_barn, output_file_barn, variable_value_labels=vlabels_barn, column_labels=clabels_barn, variable_format=formats)

pyreadstat.write_sav(
    df_resp, output_file_resp, variable_value_labels=vlabels, column_labels=clabels, variable_format=formats)

pyreadstat.write_sav(
    df.reset_index(), output_file_total, variable_value_labels=vlabels, column_labels=clabels, variable_format=formats)



#df1, meta1 = pyreadstat.read_sav(output_file_barn)
#meta1.variable_value_labels['Skole']





# ===================================================
# RENAME columns for barn GJORT I SPSS
# ===================================================
"""
import re

# B3_x -> B3_barnx
# B4_x -> B4_barnx
df.columns = df.columns.str.replace(r'B3_([1-7])', r'B3_barn\1', regex=True)
df.columns = df.columns.str.replace(r'B4_([1-7])', r'B4_barn\1', regex=True)

# Q1b_x -> Q1b_barnx
# For Q1-5    
df.columns = df.columns.str.replace(r'(Q[1-5]b_)([1-7])', r'\1barn\2', regex=True)

# Q7B_x -> Q7B_barnx, for Q7-9
df.columns = df.columns.str.replace(r'(Q[7,8,9]B_)([1-7])', r'\1barn\2', regex=True)


#Q6b_x_1 -> Q6b_barnx_1
# Subscript 1-11
df.columns = df.columns.str.replace(r'(Q6b_)([1-7])(_\d{1,2})', r'\1barn\2\3', regex=True)

# Q7_x_1': 'Q7_barnx_1', subscript 1-5
df.columns = df.columns.str.replace(r'(Q7_)([1-7])(_[1-5])', r'\1barn\2\3', regex=True)

#'Q8_1_1': 'Q8_barn1_1', subscript 1-5
df.columns = df.columns.str.replace(r'(Q8_)([1-7])(_[1-5])', r'\1barn\2\3', regex=True)
df.filter(regex='Q8_')


# 'Q9_x_1': 'Q9_barnx_1', subscript 1-8
df.columns = df.columns.str.replace(r'(Q9_)([1-7])(_[1-8])', r'\1barn\2\3', regex=True)

# 'Q9B_1': 'Q9B_barn1',
# 'Q10_1': 'Q10_barn1',
df.columns = df.columns.str.replace(r'(Q10_)([1-7])', r'\1barn\2', regex=True)

#     'Q10B_1_1': 'Q10B_barn1_1', subscript 1-14
df.columns = df.columns.str.replace(r'(Q10B_)([1-7])(_\d+)', r'\1barn\2\3', regex=True)

#     'Q11_1': 'Q11_barn1',
df.columns = df.columns.str.replace(r'(Q11_)([1-7])', r'\1barn\2', regex=True)

#    'Q12_1_1': 'Q12_barn1_1', subscript 1-9
df.columns = df.columns.str.replace(r'(Q12_)([1-7])(_\d)', r'\1barn\2\3', regex=True)"""




['id08928_3',
'id10386_2',
'id11450_1',
'id15399_1',
'id15399_2',
'id16312_1',
'id16312_2',
'id18174_1',
'id18174_2',
'id21012_1',
'id21012_2',
'id21801_1',
'id21801_2',
'id03194_2',
'id03194_4',
'id05505_7']


ids = [
    'id08928',
    'id10386',
    'id11450',
    'id15399',
    'id16312',
    'id18174',
    'id21012',
    'id21801',
    'id03194',
    'id05505']