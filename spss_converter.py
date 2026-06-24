import pandas as pd
import numpy as np
import pyreadstat
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename
from pathlib import Path
import json


path_user = Path.home()
path = path_user.joinpath('Opinion AS/')

root = tkinter.Tk()
root.withdraw()



spss_file = askopenfilename(initialdir=path)
spss_file = Path(spss_file)

path = spss_file.parent
print('\Path:')
print(path)

print('\nLeser fil: ')
print(spss_file)


(df, meta) = pyreadstat.read_sav(spss_file)


print('\nDataFrame df:\n')
print(df)

vlabels = meta.variable_value_labels
clabels = meta.column_names_to_labels 
dtypes = meta.original_variable_types


vlabels = {}

print('\nvalue_labels: \n')
print(pd.Series(vlabels))

print('\ncol_labels: \n')
print(pd.Series(clabels))


# ========================================================
# KONVERTER DATOER til string
# ========================================================


def spss_date_to_string(datecol, format='%Y-%m-%d %H:%M:%S'):
    date = pd.to_datetime((datecol/86400)-141428, unit='D')
    date_str = date.dt.strftime(format)
    return date_str


date_cols = [c for c,t in dtypes.items() if t.startswith('DATETIME')]
print(df[date_cols])

for c in date_cols:
    df[c] = spss_date_to_string(df[c])

print(df[date_cols])

# ========================================================
# JSON
# ========================================================

data_json = df.to_json(orient="records", force_ascii=False)

# Metadata (variabelnavn, labels, etc.)
meta_dict = {
    "column_labels": meta.column_names_to_labels ,
    "variable_value_labels": meta.variable_value_labels
}

output_json = spss_file.parent.joinpath(spss_file.stem + '.json')

output = {
    "data": json.loads(data_json),
    "metadata": meta_dict
}

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)


testdf = df.iloc[0:2]
testdf = testdf[list(testdf.columns[0:4])+list(testdf.columns[187:191])]
data_json = testdf.to_json(orient="records", force_ascii=False)


"""
{
  "data": [
      {"record": 1444.0, ...},
      {"record": 1445.0, ...},
      ...
        ],
  "metadata": {
    "column_labels": {...},
    "variable_value_labels": {
      "status": {...},
      "boost": {...},
       ...
      }
  }
}

"""

# ========================================================
# CSV og EXCEL
# ========================================================


# Lag df med labels istf values
df_labels = df.copy()
for k,d in vlabels.items():
    df_labels[k] = df[k].replace(d)


# Forbered column labels og value labels for lagring
clabels_df = pd.Series(clabels).to_frame().reset_index()
clabels_df.columns = ['Column name','Column label']

vlabels_df = pd.Series(vlabels).apply(pd.Series).stack().reset_index()
vlabels_df.columns = ['Column name','Value','Value label']

# Gjør om til heltall dersom verdien er float
vlabels_df['Value'] = vlabels_df['Value'].apply(
    lambda x: int(x) if isinstance(x, float) else x
)


# Lagre til CSV

path = spss_file.parent
stem = spss_file.stem

output_csv_values = path.joinpath(stem + '_values.csv')
output_csv_labels = path.joinpath(stem + '_labels.csv')
output_csv_column_labels = path.joinpath(stem + 'column_labels.csv')
output_csv_value_labels = path.joinpath(stem + 'value_labels.csv')

df.to_csv(output_csv_values, encoding='utf-8')
df_labels.to_csv(output_csv_labels)
clabels_df.to_csv(output_csv_column_labels, encoding='utf-8')
vlabels_df.to_csv(output_csv_value_labels, encoding='utf-8')

# Lagre til Excel

output_excel = path.joinpath(stem + '.xlsx')

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Values", index=False)
    print('Saved data values to excel')
    df_labels.to_excel(writer, sheet_name="Labels", index=False)
    print('Saved data with labels to excel')
    clabels_df.to_excel(writer, sheet_name="Column labels", index=False)
    vlabels_df.to_excel(writer, sheet_name="Value labels", index=False)
    print('Saved column labels and value labels to excel')