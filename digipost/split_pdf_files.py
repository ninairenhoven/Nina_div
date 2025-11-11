from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from tkinter.filedialog import askopenfilename, asksaveasfilename
import pandas as pd
import time
import importlib
import numpy as np
import zipfile
from datetime import datetime

import pdf_tools
importlib.reload(pdf_tools)
from pdf_tools import shrink_pdf, shrink_pdfs_in_folder, split_pdf_to_pages, add_extra_page_to_pdfs, zip_files_simple




# ================================================================
# SEPTEMBER 2025, DFØ
# ================================================================

user_path = Path.home()
path = user_path.joinpath('Documents/DIGIPOST_LOKAL/DIGIPOST DFØ')
wordfil = path.joinpath('01a_Invitasjonsbrev digitalt_bokmål_kommunen_FLETTET.docx')

t0 = time.time()


emnefelt = {
    'bokmål': "Delta i Innbyggerundersøkelsen",
    'nynorsk': "Delta i Innbyggjarundersøkinga",
    'engelsk': "Participate in the Citizen Survey",
    'polsk': "Weź udział w ankiecie obywatelskiej",
    'ukrainsk': "Візьміть участь в опитуванні населення"
}


# XLSX-filer med utvalg
path_flettefiler = path.joinpath('Flettefiler')
xlsx_files = list(path_flettefiler.glob("*.xlsx"))  
xlsx_filenames = [f.name for f in xlsx_files]

# Flettet pdf-fil
path_pdf_flettet = path.joinpath('pdf_flettet')
pdf_files = list(path_pdf_flettet.glob("*.pdf"))  
pdf_filenames = [f.name for f in pdf_files]

# Lag oppslags-df
s = pd.Series(xlsx_filenames)
parts = s.str.split(r"[_.,]", expand=True)

files_df = s.to_frame(name='flettefil')
files_df['skjema'] = parts[4].str.strip()
files_df['spraak'] = parts[5].str.strip()
files_df.index = parts[0].str.strip()

temp = pd.Series(pdf_filenames)
temp.index = temp.str.split('_', n=1).str[0].str.strip()
files_df['pdf_flettet'] = files_df.index.map(temp)

print(files_df)

# Generere filer

output_folder = path.joinpath('output')

lookup_files = []
lookup_merged = pd.DataFrame()
savecols = ['mottaker-identifikator-fødselsnummer','emne','filnavn']

for ix, row in files_df.iterrows():
    
    pdf_flettet = path_pdf_flettet.joinpath(row['pdf_flettet'])
    utvalgsfil = path_flettefiler.joinpath(row['flettefil'])
    spraak = row['spraak']
    
    print()
    print(pdf_flettet)
    print(utvalgsfil)

    lookup = pd.read_excel(utvalgsfil, usecols=['opinionid','altid','fodselsnr'])
    lookup['page'] = lookup.index + 1
    lookup["filnavn"] = lookup.apply(lambda r: f'DFØ_{ix}_{int(r["opinionid"]):05d}_{r["altid"]}.pdf', axis=1)
    lookup['emne'] = emnefelt[spraak]
    lookup['mottaker-identifikator-fødselsnummer'] = lookup['fodselsnr'].astype(str).str.zfill(11)
    
    print(lookup)

    filnavn_dict = lookup.set_index('page')['filnavn'].to_dict()
    split_pdf_to_pages(pdf_flettet, output_folder, filnavn_dict)

    lookup_file = path.joinpath(ix+'.xlsx')
    #lookup[savecols].to_excel(lookup_file, index=False)
    lookup_merged = pd.concat([lookup_merged,lookup])
    lookup_files = lookup_files + [lookup_file]


# Komprimere filer
compressed_folder = path.joinpath('output_compressed')
shrink_pdfs_in_folder(output_folder, compressed_folder)

# Lagre total-lookup til excel
lookup_merged.to_excel(path.joinpath('digipost lookup file.xlsx'), index=False)


#==============================================================================================================
# Dele opp i 4 utsendelser
# Lagre excel og zip for hver utsendelse
#==============================================================================================================


lookup_merged = lookup_merged.reset_index()
print(lookup_merged.index.duplicated().sum())

# Sjekk at alle verdier er unike
for col in ['opinionid','altid','mottaker-identifikator-fødselsnummer','filnavn']:
    print(lookup_merged[col].duplicated().sum())

# Sett kolonnerekkefølge - digipost-kolonner først
lookup_merged = lookup_merged[['mottaker-identifikator-fødselsnummer','emne','filnavn','altid','opinionid','page']]

# Generer batch-numre (1 til 4) gjentatt og kuttet til riktig lengde
nrows = lookup_merged.index.size
numbers = np.tile(np.arange(1, 5), nrows // 4 + 1)[:nrows]

lookup_merged['utsendelse'] = numbers


for i in np.arange(1,5):
    print(i)
    part = lookup_merged.loc[lookup_merged['utsendelse']==i]
    print(part)
    #
    output_excel = f'digipost_lookup_part_{i}.xlsx'
    output_zip = f'digipost_pdfs_{i}.zip'
    #
    print(output_excel)
    part.to_excel(compressed_folder.joinpath(output_excel), index=False)
    #
    files = part['filnavn']
    print(files)
    inp = input('zip files? y/n: ').upper()
    if inp in ["","Y"]:
        zipped = zip_files_simple(compressed_folder, files, output_zip)
        print(zipped)


"""
compress_pdfs_in_folder(output_folder, compressed_folder)
"""


'01a_Invitasjonsbrev digitalt_bokmål_kommunen_FLETTET.pdf'


"""
# ================================================================
# JUNI 2025, test RVU
# ================================================================
path = user_path.joinpath('Documents/RVU_LOKAL/Digipost/DIGIPOST runde 2')
#filename = 'Brev - digipost_flettet dokument.pdf'
#filename = 'Brev - digipost - TEST.pdf'
filename = 'Brev - digipost_flettet dokument runde 2.pdf'

total_file = path.joinpath(filename)

#total_file = askopenfilename(initialdir=path, title='Velg pdf som skal splittes opp:')


#template_file = path.joinpath('Brev - digipost.pdf')
#split_pdf_to_pages(template_file, path)

page2_file = path.joinpath('page_2.pdf')
#page2_file = askopenfilename(initialdir=path, title='Velg fil med side 2:')

output_folder = path.joinpath('output')

file_names_xlsx = path.joinpath('kryptert RVU Opinion uttrekk mars 2025-KRR_PROCESSED_DIGIPOST_batch_18_Jun06.xlsx')
file_names_xlsx = path.joinpath('TEST digipost.xlsx')
file_names_xlsx = path.joinpath('kryptert RVU Opinion uttrekk mars 2025-KRR_PROCESSED_DIGIPOST_Batch_30_Jun16.xlsx')

#file_names_xlsx = askopenfilename(initialdir=path, 'Velg fil som definerer filnavn')

filename_lookup = pd.read_excel(file_names_xlsx, usecols=['page_nr','filnavn'])
filename_lookup = filename_lookup.set_index('page_nr')['filnavn']
filename_lookup = filename_lookup.to_dict()

# Splitte PDF til enkeltsider:
# split_pdf_to_pages(total_file, output_folder)
split_pdf_to_pages(total_file, output_folder, filename_lookup)

# Legge til ekstra side:
add_extra_page_to_pdfs(output_folder, page2_file)

#file = output_folder.joinpath('RVU_0001_kme2zurs.pdf')
#compress_pdf(file)
"""