import sys, os
import numpy as np
import pandas as pd
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename

from pathlib import Path

path_user = Path.home()
path = path_user.joinpath('Opinion AS/')

root = tkinter.Tk()
root.withdraw()

file = askopenfilename(initialdir=path)

file = 'C:/Users/NinaIrenHoven/Opinion AS/Opinion SharePoint - Team kvant/Crunch/Publicis API testing/Table Endpoint Export.json'
data = pd.read_json(file)

metadata = data['metadata']
metadata = metadata.apply(pd.Series)
metadata = metadata.reset_index().set_index('alias')

var_names_descriptions = metadata[['name','description']].copy()

subref = metadata['subreferences'].dropna()

subref_stacked = subref.apply(pd.Series).stack().apply(pd.Series)
subref_stacked.index = subref_stacked.index.set_names(['array_alias', 'nr'])

subvars = subref_stacked.reset_index().set_index('alias')
subvar_names_descriptions = subvars[['array_alias', 'name', 'description']]

all_vars_metadata = pd.concat([var_names_descriptions, subvar_names_descriptions])
all_vars_metadata.to_clipboard()