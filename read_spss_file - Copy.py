import pandas as pd
import numpy as np
import pyreadstat
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename
from pathlib import Path

path_user = Path.home()
path = path_user.joinpath('Opinion AS/')
path_downloads = path_user.joinpath('Downloads')
path_lokal = path_user.joinpath('Documents/RVU_LOKAL')


root = tkinter.Tk()
root.withdraw()


spss_file = askopenfilename(initialdir=path_lokal)

(df, meta) = pyreadstat.read_sav(spss_file)

vlabels = meta.variable_value_labels
clabels = meta.column_names_to_labels 

####################################
print(df)

clabels = pd.Series(clabels)

####################################



file1 = 'C:/Users/NinaIrenHoven/Documents/RVU_LOKAL/ODS TEST/common_data_walr_q1_2.zsav'
file2 = 'C:/Users/NinaIrenHoven/Documents/RVU_LOKAL/ODS COMPLETE/svv_rvu-common_weighted-19.02.2026.zsav'

(df1, meta1) = pyreadstat.read_sav(file1)
(df2, meta2) = pyreadstat.read_sav(file2)

clabels1 = meta1.column_names_to_labels
clabels2 = meta2.column_names_to_labels
"""
x1 = clabels1.filter(regex='TRANSPORTMIDDEL_.{1,2}$').str.replace('\n','')
x2 = clabels2.filter(regex='TRANSPORTMIDDEL_.{1,2}$').str.replace('\n','')

y1 = x1.str.split('?').str[1].str.strip()
y2 = x2.str.split('?').str[1].str.strip()"""

def get_transportmiddel(clabels):
    x = pd.Series(clabels).filter(regex='TRANSPORTMIDDEL_.{1,2}$')
    x = x.str.replace('\n','')
    x = x.str.split('?').str[1]
    x = x.str.strip()
    return x

x1 = get_transportmiddel(clabels1)
x2 = get_transportmiddel(clabels2)


#####################################3

file = path_downloads.joinpath('ONB165564_260427_Unicode_Opinion_ny.sav')

(df, meta) = pyreadstat.read_sav(file)
clabels = meta.column_names_to_labels
vlabels = meta.variable_value_labels

hh_income = df['household_income']
vlabels['household_income']
df['household_income'].value_counts(dropna=False).sort_index()

midpoints = {
    1.0:  50000,
    2.0:  150000,
    3.0:  250000,
    4.0:  350000,
    5.0:  450000,
    6.0:  550000,
    7.0:  650000,
    8.0:  750000,
    9.0:  850000,
    10.0: 950000,
    11.0: 1050000,
    17.0: 1200000,
    18.0: 1400000,
    19.0: 1600000,
    20.0: 1800000,
    21.0: 2000000,
    22.0: 2100000,
    90.0: None,   # Vil ikke svare
    99.0: None,   # Vet ikke
}

hh_income = df['household_income'].map(midpoints)
hh_size = df['household_size'].replace(90,np.nan)
count_children = df['household_children_u18'].replace(90, 1)-1

count_children[hh_size==1] = 0
count_children[hh_size.isna()] = np.nan

hh_size[hh_size==count_children] = np.nan

count_adults = hh_size - count_children.fillna(0)
count_adults.name = 'Adults'





"""
4) Beregne forbruksenheter. Her skal første voksne i husstanden telle 1 og påfølgende voksne telle 0,5. 
Barn under 18 skal telle 0,3. Hvis antall i husstanden er det samme som barn under 18 er det satt til missing.
"""

hh_units = 1 + (count_adults-1)*0.5 + count_children*0.3
income_eq = (hh_income/hh_units)

data = pd.concat([hh_income,hh_size,count_children, count_adults,hh_units,income_eq], axis=1)


income_eq.describe().round(0)




df['hh_size'] = hh_size
df['antall_barn'] = antall_barn

pd.concat([hh_income, hh_size, count_children, count_adults, hh_units], axis=1).to_clipboard()

hh_units[hh_size==1]