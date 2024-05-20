import pandas as pd
import numpy as np
import pyreadstat
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename
from pathlib import Path
import os


path_user = Path.home()
path = path_user.joinpath('Opinion AS/')

root = tkinter.Tk()
root.withdraw()


#spss_file = askopenfilename(initialdir=path)

spss_file = 'C:/Users/NinaIrenHoven/Opinion AS/Opinion SharePoint - Opinions Samfunsmonitor/07 Dashbord/SPSS-filer/Samfunnsmonitoren_master.sav'

(df, meta) = pyreadstat.read_sav(spss_file)
(_, meta) = pyreadstat.read_sav(spss_file, metadataonly=True)

nrows = meta.number_rows
ncols = meta.number_columns
colnames = meta.column_names
value_labels = meta.variable_value_labels
var_labels = meta.column_names_to_labels 

####################################
print(df)

df1 = ~df.replace("",np.nan).isna()
df1 = df1.astype(int).replace(0, np.nan)
df1['unik_id'] = df['unik_id'].astype(int)
df1['samfmon_uke'] = df['samfmon_uke'].astype(int).astype(str)


col = 'jul_S8r23'
col='S61'

df1.groupby('samfmon_uke')[col].size()

out = pd.Series(var_labels).to_frame(name='Label')

res = pd.Series(index=df.columns, dtype=object)

for col in df1.columns[19:]:
    temp = pd.Series()

    print(col, end="  ")
    #counts = df1.groupby('samfmon_uke')[col].sum().replace(0, np.nan).dropna()
    uker = df1.groupby(col)['samfmon_uke'].unique().squeeze()
    uker = ', '.join(uker) 
    res[col] = uker
    