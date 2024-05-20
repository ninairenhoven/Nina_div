import pandas as pd
import numpy as np
import pyreadstat

spss_ruter = 'C:/Users/NinaIrenHoven/Opinion AS/Opinion SharePoint - RVU/Tidsserierprosjekt 2023/Del 2 Sammenligning med Ruter/Ruter_RVU_Total_raadata_uten_person_geo.sav'

(_, meta) = pyreadstat.read_sav(spss_ruter, metadataonly=True)
vars = meta.column_names
hvordan_reiste_vars = [v for v in vars if v.startswith('Ahvordanreiste')]
usecols = ['respid','AstartdatoF1','vekt'] + hvordan_reiste_vars

(df, meta) = pyreadstat.read_sav(spss_ruter, usecols=usecols)
df = df.set_index('respid')

df['Year'] = pd.to_datetime(df['AstartdatoF1'], format='%Y%m%d').dt.year
df['Month'] = pd.to_datetime(df['AstartdatoF1'], format='%Y%m%d').dt.month

value_labels = meta.variable_value_labels
labels = value_labels[hvordan_reiste_vars[0]]


data = df[hvordan_reiste_vars]
data.columns = data.columns.str.replace('Ahvordanreiste_trans_','').str.replace('N1','')
split_cols = data.columns.str.extract(r'(\d{1,2})([a-zA-Z])').rename(columns={0:'Hel',1:'Del'})
split_cols['Hel'] = split_cols['Hel'].astype(int)

data.columns =  pd.MultiIndex.from_frame(split_cols)

# Behold bare 8 første helreiser (for sammenligning med SVV)
data1 = data[range(1,9)]

# FINN TRANSPORTMIDLER BRUKT PÅ ALLE DELREISER TOTALT
data2 = data1.stack(level='Hel').stack()

counts = data2.groupby(level='respid').value_counts()
counts = counts.unstack()
counts = counts.reindex(data.index).fillna(0)
brukt_transportmiddel = (counts>0).astype(int)
