import numpy as np
import pandas as pd
import os
from pathlib import Path
from tkinter.filedialog import askopenfilename, askopenfilenames, asksaveasfilename

user_path = Path.home()
sharepoint_path = user_path.joinpath('Opinion AS')
files = askopenfilenames(title='Velg fil(er)', initialdir=sharepoint_path)
path = Path(files[0]).parent

files = askopenfilenames(title='Velg fil(er)', initialdir=path)



def combine_files(files, header=0, examine=None):
    """
    Leser inn liste av filer - csv eller excel
    Sjekker at kolonneheadere samsvarer
    Legger filnavn inn i kolonne "File"
    Slår sammen data
    """
    df = pd.DataFrame()
    suffix = Path(files[0]).suffix
    for file in files:
        filename = Path(file).name
        print('\nLeser fil:')
        print(filename)
        if suffix == ".csv":
            newdata = pd.read_csv(file, header=header, encoding='ISO8859-15')
        elif suffix == ".xlsx":
            newdata = pd.read_excel(file, header=header)
        else:
            print('Kan bare lese .xlsx eller .csv')
            # Skip to next iteration
            continue
            #newdata = pd.DataFrame()
        newdata['File'] = filename
        print(newdata)
        if examine:
            print(newdata[examine].value_counts())
        if len(df) > 0:
            if not(newdata.columns.equals(df.columns)):
                print('\nADVARSEL:\n'+filename)
                print(newdata.columns)
                print("Kombinert data:")
                print(df.columns)
        df = pd.concat([df,newdata])
    if examine:
        print(df.groupby('File')[examine].value_counts())
    return df


df = combine_files(files, header=8, examine='Måned')