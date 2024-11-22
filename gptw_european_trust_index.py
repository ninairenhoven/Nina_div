import pandas as pd
import os
from pathlib import Path
from tkinter.filedialog import askopenfilename, asksaveasfilename, askdirectory
import pyreadstat
import re

path_user = Path.home()
path_gptw = path_user.joinpath('Opinion AS\Opinion SharePoint - Great Place To Work')
#path_data = path_gptw.joinpath('2024\Europeisk Trust Index/03 Data/01 Top line')
path_data = path_gptw.joinpath('2024\Europeisk Trust Index/03 Data/Per land')


country_codes_file = path_user.joinpath('Opinion AS/Opinion SharePoint - Avinor RVU og ASQ/Rapportering/Syntax/oppslagsdata/countries_alpha2_alpha3_english_labels.csv')
temp = pd.read_csv(country_codes_file, encoding='ISO8859-15')
country_alpha2 = temp.set_index('Label')['alpha-2']

#files = [f for f in os.listdir(path_data) if f.endswith('.sav')]
files = [f for f in os.listdir(path_data) if re.match('(ON.132596.*.sav)',f)]

print('\n'.join(files))

all_data = {}
all_meta = {}
all_files = {}

for file in files:
    print(file)
    (df0, meta) = pyreadstat.read_sav(path_data.joinpath(file))
    valuelabels = meta.variable_value_labels
    country = df0['dcountry'].drop_duplicates().map(valuelabels['dcountry']).map(country_alpha2)
    print(country)
    print(df0)
    all_data[country.values[0]] = df0
    all_meta[country.values[0]] = meta
    all_files[country.values[0]] = file
    input('Press Enter to continue')


merge_vars = [
    'record', 'date', 'status', 'dcountry', 
    'zipcode',
    'Q_LANGUAGE', 'Q_JOB', 'Q_SCREEN', 'Q085', 'Q084', 
    'Q085_group', 'Q_SECTOR', 
    'Q001008r1', 'Q001008r2', 'Q001008r3', 'Q001008r4', 'Q001008r5', 'Q001008r6', 'Q001008r7', 'Q001008r8', 
    'Q009018r9', 'Q009018r10', 'Q009018r11', 'Q009018r12', 'Q009018r13', 'Q009018r14', 'Q009018r15', 'Q009018r16', 'Q009018r17', 'Q009018r18', 
    'Q019028r19', 'Q019028r20', 'Q019028r21', 'Q019028r22', 'Q019028r23', 'Q019028r24', 'Q019028r25', 'Q019028r26', 'Q019028r27', 'Q019028r28', 
    'Q029037r29', 'Q029037r30', 'Q029037r31', 'Q029037r32', 'Q029037r33', 'Q029037r34', 'Q029037r35', 'Q029037r36', 'Q029037r37', 
    'Q038049r38', 'Q038049r39', 'Q038049r40', 'Q038049r41', 'Q038049r42', 'Q038049r43', 'Q038049r44', 'Q038049r45', 'Q038049r46', 'Q038049r47', 'Q038049r48', 'Q038049r49', 
    'Q050061r50', 'Q050061r51', 'Q050061r52', 'Q050061r53', 'Q050061r54', 'Q050061r55', 'Q050061r56', 'Q050061r57', 'Q050061r58', 'Q050061r59', 'Q050061r60', 'Q050061r61', 
    'Q062063r62', 'Q062063r63', 
    'Q064066r64', 'Q064066r65', 'Q064066r66', 
    'Q067069r67', 'Q067069r68', 'Q067069r69', 
    'Q070', 'Q071', 'Q072', 
    'Q073r1', 'Q073r2', 'Q073r3', 'Q073r4', 'Q073r5', 'Q073r6', 'Q073r7', 'Q073r8', 'Q073r9', 'Q073r10', 
    'Q074076r74', 'Q074076r75', 'Q074076r76', 
    'Q077', 'Q078', 'Q079', 'Q080', 'Q081', 'Q082', 'Q083', 'Q086', 
    'qtime']

merge_vars_with_valuelabels = [v for v in merge_vars if v not in ['record','date','zipcode','Q_SCREEN','Q085','qtime']]
drop_vars = ['age_group']

template_meta = all_meta[list(all_meta.keys())[0]]

template_valuelabels = template_meta.variable_value_labels
template_valuelabels = pd.Series(template_valuelabels)[merge_vars_with_valuelabels]

template_var_labels = template_meta.column_names_to_labels 
template_var_labels = pd.Series(template_var_labels)[merge_vars]

country_labels = template_valuelabels['dcountry']
country_codes = pd.Series(country_labels).map(country_alpha2)


# SAMMENLIGNE META OG SLÅ SAMMEN DATA

df = None 
valuelabels = template_valuelabels.copy()
var_labels = template_var_labels.copy()

for key in all_data.keys():
    meta = all_meta[key]
    df1 = all_data[key]
    df1 = df1.drop(columns=drop_vars, errors='ignore')
    print('\n\nCountry: '+key)
    country_name = df1['dcountry'].drop_duplicates().map(valuelabels['dcountry'])[0]
    print(country_name)    
    #
    # Check value labels and variable labels
    this_valuelabels = pd.Series(meta.variable_valuelabels)
    this_var_labels = pd.Series(meta.column_names_to_labels)
    #
    print('\nCompare value labels:')
    test1 = this_valuelabels.reindex(merge_vars_with_valuelabels).compare(template_valuelabels).stack()
    if len(test1.index)>0:
        test1 = test1.apply(pd.Series).stack().unstack(level=1)
        test1.loc[(test1['self'] != test1['other']),'Mismatch'] = 'MISMATCH'
        print(test1.fillna(''))
    print('\nCompare variable labels:')
    test2 = this_var_labels.reindex(merge_vars).compare(template_var_labels).stack()
    if len(test2.index)>0:
        print(test2)
    #
    # Move extra variables to end
    extra_vars = [v for v in df1.columns if v not in merge_vars]
    df1 = pd.concat([df1.drop(columns=extra_vars),df1[extra_vars]], axis=1)
    #
    # Add prefix country code in df and meta
    rename_vars = {v: key+"_"+v for v in extra_vars if not(v.startswith(key))}
    new_valuelabels = this_valuelabels[[v for v in extra_vars if v in this_valuelabels.index]]
    new_var_labels = this_var_labels[extra_vars]
    #
    df1 = df1.rename(columns=rename_vars)
    new_valuelabels = new_valuelabels.rename(rename_vars)
    new_var_labels = new_var_labels.str.strip(': ')
    new_var_labels = new_var_labels.rename(rename_vars) + ' ('+country_name+')'
    #
    print('\nExtra variables:')
    print(new_var_labels)
    # Combine data
    valuelabels = pd.concat([valuelabels, new_valuelabels])
    var_labels = pd.concat([var_labels, new_var_labels])
    df = pd.concat([df, df1])
    input('\nPress Enter to continue')


# Sjekk labels for Language
language_labels = {}
for k in all_meta.keys():
    language_labels[k] = all_meta[k].variable_value_labels['Q_LANGUAGE']

print(pd.DataFrame(language_labels).T)



unik_ID = df['dcountry']*100000+df['record']
df.insert(loc=0, column='unik_ID', value=unik_ID)

date_str = pd.to_datetime(((df['date']/86400)-141428), unit = 'D').dt.strftime('%m/%d/%Y')
loc = df.columns.get_loc('date')+1
df.insert(loc=loc, column='date_str', value=date_str)

country_code = df['dcountry'].map(country_codes)
loc = df.columns.get_loc('dcountry')+1
df.insert(loc=loc, column='country_code', value=country_code)




# Variable labels: behold tekst etter ":" (fjerner variabelnavn)
var_labels = pd.Series(var_labels).str.split(":", n=1, expand=True)[1]
var_labels = var_labels.str.strip(" :")
var_labels['dcountry'] = 'Country'
var_labels['country_code'] = 'Country code'
var_labels['date_str'] = 'Date (mm/dd/yyyy)'
var_labels['unik_ID'] = 'Unik ID'


variable_format = {v:'F1.0' for v in merge_vars}
variable_format['date'] = 'Date'

# VEKTING

workforce = {
    'Norway': 2981183, 
    'Sweden': 5723799, 
    'Finland': 2845714, 
    'Denmark': 3141486, 
    'Germany': 44198105, 
    'France': 31616935, 
    'Italy': 25342466, 
    'Poland': 18300937, 
    'Netherlands': 9793778, 
    'Ireland': 2673388, 
    'Austria': 4761984, 
    'United Kingdom': 34376365, 
    'Spain': 23687273, 
    'Portugal': 5295941, 
    'Belgium': 5374303, 
    'Greece': 4651589, 
    'Switzerland': 4968223, 
    'Turkey': 34630319, 
    'Cyprus': 684941, 
    'Israel': 4450601, 
    'Luxembourg': 338747, 
}

vekting =  df['dcountry'].value_counts().sort_index().rename(country_labels).to_frame(name='N')
vekting['N_pct'] = vekting['N']/vekting['N'].sum()

vekting['workforce'] =vekting.index.map(workforce)
vekting['workforce_pct'] = vekting['workforce']/vekting['workforce'].sum()

vekting['Vekt'] = vekting['workforce_pct']/vekting['N_pct']
vekting.loc['Sum'] = vekting.sum()
print(vekting)

df['Vekt_europe'] = df['dcountry'].replace(country_labels).map(vekting['Vekt'])
var_labels['Vekt_europe'] = "Weight Europe"
# SKRIVE TIL FIL



print(df)
print(var_labels)
output_file = asksaveasfilename(initialdir=path_data, initialfile='GPTW Europeisk Trust Index Rådata.sav')

pyreadstat.write_sav(
    df, 
    output_file, 
    column_labels=var_labels.to_dict(), 
    variable_value_labels=valuelabels.to_dict(),
    variable_format=variable_format
)



###########################################################33########33
spss_file = output_file
spss_file = askopenfilename(initialdir=path_data)

df, meta = pyreadstat.read_sav(spss_file)

valuelabels = pd.Series(meta.variable_value_labels)
var_labels = pd.Series(meta.column_names_to_labels )


drop_vars = ['IT_GRG','IT_h_Province',
            'DK_municipality',
            'FI_municipality','FI_nuts3','FI_nuts2_2012','FI_geo_kunta_old','FI_postcode',
            'SE_municipality','SE_aregion','SE_County',
            'FR_department','FR_UDA13',
            'NO_kommune2024','NO_fylke2024','NO_fylke2020', 'NO_kommune2020','NO_landsdel2020']


df = df.drop(columns=drop_vars)
valuelabels = valuelabels.drop(drop_vars, errors='ignore')
var_labels = var_labels.drop(drop_vars)

# Overskriver date_str med format 03 May 2024
df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%d %b %Y')
var_labels['date_str'] = 'Date (string)'
# Variabler med flest value labels
print(valuelabels.apply(len).sort_values(ascending=False).head(10))


ISO8859_15_CHAR_MAPPING= {
    u"\u2019": u"'",
    u"`": u"'",
    u"\u2013": "-",
    }
translate_mapping = {ord(k):ord(v) for k,v in ISO8859_15_CHAR_MAPPING.items()}


# Clean value labels
#original_valuelabels = valuelabels.copy()
temp = valuelabels.apply(pd.Series).sort_index(axis=1)
temp = temp.stack()
temp = temp.apply(lambda s: s.translate(translate_mapping))
temp = temp.str.replace("€",'EUR ')
temp[temp.str.startswith('NO TO:')]="Not selected"
valuelabels_stacked = temp

valuelabels = pd.Series({k: v[k].to_dict() for k, v in temp.groupby(level=0, sort=False)})
#valuelabels = valuelabels.loc[original_valuelabels.index]

# Clean Variable labels
var_labels = var_labels.fillna('').apply(lambda s: s.translate(translate_mapping))


# Format metadata for GPTW Europe

#valuelabels_out = valuelabels.apply(pd.Series).sort_index.stack().reset_index()
valuelabels_stacked = valuelabels_stacked.reset_index()
valuelabels_stacked.columns = ['QNumber','Answer Value','Answer']

temp_var_labels = var_labels.reset_index()
temp_var_labels.columns = ['QNumber','Survey Question']

meta_out = temp_var_labels.merge(valuelabels_stacked, how='outer', on='QNumber')
meta_out = meta_out.set_index('QNumber').loc[df.columns]

#meta_out['Survey Question'] = meta_out['QNumber'].map(var_labels)
#meta_out = meta_out[['QNumber','Survey Question','Answer Value','Answer']]

# Adapt charmap
#meta_out[['Survey Question','Answer']] = meta_out[['Survey Question','Answer']].fillna('')
#meta_out['Survey Question'] = meta_out['Survey Question'].apply(lambda s: s.translate(translate_mapping))
#meta_out['Answer'] = meta_out['Answer'].apply(lambda s: s.translate(translate_mapping))
#meta_out['Answer'] = meta_out['Answer'].str.replace("€",'EUR ')
                                                    
#df['zipcode'] = df['zipcode'].fillna('').astype(str)


dir = Path(spss_file).parent
dir = askdirectory(initialdir=dir)

stem = Path(spss_file).stem
data_filename = asksaveasfilename(initialdir=dir, initialfile=stem+'.csv')
meta_filename = data_filename.replace('.csv','_meta.csv')

df.to_csv(data_filename, index=False)
#meta_out.to_csv(meta_filename, encoding='ISO8859-15')
meta_out.to_csv(meta_filename, encoding='utf-8')

#excel_filename = asksaveasfilename(initialdir=path_data, initialfile='GPTW Europeisk Trust Index Rådata.xlsx')
#with pd.ExcelWriter(excel_filename, engine = 'xlsxwriter', options={'encoding': 'ISO8859-15'}) as writer:
#    #df.to_excel(writer, sheet_name='Rådata')
#    meta_out.to_excel(writer, sheet_name='Rekkefølge påstander')

################################################################3

# Format output for GPTW USA

# Replace values with valuelabels for certain variables
replace_values = valuelabels.drop(df.loc[:,'Q001008r1':'Q050061r61'].columns)
output_df = df.replace(replace_values)

# Replace variable names with variable labels
rename_cols = var_labels.loc[var_labels!='']
output_df = output_df.rename(columns=rename_cols)

# Save to csv
us_filename = asksaveasfilename(initialdir=path_data, initialfile=stem+'_US.csv')
output_df.to_csv(us_filename, encoding='utf-8', index=False)

#########################################################################




df.to_csv(data_filename, index=False)
#df, meta = pyreadstat.read_sav(spss_file)

valuelabels = pd.Series(meta.variable_value_labels)
var_labels = pd.Series(meta.column_names_to_labels )

df = df.drop(columns=drop_vars)
valuelabels = valuelabels.drop(drop_vars, errors='ignore')
var_labels = var_labels.drop(drop_vars)

# Clean value labels
temp = valuelabels.apply(pd.Series).stack()
temp = temp.apply(lambda s: s.translate(translate_mapping))
temp = temp.str.replace("€",'EUR ')
temp[temp.str.startswith('NO TO:')]="Not selected"

valuelabels = pd.Series({k: v[k].to_dict() for k, v in temp.groupby(level=0)})

# Clean Variable labels
var_labels = var_labels.fillna('').apply(lambda s: s.translate(translate_mapping))

# Replace values with valuelabels for certain variables
replace_values = valuelabels.drop(df.loc[:,'Q001008r1':'Q050061r61'].columns)

output_df = df.replace(replace_values)

#temp1 = df.loc[:,:'Q_SECTOR'].replace(valuelabels)
#temp2 = df.loc[:,'Q001008r1':'Q050061r61']
#temp3 = df.loc[:,'Q062063r62':].replace(valuelabels)

# Combine result
#output_df = pd.concat([temp1,temp2,temp3],axis=1)

# Extract Poland cols 
#polen_cols = ['PL_region', 'PL_educationLevel', 'PL_personal_income']
#output_PL = output_df[polen_cols]
#output_df = output_df.drop(columns = polen_cols)

# Replace variable names with variable labels
rename_cols = var_labels.loc[var_labels!='']
output_df = output_df.rename(columns=rename_cols)
#output_PL = output_PL.rename(columns=rename_cols)

# Save to csv with 
csv_filename = asksaveasfilename(initialdir=path_data, initialfile='GPTW European Trust Index Raw data.csv')
#csv_filename_PL = csv_filename.replace('.csv','_PL.csv')

#output_df.to_csv(csv_filename, encoding='ISO8859-15')
o#utput_PL.to_csv(csv_filename_PL, encoding='utf-8')
output_df.to_csv(csv_filename, encoding='utf-8')


#excel_filename = asksaveasfilename(initialdir=path_data, initialfile='GPTW European Trust Index Raw data.xlsx')
#output_df.to_excel(encoding='ISO8859-15')




#######################################################################
#Polen Ekstra

file = path_data.joinpath('ONH132596_240531_Poland_EKSTRA.sav')
df_PL, meta_PL = pyreadstat.read_sav(file)
var_labels_PL = pd.Series(meta_PL.column_names_to_labels)
valuelabels_PL = pd.Series(meta_PL.variable_value_labels)

d = {'region':'PL_region',
    'educationLevel':'PL_educationLevel',
    'personal_income':'PL_personal_income'}

df_PL = df_PL.rename(columns=d)
var_labels_PL = var_labels_PL.rename(d)
valuelabels_PL = valuelabels_PL.rename(d)

var_labels_PL = var_labels_PL+' (Poland)'

valuelabels_PL_out = valuelabels_PL.apply(pd.Series).stack().reset_index()
valuelabels_PL_out.columns = ['QNumber','Answer Value','Answer']

var_labels_PL = var_labels_PL.reset_index()
var_labels_PL.columns = ['QNumber','Survey Question']

meta_PL_out = var_labels_PL.merge(valuelabels_PL_out, how='outer', on='QNumber')
meta_PL_out = meta_PL_out.set_index('QNumber').loc[df_PL.columns]

meta_PL_out.to_csv(path_data.joinpath('Polen_ekstra.csv'), encoding='utf-8')



print('\n'.join(var_labels_PL['Survey Question'].fillna('')))
print('\n'.join(meta_PL_out['Answer'].fillna('')))
print(pd.Series(valuelabels_PL['PL_region']))
print(pd.Series(valuelabels_PL['PL_educationLevel']))
print(pd.Series(valuelabels_PL['PL_personal_income']))


###################################3

melted_df = df.melt(id_vars=['dcountry', 'Vekt_europe'], value_vars=cols, 
                    var_name='question', value_name='answer')

grouped = melted_df.groupby(['dcountry', 'question', 'answer'])['Vekt_europe'].sum().reset_index()
melted_df.groupby(['dcountry', 'question'])['answer'].value_counts(normalize=True, sort=False)
melted_df.groupby(['dcountry', 'question'])['answer'].value_counts()