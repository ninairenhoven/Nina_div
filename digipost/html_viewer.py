
"""
HTML Template Viewer & Comparison Tools
=======================================
Verktøy for å se og sammenligne genererte HTML-templates
"""

import webbrowser
import http.server
import socketserver
import threading
import time
from pathlib import Path
import subprocess
import tempfile

def open_html_in_browser(html_path: str):
    """Åpner HTML-fil direkte i standard nettleser"""
    html_path = Path(html_path)
    
    if not html_path.exists():
        print(f"❌ HTML-fil ikke funnet: {html_path}")
        return False
    
    print(f"🌐 Åpner {html_path.name} i nettleser...")
    
    # Konverter til file:// URL for lokal visning
    file_url = f"file:///{html_path.absolute()}"
    
    try:
        webbrowser.open(file_url)
        print("✅ HTML åpnet i nettleser!")
        return True
    except Exception as e:
        print(f"❌ Kunne ikke åpne nettleser: {e}")
        return False

def start_local_server(directory: str, port: int = 8000):
    """Starter lokal webserver for å se HTML med bilder"""
    directory = Path(directory)
    
    if not directory.exists():
        print(f"❌ Mappe ikke funnet: {directory}")
        return None
    
    print(f"🚀 Starter lokal webserver på port {port}...")
    print(f"📁 Serverer filer fra: {directory}")
    
    # Bytt til riktig mappe
    import os
    original_dir = os.getcwd()
    os.chdir(directory)
    
    try:
        # Start server i separat tråd
        handler = http.server.SimpleHTTPRequestHandler
        httpd = socketserver.TCPServer(("", port), handler)
        
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        server_url = f"http://localhost:{port}"
        print(f"✅ Server kjører på: {server_url}")
        print("💡 Trykk Ctrl+C for å stoppe serveren")
        
        # Åpne i nettleser
        time.sleep(1)
        webbrowser.open(server_url)
        
        return httpd
        
    except Exception as e:
        print(f"❌ Kunne ikke starte server: {e}")
        os.chdir(original_dir)
        return None
    finally:
        os.chdir(original_dir)

def create_comparison_page(html_template_path: str, word_docx_path: str, output_path: str = None):
    """Lager sammenligning-side mellom HTML og Word-screenshot"""
    
    html_path = Path(html_template_path)
    word_path = Path(word_docx_path)
    
    if not html_path.exists():
        print(f"❌ HTML-template ikke funnet: {html_path}")
        return None
    
    if not word_path.exists():
        print(f"❌ Word-dokument ikke funnet: {word_path}")
        return None
    
    # Les HTML-innhold
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Lag sammenligning-side
    comparison_html = f"""
<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTML vs Word Sammenligning</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .comparison-container {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .panel {{
            flex: 1;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .panel h2 {{
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #007acc;
            color: #007acc;
        }}
        .html-preview {{
            border: 1px solid #ddd;
            padding: 20px;
            background-color: white;
            min-height: 400px;
            overflow: auto;
        }}
        .word-info {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 15px;
        }}
        .instructions {{
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .tips {{
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
        }}
        @media (max-width: 768px) {{
            .comparison-container {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 HTML vs Word Template Sammenligning</h1>
        <p>Sammenlign den genererte HTML-en med Word-originalen</p>
    </div>

    <div class="instructions">
        <h3>📋 Hvordan sammenligne:</h3>
        <ol>
            <li><strong>Åpne Word-dokumentet:</strong> {word_path.name}</li>
            <li><strong>Sammenlign med HTML:</strong> Se på farger, fonter, layout nedenfor</li>
            <li><strong>Tweake CSS:</strong> Juster styles.css filen hvis nødvendig</li>
            <li><strong>Test på nytt:</strong> Refresh denne siden etter endringer</li>
        </ol>
    </div>

    <div class="comparison-container">
        <div class="panel">
            <h2>🌐 Generert HTML</h2>
            <div class="html-preview">
                {html_content.split('<body>')[1].split('</body>')[0] if '<body>' in html_content else html_content}
            </div>
        </div>

        <div class="panel">
            <h2>📄 Word Original</h2>
            <div class="word-info">
                <strong>Word-dokument:</strong> {word_path.name}<br>
                <strong>Sti:</strong> {word_path.parent}<br><br>
                <em>Åpne dette dokumentet i Word for sammenligning</em>
            </div>
            
            <h3>🔍 Hva å sjekke:</h3>
            <ul>
                <li><strong>Farger:</strong> Matcher overskrifter og tekst?</li>
                <li><strong>Fonter:</strong> Samme skrifttype og størrelse?</li>
                <li><strong>Layout:</strong> Avsnitt, marginer, justering?</li>
                <li><strong>Bilder:</strong> Vises og er riktig størrelse?</li>
                <li><strong>Lenker:</strong> Riktig farge og stil?</li>
                <li><strong>Lister:</strong> Korrekt punktmerking?</li>
            </ul>
        </div>
    </div>

    <div class="tips">
        <h3>💡 Tweaking-tips:</h3>
        <ul>
            <li><strong>Farger feil?</strong> Juster fargeverdier i styles.css</li>
            <li><strong>Font feil?</strong> Oppdater font-family i CSS</li>
            <li><strong>Layout feil?</strong> Juster margin/padding verdier</li>
            <li><strong>Bilder for store?</strong> Legg til max-width i CSS</li>
        </ul>
        
        <p><strong>Refresh denne siden</strong> etter CSS-endringer for å se resultatet!</p>
    </div>

    <script>
        // Auto-refresh hvert 30. sekund hvis du tweaker CSS
        // setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""
    
    # Lagre sammenligning-side
    if not output_path:
        output_path = html_path.parent / "comparison.html"
    else:
        output_path = Path(output_path)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(comparison_html)
    
    print(f"✅ Sammenligning-side lagret: {output_path}")
    return str(output_path)

def view_html_template(template_dir: str):
    """Hovedfunksjon for å se HTML-template"""
    template_dir = Path(template_dir)
    
    if not template_dir.exists():
        print(f"❌ Template-mappe ikke funnet: {template_dir}")
        return
    
    # Finn HTML-filer
    html_files = list(template_dir.glob("*template.html"))
    
    if not html_files:
        print(f"❌ Ingen template.html filer funnet i {template_dir}")
        return
    
    html_file = html_files[0]  # Ta første template
    
    print(f"🎯 Viser HTML-template: {html_file.name}")
    print("\n📋 Alternativer:")
    print("1. Åpne direkte i nettleser")
    print("2. Start lokal server (bedre for bilder)")
    print("3. Lag sammenligning med Word")
    
    choice = input("\nVelg alternativ (1/2/3): ").strip()
    
    if choice == "1":
        open_html_in_browser(html_file)
        
    elif choice == "2":
        server = start_local_server(template_dir)
        if server:
            try:
                input("\nTrykk Enter for å stoppe serveren...")
            except KeyboardInterrupt:
                pass
            finally:
                server.shutdown()
                
    elif choice == "3":
        # Finn Word-dokument
        word_files = list(template_dir.parent.glob("*.docx"))
        if word_files:
            word_file = word_files[0]
            comparison_file = create_comparison_page(html_file, word_file)
            if comparison_file:
                open_html_in_browser(comparison_file)
        else:
            print("❌ Ingen Word-filer funnet for sammenligning")
    
    else:
        print("❌ Ugyldig valg")

if __name__ == "__main__":
    # Test med brukerens template-output
    from pathlib import Path
    
    user_path = Path.home()
    template_dir = user_path.joinpath('Documents/DIGIPOST_LOKAL/TEST/HTML_Template_Output')
    
    if template_dir.exists():
        view_html_template(template_dir)
    else:
        print(f"❌ Template output ikke funnet: {template_dir}")
        print("💡 Kjør først word_to_html_converter.py")
