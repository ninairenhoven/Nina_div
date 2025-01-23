import pandas as pd
import numpy as np
import pyreadstat
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename
from pathlib import Path

path_user = Path.home()
path = path_user.joinpath('OneDrive - Opinion AS/Documents/')

#path = path_user.joinpath('Opinion AS/')

root = tkinter.Tk()
root.withdraw()

spss_file = askopenfilename(initialdir=path)
spss_file = 'C:/Users/NinaIrenHoven/OneDrive - Opinion AS/Documents/Amedia_Lokalavis_BJ_kun de aktuelle var.sav'

path = Path(spss_file).parent
print('\Path:')
print(path)

print('\nLeser fil: ')
print(spss_file)
(df0, meta) = pyreadstat.read_sav(spss_file)

print('\nDataFrame df:\n')
print(df0)

value_labels = pd.Series(meta.variable_value_labels)
col_labels = pd.Series(meta.column_names_to_labels )

print('\nvalue_labels: \n')
print(pd.Series(value_labels))

print('\ncol_labels: \n')
print(pd.Series(col_labels))



####################################

df0 = df0.set_index('sys_RespNum')

#Fjerne tomme rader
df = df0.replace('',np.nan).dropna(how='all')

reads_newsp = df.filter(regex='^CustomDropdown')
reads_newsp.columns = reads_newsp.columns.str.split('_').str[1].astype(int)

reads_newsp_vlabels = value_labels.filter(regex='^CustomDropdown')
reads_newsp_vlabels.index = reads_newsp_vlabels.index.str.split('_').str[1].astype(int)
newsp_labels = reads_newsp_vlabels.apply(pd.Series).squeeze()

#mest_leste = leser.columns[leser.sum()>100].astype(int).to_list()
readers =  reads_newsp.sum().sort_values(ascending=False).to_frame('Count')
readers['Newspaper'] = readers.index.map(newsp_labels)

# Behold topp 10
use_newspapers = readers['Count'].sort_values(ascending=False).iloc[0:10].index.astype(int).to_list()

# Antall lesere (topp 10)
print(readers.loc[use_newspapers])

# Hvilke aviser har man svart for i Q11, Q12, Q13
newsp123 = df.filter(regex='^RandomNewspaperConList').copy()

newsp123_labels = pd.Series(value_labels[newsp123.columns[0]])
temp = newsp123_labels.str.extract('<b>(.*)</b>').squeeze()
newsp123_labels = temp.fillna(newsp123_labels)

print('Sjekker samsvar i label:')
print(newsp123_labels.compare(newsp_labels))

# Columns ['answer_1', 'answer_2', 'answer_3']
newsp123.columns = 'answer_'+newsp123.columns.str.split('_').str[1]

# Legg inn "Den jeg leser mest"
newsp123['answer_1'] = newsp123['answer_1'].fillna(997)
newsp123_labels[997] = 'Den jeg leser mest (har ikke valgt noen i lista)'


print(newsp123.map(lambda x: newsp123_labels[x] if ~np.isnan(x) else np.nan))

# Behold de mest leste, erstatt øvrige med 999 (behold nan)
newsp123_selected = newsp123.map(lambda x: x if (pd.isna(x) or x in use_newspapers or x==997) else 999)

# Antall svar per avis:
newsp123_selected.stack().value_counts().rename(newsp123_labels)


cols_tilgang ={
    'Q11':'answer_1',
    'Q11b':'answer_2',
    'Q11c':'answer_3'
}

cols_abb ={
    'Q12':'answer_1',
    'Q12b':'answer_2',
    'Q12c':'answer_3'
}
cols_hvorlenge ={
    'Q13':'answer_1',
    'Q13b':'answer_2',
    'Q13c':'answer_3'
}

tilgang = df[cols_tilgang.keys()].rename(columns=cols_tilgang)
abonnement = df[cols_abb.keys()].rename(columns=cols_abb)
hvorlenge = df[cols_hvorlenge.keys()].rename(columns=cols_hvorlenge)


def restructure_answers(answers, newspaper_in_answer):
    # Sett sammen data for svar og hvilken avis det er svart for
    data = pd.concat([answers, newspaper_in_answer], axis=1, keys=['Answer','Newspaper'])
    print('\nData:')
    print(data)
    # Stack data - legg de 3 svarene under hverandre. 
    sdata = data.stack(future_stack=True)
    # Pivoter data - lag én kolonne per avis
    pdata = sdata.pivot(columns='Newspaper')
    pdata.columns = pdata.columns.droplevel(0)
    pdata = pdata.drop(columns=[np.nan,999])
    print('\nPivotert:')
    print(pdata)
    antall_svar = pdata.groupby(level=0).count()
    if antall_svar.max().max() > 1:
        print('ADVARSEL >1 svar per avis/respondent')
        print(antall_svar.stack().value_counts())
    result = pdata.groupby(level=0).max()
    print('\nResultat:')
    print(result)
    return result



tilgang_total = restructure_answers(tilgang, newsp123_selected)
abonnement_total = restructure_answers(abonnement, newsp123_selected)
hvorlenge_total = restructure_answers(hvorlenge, newsp123_selected)

# Output data



# Kolonnenavn og labels på reads_newsp
reads_newsp_out = reads_newsp.rename(columns = lambda x: 'Q10_{}'.format(x))
reads_newsp_vlabels_out = reads_newsp_vlabels.rename(lambda x: 'Q10_{}'.format(x))
reads_newsp_col_labels = newsp_labels.rename(lambda x: 'Q10_{}'.format(x))
reads_newsp_col_labels = reads_newsp_col_labels + " - Hvilken/hvilke av disse lokalavisene leser du?"


# Genererer column labels til tilgang, abonnement, hvorlenge
# "Avisnavn - Spørsmålstekst"
tilgang_col_labels = newsp123_labels[tilgang_total.columns] + ' - Hvilken tilgang har du til ...'
abonnement_col_labels = newsp123_labels[tilgang_total.columns] + ' - Hvilken type abonnement har du på...'
hvorlenge_col_labels = newsp123_labels[tilgang_total.columns] + ' - Hvor lenge har du abonnert på ...'


# Renavner variabler
tilgang_total = tilgang_total.rename(columns = lambda x: 'Q11_{:.0f}'.format(x))
tilgang_col_labels = tilgang_col_labels.rename(lambda x: 'Q11_{:.0f}'.format(x))

abonnement_total = abonnement_total.rename(columns = lambda x: 'Q12_{:.0f}'.format(x))
abonnement_col_labels = abonnement_col_labels.rename(lambda x: 'Q12_{:.0f}'.format(x))

hvorlenge_total = hvorlenge_total.rename(columns = lambda x: 'Q13_{:.0f}'.format(x))
hvorlenge_col_labels = hvorlenge_col_labels.rename(lambda x: 'Q13_{:.0f}'.format(x))


# Henter value labels fra input data
d_tilgang = value_labels[list(cols_tilgang.keys())[0]]
d_abonnement = value_labels[list(cols_abb.keys())[0]]
d_hvorlenge = value_labels[list(cols_hvorlenge.keys())[0]]

# Genererer value labels for output-data
tilgang_vlabels = {c:d_tilgang for c in tilgang_total.columns}
abonnement_vlabels = {c:d_abonnement for c in abonnement_total.columns}
hvorlenge_vlabels =  {c:d_hvorlenge for c in hvorlenge_total.columns}



output_df = pd.concat([
    reads_newsp_out,
    tilgang_total,
    abonnement_total,
    hvorlenge_total],
    axis=1
    )

output_df = output_df.reset_index()

output_vlabels = reads_newsp_vlabels_out.to_dict() | tilgang_vlabels | abonnement_vlabels | hvorlenge_vlabels

output_col_labels = pd.concat([
    reads_newsp_col_labels,
    tilgang_col_labels,
    abonnement_col_labels,
    hvorlenge_col_labels]
    ).to_dict()


output_file = spss_file.replace('.sav','_OMSTRUKTURERT.sav')

formats = {c:'F4.0' for c in output_df.columns}

pyreadstat.write_sav(
    output_df,
    output_file,
    variable_value_labels=output_vlabels,
    column_labels = output_col_labels,
    variable_format  = formats
)