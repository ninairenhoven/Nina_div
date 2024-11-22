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

#spss_file = askopenfilename(initialdir=path)
spss_file = path.joinpath('Opinion SharePoint - Byggmakker/Byggmakker 2024/Byggmakker tracker 2024/data/Byggmakker_tracker_akkumulert_240903.sav')
(df, meta) = pyreadstat.read_sav(spss_file)

value_labels = meta.variable_value_labels
column_labels = meta.column_names_to_labels 

####################################
print(df)
df = df.set_index('uuid')

# Hent alle variabler med navn som starter på Q7 (252 variabler)
q7 = df.filter(regex='^Q7')
print(q7)

# Definere verdi-mapping
d = {
    1: 1, 
    2: 1,
    3: 0, 
    4: 0, 
    5: 0, 
    6: 0, 
    7: 0, 
    np.nan: np.nan
}

# lag nytt variabelsett
q7_siste_3mnd = q7.replace(d)

# Nye variabelnavn
q7_siste_3mnd.columns = q7_siste_3mnd.columns+'_siste3mnd'

# Nye value labels
temp = {1: 'Besøkt siste 3 mnd', 0: 'Ikke besøkt siste 3 mnd'}
new_value_labels = {v:temp for v in q7_siste_3mnd.columns}


# Nye variable labels
# Input: 'Bauhaus - I forbindelse med å bytte gulv, når besøkte du sist følgende butikkjeder enten i butikk eller på nett?'
# Nye labels: "Bauhaus - bytte gulv - Besøkt siste 3 mnd"
q7_labels = pd.Series(column_labels)[q7.columns]
pattern = r'^(.*? - )I forbindelse med å (.*?),'
temp = q7_labels.str.extract(pattern) 
new_col_labels = temp[0]+temp[1]+' - Besøkt siste 3 mnd'
new_col_labels.index = new_col_labels.index+'_siste3mnd'
new_col_labels = new_col_labels.to_dict()


# Skrive nye variabler til fil
output_path = Path(spss_file).parent
output_filename = Path(spss_file).stem + ' Q7 besøkt siste 3 mmnd.sav'
output_file = output_path.joinpath(output_filename)


pyreadstat.write_sav(
    q7_siste_3mnd.reset_index(),
    output_file,
    variable_value_labels = new_value_labels,
    column_labels = new_col_labels
)


