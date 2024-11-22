import pandas as pd
import numpy as np
import datetime as dt
import sys, os
from pathlib import Path
import pyreadstat

import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename

pd.set_option('display.max_colwidth', 100)

def keep_variables(df, keep_vars):
    keep = [v for v in df.columns if v in keep_vars]
    return df[keep]


def stack_value_labels(labels):
    return pd.Series(labels).apply(pd.Series).stack()
    
    
def compare_value_labels(labels, master_labels, ignore_empty=True):
    labels = pd.Series(labels)
    master_labels = pd.Series(master_labels)
    # ignore_empty -> sammenligner kun variabler som har labels i begge datasett
    # ignore_vars -> ignorerer spesifikke variabler
    if ignore_empty:
        common_vars = [v for v in master_labels.index if v in labels.index]
        master_labels = master_labels.loc[common_vars]
    # Omstrukturer slik at verdier ligger vertikalt
    labels = stack_value_labels(labels)
    master_labels = stack_value_labels(master_labels)
    # Sammenligner
    labels = labels.reindex_like(master_labels)
    comparison = labels.compare(master_labels)
    comparison = comparison.rename(columns={'self':'NEW','other':'MASTER'})
    if len(comparison.index)==0:
        print('Ingen forskjell i value labels')
    else:
        print('Forskjell i Value labels:')
        print(comparison)
    input('Press Enter to continue')
    return comparison


def get_available_value(existing_values):
    # Hvis siste eksisterende verdi er høy, fjernes øye verdier fra lista
    if existing_values[-1] > 90:
        # Skreller bort 97,98,99, 998,999, 9998, 9999
        temp_values = [x for x in existing_values if x < existing_values[-1]-10]
    else:
        temp_values = existing_values
    #
    # Velger laveste ledige verdi etter at 99 etc. er tatt bort
    try_value = max(temp_values)+1
    #
    # Ekstra sjekk for å sikre at foreslått verdi faktisk er ledig
    while try_value in existing_values:
        try_value = try_value+1
    #
    available_value = try_value
    return available_value
        



def resolve_value_labels(new_data, new_labels, master_labels):
    #
    master_labels = pd.Series(master_labels)
    master_labels_stacked = stack_value_labels(master_labels)
    new_labels_stacked = stack_value_labels(new_labels)
    #
    new_labels_stacked = new_labels_stacked.reindex_like(master_labels_stacked)
    comparison = new_labels_stacked.compare(master_labels_stacked)
    comparison = comparison.rename(columns={'self':'NEW','other':'MASTER'})
    #
    c = comparison.dropna(subset='NEW')
    c = c.reset_index().rename(columns={'level_1':'Value', 'level_0':'Var'})
    print('\nValue label mismatch:')
    print(c)
    c['item'] = c[['Value','NEW','MASTER']].agg(tuple, axis=1)
    g = c.groupby('item')['Var'].agg(list)
    #
    additional_labels = pd.Series()
    new_data_resolved = new_data.copy()
    #
    for item in g.index:
        value, new_data_label, master_label = item
        vars = g[item]
        print('\nIssue in variables:\n\t'+ '\n\t'.join(vars))
        print('Value: {}\nNew data label: {}\nMaster label:   {}'.format(value, new_data_label, master_label))
        inp = 0
        while inp not in ['1','2']:
            print('\n[1] Ignore difference, keep master label\n[2] Recode new data and generate new value/label pair')
            inp = input('\nSelection: ')
        if inp=='1':
            pass
        if inp=='2':
            print('Existing Master labels for variable set:')
            existing_master_labels = master_labels_stacked[vars].unstack(level=1).drop_duplicates().T
            print(existing_master_labels)
            # Find available data value
            available_value = get_available_value(existing_master_labels.index)
            #
            recode = {value: available_value}
            print('Recoding new data: {} -> {}'.format(value, available_value))
            new_data_resolved[vars] = new_data_resolved[vars].replace(recode)
            #
            temp = {available_value:new_data_label}
            add_labels = pd.Series(index=vars, data=[temp]*len(vars))
            print('Add value labels:')
            print(add_labels)
            additional_labels = pd.concat([additional_labels, add_labels])
    #
    # Add generated labels to master labels
    master_labels_resolved = master_labels.copy()
    for varname, addlabel in additional_labels.items():
        master_labels_resolved[varname] = master_labels[varname]|addlabel
    return new_data_resolved, master_labels_resolved



def compare_column_labels(labels, master_labels, ignore_case=False, ignore_empty=True):
    labels = pd.Series(labels)
    master_labels = pd.Series(master_labels)
    if ignore_empty:
        common_vars = [v for v in master_labels.index if v in labels.index]
        master_labels = master_labels.loc[common_vars]
    if ignore_case:
        labels = labels.str.lower()
        master_labels = master_labels.str.lower()
    labels = labels.reindex_like(master_labels)
    comparison = labels.compare(master_labels)
    comparison = comparison.rename(columns={'self':'NEW','other':'MASTER'})
    comparison = comparison.stack()
    if len(comparison.index)==0:
        print('Ingen forskjell i column labels')
    else:
        print('Forskjell i column labels:')
        print(comparison)
    input('Press Enter to continue')
    return comparison


def check_waves(df, master, wave_variable, wave_labels={}):
    new_data_waves = df[wave_variable].value_counts().rename(wave_labels)
    master_waves = master[wave_variable].value_counts().sort_index().rename(wave_labels)
    print('\nWaves in Master data:')
    print(master_waves)
    print('\nWaves in new data:')
    print(new_data_waves)
    if new_data_waves.index.size > 1:
        print('\nWARNING: More than one wave in new data')
    if new_data_waves.index in list(master_waves.index):
        print('\nWARNING: New wave exists in Master data')
    input('Press Enter to continue')
    return


def merge_spss_data_main(master_data, master_value_labels, master_column_labels, new_datafile, wave_variable=''):
    # Leser inn nye data
    new_data, new_meta = pyreadstat.read_sav(new_datafile)
    print(new_data)

    new_value_labels = new_meta.variable_value_labels
    new_column_labels = new_meta.column_names_to_labels

    # Finner kolonner som ikke er i begge datasett
    cols_only_master = set(master_data.columns) - set(new_data.columns)
    cols_only_new = set(new_data.columns) - set(master_data.columns)

    if len(cols_only_master)>0:
        print('\nMaster data inneholder {} variabler som ikke finnes i nye data:'.format(len(cols_only_master)))
        print(cols_only_master)

    if len(cols_only_new)>0:
        print('\nNye data inneholder {} variabler som ikke finnes i master:'.format(len(cols_only_new)))
        print(cols_only_new)

    if len(cols_only_master) + len(cols_only_new) > 0:
        inp = input('\nVelg hvilke variabler som skal beholdes? \n\tM: Bare variabler fra Master (Default)\n\tF: Bare felles variabler\n\tA: Alle kolonner\nValg: ')
        if inp.upper() == 'F':
            # Beholder bare kolonner som finnes i begge datasett
            master_data = master_data.drop(columns=cols_only_master)
            new_data = new_data.reindex(columns = master_data.columns)
            # Fjerner labels fra master
            master_value_labels = {k:v for k,v in master_value_labels.items() if k not in cols_only_master}
            master_column_labels = {k:v for k,v in master_column_labels.items() if k not in cols_only_master}

        elif inp.upper() == 'A':
            # Beholder alle kolonner
            all_cols = list(master_data.columns) + list(cols_only_new)
            master_data  = master_data.reindex(columns=all_cols)
            new_data = new_data.reindex(columns=all_cols)
            # Legger inn nye labels i master labels
            master_value_labels.update(new_value_labels)
            master_column_labels.update(new_column_labels)

        else:
            # Beholder kolonner fra Master
            new_data = new_data.reindex(columns = master_data.columns)
    else:
        print('\nAlle variabler finnes i begge datasett.')
            
    print('\nSAMMENLIGNE VALUE LABELS')
    c = compare_value_labels(new_value_labels, master_value_labels, ignore_empty=True)
    new_data, master_value_labels = resolve_value_labels(new_data, new_value_labels, master_value_labels)
    
    print('\nSAMMENLIGNER COLUMN LABELS (SPSS VARIABLE LABELS)')
    c = compare_column_labels(new_column_labels, master_column_labels, ignore_empty=True)

    if wave_variable != '':
        wave_labels = master_value_labels.get(wave_variable, {})
        check_waves(new_data, master_data, wave_variable, wave_labels)
    
    # Slår sammen data
    accumulated_data = pd.concat([master_data, new_data], axis=0)
    print(accumulated_data)

    return {'df':accumulated_data, 'value_labels':master_value_labels, 'column_labels':master_column_labels}





def merge_spss_in_directory(dir='', master='', keep_vars=[]):
    if dir=='':
        sharepoint_path = Path.home().joinpath('Opinion AS')
        dir = tkinter.filedialog.askdirectory(title='Merge alle spss-filer in directory: ', initialdir=sharepoint_path)
    
    dir = Path(dir)
    files = os.listdir(dir)
    files = [f for f in files if f.endswith('.sav')]
    print(dir)
    print('\n'.join(files))

    if master=='':
        inp = input('\nSelect master file? [y/n]: ')
        if inp.upper()=='Y':
            master_file = askopenfilename(initialdir=dir, title='Velg masterfil', filetypes=[('SAV','*.sav')])
            print('\nMaster file:')
            print(master_file)
            files = [f for f in files if f!=Path(master_file).name]
        else:
            master_file = dir.joinpath(files[0])
            print('\nSelecting first file as Master:')
            print(master_file)
            files = files[1:]

    input('Press Enter to merge files')

    master_data, master_meta = pyreadstat.read_sav(master_file)
    master_value_labels = master_meta.variable_value_labels
    master_column_labels = master_meta.column_names_to_labels

    if len(keep_vars)>0:
        master_data = master_data[keep_vars]
        master_value_labels = {k:v for k,v in master_value_labels.items() if k in keep_vars}
        master_column_labels = {k:v for k,v in master_column_labels.items() if k in keep_vars}

    wave_var = input('Hvis aktuelt: skriv inn navn på Wave-variabel (unik per datafil): ')

    acc_data = master_data.copy()
    acc_value_labels = master_value_labels.copy()
    acc_column_labels = master_column_labels.copy()

    for file in files:
        new_file = dir.joinpath(file)
        print(new_file)
        
        d = merge_spss_data_main(acc_data, acc_value_labels, acc_column_labels, new_file, wave_var)
        acc_data = d['df']
        acc_value_labels = d['value_labels']
        acc_column_labels = d['column_labels']
        print('Merged file {} with Master'.format(file))
        if wave_var!='':
            print('Waves in accumulated data:')
            print(acc_data[wave_var].value_counts().sort_index().rename(acc_value_labels.get(wave_var, {})))
        input('Press Enter to continue')
    
    output_file = asksaveasfilename(initialdir=dir, initialfile='merged.sav')
    pyreadstat.write_sav(acc_data, output_file, column_labels=acc_column_labels, variable_value_labels=acc_value_labels.to_dict())
    print('Lagret til fil')
    print(output_file)

    return {'df':acc_data, 'value_labels':acc_value_labels, 'column_labels':acc_column_labels}

##############################

"""

dir = 'C:/Users/NinaIrenHoven/Opinion AS/Opinion SharePoint - ForbrukerMeteret/DATA AKKUMULERT/SPSS-filer/Kodet 2023'
files = [f for f in os.listdir(dir) if f.endswith('.sav')]
file = Path(dir).joinpath(files[0])
master_file = Path(dir).joinpath(files[11])

master_data, master_meta = pyreadstat.read_sav(master_file)
master_value_labels = master_meta.variable_value_labels
master_column_labels = master_meta.column_names_to_labels

# Leser inn nye data
new_data, new_meta = pyreadstat.read_sav(file)
new_value_labels = new_meta.variable_value_labels
new_column_labels = new_meta.column_names_to_labels

var = 'Gxny1r1'
new_data[var].value_counts().sort_index()
new_value_labels[var]

master_data[var].value_counts().sort_index()
master_value_labels[var]

new_data_resolved, master_value_labels_resolved = resolve_value_labels(new_data, new_value_labels, master_value_labels)
new_data_resolved[var].value_counts().sort_index()
master_value_labels_resolved[var]


"""

"""

    today = dt.datetime.now().strftime('%y%m%d')
    output_file = 'CCI_MASTER_{}.sav'.format(today)
    output_file = asksaveasfilename(initialdir=master_file.parent, initialfile=output_file)

    try:
        pyreadstat.write_sav(
            accumulated_data, 
            output_file, 
            column_labels=master_column_labels, 
            variable_value_labels=master_value_labels,
            )
        print('Lagret til {}'.format(output_file))
    except:
        print('Kan ikke lagre til {}'.format(output_file))
"""