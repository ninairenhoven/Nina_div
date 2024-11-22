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

(df, meta) = pyreadstat.read_sav(spss_file)

value_labels = meta.variable_value_labels
var_labels = meta.column_names_to_labels 

####################################
print(df)

