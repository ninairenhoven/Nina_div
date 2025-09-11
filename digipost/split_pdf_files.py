from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from tkinter.filedialog import askopenfilename, asksaveasfilename
import pandas as pd
import win32com.client as win32
import time
import importlib


#from PIL import Image
#import io

def split_pdf_to_pages(input_pdf_path, output_folder, filnavn_dict=None):
    """
    Splitter en PDF i enkeltfiler per side.
    filnavn_dict: dict med key=sidenummer (1-baserte), value=filnavn (med eller uten .pdf)
    Hvis None, genereres dict med standardnavn inkludert .pdf.
    """
    output_folder.mkdir(parents=True, exist_ok=True)
    input_pdf = PdfReader(input_pdf_path)
    total_pages = len(input_pdf.pages)
    print(f"Starter splitting av '{input_pdf_path.name}' til '{output_folder}'...")

    # Lag standard dict hvis ingen filnavn_dict er gitt, nå med .pdf inkludert
    if filnavn_dict is None:
        filnavn_dict = {i: f"page_{i}.pdf" for i in range(1, total_pages + 1)}

    pages = set(range(1, total_pages + 1))
    given_keys = set(filnavn_dict.keys())
    missing_keys = sorted(pages - given_keys)
    for i in missing_keys:
        filnavn_dict[i] = f"page_{i}.pdf"

    # Forenklet kontroll: keys skal være nøyaktig 1..total_pages
    if set(filnavn_dict.keys()) != set(range(1, total_pages + 1)):
        raise ValueError(
            f"filnavn_dict må ha keys 1 til {total_pages}. "
            f"Fikk: {sorted(filnavn_dict.keys())}"
        )

    # Skriv ut alle sidene
    for i in range(1, total_pages + 1):
        filnavn = filnavn_dict[i]
        # Sjekk om filnavnet allerede har .pdf-endelse
        #if not filnavn.lower().endswith('.pdf'):
        #    filnavn = f"{filnavn}.pdf"
        
        out_path = output_folder / filnavn
        writer = PdfWriter()
        writer.add_page(input_pdf.pages[i - 1])
        with open(out_path, "wb") as out_file:
            writer.write(out_file)
        print(f"  Lagret side {i} som '{out_path.name}'")
    print(f"Splitting ferdig: {total_pages} filer opprettet.\n")




def add_extra_page_to_pdfs(folder: Path, extra_page_file: Path):
    """
    Legger til en ekstra side (fra extra_page_file) til alle PDF-er i folder
    (bortsett fra extra_page_file selv).
    """
    print(f"Legger til ekstra side fra '{extra_page_file.name}' i alle PDF-er i '{folder}'...")
    extra_reader = PdfReader(extra_page_file)
    extra_page = extra_reader.pages[0]
    pdf_files = list(folder.glob('*.pdf'))
    total_files = len(pdf_files)
    print(f"Antall filer: {total_files}")
    for idx, pdf_file in enumerate(pdf_files, 1):
        if pdf_file == extra_page_file:
            print(f"  Hopper over '{pdf_file.name}' (ekstra side).")
            continue
        reader = PdfReader(pdf_file)
        writer = PdfWriter()
        writer.add_page(reader.pages[0])
        writer.add_page(extra_page)
        with open(pdf_file, "wb") as out_file:
            writer.write(out_file)
        print(f"  ({idx}/{total_files}) Lagt til ekstra side i '{pdf_file.name}'")
    print("Ekstra side lagt til i alle aktuelle filer.\n")





# Eksempel på bruk:
user_path = Path.home()

# ================================================================
# SEPTEMBER 2025, DFØ
# ================================================================
path = user_path.joinpath('Documents/DIGIPOST_LOKAL/DIGIPOST DFØ')
wordfil = path.joinpath('01a_Invitasjonsbrev digitalt_bokmål_kommunen_FLETTET.docx')

t0 = time.time()
"""
t0 = time.time()
p = docx_to_pdf(wordfil)
print(round(time.time()-t0))

p = docx_to_pdf_file(wordfil)

"""
#print(round(time.time()-t0))
#print(p)

emnefelt = {
    'bokmål': "Delta i Innbyggerundersøkelsen",
    'nynorsk': "Delta i Innbyggjarundersøkinga",
    'engelsk': "Participate in the Citizen Survey",
    'polsk': "Weź udział w ankiecie obywatelskiej",
    'ukrainsk': "Візьміть участь в опитуванні населення"
}


path_flettefiler = path.joinpath('Flettefiler')
path_pdf_flettet = path.joinpath('pdf_flettet')


xlsx_files = list(path_flettefiler.glob("*.xlsx"))  
xlsx_filenames = [f.name for f in xlsx_files]

pdf_files = list(path_pdf_flettet.glob("*.pdf"))  
pdf_filenames = [f.name for f in pdf_files]

s = pd.Series(xlsx_filenames)
parts = s.str.split(r"[_.,]", expand=True)

files_df = s.to_frame(name='flettefil')
files_df['skjema'] = parts[4].str.strip()
files_df['spraak'] = parts[5].str.strip()
files_df.index = parts[0].str.strip()

temp = pd.Series(pdf_filenames)
temp.index = temp.str.split('_', n=1).str[0].str.strip()
files_df['pdf_flettet'] = files_df.index.map(temp)

output_folder = path.joinpath('output')

"""
ix = '02'
row = files_df.loc[ix]

pdf_flettet = path_pdf_flettet.joinpath(row['pdf_flettet'])
utvalgsfil = path_flettefiler.joinpath(row['flettefil'])
spraak = row['spraak']

print(pdf_flettet)
print(utvalgsfil)

lookup = pd.read_excel(utvalgsfil, usecols=['opinionid','altid','fodselsnr'])
lookup['page'] = lookup.index + 1
lookup["filnavn"] = lookup.apply(lambda r: f'DFØ_{ix}_{int(r["opinionid"]):05d}_{r["altid"]}.pdf', axis=1)
lookup['emne'] = emnefelt[spraak]
lookup = lookup.rename(columns={'fodselsnr':'mottaker-identifikator-fødselsnummer'})

print(lookup)

filnavn_dict = lookup.set_index('page')['filnavn'].to_dict()
split_pdf_to_pages(pdf_flettet, output_folder, filnavn_dict)

savecols = ['mottaker-identifikator-fødselsnummer','emne','filnavn']
lookup[savecols].to_excel(path.joinpath(ix+'.xlsx'), index=False)

"""
lookup_files = []
lookup_merged = pd.DataFrame()

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
    lookup = lookup.rename(columns={'fodselsnr':'mottaker-identifikator-fødselsnummer'})

    print(lookup)

    filnavn_dict = lookup.set_index('page')['filnavn'].to_dict()
    #split_pdf_to_pages(pdf_flettet, output_folder, filnavn_dict)

    savecols = ['mottaker-identifikator-fødselsnummer','emne','filnavn']
    lookup_file = path.joinpath(ix+'.xlsx')
    #lookup[savecols].to_excel(lookup_file, index=False)
    lookup_merged = pd.concat([lookup_merged,lookup])
    lookup_files = lookup_files + [lookup_file]



compressed_folder = path.joinpath('output_compressed')

"""
compress_pdfs_in_folder(output_folder, compressed_folder)
shrink_pdfs_in_folder(output_folder, compressed_folder)
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