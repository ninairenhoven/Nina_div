import pandas as pd
import numpy as np
import datetime as dt
import sys, os
from pathlib import Path
import pyreadstat

import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename, askdirectory

user_path = Path.home()

var_definition_file = user_path.joinpath('src_github/Nina_div/test variabelkoding.xlsx')
#spss_file = askopenfilename(initialdir=user_path, filetypes=[('SAV','*.sav')])
spss_file = 'C:/Users/NinaIrenHoven/Opinion AS/Opinion SharePoint - ForbrukerMeteret/01 Data/Månedlige SPSS-filer/Rådata 2024/ONJ127298_241015_weight_toPM.sav'

recode_var_definition = pd.read_excel(var_definition_file, index_col=[0,1], sheet_name='Recode')
recode_var_definition = recode_var_definition.dropna(how='all')

variable_value_mapping = recode_var_definition.groupby(level=0).apply(lambda x: dict(zip(x['From value'], x['To value'])))
recode_var_mapping = recode_var_definition.reset_index()[['New var','From var']].drop_duplicates().set_index('New var')['From var'].to_dict()

value_label_input =  recode_var_definition.dropna(subset='New value labels')
new_value_labels = value_label_input.groupby(level=0).apply(lambda x: dict(zip(x['To value'], x['New value labels'])))




df, meta = pyreadstat.read_sav(spss_file)
value_labels = meta.variable_value_labels

for newvar, fromvar in recode_var_mapping.items():
    d = variable_value_mapping[newvar]
    print('\n{} --> {}'.format(fromvar, newvar))
    print('Value mapping from definition:')
    print(pd.Series(d))
    #
    if fromvar in df.columns:
        # Check if oldvar contains values not defined in mapping
        test = set(df[fromvar])-set(d.keys())
        if len(test)>0:
            print('\nWARNING: Variable {} includes values not defined in mapping for {}. Keeping input value.'.format(fromvar, newvar))
            print(test)
            input('Press Enter to continue or Ctrl-C to cancel.')
        df[newvar] = df[fromvar].replace(d)
    else:
        print('\nWARNING: Variable {} does not exist in input data'.format(fromvar))
        input('Press Enter to continue or Ctrl-C to cancel.')
        df[newvar] = np.nan
    value_labels[newvar] = new_value_labels[newvar]
    print('\nResult of mapping:')
    result = df.groupby([newvar,fromvar]).size().reset_index().set_index(fromvar)
    result = result.rename(value_labels[fromvar]).rename(columns={0:'rows'})
    result[newvar] = result[newvar].replace(value_labels[newvar])
    print(result)
    input('Press Enter to continue')




bin_var_definition = pd.read_excel(var_definition_file, index_col=[0,1], sheet_name='Bin')
bin_var_mapping = bin_var_definition.reset_index()[['New var','From var']].drop_duplicates().set_index('New var')['From var'].to_dict()
bin_edges = bin_var_definition['Bins'].values
bin_numbers = bin_var_definition['To value'].values
bin_include = bin_var_definition['Include'].dropna().values[0]

for newvar, fromvar in bin_var_mapping.items():


# TRACKERVARIABLER
def tracker_variables(date_column):
    tracker = pd.DataFrame()
    tracker['date_dt'] = pd.to_datetime(date_column)
    
    tracker['mnd_num'] = tracker['date_dt'].dt.month
    tracker['kvartal_num'] = tracker['date_dt'].dt.quarter
    tracker['year'] = tracker['date_dt'].dt.year
    tracker['yymm'] = (tracker['year']-2000)*100+tracker['mnd_num']
    tracker['yyq'] = (tracker['year']-2000)*10+tracker['kvartal_num']

    # Id format yyyymmxxxx, f.eks 2024080001
    tracker['unik_id'] = (tracker['yymm']*1E5 + tracker.index).astype(int)
    tracker['date_dt'] = tracker['date_dt'].dt.date

    print('\nGenerated tracker variables:')
    print(tracker)
    input('Press Enter to continue')
    return tracker




def get_age_groups(age_col):
    # Grupper numerisk alder i aldersgrupper. 
    # Inkluderer VENSTRE og ikke høyre endepunkt
    age_bins = [18, 30, 40, 50, 60, 111]
    age_groups = pd.cut(age_col, bins=age_bins, labels=np.arange(5)+1, right=False)
    labels = {
        1: 'Under 30 år', 
        2: '30–39 år', 
        3: '40–49 år', 
        4: '50–59 år', 
        5: '60 år +'
        }
    if (min(age_col)<min(age_bins))|(max(age_col)>=max(age_bins)):
        print('\nADVARSEL: Aldersgrupper\nInputdata inkluderer verdier utenfor definerte alderskategorier')
        print(age_col.apply([min,max]))
        input('Press Enter for å fortsette ellr Ctrl-C for å avbryte.')
    return age_groups, labels




