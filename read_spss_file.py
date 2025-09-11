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

value_labels = meta.variable_value_labels
col_labels = meta.column_names_to_labels 

print('\nvalue_labels: \n')
print(pd.Series(value_labels))

print('\ncol_labels: \n')
print(pd.Series(col_labels))



####################################

kommune_labels = pd.Series(value_labels['BOSTED_KommuneNummer'])
kommune_labels = 'K-'+kommune_labels.index.astype(int).astype(str).str.zfill(4) +' '+ kommune_labels
kommune_labels.index = kommune_labels.index.astype(int)




#========================================================================
# Labels til excel
#========================================================================

labels = pd.Series(col_labels).to_frame(name='Variable label')

vlabels = pd.Series(value_labels)
vlabels = vlabels.apply(lambda d: {int(k):v for k,v in d.items()})

labels['Values'] =  vlabels.apply(lambda d: set(d.keys()))
labels['Value_labels'] = vlabels
n_values = labels['Values'].apply(lambda x: len(x) if isinstance(x, (set)) else np.nan)

output_file = Path(spss_file).with_name(Path(spss_file).stem + "_LABELS" + ".xlsx")
labels.to_excel(output_file)