from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from tkinter.filedialog import askopenfilename, asksaveasfilename
import pandas as pd
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





def compress_pdf(input_path, output_path=None):
    """
    Komprimerer en enkelt PDF-fil.
    
    Args:
        input_path (str eller Path): Sti til original PDF-fil
        output_path (str eller Path, optional): Sti hvor komprimert PDF-fil skal lagres.
                                              Hvis None, brukes input-filnavnet med "_compressed" lagt til.
    
    Returns:
        dict: Resultat av komprimeringen med statistikk
    """
    # Konverter til Path-objekter
    input_path = Path(input_path)
    
    # Hvis output_path ikke er definert, lag et standardnavn basert på input-filen
    if output_path is None:
        # Lag et nytt filnavn med "_compressed" før filendelsen
        stem = input_path.stem  # Filnavn uten endelse
        suffix = input_path.suffix  # Filendelse inkludert punktum
        output_path = input_path.with_name(f"{stem}_compressed{suffix}")
    else:
        output_path = Path(output_path)
    
    try:
        # Les PDF-filen
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        # Kopier alle sider og komprimer innholdsstrømmene
        for page in reader.pages:
            # Komprimer innholdsstrømmene uten level-parameter
            try:
                page.compress_content_streams()
            except Exception as e:
                print(f"Advarsel: Kunne ikke komprimere side: {str(e)}")
            writer.add_page(page)
        
        # Kopier metadata fra originalen hvis tilgjengelig
        try:
            if reader.metadata:
                writer.add_metadata(reader.metadata)
        except (AttributeError, TypeError):
            pass
        
        # Opprett output-mappe hvis den ikke eksisterer
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Lagre den komprimerte PDF-en
        with output_path.open("wb") as output_file:
            writer.write(output_file)
        
        # Beregn filstørrelser og komprimeringsrate
        original_size = input_path.stat().st_size
        compressed_size = output_path.stat().st_size
        reduction_percent = (1 - compressed_size / original_size) * 100
        
        return {
            "original_size_kb": original_size / 1024,
            "compressed_size_kb": compressed_size / 1024,
            "reduction_percent": reduction_percent,
            "status": "success",
            "output_path": str(output_path)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }

def compress_pdfs_in_folder(input_folder, output_folder):
    """
    Komprimerer alle PDF-filer i en mappe og lagrer dem i en annen mappe.
    
    Args:
        input_folder (str eller Path): Sti til mappen med originale PDF-filer
        output_folder (str eller Path): Sti til mappen hvor komprimerte PDF-filer skal lagres
    
    Returns:
        dict: Ordbok med filnavn og deres komprimeringsresultater
    """
    # Konverter til Path-objekter
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    
    # Sørg for at output-mappen eksisterer
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Finn alle PDF-filer i input-mappen
    pdf_files = list(input_folder.glob("*.pdf"))
    pdf_files.extend(input_folder.glob("*.PDF"))
    
    if not pdf_files:
        print(f"Ingen PDF-filer funnet i {input_folder}")
        return {}
    
    results = {}
    
    for pdf_file in pdf_files:
        output_path = output_folder / pdf_file.name
        
        print(f"Komprimerer {pdf_file.name}...")
        result = compress_pdf(pdf_file, output_path)
        results[pdf_file.name] = result
        
        if result["status"] == "success":
            print(f"  Fullført: {result['reduction_percent']:.2f}% reduksjon")
        else:
            print(f"  Feil: {result['error_message']}")
    
    # Oppsummering
    successful = sum(1 for r in results.values() if r.get("status") == "success")
    print(f"\nKomprimering fullført: {successful} av {len(pdf_files)} filer behandlet.")
    
    if successful > 0:
        avg_reduction = sum(r["reduction_percent"] for r in results.values() if r.get("status") == "success") / successful
        print(f"Gjennomsnittlig reduksjon: {avg_reduction:.2f}%")
    
    return results



# Eksempel på bruk:
user_path = Path.home()

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
