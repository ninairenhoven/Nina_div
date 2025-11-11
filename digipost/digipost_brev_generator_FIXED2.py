import pandas as pd
from docx import Document
import os
from pathlib import Path
from datetime import datetime
import logging
import shutil
import gc
from xhtml2pdf import pisa
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import time
import re
from tqdm import tqdm  # Progress bar

# Mammoth import moved to the top to avoid repeated imports
try:
    from mammoth import convert_to_html
    MAMMOTH_AVAILABLE = True
except ImportError:
    MAMMOTH_AVAILABLE = False
    print("Warning: mammoth not installed, using basic conversion")

# =============================================================================
# INPUT FILES
# =============================================================================

# Define paths for user and input files
user_path = Path.home()
path = user_path.joinpath(r'Documents\RVU_LOKAL\BRAKAR Sample')
TEMPLATE_FILE = path.joinpath("Invitasjonsbrev_ORDA_Brakar.docx")
LOOKUP_FILE = path.joinpath("Buskerud FK, Brakar, Opinion FREG uttrekk-krr_BRAKAR_Batch_0_23_PROCESSED_Nov11.csv")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FOLDER = path.joinpath(f"OUTPUT_{timestamp}")

# IMPORTANT: For best performance, use SSD for OUTPUT_FOLDER!

# Define placeholders to be replaced in the template
PLACEHOLDERS = [
    "mic",
    "navn",
    "uniksurveylink"
]

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default styles for the generated HTML
DEFAULT_FONT_FAMILY = "Helvetica, Arial, sans-serif"
DEFAULT_FONT_SIZE = "11pt"
DEFAULT_LINE_HEIGHT = "1.5"
LIST_LINE_HEIGHT = "1.2"
HEADING_1_SIZE = "14pt"
HEADING_2_SIZE = "12pt"

# HTML template for the generated PDF
from string import Template
HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4;
            margin: 2.5cm;
        }
        body {
            font-family: $DEFAULT_FONT_FAMILY;
            font-size: $DEFAULT_FONT_SIZE;
            line-height: $DEFAULT_LINE_HEIGHT;
            color: #000;
        }
        h1, h2, h3 {
            color: #000;
            margin-top: 1.5em;
            margin-bottom: 0.6em;
        }
        h1 { font-size: $HEADING_1_SIZE; font-weight: bold; }
        h2 { font-size: $HEADING_2_SIZE; font-weight: bold; }
        p {
            margin: 0.5em 0;
        }
        strong {
            font-weight: bold;
        }
        ul, ol {
            margin: 0.5em 0;
            padding-left: 2em;
            line-height: $LIST_LINE_HEIGHT;
        }
        li {
            margin: 0.3em 0;
            line-height: $LIST_LINE_HEIGHT;
        }
        a.survey-link {
            color: #0066cc;
            text-decoration: underline;
        }
        a.email-link {
            color: #0066cc;
            text-decoration: underline;
        }
    </style>
</head>
<body>
$HTML_BODY
</body>
</html>
""")

# =============================================================================
# READ LOOKUP FILE
# =============================================================================


def load_and_validate_data(file_path, required_columns, limit_rows=None):
    """
    Load and validate data from a lookup file (Excel or CSV).

    Parameters:
    -----------
    file_path : str or Path
        Path to the lookup file (Excel or CSV).
    required_columns : list
        List of required column names.
    limit_rows : int, optional
        Limit number of rows to read (for testing).

    Returns:
    --------
    pd.DataFrame
        Loaded and validated data as a Pandas DataFrame.

    Raises:
    -------
    ValueError
        If the file is missing required columns or cannot be loaded.
    """
    file_path = Path(file_path).resolve()
    file_extension = file_path.suffix.lower()

    try:
        # Load the file based on its extension
        if file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(
                file_path,
                usecols=required_columns,
                nrows=limit_rows,
                engine='openpyxl',
                dtype={'filename_tag': str}  # Preserve leading zeros
            )
        elif file_extension == '.csv':
            df = pd.read_csv(
                file_path,
                usecols=required_columns,
                nrows=limit_rows,
                dtype={'filename_tag': str}  # Preserve leading zeros
            )
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    except ValueError as e:
        raise ValueError(f"Failed to load file: {e}")

    # Validate required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    logging.info(f"Loaded {len(df)} rows from {file_path}")
    logging.info(f"Columns: {list(df.columns)}")
    
    return df



# =============================================================================
# GLOBAL WORKER TEMPLATE CACHE - Optimization for multiprocessing
# =============================================================================
_worker_template_cache = None


def init_worker(template_path):
    """
    Initialize worker process with template (called once per worker).
    This saves memory usage by avoiding sending the template via pickle to each worker.
    """
    global _worker_template_cache
    if _worker_template_cache is None:
        _worker_template_cache = load_template_for_worker(template_path)


def load_template_for_worker(template_path):
    """Load and convert template to HTML in worker process"""
    try:
        if MAMMOTH_AVAILABLE:
            with open(template_path, "rb") as docx_file:
                result = convert_to_html(docx_file)
                body = result.value
        else:
            doc = Document(template_path)
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text
                if text.strip():
                    paragraphs.append(f"<p>{text}</p>")
            body = "\n".join(paragraphs)
        
        # Process spacing tags and emails
        body = convert_emails_to_links(body)
        body = process_spacing_tags(body)
        
        # Use Template.substitute() to insert HTML body
        return HTML_TEMPLATE.substitute(
            DEFAULT_FONT_FAMILY=DEFAULT_FONT_FAMILY,
            DEFAULT_FONT_SIZE=DEFAULT_FONT_SIZE,
            DEFAULT_LINE_HEIGHT=DEFAULT_LINE_HEIGHT,
            LIST_LINE_HEIGHT=LIST_LINE_HEIGHT,
            HEADING_1_SIZE=HEADING_1_SIZE,
            HEADING_2_SIZE=HEADING_2_SIZE,
            HTML_BODY=body
        )
    
    except Exception as e:
        raise Exception(f"Failed to load template in worker: {e}")


def convert_emails_to_links(html_content):
    """Convert email addresses in HTML to clickable mailto: links"""
    email_pattern = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
    
    def replace_email(match):
        email = match.group(1)
        return f'<a href="mailto:{email}" class="email-link">{email}</a>'
    
    return re.sub(email_pattern, replace_email, html_content)


def process_spacing_tags(html_content):
    """Process spacing tags from Word document"""
    tag_count = html_content.count('&lt;linjeskift&gt;')
    if tag_count > 0:
        html_content = html_content.replace('&lt;linjeskift&gt;', '<p>&nbsp;</p>')
    return html_content


def process_single_file_worker(row_dict, output_folder, required_placeholders):
    """
    Worker function for parallel processing.
    Uses cached template from worker process.
    """
    global _worker_template_cache
    
    try:
        # Use cached template
        content = _worker_template_cache
        
        # Replace placeholders
        for placeholder in required_placeholders:
            value = str(row_dict.get(placeholder, ''))
            
            # Special handling for survey link
            if placeholder.lower() == 'uniksurveylink':
                value = f'<a href="{value}" class="survey-link">{value}</a>'
            
            content = content.replace(f'[{placeholder}]', value)
        
        # Generate filename
        filename_tag = str(row_dict['filename_tag'])
        filename_tag_clean = filename_tag.replace('/', '_').replace('\\', '_').replace(':', '_')
        filename = f"brakar_opinion_{filename_tag_clean}.pdf"
        pdf_path = os.path.join(output_folder, filename)
        
        # Create PDF using xhtml2pdf
        with open(pdf_path, 'wb') as pdf_file:
            pisa_status = pisa.CreatePDF(
                content.encode('utf-8'),
                dest=pdf_file,
                encoding='utf-8'
            )
        
        if pisa_status.err:
            return {'success': False, 'error': 'xhtml2pdf conversion failed'}
        
        return {'success': True, 'filename': filename}
    
    except Exception as e:
        filename_tag = row_dict.get('filename_tag', 'unknown')
        return {'success': False, 'error': str(e)}

# =============================================================================
# GENERATOR
# =============================================================================

class HTMLPDFGenerator:
    """
    Fast HTML-based PDF generator with parallel processing using xhtml2pdf
    """
    def __init__(self, template_path, lookup, output_folder, required_placeholders, batch_size=2000, num_workers=None):
        """
        Initialize generator

        Parameters:
        -----------
        template_path : str or Path
            Path to Word template
        df : pd.DataFrame
            Preloaded and validated DataFrame
        output_folder : str or Path
            Output folder for PDFs
        required_placeholders : list
            List of required placeholder names (without [])
        batch_size : int
            Number of files to process per batch
        num_workers : int
            Number of parallel workers (default: CPU count - 1)
        """
        self.template_path = str(Path(template_path).resolve())
        self.lookup = lookup  # DataFrame is now passed in directly
        self.output_folder = str(Path(output_folder).resolve())
        self.required_placeholders = required_placeholders
        self.batch_size = batch_size
        self.num_workers = num_workers or max(1, multiprocessing.cpu_count() - 1)

        # Create output folder
        Path(self.output_folder).mkdir(parents=True, exist_ok=True)

        # Cleanup old temp folders
        self.cleanup_temp_folders()

        # Setup logging
        self.setup_logging()

        # Stats
        self.stats = {
            'total': len(lookup),
            'success': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }

    def cleanup_temp_folders(self):
        """Remove old temp folders from previous runs"""
        for folder in Path(self.output_folder).glob("temp_*"):
            if folder.is_dir():
                try:
                    shutil.rmtree(folder)
                except:
                    pass

    def setup_logging(self):
        """Setup logging to file and console"""
        log_filename = os.path.join(
            self.output_folder,
            f'generation_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )

        # Clear any existing handlers
        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Log file created: {log_filename}")

    def process_batch(self, batch_df, batch_num, output_folder):
        """
        Process a batch of files in parallel with worker template caching
        """
        self.logger.info(f"\nProcessing batch {batch_num} ({len(batch_df)} files)...")

        batch_success = 0
        batch_failed = 0

        # Optimize: Workers initialized with template via initializer
        with ProcessPoolExecutor(
            max_workers=self.num_workers,
            initializer=init_worker,
            initargs=(self.template_path,)
        ) as executor:
            # Submit all tasks
            futures = {}
            for idx, row in batch_df.iterrows():
                # Send only necessary data (not the entire row)
                row_dict = {
                    col: row[col]
                    for col in self.required_placeholders + ['filename_tag']
                }

                future = executor.submit(
                    process_single_file_worker,
                    row_dict,
                    output_folder,
                    self.required_placeholders
                )
                futures[future] = row.get('filename_tag', idx)

            # Collect results with progress bar
            with tqdm(total=len(futures), desc=f"Batch {batch_num}") as pbar:
                for future in as_completed(futures):
                    filename_tag = futures[future]
                    try:
                        result = future.result()
                        if result['success']:
                            batch_success += 1
                            self.stats['success'] += 1
                        else:
                            batch_failed += 1
                            self.stats['failed'] += 1
                            self.logger.error(f"Failed {filename_tag}: {result.get('error', 'Unknown')}")
                    except Exception as e:
                        batch_failed += 1
                        self.stats['failed'] += 1
                        self.logger.error(f"Failed {filename_tag}: {str(e)}")
                    finally:
                        pbar.update(1)  # Update progress bar

            self.logger.info(f"Batch {batch_num} complete: {batch_success} success, {batch_failed} failed")
            gc.collect()

            return batch_success, batch_failed

    def generate(self):
        """
        Main generation process
        """
        self.stats['start_time'] = datetime.now()
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Starting PDF Generation (xhtml2pdf + worker caching)")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Template: {self.template_path}")
        self.logger.info(f"Output: {self.output_folder}")
        self.logger.info(f"Batch size: {self.batch_size}")
        self.logger.info(f"Parallel workers: {self.num_workers}")

        # Process in batches
        num_batches = (len(self.lookup) + self.batch_size - 1) // self.batch_size
        for batch_num in range(num_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min((batch_num + 1) * self.batch_size, len(self.lookup))
            batch_df = self.lookup.iloc[start_idx:end_idx]

            self.process_batch(batch_df, batch_num + 1, self.output_folder)

        # Final stats
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"GENERATION COMPLETE")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total files: {self.stats['total']}")
        self.logger.info(f"Successful: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Total time: {duration/60:.1f} minutes")
        self.logger.info(f"{'='*60}")

        return True


# =============================================================================
# MAIN
# =============================================================================


if __name__ == "__main__":

    # Prompt user for input
    user_input = input("Process entire lookup file? (Y or specify number of rows): ").strip().lower()

    if user_input == "y":
        limit_rows = None
        print("\n✅ Processing entire lookup file...")

    elif user_input.isdigit():
        limit_rows = int(user_input)
        print(f"\n✅ Processing {limit_rows} rows")

    else:
        print("\n❌ Invalid input")
        exit(1)

   # Load and validate data
    try:
        lookup_df = load_and_validate_data(
            file_path=LOOKUP_FILE,
            required_columns=PLACEHOLDERS + ['filename_tag'],
            limit_rows = limit_rows
        )
    except ValueError as e:
        print(f"❌ Error loading or validating data: {e}")
        exit(1)

    print(lookup_df)
    print("\n" + "=" * 70)

    generator = HTMLPDFGenerator(
        template_path=TEMPLATE_FILE,
        lookup=lookup_df,
        output_folder=str(OUTPUT_FOLDER),
        required_placeholders=PLACEHOLDERS,
        batch_size=2000,
        num_workers=None  # Auto-detect CPU cores
    )
    generator.generate()

