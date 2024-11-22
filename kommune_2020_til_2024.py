import pandas as pd
import numpy as np
import pyreadstat
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename
from pathlib import Path

path_user = Path.home()
path = path_user.joinpath('Opinion AS/')

root = tkinter.Tk()
root.withdraw()


kommune_oppslagsfil = path.joinpath('Opinion SharePoint - Team kvant/Oppslagsdata/fylker-kommuner-2023-2024-alle.xlsx')
kommuner_oppslag = pd.read_excel(kommune_oppslagsfil)

kommune_mapping = kommuner_oppslag[['Kommunenummer 2023','Kommunenummer']].dropna().set_index('Kommunenummer 2023').squeeze()
kommune_til_fylke = kommuner_oppslag[['Kommunenummer','Fylkesnummer']].dropna().set_index('Kommunenummer').squeeze()

k2024_labels = kommuner_oppslag.set_index('Kommunenummer')['Kommunenavn']
f2024_labels = kommuner_oppslag.drop_duplicates(subset='Fylkesnummer').set_index('Fylkesnummer')['Fylkesnavn']

####################################
# Nasjonal RVU tidsserie
#

spss_file = askopenfilename(initialdir=path)

# Nasjonal RVU tidsserie
#spss_file = 'C:/Users/NinaIrenHoven/Opinion AS/Opinion SharePoint - RVU/Displayr nøkkeltallsrapportering/data/RVU 2019_2023 Personfil_240605_dash.sav'

# Nasjonal RVU 2023
#spss_file = 'C:/Users/NinaIrenHoven/Opinion AS/Opinion SharePoint - RVU/DATA SAMLET (endelig versjon alle år)/2023/RVU 2023 Personfil vektet alle utvalg 02Sept2024.sav'

(df, meta) = pyreadstat.read_sav(spss_file)
print(df)

value_labels = meta.variable_value_labels
var_labels = meta.column_names_to_labels 

# Legg til verdier for utlandet
kommune_mapping[9999] = 9999
kommune_til_fylke[9999] = 99
k2024_labels[9999] = 'Utlandet'
f2024_labels[99] = 'Utlandet'

# Map kommune2020 til kommune2024
df['kommune2024'] = df['kommune2020'].map(kommune_mapping)

# Sjekk manglende verdier
test = df['kommune2024'].isna()
print(test.sum())
print(df.loc[test,['kommune2024','kommune2020','kommune2019','Year']])
print(df.loc[test,['kommune2024','kommune2020','kommune2019','Year']].apply(pd.Series.value_counts))

# Map kommune2024 til fylke2024
df['fylke2024'] = df['kommune2024'].map(kommune_til_fylke)
print(df['fylke2024'].isna().sum())
print(df['fylke2024'].value_counts(dropna=False).sort_index())




###############################################################
# Lagre til fil
# 

output_data = df[['uuid','kommune2024','fylke2024']]
output_value_labels = {
    'kommune2024': k2024_labels.to_dict(),
    'fylke2024': f2024_labels.to_dict()
}
output_column_labels = {
    'kommune2024': 'Kommune (2024)',
    'fylke2024': 'Fylke (2024)'
}

output_file = Path(spss_file).stem+'_kommune_fylke_2024.sav'
output_path = Path(spss_file).parent
output_file = asksaveasfilename(initialdir=output_path, initialfile=output_file)

pyreadstat.write_sav(
    output_data,
    output_file, 
    column_labels=output_column_labels, 
    variable_value_labels=output_value_labels
    )