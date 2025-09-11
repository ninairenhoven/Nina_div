import pikepdf
from pathlib import Path


def shrink_pdf(inp, outp):
    """
    Krymper PDF ved å:
    - tømme Document Info (metadata)
    - fjerne /Metadata, /Outlines, /Names, /OpenAction, /AA fra Root (hvis til stede)
    - lagre med komprimerte streams og genererte object streams (fallbacks ved behov)
    Kompatibel med pikepdf 9.10.2 og eldre varianter via try/except-fallbacks.
    """
    with pikepdf.open(inp) as pdf:
        # 1) Tøm Document Info som indirekte objekt (krav i noen versjoner)
        try:
            try:
                empty_info = pdf.make_indirect(pikepdf.Dictionary())
            except AttributeError:
                # Hvis Dictionary ikke finnes, bruk tom dict
                empty_info = pdf.make_indirect({})
            pdf.docinfo = empty_info
        except Exception:
            # Fallback: tøm eksisterende nøkler i docinfo
            try:
                di = pdf.docinfo
                for k in list(di.keys()):
                    try:
                        del di[k]
                    except Exception:
                        pass
            except Exception:
                pass  # Hvis også dette feiler, lar vi metadata være

        # 2) Fjern unødvendige nøkler fra Root (merk pdf.Root, ikke pdf.root)
        try:
            root = pdf.Root
            # Ta med /Metadata eksplisitt, pluss noen vanlige "ballast"-nøkler
            for key in ["/Metadata", "/Outlines", "/Names", "/OpenAction", "/AA"]:
                if key in root:
                    try:
                        del root[key]
                    except Exception:
                        pass
        except Exception:
            pass

        # 3) Lagre med best-effort komprimering og fallbacks
        # Primær: object streams + compress_streams + (ikke linearize)
        try:
            pdf.save(
                outp,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
                compress_streams=True,
                linearize=False
            )
        except TypeError:
            # Fallback 1: dropp object_stream_mode
            try:
                pdf.save(
                    outp,
                    compress_streams=True,
                    linearize=False
                )
            except TypeError:
                # Fallback 2: minimalistisk save
                pdf.save(outp)

import os
from pathlib import Path
import pikepdf

def shrink_pdf(inp, outp):
    """
    Krymper PDF ved å:
    - tømme Document Info (metadata)
    - fjerne /Metadata, /Outlines, /Names, /OpenAction, /AA fra Root
    - lagre med komprimerte streams og (om støttet) object streams

    Returnerer ett samlet result-objekt med før/etter-størrelser og status.
    Kompatibel med pikepdf 9.10.2 via try/except-fallbacks.
    """
    input_path = Path(inp)
    output_path = Path(outp)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "original_size_kb": None,
        "compressed_size_kb": None,
        "reduction_percent": None,
        "status": "init",
        "output_path": str(output_path)
    }

    # Mål original størrelse
    try:
        original_size = os.path.getsize(input_path)
        result["original_size_kb"] = original_size / 1024
    except Exception as e:
        result["status"] = f"error: cannot stat input ({e})"
        return result

    # Prosesser PDF
    try:
        with pikepdf.open(str(input_path)) as pdf:
            # 1) Tøm Document Info som indirekte objekt (fallback til å slette nøkler)
            try:
                try:
                    empty_info = pdf.make_indirect(pikepdf.Dictionary())
                except AttributeError:
                    empty_info = pdf.make_indirect({})
                pdf.docinfo = empty_info
            except Exception:
                try:
                    di = pdf.docinfo
                    for k in list(di.keys()):
                        try:
                            del di[k]
                        except Exception:
                            pass
                except Exception:
                    pass

            # 2) Fjern unødvendige nøkler fra Root
            try:
                root = pdf.Root  # Merk stor R
                for key in ["/Metadata", "/Outlines", "/Names", "/OpenAction", "/AA"]:
                    if key in root:
                        try:
                            del root[key]
                        except Exception:
                            pass
            except Exception:
                pass

            # 3) Lagre med best-effort komprimering og fallbacks (ingen fler-returns)
            try:
                pdf.save(
                    str(output_path),
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                    compress_streams=True,
                    linearize=False
                )
            except TypeError:
                try:
                    pdf.save(
                        str(output_path),
                        compress_streams=True,
                        linearize=False
                    )
                except TypeError:
                    pdf.save(str(output_path))

    except Exception as e:
        result["status"] = f"error: processing failed ({e})"
        return result

    # Mål komprimert størrelse og beregn reduksjon
    try:
        compressed_size = os.path.getsize(output_path)
        result["compressed_size_kb"] = compressed_size / 1024
        if original_size and original_size > 0:
            result["reduction_percent"] = (1 - (compressed_size / original_size)) * 100.0
        result["status"] = "success"
    except Exception as e:
        result["status"] = f"error: cannot stat output ({e})"

    return result



def shrink_pdfs_in_folder(input_folder, output_folder):
    pdf_files = list(input_folder.glob("*.pdf"))
    for n, pdf_file in enumerate(pdf_files):
        output_path = output_folder / pdf_file.name
        r = shrink_pdf(pdf_file, output_path)
        print(f"{n}: {output_path} - {r['reduction_percent']}")




def compress_pdf(input_path, output_path=None, keep_meta=False):
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
    #
    # Hvis output_path ikke er definert, lag et standardnavn basert på input-filen
    if output_path is None:
        # Lag et nytt filnavn med "_compressed" før filendelsen
        stem = input_path.stem  # Filnavn uten endelse
        suffix = input_path.suffix  # Filendelse inkludert punktum
        output_path = input_path.with_name(f"{stem}_compressed{suffix}")
    else:
        output_path = Path(output_path)
    #
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
        #
        # Kopier metadata fra originalen hvis tilgjengelig
        if(keep_meta):
            try:
                if reader.metadata:
                    writer.add_metadata(reader.metadata)
            except (AttributeError, TypeError):
                pass
        #
        # Opprett output-mappe hvis den ikke eksisterer
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Lagre den komprimerte PDF-en
        with output_path.open("wb") as output_file:
            writer.write(output_file)
        #
        # Beregn filstørrelser og komprimeringsrate
        original_size = input_path.stat().st_size
        compressed_size = output_path.stat().st_size
        reduction_percent = (1 - compressed_size / original_size) * 100
        #
        return {
            "original_size_kb": original_size / 1024,
            "compressed_size_kb": compressed_size / 1024,
            "reduction_percent": reduction_percent,
            "status": "success",
            "output_path": str(output_path)
        }
        #
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


def compress_pdfs_in_folder(input_folder, output_folder, keep_meta=False):
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
        result = compress_pdf(pdf_file, output_path, keep_meta=keep_meta)
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

        





from docx2pdf import convert

def docx_to_pdf(input_path: Path, output_path: Path | None = None) -> Path:
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Finner ikke input-fil: {input_path}")
    if input_path.suffix.lower() not in {".doc", ".docx"}:
        raise ValueError("Input må være .doc eller .docx")

    if output_path is None:
        output_path = input_path.with_suffix(".pdf")
    else:
        output_path = Path(output_path).resolve()
        # Hvis output_path er en mappe, lag filnavn basert på input
        if output_path.is_dir():
            output_path = output_path / (input_path.stem + ".pdf")

    word = win32.gencache.EnsureDispatch("Word.Application")
    word.Visible = False

    try:
        doc = word.Documents.Open(str(input_path))
        # 17 = wdFormatPDF
        doc.SaveAs(str(output_path), FileFormat=17)
        doc.Close()
    finally:
        word.Quit()

    if not output_path.exists():
        raise FileNotFoundError("PDF ble ikke generert som forventet.")
    return output_path


def docx_to_pdf_file(input_path: Path, output_path: Path | None = None) -> Path:
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Finner ikke input-fil: {input_path}")
    if input_path.suffix.lower() != ".docx":
        raise ValueError("Input må være en .docx-fil")

    if output_path is None:
        output_path = input_path.with_suffix(".pdf")
    else:
        output_path = Path(output_path).resolve()
        if output_path.is_dir():
            output_path = output_path / (input_path.stem + ".pdf")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # docx2pdf krever str-stier
    convert(str(input_path), str(output_path))
    if not output_path.exists():
        raise FileNotFoundError("PDF ble ikke generert som forventet.")
    return output_path

