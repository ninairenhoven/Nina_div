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
formats = meta.original_variable_types 
measure = meta.variable_measure
missing = meta.missing_ranges

print('\nvalue_labels: \n')
print(pd.Series(value_labels))

print('\ncol_labels: \n')
print(pd.Series(col_labels))



####################################
print('\nVariabelnavn i fil:')
print(np.array(df.columns))

print('\nErstatter hashtag # med underscore _')

varname_mapping = df.columns.to_series()
varname_mapping = varname_mapping.str.replace("#","_")

if varname_mapping.duplicated().sum() > 0:
    print('***** ADVARSEL Dupliserte variabelnavn! *****')

df1 = df.rename(columns = varname_mapping)

def rename_dict_keys(d, mapping):
    return {mapping[k]:v for k,v in d.items()}

value_labels1 = rename_dict_keys(value_labels, varname_mapping)
col_labels1 = rename_dict_keys(col_labels, varname_mapping)
missing1 = rename_dict_keys(missing, varname_mapping)
measure1 = rename_dict_keys(measure, varname_mapping)
formats1 = rename_dict_keys(formats, varname_mapping)

# Fjerne formatering for stringvariabler - de lagres da med riktig width
formats1 = {k:v for k,v in formats1.items() if not(v.startswith('A')) }


#################################################
print('\nLagre til fil')

output_file = Path(spss_file).stem + "_1.sav"
output_file = asksaveasfilename(initialdir=path, initialfile=output_file)

pyreadstat.write_sav(
    df1, 
    output_file,
    column_labels= col_labels1,
    variable_value_labels = value_labels1,
    missing_ranges = missing1,
    variable_measure = measure1,
    variable_format = formats1
    )

print('Lagret til '+ output_file)