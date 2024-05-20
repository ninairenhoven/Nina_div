import pandas as pd
import numpy as np
from pathlib import Path


path_user = Path.home()
path = path_user.joinpath('OneDrive - Opinion AS\Documents')
file = path.joinpath('Valgsett_Total.xlsx')

responses = pd.read_excel(file, sheet_name='Responses')
design = pd.read_excel(file, sheet_name='Design')

responses = responses.rename(columns={'sys_RespNum':'Respondent'})
responses.columns = responses.columns.str.replace('CBC_Random',"")
responses = responses.set_index('Respondent')

# Legg til nummer 1-24 innenfor hver versjon
design['nr'] = design.groupby('Version').cumcount()+1
design['task_concept'] = design[['Task','Concept']].astype(str).agg('_'.join, axis=1)

df = pd.concat([responses['Version']]*24, axis=0).to_frame(name='Version').sort_index()
task_concept = ["{}_{}".format(t,c) for t in np.arange(8)+1 for c in np.arange(3)+1]
# ['1_1', '1_2', '1_3', '2_1', '2_2', '2_3' ... '8_1', '8_2', '8_3']
df['task_concept'] = task_concept*responses.index.size


# Koble respondent til riktig design
df1 = df.reset_index().merge(design, how='inner', on=['Version','task_concept'])
df1 = df1.sort_values(['Respondent','task_concept'])
df1 = df1.drop(columns='task_concept')
df1.to_clipboard()


# Sortere svarene til tasker i separate rader
df2 = responses.drop(columns='Version')
df2.columns = df2.columns.str.split('_',expand=True).rename(['Task','Answer'])
df2 = df2.stack(level='Task', future_stack=True)


# Gjør om best og worst til dummies (3 rader med 0/1 )
bestworst = pd.get_dummies(df2, columns=['b','w']).astype(int).drop(columns='none')
bestworst.columns = bestworst.columns.str.split('_',expand=True).rename(['','Concept'])
bestworst = bestworst.stack(future_stack=True)


# For best-alternativet: Legg inn om man faktisk ville valgt det
mask = bestworst['b']==1
wouldchoose = df2['none']
bestworst.loc[mask,'wouldchoose'] = wouldchoose


# Merge med df1
bestworst = bestworst.reset_index()
bestworst[['Task','Concept']] = bestworst[['Task','Concept']].astype(int)
df1 = df1.merge(bestworst, how='outer', on=['Respondent','Task','Concept'])

df1 = df1.rename(columns={'b':'Best','w':'Worst'})
df1.to_clipboard()