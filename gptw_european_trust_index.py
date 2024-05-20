import pandas as pd
import os
from pathlib import Path
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename, askdirectory
import pyreadstat


path_user = Path.home()
path_gptw = path_user.joinpath('Opinion AS\Opinion SharePoint - Great Place To Work')
path_data = path_gptw.joinpath('2024\Europeisk Trust Index/03 Data/01 Top line')


country_codes_file = path_user.joinpath('Opinion AS/Opinion SharePoint - Avinor RVU og ASQ/Rapportering/Syntax/oppslagsdata/countries_alpha2_alpha3_english_labels.csv')
temp = pd.read_csv(country_codes_file, encoding='ISO8859-15')
country_alpha2 = temp.set_index('Label')['alpha-2']

files = [f for f in os.listdir(path_data) if f.endswith('.sav')]

all_data = {}
all_meta = {}

for file in files:
    print(file)
    (df, meta) = pyreadstat.read_sav(path_data.joinpath(file))
    value_labels = meta.variable_value_labels
    country = df['dcountry'].drop_duplicates() #'_'.join(df['dcountry'].map(value_labels['dcountry']).unique())
    print(country.map(value_labels['dcountry']))
    all_data[country.values[0]] = df
    all_meta[country.values[0]] = meta
    input('Press Enter to continue')


merge_vars = [
    'record', 'date', 'status', 'dcountry', 
    'zipcode',
    'Q_LANGUAGE', 'Q_JOB', 'Q_SCREEN', 'Q085', 'Q084', 
    'Q085_group', 'Q_SECTOR', 
    'Q001008r1', 'Q001008r2', 'Q001008r3', 'Q001008r4', 'Q001008r5', 'Q001008r6', 'Q001008r7', 'Q001008r8', 
    'Q009018r9', 'Q009018r10', 'Q009018r11', 'Q009018r12', 'Q009018r13', 'Q009018r14', 'Q009018r15', 'Q009018r16', 'Q009018r17', 'Q009018r18', 
    'Q019028r19', 'Q019028r20', 'Q019028r21', 'Q019028r22', 'Q019028r23', 'Q019028r24', 'Q019028r25', 'Q019028r26', 'Q019028r27', 'Q019028r28', 
    'Q029037r29', 'Q029037r30', 'Q029037r31', 'Q029037r32', 'Q029037r33', 'Q029037r34', 'Q029037r35', 'Q029037r36', 'Q029037r37', 
    'Q038049r38', 'Q038049r39', 'Q038049r40', 'Q038049r41', 'Q038049r42', 'Q038049r43', 'Q038049r44', 'Q038049r45', 'Q038049r46', 'Q038049r47', 'Q038049r48', 'Q038049r49', 
    'Q050061r50', 'Q050061r51', 'Q050061r52', 'Q050061r53', 'Q050061r54', 'Q050061r55', 'Q050061r56', 'Q050061r57', 'Q050061r58', 'Q050061r59', 'Q050061r60', 'Q050061r61', 
    'Q062063r62', 'Q062063r63', 
    'Q064066r64', 'Q064066r65', 'Q064066r66', 
    'Q067069r67', 'Q067069r68', 'Q067069r69', 
    'Q070', 'Q071', 'Q072', 
    'Q073r1', 'Q073r2', 'Q073r3', 'Q073r4', 'Q073r5', 'Q073r6', 'Q073r7', 'Q073r8', 'Q073r9', 'Q073r10', 
    'Q074076r74', 'Q074076r75', 'Q074076r76', 
    'Q077', 'Q078', 'Q079', 'Q080', 'Q081', 'Q082', 'Q083', 'Q086', 
    'qtime']


merge_vars_with_value_labels = [v for v in merge_vars if v not in ['record','date','zipcode','Q_SCREEN','Q085','qtime']]


template_meta = all_meta[list(all_meta.keys())[0]]
template_value_labels = template_meta.variable_value_labels
template_var_labels = template_meta.column_names_to_labels 

template_value_labels = pd.Series(template_value_labels)[merge_vars_with_value_labels]
template_var_labels = pd.Series(template_var_labels)[merge_vars]

country_labels = template_value_labels['dcountry']
country_codes = pd.Series(country_labels).map(country_alpha2)


for key in all_data.keys():
    print(country_labels[key])
    meta = all_meta[key]
    df = all_data[key]
    #
    # Check value labels and variable labels
    this_value_labels = pd.Series(meta.variable_value_labels)[merge_vars_with_value_labels]
    this_var_labels = pd.Series(meta.column_names_to_labels )[merge_vars]
    #
    print('Mismatch value labels:')
    this_value_labels[this_value_labels != template_value_labels]
    print('Mismatch variable labels:')
    this_var_labels[this_var_labels != template_var_labels]
    #
    # Add country label in country variables
    code = country_codes[key]
    country_vars = [v for v in df.columns if v not in merge_vars]
    rename_vars = {v: code+"_"+v for v in country_vars if not(v.startswith(code))}
    # Rename vars in df and meta
    df = df.rename(columns=rename_vars)
    new_val_labels = {rename_vars.get(var, var):labels for var,labels in this_value_labels if var in country_vars}
    new_var_labels = {rename_vars.get(var, var):labels for var,labels in this_var_labels if var in country_vars}



all_age_groups = {}
for key, meta in all_meta.items():
    code = country_codes[key]
    print(code)
    all_age_groups[code]= meta.variable_value_labels.get('age_group',{})



df = pd.DataFrame()