import pandas as pd
from pathlib import Path
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename
import pyreadstat

user_path = Path.home()
path = user_path.joinpath("Downloads")
file = path.joinpath("data.csv")

data = pd.read_csv(file, sep=";")
data = data.set_index('panelist_id')

data2 = pd.get_dummies(data['name']).astype(int)
data2 = data2.groupby(level=0).max()
data2['Antall eksponeringer'] = data2.sum(axis=1)
data2['Flereksponering'] = (data2['Antall eksponeringer']>1).astype(int)

output_csv = asksaveasfilename(initialdir=path)
data2.to_csv(output_csv)

