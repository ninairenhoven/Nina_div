import pandas as pd
import os
from pathlib import Path
from tkinter.filedialog import askopenfilename, asksaveasfilename, askdirectory
import pyreadstat
import re

path_user = Path.home()
path_gptw = path_user.joinpath('Opinion AS\Opinion SharePoint - Great Place To Work')
#path_data = path_gptw.joinpath('2024\Europeisk Trust Index/03 Data/01 Top line')
path_data = path_gptw.joinpath('2024\Europeisk Trust Index/03 Data/')


country_codes_file = path_user.joinpath('Opinion AS/Opinion SharePoint - Avinor RVU og ASQ/Rapportering/Syntax/oppslagsdata/countries_alpha2_alpha3_english_labels.csv')
temp = pd.read_csv(country_codes_file, encoding='ISO8859-15')
country_alpha2 = temp.set_index('Label')['alpha-2']



spss_file = askopenfilename(initialdir=path_data)

df, meta = pyreadstat.read_sav(spss_file)
var_labels = pd.Series(meta.column_names_to_labels)
value_labels = pd.Series(meta.variable_value_labels)

df = df.set_index('unik_ID')

statements = {
    'credibility' : [
        'Q009018r18',
        'Q001008r6',
        'Q001008r7',
        'Q009018r13',
        'Q038049r43',
        'Q050061r55',
        'Q019028r24',
        'Q019028r20',
        'Q019028r25',
        'Q019028r19',
        'Q029037r31',
        'Q029037r34',
        'Q038049r39',
        'Q038049r46',
        'Q050061r58'
        ],
    'respect' : [
        'Q009018r15',
        'Q019028r21',
        'Q001008r8',
        'Q001008r1',
        'Q009018r9',
        'Q009018r14',
        'Q050061r59',
        'Q001008r2',
        'Q019028r26',
        'Q029037r35',
        'Q050061r51',
        'Q038049r41',
        'Q038049r47',
        'Q038049r45'
        ],
    'fairness' : [
        'Q019028r27',
        'Q029037r32',
        'Q029037r36',
        'Q038049r42',
        'Q038049r48',
        'Q038049r44',
        'Q009018r10',
        'Q009018r17',
        'Q001008r3',
        'Q050061r50',
        'Q019028r28',
        'Q019028r22',
        'Q038049r40'
    ],
    'pride': [
        'Q038049r49',
        'Q029037r37',
        'Q029037r29',
        'Q019028r23',
        'Q050061r56',
        'Q050061r57',
        'Q009018r16',
        'Q001008r4',
        'Q050061r60',
        'Q050061r52',
        'Q009018r11',
    ],
    'cameraderie':[
        'Q001008r5',
        'Q050061r54',
        'Q050061r53',
        'Q009018r12',
        'Q029037r30',
        'Q038049r38',
        'Q029037r33',
    ],
    'overall_satisfaction':[
        'Q050061r61'
    ]
} 

other_5p_statements = ['Q062063r62', 'Q062063r63', 'Q067069r67',
       'Q067069r68', 'Q067069r69', 'Q074076r74', 'Q074076r75', 'Q074076r76']



# Code to Top 2

std_statements = [x for v in statements.values() for x in v] 
all_5p_statements = std_statements + other_5p_statements

top2_mapping = {1:0,2:0,3:0,4:1,5:1}

df2 = df[all_5p_statements].replace(top2_mapping)

for key, varlist in statements.items():
    df2[key] = df2[varlist].mean(axis=1)*100

df2['TI'] = df2[std_statements].mean(axis=1)*100

qnumbers = pd.Series(all_5p_statements).to_frame(name='Var_name')
qnumbers['nr'] = qnumbers['Var_name'].str.split('r',expand=True)[1].astype(int)
qnumbers = qnumbers.set_index('Var_name')
qnumbers['new_name'] = qnumbers['nr'].apply(lambda x:'Q{:02}_top2'.format(x))
rename_variables = qnumbers['new_name']


var_labels['credibility'] = 'Credibility'
var_labels['respect'] = 'Respect'
var_labels['fairness'] = 'Fairness'
var_labels['pride'] = 'Pride'
var_labels['cameraderie'] = 'Cameraderie'
var_labels['overall_satisfaction'] = 'Overall Satisfaction'
var_labels['TI'] = 'Trust Index'



extra_questions = [
    'Q064066r64', 
    'Q064066r65', 
    'Q064066r66', 
    'Q070', 
    'Q071', 
    'Q072', 
    'Q073r1', 
    'Q073r2', 
    'Q073r3', 
    'Q073r4', 
    'Q073r5', 
    'Q073r6', 
    'Q073r7', 
    'Q073r8', 
    'Q073r9', 
    'Q073r10', 
    'Q077', 
    'Q078']



# COMBINE REGIONS FOR ALL COUNTRIES


region_variables = [
'NO_landsdel2024',
'SE_nuts2',
'DK_region',
'FI_county',
'DE_ImageMapGermany',
'FR_UDA5',
'IT_h_Area',
'PL_region',
'NL_region',
'IE_region',
'AT_region',
'GB_UK_region5',
'ES_region_spain',
'PT_region_port',
'BE_region',
'GR_region_Greece',
'CH_nuts2',
'TR_region_turkey',
'IL_region_isreal',
'CY_district',
'LU_region']




# Create unique values for all regions in all countries
temp_regions = df[region_variables].add(df['dcountry']*100,axis='index')
temp_regions.columns = temp_regions.columns.str[:2]

# Select region from temp_regions based on country code
df['region_combined'] = df.apply(lambda row: temp_regions.loc[row.name, row['country_code']], axis=1)

# Get mapping from country code to country number
country_numbers = pd.Series(value_labels['dcountry']).map(country_alpha2).reset_index().set_index(0).squeeze()

# Combine all region labels
region_labels = value_labels[region_variables].apply(pd.Series).stack().reset_index()
region_labels.columns = ['Variable','Value','Label']
region_labels['cc'] = region_labels['Variable'].str[:2]
region_labels['country_nr'] = region_labels['cc'].map(country_numbers)
region_labels['New_value'] = region_labels['Value']+region_labels['country_nr']*100

value_labels['region_combined'] = region_labels.set_index('New_value')['Label'].to_dict()
var_labels['region_combined'] = 'Region (combined)'






# CALCULATE FLAT WEIGHT (Equal contribution from all countries)

country_counts = df.groupby('dcountry').size()
country_weight = 1000/country_counts
df['flat_weight'] = df['dcountry'].map(country_weight)
var_labels['flat_weight'] = 'Flat weight (equal contribution from all countries)'



# OUTPUT DATA

output_data = df2.copy()
output_data = output_data.rename(columns=rename_variables).reset_index()
output_var_labels = var_labels[df2.columns].rename(rename_variables).to_dict()


#output_data = pd.concat([df2,df[['region_combined','flat_weight']]],axis=1).reset_index()


output_file = Path(spss_file).stem + '_calculations.sav'
output_file = asksaveasfilename(initialdir=path_data, initialfile=output_file)

pyreadstat.write_sav(
    output_data, 
    output_file,
    column_labels=output_var_labels, 
    variable_value_labels=value_labels.to_dict()
)





















ISO8859_15_CHAR_MAPPING= {
    u"\u2019": u"'",
    u"`": u"'",
    u"\u2013": "-",
    }
translate_mapping = {ord(k):ord(v) for k,v in ISO8859_15_CHAR_MAPPING.items()}


# Clean value labels
#original_valuelabels = valuelabels.copy()
temp = value_labels.apply(pd.Series).sort_index(axis=1)
temp = temp.stack()
temp = temp.apply(lambda s: s.translate(translate_mapping))
temp = temp.str.replace("€",'EUR ')
temp[temp.str.startswith('NO TO:')]="Not selected"
valuelabels_stacked = temp

valuelabels = pd.Series({k: v[k].to_dict() for k, v in temp.groupby(level=0, sort=False)})
#valuelabels = valuelabels.loc[original_valuelabels.index]

# Clean Variable labels
var_labels = var_labels.fillna('').apply(lambda s: s.translate(translate_mapping))






###################################3

melted_df = df.melt(id_vars=['dcountry', 'Vekt_europe'], value_vars=cols, 
                    var_name='question', value_name='answer')

grouped = melted_df.groupby(['dcountry', 'question', 'answer'])['Vekt_europe'].sum().reset_index()
melted_df.groupby(['dcountry', 'question'])['answer'].value_counts(normalize=True, sort=False)
melted_df.groupby(['dcountry', 'question'])['answer'].value_counts()


############################################################################################