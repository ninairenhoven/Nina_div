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
path = Path(spss_file).parent
print('\Path:')
print(path)

print('\nLeser fil: ')
print(spss_file)


(df, meta) = pyreadstat.read_sav(spss_file)


print('\nDataFrame df:\n')
print(df)

vlabels = meta.variable_value_labels
clabels = meta.column_names_to_labels 

print('\nvalue_labels: \n')
print(pd.Series(vlabels))

print('\ncol_labels: \n')
print(pd.Series(clabels))

####################################

#kommune_labels = pd.Series(value_labels['BOSTED_KommuneNummer'])
#kommune_labels = 'K-'+kommune_labels.index.astype(int).astype(str).str.zfill(4) +' '+ kommune_labels
#kommune_labels.index = kommune_labels.index.astype(int)




#========================================================================
# Labels til excel
#========================================================================
"""

clabels = pd.Series(col_labels)

vlabels = pd.Series(value_labels)
# Gjør om til heltall i key for value labels
vlabels = vlabels.apply(lambda d: {(int(k) if isinstance(k, float) else k): v for k, v in d.items()})

values =  vlabels.apply(lambda d: list(d.keys()))
n_values = values.apply(lambda x: len(x) if isinstance(x, (list)) else np.nan)
values[n_values>20] = ">20 verdier"

labels = pd.concat([clabels, vlabels, values], axis=1)

df_info = pd.DataFrame.from_dict({
    'Variable label':clabels, 
    'Values':values,
    'Value labels':vlabels,
    })


# Samfunnsmonitoren: Sjekk når hvert spørsmål har data
s = pd.Series()

for var in df.columns:
    mask = ~df[var].isna()
    antall_maalinger = df.loc[mask, 'samfmon_uke'].astype(int).nunique()
    maalinger = df.loc[mask, 'samfmon_uke'].unique()
    if (antall_maalinger<10):
        temp = [vlabels['samfmon_uke'][x] for x in maalinger]
        s[var] = ', '.join(temp)
    else:
        s[var] = f"({antall_maalinger} maalinger)"

s = s.apply(lambda x: x if len(x)<10 else x)

df_info['Målinger'] = s

"""

output_file = Path(spss_file).parent.joinpath(Path(spss_file).stem +'_info.xlsx')
#df_info.to_excel(output_file)