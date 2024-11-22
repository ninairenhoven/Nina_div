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

spss_file = askopenfilename(initialdir=path)
# spss_file = 'C:/Users/NinaIrenHoven/OneDrive - Opinion AS/Documents/VMP_tekst og et par variabler_korr.sav'
path = Path(spss_file).parent

(df, meta) = pyreadstat.read_sav(spss_file)
value_labels = meta.variable_value_labels
col_labels = meta.column_names_to_labels 

####################################
print(df)

# MRSETS FRA PSPP - med variabeNAVN for alle MR-sets
# Åpne sav-fil i PSPP
# Kjør syntax :
# MRSETS /DISPLAY NAME=ALL.
# Eksporter fra output-vindu til csv

mrset_overview_file = askopenfilename(initialdir=path)
#mrset_overview_file = 'C:/Users/NinaIrenHoven/OneDrive - Opinion AS/Documents/mrsets_vmp.csv'

# Les inn info om MR-sets
mrset_overview = pd.read_csv(mrset_overview_file, header=1)
mrsets = mrset_overview.set_index('Name')['Member Variables']
mrsets = mrsets.str.replace('\r','')
mrsets.index = mrsets.index.str.replace('$','')

# Fjern MR-set som ikke skal brukes til renavning
mrsets = mrsets.drop('BinaryvariablesfromVinmonopoletsikrerkvalitetpåvareneforforbru')

# Splitt variabelliste til kolonner, lag nummerering
mrsets = mrsets.str.split('\n', expand=True)
mrsets.columns = (mrsets.columns+1).astype(str).set_names(['Nr'])

# Legg variabler vertikalt, gjør om til df
mrsets = mrsets.stack().reset_index()

mrsets = mrsets.rename(columns={0:'var_name'})

# Generer nytt variabelnavn fra MRset-navn pluss variabelnummer
mrsets['new_name'] = mrsets['Name'].str.replace('multi','')+'_'+mrsets['Nr']

# Sjekk at alle nye variabelnavn er unike 
print(mrsets['new_name'].duplicated().sum())

# Mapping navn -> nytt navn
rename_cols = mrsets.set_index('var_name')['new_name']

# Hent column labels for variablene i multisett, renavne til nye variabelnavn
labels = pd.Series(col_labels)[rename_cols.index].rename(rename_cols)

# Lag value labels {0 : "Not Selected", 1: label}
new_value_labels = labels.to_frame(name=1)
new_value_labels[0] = 'Not Selected'
new_value_labels = new_value_labels.apply(pd.Series.to_dict, axis=1)

new_value_labels = new_value_labels.to_dict()
new_col_labels = labels.to_dict()

# Renavne kolonner
df1 = df.rename(columns=rename_cols)

# Definer format uten desimaler for alle numeriske variabler
types = pd.Series(meta.readstat_variable_types)
string_vars = types[types=='string'].index
numeric_vars = df1.columns.drop(string_vars)
formats = {var: 'F4.0' for var in numeric_vars}
formats['weight'] = 'F6.4'

output_file = Path(spss_file).stem + '_FIX.sav'
output_file = asksaveasfilename(initialdir=path, initialfile=output_file)

pyreadstat.write_sav(
    df1,
    output_file,
    variable_value_labels = value_labels|new_value_labels,
    column_labels = col_labels|new_col_labels,
    variable_format = formats
    )