import sys, os
import numpy as np
import pandas as pd
import tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename

os.add_dll_directory(r'C:\Users\NinaIrenHoven\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\LocalCache\local-packages\Lib\site-packages\pyreadstat')
import pyreadstat

sys.path.append(r"C:/Users/NinaIrenHoven/src/lib")
# Force reload of python modules
# import importlib
# import  pandas_utils
# importlib.reload(pandas_utils)
# from pandas_utils import meta_to_df

path = 'C:/Users/NinaIrenHoven/Dropbox (Opinion AS)/Opinion Felles/01 kunder og prosjekter/A/Avinor/RVU og ASQ/Rapportering/JSON/RVU Jan 2020/'

json_files_periodic = {
    'Response': 'json_2020_Jan_Response_1.json',
    'Interview': 'json_2020_Jan_Interview_1.json',
    'Filter': 'json_2020_Jan_Filter_1.json',
    'ResponseOption': 'json_2020_Jan_ResponseOption_partial.json',
}

json_files_static = {
    'Question': 'json_Question.json',
    'QuestionGroup': 'json_QuestionGroup.json',
    'QuestionType': 'json_QuestionType.json',
    'ResponseOption': 'json_ResponseOption.json',
}


def read_json_query_data(key, file):
    json = pd.read_json(file)
    print(json.shape)
    query_data = json['QueryData']
    df = pd.DataFrame(list(query_data))
    key_cols = df.columns[df.columns.str.endswith('Key')]
    df[key_cols] = df[key_cols].astype(int)
    primary_key = key+'Key'
    if primary_key in df.columns:
        df = df.set_index(primary_key)
        df = df.sort_index()
    return(df)


json_periodic = {}
json_static = {}

for key, filename in json_files_periodic.items():
    print()
    print('{}: {}'.format(key, filename))
    file = path + filename
    df = read_json_query_data(key, file)
    print(df)
    json_periodic[key] = df

for key, filename in json_files_static.items():
    print()
    print('{}: {}'.format(key, filename))
    file = path + filename
    df = read_json_query_data(key, file)
    print(df)
    json_static[key] = df


# Save json data to variables
response = json_periodic['Response'].copy()
interview = json_periodic['Interview'].copy()
filter = json_periodic['Filter'].copy()
resp_opt_part = json_periodic['ResponseOption'].copy()

questions = json_static['Question'].copy()
q_group = json_static['QuestionGroup'].copy()
q_type = json_static['QuestionType'].copy()
resp_opt = json_static['ResponseOption'].copy()


# Get response options per question
resp_per_q = resp_opt.groupby('QuestionKey')['ResponseOption'].agg(['count', list])
resp_per_q.columns = 'resp_opt_' + resp_per_q.columns
resp_per_q['resp_opt_list'] = resp_per_q['resp_opt_list'].apply(lambda x:x[0:10])
questions = questions.join(resp_per_q, how='outer')


resp_opt['tuple'] = list(zip(resp_opt.index, resp_opt['ResponseOption']))
temp_resp_opt = resp_opt.reset_index().set_index('ResponseOptionValue')
temp_resp_opt['ResponseOption'] = temp_resp_opt['ResponseOption'].str.lower()

resp_opt_dicts = temp_resp_opt.groupby('QuestionKey').apply(lambda g: g['ResponseOption'].to_dict())
resp_opt_value_to_key = temp_resp_opt.groupby('QuestionKey').apply(lambda g: g['ResponseOptionKey'].to_dict())




# Maps to variables from sav-file meta
spss_questions = meta_df.set_index('name', drop=False)
spss_questions.columns =  'spss_'+ spss_questions.columns
spss_questions.index = spss_questions.index.str.lower()
questions = questions.join(spss_questions, on=questions['QuestionId'].str.lower(), how='outer')

questions.to_csv('questions_json.csv', encoding='ISO-8859-15', errors='replace')

# Number of non-empty cells per column
response.replace('', np.nan).count()

# Number of items per InterviewKey
response['InterviewKey'].value_counts()
