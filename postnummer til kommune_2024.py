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

postnummer_oppslagsfil = path.joinpath('Opinion SharePoint - Team kvant/Oppslagsdata/Postnummerregister_2024.xlsx')
kommune_oppslagsfil = path.joinpath('Opinion SharePoint - Team kvant/Oppslagsdata/fylker-kommuner-2023-2024-alle.xlsx')

postnr_oppslag = pd.read_excel(postnummer_oppslagsfil)
kommuner_oppslag = pd.read_excel(kommune_oppslagsfil)

postnr_oppslag['Postnummer'] = postnr_oppslag['Postnummer'].astype(str).str.zfill(4)
postnr_til_kommune = postnr_oppslag.set_index('Postnummer')['Kommunenummer']
kommune_til_fylke = kommuner_oppslag[['Kommunenummer','Fylkesnummer']].dropna().set_index('Kommunenummer').squeeze()

k2024_labels = kommuner_oppslag.set_index('Kommunenummer')['Kommunenavn']
f2024_labels = kommuner_oppslag.drop_duplicates(subset='Fylkesnummer').set_index('Fylkesnummer')['Fylkesnavn']

fylke_til_landsdel = {
    18: 1,
    55: 1,
    56: 1,
    15: 2,
    50: 2,
    11: 3,
    46: 3,
    31: 4,
    32: 4,
    33: 4,
    34: 4,
    39: 5,
    40: 5,
    42: 5,
     3: 6
}

landsdel_labels = {
    1: "Nord-Norge",
    2: "Midt-Norge",
    3: "Vestlandet",
    4: "Østlandet",
    5: "Sørlandet inkludert TeVe",
    6: "Oslo"
}

################################33
# Les inn data
#
spss_file = askopenfilename(initialdir=path)

(df, meta) = pyreadstat.read_sav(spss_file)
print(df)


value_labels = meta.variable_value_labels
var_labels = meta.column_names_to_labels 


# Map kommune2020 til kommune2024
df['kommune_fra_postnr'] = df['zipcode'].map(postnr_til_kommune)
df['fylke_fra_postnr'] = df['kommune_fra_postnr'].map(kommune_til_fylke)
df['landsdel_fra_postnr'] = df['fylke_fra_postnr'].map(fylke_til_landsdel)



####################################################################################



###############################################################
# Lagre til fil
# 

#output_data = df[['uuid','kommune2024','fylke2024']]
output_value_labels = {
    'kommune_fra_postnr': k2024_labels.to_dict(),
    'fylke_fra_postnr': f2024_labels.to_dict(),
    'landsdel_fra_postnr': landsdel_labels
}


output_column_labels = {
    'kommune_fra_postnr': 'Kommune (fra postnummer)',
    'fylke_fra_postnr': 'Fylke (fra postnummer)',
    'landsdel_fra_postnr': 'Landedel (fra postnummer)'
}

output_file = Path(spss_file).stem+'_kommune_fylke_2024.sav'
output_path = Path(spss_file).parent
output_file = asksaveasfilename(initialdir=output_path, initialfile=output_file)

pyreadstat.write_sav(
    df,
    output_file, 
    column_labels=output_column_labels, 
    variable_value_labels=output_value_labels
    )